# Implementation Plan: Intelligent Course Search Engine

This document outlines the detailed plan for building a hybrid search engine that combines precise, logic-based SQL filtering with powerful semantic vector search to answer a wide range of user queries about university courses.

## High-Level Architecture

The system is composed of three main components:

1.  **Upstream LLM (External):** This component is responsible for the initial Natural Language Understanding. It receives a raw user query and transforms it into a structured JSON object, identifying the user's **intent** and extracting key **entities**.
2.  **Application Layer (Python):** This is the core of our system. It acts as a "router" and "normalizer."
    *   It receives the JSON from the LLM.
    *   It **normalizes** the extracted entities (e.g., mapping "maths" to "Mathematics") using a local vector search.
    *   It **routes** the normalized request to the appropriate search function based on the user's intent.
3.  **Database Layer (PostgreSQL + pgvector):** This is our data and search foundation.
    *   It stores all course and eligibility data.
    *   It uses the `pgvector` extension to store embeddings and perform fast semantic and normalization searches.

---

## Phase 1: The Foundation (Database Setup & Data Population)

**Objective:** Prepare the database schema, load all course data from a JSON file, and generate all necessary vector embeddings for search and normalization.

**Scripts:** 
- `create_step6.py` (for data transformation)
- `populate_database.py` (for database population)

### 1.1. Dependencies
Install the required Python libraries:
```bash
pip install psycopg2-binary pgvector sentence-transformers
```

### 1.2. Data Transformation
A preliminary script, `create_step6.py`, is run to process the initial `data/step5.json`. This script transforms the string-based `admission_test_requirement` field into a structured JSON object, `admission_test_requirement_json`, and saves the output as `data/step6.json`. This pre-processing step makes the data easier to load and query in the database.

### 1.3. Database Schema Definition
The `populate_database.py` script will first connect to PostgreSQL and execute the following SQL commands to set up the necessary tables and extensions.

```sql
-- Enable vector and trigram support
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

-- Main table for course information with a vector for semantic search
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL,
    alternate_names TEXT[],
    stream VARCHAR(255),
    course_category VARCHAR(255),
    program_level VARCHAR(10), -- UG, PG, or PhD
    course_description TEXT,
    program_highlights TEXT,
    career_prospects TEXT,
    fees_inr INTEGER,
    admission_eligibility_rules TEXT,
    admission_test_requirement JSONB,
    lateral_entry BOOLEAN DEFAULT FALSE,
    course_embedding VECTOR(384) -- For semantic "discovery" search
);

-- Table for complex, multi-path eligibility rules
CREATE TABLE eligibility_rules (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    qualification VARCHAR(255) NOT NULL,
    min_percentage INTEGER,
    accepted_specializations TEXT[],
    required_subjects TEXT[],
    is_lateral_entry BOOLEAN DEFAULT FALSE,
    notes TEXT
);

-- Tables for high-speed normalization of user input
CREATE TABLE canonical_subjects (
    subject TEXT PRIMARY KEY,
    embedding VECTOR(384)
);

CREATE TABLE canonical_qualifications (
    qualification TEXT PRIMARY KEY,
    embedding VECTOR(384)
);

CREATE TABLE canonical_specializations (
    specialization TEXT PRIMARY KEY,
    embedding VECTOR(384)
);

-- Create an IVFFlat index for efficient vector search on courses
CREATE INDEX ON courses USING ivfflat (course_embedding vector_cosine_ops) WITH (lists = 100);
```

### 1.4. Script Logic (`populate_database.py`)
1.  **Initialization:**
    *   Load the `sentence-transformers` model (`all-MiniLM-L6-v2`).
    *   Establish a connection to the PostgreSQL database.
    *   Execute the schema setup SQL from step 1.3.
2.  **Data Ingestion:**
    *   Read and parse the transformed `data/step6.json` file.
    *   Initialize empty sets to collect unique terms: `unique_subjects = set()`, `unique_qualifications = set()`, `unique_specializations = set()`.
3.  **Processing Loop:**
    *   Iterate through each `course` object in the JSON data.
    *   **Determine Program Level:** Based on the `course_tag_text` or `source_course_name` (e.g., "B.Tech" is UG, "M.Tech" is PG), determine the program level.
    *   **Create Course Document:** Concatenate the text from `source_course_name`, `summary`, `career_prospects`, `why_us`, and `alternate_names` into a single, comprehensive text document.
    *   **Generate Course Embedding:** Use the loaded model to convert this document into a `course_embedding` vector.
    *   **Insert Course:** `INSERT` the course data (name, stream, program_level, etc.) and the new fields (`admission_eligibility_rules`, `admission_test_requirement`, `lateral_entry`) into the `courses` table. Use `RETURNING id` to get the `course_id`.
    *   **Process Eligibility Rules:** For each `rule` in the course's `eligibility_rules` array:
        *   `INSERT` the rule's data into the `eligibility_rules` table, linking it with the `course_id`.
        *   Add the rule's `qualification` to the `unique_qualifications` set.
        *   If `required_subjects` is not null, add all subjects to the `unique_subjects` set.
        *   If `accepted_specializations` is not null, add all specializations to the `unique_specializations` set.
4.  **Populate Normalization Tables:**
    *   Iterate through the `unique_subjects` set. For each subject, generate its embedding and `INSERT` into the `canonical_subjects` table.
    *   Iterate through the `unique_qualifications` set. For each qualification, generate its embedding and `INSERT` into the `canonical_qualifications` table.
    *   Iterate through the `unique_specializations` set. For each specialization, generate its embedding and `INSERT` into the `canonical_specializations` table.
5.  **Completion:** Close the database connection.

**Outcome:** A fully populated database with all data and embeddings, ready for querying.

---

## Phase 2: The Search Engine (Core Logic)

**Objective:** Create a modular set of functions that handle all database interactions for the different types of queries.

**Script:** `search_engine.py`

### 2.1. Function: `find_by_eligibility(criteria)`
*   **Input:** A structured `criteria` dictionary (e.g., `{'qualification': '10+2', 'percentage': 60, 'stream': 'arts'}`).
*   **Logic:**
    *   Dynamically constructs a SQL `SELECT` query based on the keys in the `criteria` dictionary.
    *   Applies a `WHERE` clause for `qualification`.
    *   Applies a `WHERE` clause for `min_percentage <= X`.
    *   Implements the logic for `stream` or `subjects`:
        *   If `stream` is 'arts', add a `WHERE` clause for `required_subjects IS NULL`.
        *   If a specific `subject` is provided, add a `WHERE` clause for `'Subject' = ANY(required_subjects)`.
        *   If a specific `specialization` is provided, add a `WHERE` clause for `'Specialization' = ANY(accepted_specializations)`.
*   **Output:** Returns a list of course name strings.

### 2.2. Function: `find_by_discovery(query_text, model)`
*   **Input:** A user's query string and the loaded sentence transformer model.
*   **Logic:**
    *   Generates a vector embedding from the `query_text`.
    *   Executes a vector search query: `SELECT course_name FROM courses ORDER BY course_embedding <=> %(query_vector)s LIMIT 20;`.
*   **Output:** Returns a ranked list of the top 20 most semantically similar course names.

### 2.3. Function: `get_course_requirements(course_id)`
*   **Input:** A single `course_id`.
*   **Logic:** Executes a simple `SELECT * FROM eligibility_rules WHERE course_id = %s;`.
*   **Output:** Returns a list of dictionaries, where each dictionary represents an eligibility rule.

---

## Phase 3: The Main Application (Router & Normalizer)

**Objective:** Create the main script that simulates receiving LLM output, normalizes the data, routes it to the correct search engine function, and displays the results.

**Script:** `main.py`

### 3.1. Helper Functions
*   **`normalize_term(term, canonical_table, model, db_connection)`:**
    *   A generic function that takes a term (e.g., "maths") and the table to check (`canonical_subjects`).
    *   Generates a vector for the term.
    *   Queries the specified canonical table to find the single closest match.
    *   Returns the canonical string (e.g., "Mathematics").
*   **`find_closest_course(course_name, model, db_connection)`:**
    *   A specialized function that uses the `course_embedding` to find the `course_id` of the most likely course.
    *   Returns the `course_id`.

### 3.2. Main Application Logic
1.  **Initialization:** Load the sentence transformer model and establish a persistent database connection.
2.  **Simulate LLM Input:** For testing, create a sample JSON object representing the LLM's output.
    ```python
    llm_output = {
      "intent": "check_eligibility",
      "percentage": "60%",
      "qualification": "12th",
      "stream": "arts"
    }
    ```
3.  **The Router:** Use an `if/elif/else` block to check the `intent` from the `llm_output`.

    *   **If `intent == 'check_eligibility'`:**
        1.  Create an empty `normalized_criteria` dictionary.
        2.  Iterate through the `llm_output` entities.
        3.  For `qualification`, call `normalize_term` with the `canonical_qualifications` table.
        4.  For `subject`, call `normalize_term` with the `canonical_subjects` table.
        5.  For `specialization`, call `normalize_term` with the `canonical_specializations` table.
        6.  Clean the `percentage` value.
        7.  Call `search_engine.find_by_eligibility(normalized_criteria)`.

    *   **If `intent == 'get_course_requirements'`:**
        1.  Call `find_closest_course()` with the `course_name` from the JSON to get the `course_id`.
        2.  Call `search_engine.get_course_requirements(course_id)`.

    *   **If `intent == 'discovery_search'`:**
        1.  Call `search_engine.find_by_discovery()` with the `query_text` from the JSON.

4.  **Format and Display:** Write simple print functions to display the results from the search engine in a user-friendly format.

---

## Execution Workflow

1.  **Setup:** Install Python dependencies and ensure PostgreSQL is running.
2.  **Transform Data:** Run `python create_step6.py` to generate the structured JSON file.
3.  **Populate:** Run `python populate_database.py` from the terminal. This only needs to be done once per data update.
4.  **Run Application:** Run `python main.py`. The script will process the hard-coded test query and print the results. From here, it can be adapted into a web server (API) or a more interactive CLI.
