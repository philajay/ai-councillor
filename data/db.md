# University Course Catalog: Database Schema

This document outlines the complete database schema for the university course catalog, designed to be robust, flexible, and performant. It has been updated to handle complex, multi-faceted eligibility criteria.

### `CREATE TABLE` Statements

```sql
-- Enable the trigram extension for fuzzy string matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- The main table for storing core course information
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL,
    alternate_names TEXT[],           -- For search synonyms (e.g., "BA in Media Studies")

    -- Classification
    stream VARCHAR(255),              -- e.g., 'Engineering', 'Management'
    course_category VARCHAR(255),     -- e.g., 'BE/B.Tech', 'BCA'

    -- Course Content
    course_description TEXT,
    program_highlights TEXT,          -- The 'Why Us' section for marketing
    career_prospects TEXT,            -- Detailed career opportunities after the course

    -- Non-academic requirements
    test_requirements JSONB,          -- Array of structured test objects, e.g., [{"name": "CGCUET", "admission": true, "scholarship": true}]

    -- Financials
    fees_inr INTEGER,                 -- Fee in INR

    -- Full-Text Search Vector
    course_tsv tsvector
);

-- A separate table to handle complex academic eligibility rules.
-- One course can have multiple eligibility paths (e.g., 10+2 OR a Diploma).
CREATE TABLE eligibility_rules (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,

    -- Core academic requirements
    qualification VARCHAR(255) NOT NULL,    -- e.g., '10+2', 'Diploma', 'B.E./B.Tech'
    min_percentage INTEGER,

    -- Specializations and Subjects
    accepted_specializations TEXT[],      -- e.g., {'CSE', 'IT', 'Electronics'}. If NULL or empty, any specialization is valid.
    required_subjects TEXT[],             -- e.g., {'Physics', 'Maths'}

    -- Flags and Notes
    is_lateral_entry BOOLEAN DEFAULT FALSE, -- True if this rule is for lateral entry
    notes TEXT                            -- For extra unstructured info (e.g., "Requires 2 years IT experience")
);


-- GIN index for fast full-text search on courses
CREATE INDEX courses_tsv_idx ON courses USING GIN(course_tsv);

-- Define and create the function for the trigger
CREATE OR REPLACE FUNCTION update_courses_tsv()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.course_tsv :=
            to_tsvector('english', COALESCE(NEW.course_name, '')) ||
            to_tsvector('english', COALESCE(NEW.course_description, '')) ||
            to_tsvector('english', COALESCE(NEW.program_highlights, '')) ||
            to_tsvector('english', COALESCE(NEW.career_prospects, ''));
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
CREATE TRIGGER courses_tsv_update
BEFORE INSERT OR UPDATE ON courses
FOR EACH ROW EXECUTE FUNCTION update_courses_tsv();

-- === Trigram Indexes for Fuzzy String Matching ===
-- These indexes use the pg_trgm extension to provide fast, efficient fuzzy searching,
-- making the application resilient to typos, abbreviations, and other data inconsistencies.

-- For single text columns, we use 'gin_trgm_ops'
CREATE INDEX courses_name_trgm_idx ON courses USING GIN (course_name gin_trgm_ops);
CREATE INDEX courses_stream_trgm_idx ON courses USING GIN (stream gin_trgm_ops);
CREATE INDEX courses_category_trgm_idx ON courses USING GIN (course_category gin_trgm_ops);
CREATE INDEX eligibility_qualification_trgm_idx ON eligibility_rules USING GIN (qualification gin_trgm_ops);

-- For text array columns, we use the default GIN index.
-- This indexes each element in the array, allowing for fast fuzzy searching within the arrays.
CREATE INDEX courses_alt_names_trgm_idx ON courses USING GIN (alternate_names);
CREATE INDEX eligibility_specializations_trgm_idx ON eligibility_rules USING GIN (accepted_specializations);
CREATE INDEX eligibility_subjects_trgm_idx ON eligibility_rules USING GIN (required_subjects);


```

---

### Design Rationale

#### 1. Decoupling Eligibility from Courses

The primary design change is the separation of academic eligibility into its own `eligibility_rules` table. Raw eligibility criteria are often complex and contain multiple independent conditions (e.g., "A student is eligible if they have a 10+2 with PCM **OR** if they have a 3-year Diploma").

-   **One-to-Many Relationship**: A single course in the `courses` table can have multiple corresponding rows in `eligibility_rules`. Each row represents one complete, distinct path to eligibility.
-   **Clarity and Queryability**: This structure allows us to store each rule's specific requirements (qualification, percentage, specializations) in a structured way, making it easy to write precise SQL queries.

#### 2. Handling "Catch-All" and Specific Specializations

The `accepted_specializations TEXT[]` column is key to handling requirements for degrees like B.Tech or M.Tech.

-   **Specific Rules**: If a course requires a B.Tech in 'CSE' or 'IT', the array would contain `{'CSE', 'IT'}`. A query can then efficiently check if a student's specialization is in this list.
-   **"Catch-All" Rules**: If a course accepts a B.Tech from **any** branch, the `accepted_specializations` column for that rule will be `NULL` or empty. This is an explicit, queryable way to represent a generic requirement, preventing the need for fuzzy text matching on a notes field.

#### 3. `JSONB` for Test Requirements

While academic eligibility is now relational, `test_requirements` remains `JSONB` in the `courses` table. This is because it represents a different kind of data—structured, key-value information about specific tests and their purpose (admission vs. scholarship), which is a perfect use case for `JSONB`.

#### 4. Full-Text and Trigram Search

The `courses` table retains its powerful search capabilities on `course_name` and the composite `course_tsv` vector, ensuring users can easily find courses by name, description, or career outcome, regardless of the eligibility logic.

#### 5. Resilience with Fuzzy Search

Real-world data is often inconsistent, containing typos ("Enginering"), abbreviations ("Mech Engg"), or variations ("B.Tech" vs. "B.E."). To handle this, we've added GIN trigram indexes (`gin_trgm_ops`) to several key text and text array fields:
- `courses`: `course_name`, `alternate_names`, `stream`, `course_category`
- `eligibility_rules`: `qualification`, `accepted_specializations`, `required_subjects`

These indexes allow for extremely fast and efficient "fuzzy" searching. This makes the application's search and filtering features far more robust and user-friendly, as it can deliver accurate results even when the user's input doesn't exactly match the stored data. This is powered by the `pg_trgm` PostgreSQL extension.