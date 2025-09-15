import psycopg2
from pgvector.psycopg2 import register_vector

# --- Database Configuration ---
# It's recommended to use environment variables for these in a real application
DB_NAME = "chatbot"
DB_USER = "postgres"
DB_PASS = "1234"
DB_HOST = "localhost"
DB_PORT = "5432"

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
        # IMPORTANT: Register the vector type for this connection
        register_vector(conn)
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to the database: {e}")
        return None

def find_by_eligibility(criteria):
    """
    Finds courses based on a structured criteria dictionary.
    
    Args:
        criteria (dict): A dictionary with keys like 'qualification', 
                         'percentage', 'stream', 'subject', 'specialization'.
    
    Returns:
        list: A list of course names that match the criteria.
    """
    conn = get_db_connection()
    if not conn:
        return ["Error: Could not connect to the database."]

    with conn.cursor() as cur:
        # Start with a base query that joins the tables
        query = """
            SELECT DISTINCT c.course_name
            FROM courses c
            JOIN eligibility_rules er ON c.id = er.course_id
        """
        where_clauses = []
        params = {}

        # --- Dynamically build the WHERE clause ---

        if 'qualification' in criteria:
            where_clauses.append("er.qualification = %(qualification)s")
            params['qualification'] = criteria['qualification']

        if 'percentage' in criteria and criteria['percentage'] is not None:
            where_clauses.append("(er.min_percentage <= %(percentage)s OR er.min_percentage IS NULL)")
            params['percentage'] = criteria['percentage']
            
        if 'subject' in criteria:
            where_clauses.append(" %(subject)s = ANY(er.required_subjects)")
            params['subject'] = criteria['subject']

        if 'specialization' in criteria:
            # This clause handles cases where a rule accepts any specialization
            where_clauses.append("""
                (er.accepted_specializations IS NULL OR 
                 cardinality(er.accepted_specializations) = 0 OR 
                 %(specialization)s = ANY(er.accepted_specializations))
            """)
            params['specialization'] = criteria['specialization']

        # Handle the logical 'stream' constraint
        if 'stream' in criteria and criteria['stream'] == 'arts':
            # An 'arts' student is eligible if there are no specific subject requirements
            where_clauses.append("(er.required_subjects IS NULL OR cardinality(er.required_subjects) = 0)")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY c.course_name;"

        try:
            cur.execute(query, params)
            results = [row[0] for row in cur.fetchall()]
            return results if results else ["No courses found matching your specific eligibility criteria."]
        except Exception as e:
            print(f"An error occurred during eligibility search: {e}")
            return [f"Error during search: {e}"]
        finally:
            conn.close()

def find_by_discovery(query_text, model):
    """
    Finds courses by semantic similarity to a query text.
    
    Args:
        query_text (str): The user's natural language query.
        model: The loaded sentence transformer model.
        
    Returns:
        list: A ranked list of the most relevant course names.
    """
    conn = get_db_connection()
    if not conn:
        return ["Error: Could not connect to the database."]

    with conn.cursor() as cur:
        try:
            # Generate embedding for the user's query
            query_embedding = model.encode(query_text)
            
            # Execute the vector search query
            cur.execute(
                "SELECT course_name, 1 - (course_embedding <=> %s) AS similarity FROM courses ORDER BY similarity DESC LIMIT 20",
                (query_embedding,)
            )
            results = [row[0] for row in cur.fetchall()]
            return results if results else ["No relevant courses found."]
        except Exception as e:
            print(f"An error occurred during discovery search: {e}")
            return [f"Error during search: {e}"]
        finally:
            conn.close()

def get_course_requirements(course_id):
    """
    Retrieves all eligibility rules for a specific course ID.
    
    Args:
        course_id (int): The ID of the course.
        
    Returns:
        list: A list of dictionaries, each representing an eligibility rule.
    """
    conn = get_db_connection()
    if not conn:
        return [{"error": "Could not connect to the database."}]

    with conn.cursor() as cur:
        try:
            cur.execute(
                "SELECT qualification, min_percentage, required_subjects, notes FROM eligibility_rules WHERE course_id = %s",
                (course_id,)
            )
            # Fetch all results and format them as a list of dicts
            results = [
                {
                    "qualification": row[0],
                    "min_percentage": row[1],
                    "required_subjects": row[2],
                    "notes": row[3]
                }
                for row in cur.fetchall()
            ]
            return results if results else [{"info": "No specific requirements found for this course."}]
        except Exception as e:
            print(f"An error occurred while fetching course requirements: {e}")
            return [{"error": f"An error occurred: {e}"}]
        finally:
            conn.close()
