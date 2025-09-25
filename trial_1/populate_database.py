import json
import psycopg2
from psycopg2.extras import execute_values, Json
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
MODEL_NAME = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'trial_1' ,'server', 'models', 'all-MiniLM-L6-v2'))
from google import genai
def generate_synonym_map(terms_set: set) -> dict:
    """
    Uses a generative model to create a synonym map for a set of terms.
    """
    if not terms_set:
        return {}



    print(f"Generating synonyms for {len(terms_set)} terms using generative AI...")
    client = genai.Client()
    synonym_map = {}

    for term in terms_set:
        if not term or not isinstance(term, str):
            continue
        try:
            prompt = f"Generate a short, comma-separated list of 2-3 common synonyms or abbreviations for the academic term: '{term}'. For example, for 'Computer Science' you might provide 'CS, CompSci'. Only provide the list itself, with no other text, labels, or explanations."
            response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt
            )
            # Clean up the response
            synonyms_text = response.text.strip()
            if synonyms_text:
                synonyms = [s.strip() for s in synonyms_text.split(',')]
                synonym_map[term] = synonyms
                print(f"  - {term}: {synonyms}")
            else:
                synonym_map[term] = [] # No synonyms found
        except Exception as e:
            print(f"Could not generate synonyms for '{term}': {e}")
            synonym_map[term] = [] # Default to empty list on error
            
    print("Synonym generation complete.")
    return synonym_map

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
        cur.execute("DROP TABLE IF EXISTS synonyms CASCADE;")
        cur.execute("DROP TABLE IF EXISTS canonical_terms CASCADE;")
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
                admission_eligibility_rules TEXT,
                admission_test_requirement JSONB,
                lateral_entry BOOLEAN DEFAULT FALSE,
                placements TEXT,
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
                must_have_subjects TEXT[],
                can_have_subjects TEXT[],
                is_lateral_entry BOOLEAN DEFAULT FALSE,
                notes TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE canonical_terms (
                id SERIAL PRIMARY KEY,
                term TEXT NOT NULL,
                term_type VARCHAR(50) NOT NULL,
                embedding VECTOR(384),
                CONSTRAINT unique_term_type UNIQUE (term, term_type)
            );
        """)
        cur.execute("""
            CREATE TABLE synonyms (
                id SERIAL PRIMARY KEY,
                synonym TEXT NOT NULL,
                canonical_id INTEGER NOT NULL REFERENCES canonical_terms(id) ON DELETE CASCADE
            );
        """)

        # Create indexes for fast search
        cur.execute("CREATE INDEX ON courses USING ivfflat (course_embedding vector_cosine_ops) WITH (lists = 100);")
        cur.execute("CREATE INDEX ON canonical_terms USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);")
        cur.execute("CREATE INDEX ON synonyms (synonym);") # Index for text search on synonyms
        cur.execute("CREATE INDEX ON canonical_terms (term_type);") # Index for filtering by type

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

def populate_canonical_and_synonyms(conn, model, synonym_map, term_type):
    """
    Populates the canonical_terms and synonyms tables from a given map.
    Handles conflicts gracefully by updating and returning existing IDs.
    """
    if not synonym_map:
        print(f"No items to populate for term type '{term_type}'.")
        return

    print(f"Populating canonical terms and synonyms for type: '{term_type}'...")
    
    canonical_terms_to_insert = []
    synonyms_to_insert_map = {}

    for canonical, synonyms in synonym_map.items():
        doc = f"{canonical} {', '.join(synonyms)}"
        embedding = model.encode(doc)
        canonical_terms_to_insert.append((canonical, term_type, embedding))
        synonyms_to_insert_map[canonical] = synonyms

    with conn.cursor() as cur:
        # Use ON CONFLICT to handle duplicates.
        # DO UPDATE is a trick to make RETURNING work for existing rows.
        sql = """
            INSERT INTO canonical_terms (term, term_type, embedding) VALUES %s
            ON CONFLICT (term, term_type) DO UPDATE SET term = EXCLUDED.term
            RETURNING id, term
        """
        inserted_ids = execute_values(
            cur, sql, canonical_terms_to_insert, template=None, page_size=100, fetch=True
        )
        
        term_id_map = {term: term_id for term_id, term in inserted_ids}
        
        synonyms_to_insert = []
        for canonical, synonyms in synonyms_to_insert_map.items():
            if canonical in term_id_map:
                canonical_id = term_id_map[canonical]
                for s in synonyms:
                    synonyms_to_insert.append((s, canonical_id))

        if synonyms_to_insert:
            execute_values(
                cur,
                "INSERT INTO synonyms (synonym, canonical_id) VALUES %s",
                synonyms_to_insert,
                page_size=100
            )
    print(f"Finished populating for '{term_type}'.")


def populate_data(conn, model):
    """Reads data from JSON, generates embeddings, and populates the database."""
    print("Starting data population...")
    
    script_dir = os.path.dirname(__file__)
    json_path = os.path.join(script_dir, '..', 'data', 'step8.json')

    with open(json_path, 'r') as f:
        data = json.load(f)

    unique_subjects = set()
    unique_qualifications = set()
    unique_specializations = set()

    courses_to_insert = []
    
    print(f"Processing {len(data)} courses from JSON file...")
    for course in data:
        alt_names = course.get('alternate_names', [])
        if isinstance(alt_names, str):
            alt_names = [name.strip() for name in alt_names.split(',')]

        placements_text = json.dumps(course.get('placements')) if course.get('placements') else ''

        doc = " ".join(filter(None, [
            course.get('source_course_name', ''), " ".join(alt_names),
            course.get('stream_text', ''), course.get('course_tag_text', ''),
            course.get('summary', ''), course.get('why_us', ''),
            course.get('career_prospects', ''), placements_text,
        ]))
        
        program_level = get_program_level(course.get('source_course_name', ''), course.get('course_tag_text', ''))
        lateral_entry_bool = course.get('lateral_entry', 'No').lower() == 'yes'

        courses_to_insert.append({
            'name': course.get('source_course_name'), 'alt_names': alt_names,
            'stream': course.get('stream_text'), 'category': course.get('course_tag_text'),
            'program_level': program_level, 'desc': course.get('summary'),
            'highlights': course.get('why_us'), 'careers': course.get('career_prospects'),
            'fees': int(course['fees_inr']) if course.get('fees_inr') and course['fees_inr'].isdigit() else None,
            'admission_rules': course.get('eligibility_criteria'),
            'admission_test_req': course.get('admission_test_requirement_json'),
            'lateral_entry': lateral_entry_bool,
            'placements': json.dumps(course.get('placements')) if course.get('placements') else None,
            'doc': doc
        })

        for rule in course.get('eligibility_rules', []):
            if rule.get('qualification'):
                unique_qualifications.add(rule['qualification'])
            if rule.get('must_have_subjects'):
                unique_subjects.update(rule['must_have_subjects'])
            if rule.get('can_have_subjects'):
                unique_subjects.update(rule['can_have_subjects'])
            if rule.get('accepted_specializations'):
                specs = [s for s in rule['accepted_specializations'] if s]
                unique_specializations.update(specs)

    print("Generating embeddings for courses...")
    course_docs = [c['doc'] for c in courses_to_insert]
    course_embeddings = model.encode(course_docs, show_progress_bar=True)

    with conn.cursor() as cur:
        course_data_for_sql = [
            (c['name'], c['alt_names'], c['stream'], c['category'], c['program_level'], c['desc'], 
             c['highlights'], c['careers'], c['fees'], c['admission_rules'], Json(c['admission_test_req']), 
             c['lateral_entry'], c['placements'], emb)
            for c, emb in zip(courses_to_insert, course_embeddings)
        ]
        
        inserted_ids = execute_values(
            cur,
            """INSERT INTO courses (course_name, alternate_names, stream, course_category, program_level, 
                   course_description, program_highlights, career_prospects, fees_inr, 
                   admission_eligibility_rules, admission_test_requirement, lateral_entry, 
                   placements, course_embedding) VALUES %s RETURNING id""",
            course_data_for_sql, fetch=True
        )
        course_id_map = {courses_to_insert[i]['name']: inserted_id[0] for i, inserted_id in enumerate(inserted_ids)}
        print(f"Inserted {len(course_id_map)} courses.")

        rules_to_insert = []
        for course in data:
            course_name = course.get('source_course_name')
            if course_name in course_id_map:
                course_id = course_id_map[course_name]
                for rule in course.get('eligibility_rules', []):
                    rules_to_insert.append((
                        course_id, rule.get('qualification'), rule.get('min_percentage'),
                        rule.get('accepted_specializations'), rule.get('must_have_subjects'),
                        rule.get('can_have_subjects'), rule.get('is_lateral_entry', False), 
                        rule.get('notes')
                    ))
        
        execute_values(
            cur,
            """INSERT INTO eligibility_rules (course_id, qualification, min_percentage, 
               accepted_specializations, must_have_subjects, can_have_subjects, is_lateral_entry, notes) VALUES %s""",
            rules_to_insert
        )
        print(f"Inserted {len(rules_to_insert)} eligibility rules.")

    # --- Populate Canonical and Synonym Tables ---
    DEGREE_SYNONYM_MAP = {
        "10+2": ["12th", "plus two", "senior secondary", "higher secondary", "higher secondary school", "intermediate", "twelfth", "+2"],
        "Diploma": [], "Certificate course": ["certificate"],
        "Graduate": ["graduation", "undergraduate degree"],
        "Bachelor's Degree": ["bachelors degree", "bachelors", "bachelor"],
        "B.C.A": ["bca", "bachelor of computer applications"],
        "B.E./B.Tech": ["be/btech", "be", "btech", "bachelor of engineering", "bachelor of technology"],
        "M. Sc.": ["msc", "m sc", "master of science"],
    }
    populate_canonical_and_synonyms(conn, model, DEGREE_SYNONYM_MAP, 'qualification')

    QUALIFICATION_SYNONYM_MAP = {
        "MCA": ["Master of Computer Applications", "masters in computer applications", "M.C.A."],
        "BA": ["Bachelor of Arts", "bachelors in arts", "B.A."],
        "B.Pharm": ["Bachelor of Pharmacy", "BPharm", "Bachelors in Pharmacy"],
        "LLB": ["Bachelor of Laws", "Legum Baccalaureus", "L.L.B.", "bachelor of legislative law"],
        "BBA/BMS": ["Bachelor of Business Administration", "Bachelor of Management Studies", "B.B.A.", "B.M.S.", "BBA", "BMS"],
        "BA/BBA LLB": ["Bachelor of Arts Bachelor of Laws", "Bachelor of Business Administration Bachelor of Laws", "BA LLB", "BBA LLB", "B.A. L.L.B.", "B.B.A. L.L.B."],
        "MBA/PGDM": ["Master of Business Administration", "Post Graduate Diploma in Management", "M.B.A.", "P.G.D.M.", "MBA", "PGDM"],
        "B.Com": ["Bachelor of Commerce", "bachelors in commerce", "B.Com."],
        "D.El.Ed": ["Diploma in Elementary Education", "D.Ed.", "Diploma in Ed"],
        "ME/M.Tech": ["Master of Engineering", "Master of Technology", "M.E.", "M.Tech", "MTech", "Masters in Technology"],
        "B.Sc": ["bsc", "b sc", "Bachelor of Science", "B.Sc.", "BSc", "Bachelors in Science"],
    }
    populate_canonical_and_synonyms(conn, model, QUALIFICATION_SYNONYM_MAP, 'qualification')

    STREAM_SYNONYM_MAP = {
        "Design": ["Fashion Design", "Apparel Design", "Textile Design", "Dress Design"],
        "Law": ["Legal Studies", "Jurisprudence"], "Mass Communications": ["Journalism", "Media Studies", "Mass Comm"],
        "Computer Applications": ["IT", "Information Technology", "BCA", "MCA", "Graphic Design", "Web Design"],
        "Paramedical": ["Paramedical Science", "Allied Health Sciences"], "Management": ["Business Administration", "BBA", "MBA"],
        "Pharmacy": ["Pharmaceutical Science", "B.Pharm", "D.Pharm"], "Commerce": ["Business", "B.Com", "M.Com"],
        "Engineering": ["Technology", "B.Tech", "M.Tech", "B.E.", "M.E."], "Medical": ["Medicine", "Healthcare", "MBBS"],
    }
    populate_canonical_and_synonyms(conn, model, STREAM_SYNONYM_MAP, 'stream')

    # Generate synonyms for discovered terms and populate them
    generated_subject_map = generate_synonym_map(unique_subjects)
    populate_canonical_and_synonyms(conn, model, generated_subject_map, 'subject')

    generated_specialization_map = generate_synonym_map(unique_specializations)
    populate_canonical_and_synonyms(conn, model, generated_specialization_map, 'specialization')
    

    conn.commit()
    print("Data population complete.")

def main():
    """Main function to run the database population process."""
    print("--- Starting Database Population Script ---")
    
    conn = get_db_connection()
    if conn is None:
        return

    setup_database_schema(conn)
    
    register_vector(conn)
    
    print(f"Loading sentence transformer model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    populate_data(conn, model)
    
    conn.close()
    print("--- Script Finished ---")

if __name__ == "__main__":
    main()
