import json
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
from pgvector.psycopg2 import register_vector
import os

# --- Database Configuration ---
DB_NAME = "chatbot"
DB_USER = "postgres"
DB_PASS = "1234"
DB_HOST = "localhost"
DB_PORT = "5432" # Default PostgreSQL port

# --- Model Configuration ---
import os
MODEL_NAME = os.path.join(os.path.dirname(__file__), '..', 'models', 'all-MiniLM-L6-v2')

def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        print("Database connection successful.")
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to the database: {e}")
        print("Please ensure PostgreSQL is running and the connection details are correct.")
        return None

def setup_database_schema(conn):
    """Drops existing tables and creates the new schema."""
    with conn.cursor() as cur:
        print("Setting up database schema...")

        # Drop existing tables in reverse order of dependency
        cur.execute("DROP TABLE IF EXISTS eligibility_rules CASCADE;")
        cur.execute("DROP TABLE IF EXISTS canonical_specializations CASCADE;")
        cur.execute("DROP TABLE IF EXISTS canonical_subjects CASCADE;")
        cur.execute("DROP TABLE IF EXISTS canonical_qualifications CASCADE;")
        cur.execute("DROP TABLE IF EXISTS courses CASCADE;")

        # Enable extensions
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

        # Create tables
        cur.execute("""
            CREATE TABLE courses (
                id SERIAL PRIMARY KEY,
                course_name VARCHAR(255) NOT NULL,
                alternate_names TEXT[],
                stream VARCHAR(255),
                course_category VARCHAR(255),
                program_level VARCHAR(10),
                course_description TEXT,
                program_highlights TEXT,
                career_prospects TEXT,
                fees_inr INTEGER,
                course_embedding VECTOR(384)
            );
        """)
        cur.execute("""
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
        """)
        cur.execute("""
            CREATE TABLE canonical_subjects (
                subject TEXT PRIMARY KEY,
                embedding VECTOR(384)
            );
        """)
        cur.execute("""
            CREATE TABLE canonical_qualifications (
                qualification TEXT PRIMARY KEY,
                embedding VECTOR(384)
            );
        """)
        cur.execute("""
            CREATE TABLE canonical_specializations (
                specialization TEXT PRIMARY KEY,
                embedding VECTOR(384)
            );
        """)

        # Create index for fast vector search
        cur.execute("""
            CREATE INDEX ON courses USING ivfflat (course_embedding vector_cosine_ops) WITH (lists = 100);
        """)
        print("Schema setup complete.")
    conn.commit()

def get_program_level(course_name, course_tag):
    """Determines if a course is Undergraduate (UG) or Postgraduate (PG)."""
    ug_keywords = ['B.Tech', 'BE', 'B.Sc', 'BCA', 'B.Com', 'B.A', 'LL.B', 'BBA', 'B.Optometry', 'D.Pharmacy', 'B.Pharm', 'Bachelor']
    pg_keywords = ['M.Tech', 'ME', 'M.Sc', 'MCA', 'MBA', 'Master']

    # Check both the course name and the tag
    check_string = f"{course_name} {course_tag}".lower()

    for keyword in pg_keywords:
        if keyword.lower() in check_string:
            return 'PG'
    for keyword in ug_keywords:
        if keyword.lower() in check_string:
            return 'UG'
    return 'UG' # Default if no match

def populate_data(conn, model):
    """Reads data from JSON, generates embeddings, and populates the database."""
    print("Starting data population...")
    
    # Correct the path to step5.json relative to the script's location
    script_dir = os.path.dirname(__file__) # Gets the directory where the script is located
    json_path = os.path.join(script_dir, '..', 'data', 'step5.json') # Go up one level, then into data/

    with open(json_path, 'r') as f:
        data = json.load(f)

    unique_subjects = set()
    unique_qualifications = set()
    unique_specializations = set()

    courses_to_insert = []
    all_eligibility_rules = []

    print(f"Processing {len(data)} courses from JSON file...")
    for course in data:

        if course["source_course_name"] == "B.Tech. CE (Civil Engineering)":
            print("halt")

        # 1. Prepare course data and collect unique terms
        alt_names = course.get('alternate_names', [])
        # Handle cases where alternate_names might be a string instead of a list
        if isinstance(alt_names, str):
            alt_names = [name.strip() for name in alt_names.split(',')]

        doc = " ".join(filter(None, [
            course.get('source_course_name', ''),
            " ".join(alt_names),
            course.get('stream_text', ''),
            course.get('course_tag_text', ''),
            course.get('summary', ''),
            course.get('why_us', ''),
            course.get('career_prospects', ''),
        ]))
        
        program_level = get_program_level(course.get('source_course_name', ''), course.get('course_tag_text', ''))

        courses_to_insert.append({
            'name': course.get('source_course_name'),
            'alt_names': alt_names,
            'stream': course.get('stream_text'),
            'category': course.get('course_tag_text'),
            'program_level': program_level,
            'desc': course.get('summary'), # Using summary as description
            'highlights': course.get('why_us'),
            'careers': course.get('career_prospects'),
            'fees': int(course['fees_inr']) if course.get('fees_inr') and course['fees_inr'].isdigit() else None,
            'doc': doc
        })

        for rule in course.get('eligibility_rules', []):
            all_eligibility_rules.append(rule)
            if rule.get('qualification'):
                unique_qualifications.add(rule['qualification'])
            if rule.get('required_subjects'):
                unique_subjects.update(rule['required_subjects'])
            if rule.get('accepted_specializations'):
                # Filter out potential None values from lists
                specs = [s for s in rule['accepted_specializations'] if s]
                unique_specializations.update(specs)

    # 2. Generate embeddings in batches for efficiency
    print("Generating embeddings for courses...")
    course_docs = [c['doc'] for c in courses_to_insert]
    course_embeddings = model.encode(course_docs, show_progress_bar=True)

    # --- DEBUG: Print the forensic science embedding ---
    for i, course in enumerate(courses_to_insert):
        if "Forensic" in course['name']:
            print(f"DEBUG: Embedding for {course['name']}:\n{course_embeddings[i][:10]}...")
    # --- END DEBUG ---

    # 3. Insert courses and get their IDs
    with conn.cursor() as cur:
        course_data_for_sql = [
            (c['name'], c['alt_names'], c['stream'], c['category'], c['program_level'], c['desc'], c['highlights'], c['careers'], c['fees'], emb)
            for c, emb in zip(courses_to_insert, course_embeddings)
        ]
        
        # Use execute_values for efficient batch insertion
        inserted_ids = execute_values(
            cur,
            """INSERT INTO courses (course_name, alternate_names, stream, course_category, program_level, course_description, program_highlights, career_prospects, fees_inr, course_embedding)
               VALUES %s RETURNING id""",
            course_data_for_sql,
            template=None,
            page_size=100,
            fetch=True
        )
        course_id_map = {courses_to_insert[i]['name']: inserted_id[0] for i, inserted_id in enumerate(inserted_ids)}
        print(f"Inserted {len(course_id_map)} courses.")

        # 4. Insert eligibility rules
        # Re-iterate through the original data to map rules to the new course IDs
        rules_to_insert = []
        for course in data:
            course_name = course.get('source_course_name')
            if course_name in course_id_map:
                course_id = course_id_map[course_name]
                for rule in course.get('eligibility_rules', []):
                    rules_to_insert.append((
                        course_id,
                        rule.get('qualification'),
                        rule.get('min_percentage'),
                        rule.get('accepted_specializations'),
                        rule.get('required_subjects'),
                        rule.get('is_lateral_entry', False),
                        rule.get('notes')
                    ))
        
        execute_values(
            cur,
            """INSERT INTO eligibility_rules (course_id, qualification, min_percentage, accepted_specializations, required_subjects, is_lateral_entry, notes)
               VALUES %s""",
            rules_to_insert,
            page_size=100
        )
        print(f"Inserted {len(rules_to_insert)} eligibility rules.")

    # 5. Populate canonical tables
    def populate_canonical_table(table_name, items):
        if not items:
            print(f"No items to populate for {table_name}.")
            return
        print(f"Populating {table_name} with {len(items)} unique items...")
        item_list = list(items)
        embeddings = model.encode(item_list, show_progress_bar=True)
        with conn.cursor() as cur:
            execute_values(
                cur,
                f"INSERT INTO {table_name} (embedding, {table_name.split('_')[1][:-1]}) VALUES %s ON CONFLICT DO NOTHING",
                [(emb, item) for item, emb in zip(item_list, embeddings)],
                template=f"(%s, %s)",
                page_size=100
            )

    populate_canonical_table('canonical_subjects', unique_subjects)
    populate_qualifications_with_synonyms(conn, model, unique_qualifications)
    populate_canonical_table('canonical_specializations', unique_specializations)

    conn.commit()
    print("Data population complete.")

def populate_qualifications_with_synonyms(conn, model, unique_qualifications):
    """
    Populates the canonical_qualifications table by creating embeddings
    from documents enriched with synonyms.
    """
    if not unique_qualifications:
        print("No qualifications to populate.")
        return

    print(f"Populating canonical_qualifications with {len(unique_qualifications)} unique items...")

    # This map defines the synonyms for our canonical terms
    SYNONYM_MAP = {
        "10+2": ["12th", "plus two", "senior secondary", "higher secondary", "higher secondary school", "intermediate", "twelfth", "+2"],
        "Diploma": [],
        "Certificate course": ["certificate"],
        "Graduate": ["graduation", "undergraduate degree"],
        "Bachelor's Degree": ["bachelors degree", "bachelors", "bachelor"],
        "B.C.A": ["bca", "bachelor of computer applications"],
        "B.Sc.": ["bsc", "b sc", "bachelor of science"],
        "B.E./B.Tech": ["be/btech", "be", "btech", "bachelor of engineering", "bachelor of technology"],
        "M. Sc.": ["msc", "m sc", "master of science"],
    }

    items_to_insert = []
    # Ensure all unique qualifications from the data are processed.
    # If a qualification is not in the map, it will be processed with just its own name.
    for qual in unique_qualifications:
        synonyms = SYNONYM_MAP.get(qual, [])
        doc = f"{qual} {', '.join(synonyms)}"
        
        embedding = model.encode(doc)
        items_to_insert.append((embedding, qual))

    with conn.cursor() as cur:
        # The table is dropped on each run, so a simple INSERT is sufficient.
        # Using ON CONFLICT just in case the script is modified to not drop tables.
        execute_values(
            cur,
            "INSERT INTO canonical_qualifications (embedding, qualification) VALUES %s ON CONFLICT (qualification) DO NOTHING",
            items_to_insert,
            template="(%s, %s)",
            page_size=100
        )
    print("Finished populating canonical_qualifications.")

def main():
    """Main function to run the database population process."""
    print("--- Starting Database Population Script ---")
    
    conn = get_db_connection()
    if conn is None:
        return

    setup_database_schema(conn)
    
    # Register the vector type with psycopg2 AFTER the extension is created
    register_vector(conn)
    
    print(f"Loading sentence transformer model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    populate_data(conn, model)
    
    conn.close()
    print("--- Script Finished ---")

if __name__ == "__main__":
    main()
