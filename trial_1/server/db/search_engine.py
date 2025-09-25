import psycopg2
from pgvector.psycopg2 import register_vector


import google.genai as genai
from google.genai import types
from google.adk.tools import ToolContext
from google.adk.tools.base_tool import BaseTool
from typing import Optional, Dict
from copy import deepcopy
import os
# --- Database Configuration ---
# It's recommended to use environment variables for these in a real application
DB_NAME = "chatbot"
DB_USER = "postgres"
DB_PASS = '1234'
DB_HOST = 'localhost'
DB_PORT = "5432"


import asyncio
import threading

model = None
model_lock = threading.Lock()

def getModel():
    global model
    if model:
        return model
    
    with model_lock:
        if model:
            return model
            
        from sentence_transformers import SentenceTransformer
        import os
        # Get the absolute path to the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # The model is in the 'models' directory, a sibling to the 'db' directory
        model_path = os.path.join(script_dir, '..', 'models', 'all-MiniLM-L6-v2')
        # Normalize the path to resolve '..' components
        MODEL_NAME = os.path.normpath(model_path)
        model = SentenceTransformer(MODEL_NAME, device='cpu')
        print("********** Model loaded ************")
    return model

async def load_model_async(app_state):
    """Asynchronously loads the sentence transformer model."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, getModel)
    app_state.is_model_loaded = True
    print("********** Model loading complete. Bot is ready. ************")

def normalize_term(term: str, term_type: str, conn) -> str:
    """
    Finds the closest canonical term for a given user term using vector search.
    
    Args:
        term (str): The user-provided term (e.g., "maths").
        term_type (str): The type of term to search for (e.g., "subject", "qualification").
        conn: An active database connection.
        
    Returns:
        str: The closest canonical term (e.g., "Mathematics").
    """
    if not term:
        return None
    
    with conn.cursor() as cur:
        try:
            term_embedding = getModel().encode(term)
            
            cur.execute(
                """
                SELECT term 
                FROM canonical_terms 
                WHERE term_type = %s 
                ORDER BY embedding <=> %s 
                LIMIT 1
                """,
                (term_type, term_embedding)
            )
            result = cur.fetchone()
            return result[0] if result else term # Return original term if no match
        except Exception as e:
            print(f"Error normalizing term '{term}' of type '{term_type}': {e}")
            return term # Fallback to original term on error


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


def find_by_discovery(query_text: str, program_level: str, course_stream_type: str = None):
    """
    Finds courses by semantic similarity to a query text.

    Args:
        query_text (str): The user's natural language query.
        program_level (str): level for which course is being discovered. Must be either ug or pg
        course_stream_type (str, optional): The program type user is searching for, e.g., BE/Btech, bsc. Defaults to None.
    Returns:
        list: A ranked list of the most relevant course names.
    """
    conn = get_db_connection()
    if not conn:
        return ["Error: Could not connect to the database."]

    with conn.cursor() as cur:
        try:
            # Generate embedding for the user's query
            query_embedding = getModel().encode(query_text)

            # Base query and parameters
            query = """
                SELECT id, course_name, course_description,
                       career_prospects, program_highlights,
                       admission_eligibility_rules, admission_test_requirement, lateral_entry,
                       placements,
                       1 - (course_embedding <=> %s) AS similarity
                FROM courses
                WHERE program_level = %s
            """
            params = [query_embedding, program_level.upper()]

            # Conditionally add the course_category filter
            if course_stream_type:
                query += " AND course_category = %s"
                params.append(course_stream_type)

            # Add ordering and limit
            query += " ORDER BY similarity DESC"

            # Execute the query
            cur.execute(query, tuple(params))

            rows = cur.fetchall()
            if not rows:
                return ["No relevant courses found."]
            
            # Exclude the last column ('similarity') from the header and results
            header = ",".join([desc[0] for desc in cur.description[:-1]])
            results = [header]
            results.extend([",".join(map(str, row[:-1])) for row in rows])
            return results
        except Exception as e:
            print(f"An error occurred during discovery search: {e}")
            return [f"Error during search: {e}"]
        finally:
            conn.close()




def normalize_criteria(llm_output, conn):
    criteria = {}
    if llm_output.get('qualification'):
        criteria['qualification'] = normalize_term(llm_output['qualification'], 'qualification', conn)
    
    # Handle a list of subjects for subset matching, with a fallback for a single subject.
    if llm_output.get('subjects') and isinstance(llm_output.get('subjects'), list):
        normalized_subjects = [normalize_term(s, 'subject', conn) for s in llm_output['subjects']]
        criteria['subjects'] = normalized_subjects
    elif llm_output.get('subject'): # Fallback for a single subject
        criteria['subjects'] = [normalize_term(llm_output['subject'], 'subject', conn)]

    if llm_output.get('specialization'):
        criteria['specialization'] = normalize_term(llm_output['specialization'], 'specialization', conn)
    if llm_output.get('stream'):
        criteria['stream'] = normalize_term(llm_output['stream'], 'stream', conn)
        
    if 'percentage' in llm_output:
        try:
            criteria['percentage'] = int(str(llm_output['percentage']).replace('%', ''))
        except (ValueError, TypeError):
            criteria['percentage'] = None

    return criteria

def find_by_eligibility(criteria:dict) -> list:
    """
    Finds courses based on a structured criteria dictionary.
    
    Args:
        criteria (dict): A dictionary with keys 'qualification', 
                         'percentage', 'stream', 'subjects' (list), 'specialization'.
    
    Returns:
        list: A list of course names that match the criteria.
    """
    conn = get_db_connection()
    if not conn:
        return ["Error: Could not connect to the database."]
    
    criteria = normalize_criteria(criteria, conn)

    with conn.cursor() as cur:
        # Start with a base query that joins the tables
        query = """
            SELECT DISTINCT c.course_category
            FROM courses c
            JOIN eligibility_rules er ON c.id = er.course_id
        """
        where_clauses = []
        params = {}

        # --- Dynamically build the WHERE clause ---

        if 'qualification' in criteria and criteria['qualification']:
            addGraduation = ["Diploma", "10+2"]
            if not criteria['qualification'] in addGraduation:
                where_clauses.append("(er.qualification = %(qualification)s or er.qualification = 'Graduate')")     
                params['qualification'] = criteria['qualification']
            else:
                where_clauses.append("er.qualification = %(qualification)s")
                params['qualification'] = criteria['qualification']
            

        if 'percentage' in criteria and criteria['percentage']:
            where_clauses.append("(er.min_percentage <= %(percentage)s OR er.min_percentage IS NULL)")
            params['percentage'] = criteria['percentage']
            
        # Use subset matching for subjects. The course's required subjects must be
        # a subset of (be contained by) the subjects the student has taken.
        if 'subjects' in criteria and criteria['subjects']:
            where_clauses.append("(er.required_subjects @> %(subjects)s OR er.required_subjects IS NULL OR cardinality(er.required_subjects) = 0)")
            params['subjects'] = criteria['subjects']
        else:
            # If no student subjects are provided, only match courses that have no subject requirements.
            where_clauses.append("(er.required_subjects IS NULL OR cardinality(er.required_subjects) = 0)")

        if 'specialization' in criteria and criteria['specialization']:
            # This clause handles cases where a rule accepts any specialization
            where_clauses.append("""
                (er.accepted_specializations IS NULL OR 
                 cardinality(er.accepted_specializations) = 0 OR 
                 %(specialization)s = ANY(er.accepted_specializations))
            """)
            params['specialization'] = criteria['specialization']

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY c.course_category;"

        try:
            cur.execute(query, params)
            rows = cur.fetchall()
            if not rows:
                return ["No courses found matching your specific eligibility criteria."]
            results = []
            results.extend([",".join(map(str, row)) for row in rows])
            s = len(''.join(results))
            print(f"length of results is {s}")
            return results
        except Exception as e:
            print(f"An error occurred during eligibility search: {e}")
            return [f"Error during search: {e}"]
        finally:
            conn.close()




def get_course_details_by_id(course_id: int):
    """
    Retrieves course and eligibility details for a specific course ID.

    Args:
        course_id (int): The ID of the course to retrieve.

    Returns:
        list: A list of strings, where each string contains the comma-separated
              details of a course and its eligibility rules. Returns an error
              message if the connection fails or the course is not found.
    """
    conn = get_db_connection()
    if not conn:
        return ["Error: Could not connect to the database."]

    with conn.cursor() as cur:
        try:
            cur.execute("""
                SELECT c.id, c.course_name, c.course_description, c.career_prospects,
                       c.program_highlights, er.qualification, er.min_percentage,
                       er.accepted_specializations, er.required_subjects, er.notes
                FROM courses c
                LEFT JOIN eligibility_rules er ON c.id = er.course_id
                WHERE c.id = %s;
            """, (course_id,))
            rows = cur.fetchall()
            if not rows:
                return [f"No course found with ID: {course_id}"]
            header = ",".join([desc[0] for desc in cur.description])
            results = [header]
            results.extend([",".join(map(str, row)) for row in rows])
            return results
        except Exception as e:
            print(f"An error occurred during course detail retrieval: {e}")
            return [f"Error retrieving course details: {e}"]
        finally:
            conn.close()


def modify_course_result(
        tool:BaseExceptionGroup, args:Dict[str, any], tool_context:ToolContext, 
        tool_response: Dict
    ) -> Optional[Dict]:
        try:
            # Add it to state so that we can reterive it to send to client in live_adk
            tool_context.state["last_db_results"] = tool_response 
        except:
            return None