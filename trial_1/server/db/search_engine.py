import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer


import google.genai as genai
from google.genai import types
from google.adk.tools import ToolContext
from google.adk.tools.base_tool import BaseTool
from typing import Optional, Dict
from copy import deepcopy

# --- Database Configuration ---
# It's recommended to use environment variables for these in a real application
DB_NAME = "chatbot"
DB_USER = "postgres"
DB_PASS = "1234"
DB_HOST = "localhost"
DB_PORT = "5432"


import os
MODEL_NAME = os.path.join('/Users/ajay/2.0/cu/scraper/models', 'all-MiniLM-L6-v2')
model = SentenceTransformer(MODEL_NAME)

def normalize_term(term, canonical_table, conn):
    """
    Finds the closest canonical term for a given user term using vector search.
    
    Args:
        term (str): The user-provided term (e.g., "maths").
        canonical_table (str): The name of the canonical table to search 
                               (e.g., "canonical_subjects").
        model: The loaded sentence transformer model.
        conn: An active database connection.
        
    Returns:
        str: The closest canonical term (e.g., "Mathematics").
    """
    if not term:
        return None
    
    with conn.cursor() as cur:
        try:
            term_embedding = model.encode(term)
            
            # Dynamically get the column name from the table name
            column_name = canonical_table.split('_')[1][:-1] # subjects -> subject
            
            cur.execute(
                f"SELECT {column_name} FROM {canonical_table} ORDER BY embedding <=> %s LIMIT 1",
                (term_embedding,)
            )
            result = cur.fetchone()
            return result[0] if result else term # Return original term if no match
        except Exception as e:
            print(f"Error normalizing term '{term}' in table '{canonical_table}': {e}")
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


def find_by_discovery(query_text:str, program_level:str):
    """
    Finds courses by semantic similarity to a query text.
    
    Args:
        query_text (str): The user's natural language query.
        program_leve (str): level for which course is being didcovered. Must be either ug or pg
    Returns:
        list: A ranked list of the most relevant course names.
    """
    conn = get_db_connection()
    if not conn:
        return ["Error: Could not connect to the database."]

    pl = program_level.upper()

    with conn.cursor() as cur:
        try:
            # Generate embedding for the user's query
            query_embedding = model.encode(query_text)
            
            pl = program_level.upper()
            # Execute the vector search query
            cur.execute(
                f'''SELECT id, course_name, course_description, career_prospects, program_highlights, 1 - (course_embedding <=> %s) AS similarity FROM courses 
                where program_level = '{pl}'
                ORDER BY similarity DESC LIMIT 10''',
                (query_embedding,)
            )
            results = [",".join(map(str, row)) for row in cur.fetchall()]
            return results if results else ["No relevant courses found."]
        except Exception as e:
            print(f"An error occurred during discovery search: {e}")
            return [f"Error during search: {e}"]
        finally:
            conn.close()




def normalize_criteria(llm_output, conn):
    criteria = {}
    if 'qualification' in llm_output:
            criteria['qualification'] = normalize_term(llm_output['qualification'], 'canonical_qualifications',conn)
    if 'subject' in llm_output:
        criteria['subject'] = normalize_term(llm_output['subject'], 'canonical_subjects', conn)
    if 'specialization' in llm_output:
        criteria['specialization'] = normalize_term(llm_output['specialization'], 'canonical_specializations',  conn)
    if 'percentage' in llm_output:
        # Clean percentage value
        try:
            criteria['percentage'] = int(str(llm_output['percentage']).replace('%', ''))
        except (ValueError, TypeError):
            criteria['percentage'] = None
    if 'stream' in llm_output:
        criteria['stream'] = llm_output['stream']

    return criteria

def find_by_eligibility(criteria:dict) -> list:
    """
    Finds courses based on a structured criteria dictionary.
    
    Args:
        criteria (dict): A dictionary with keys 'qualification', 
                         'percentage', 'stream', 'subject', 'specialization'.
    
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
            SELECT DISTINCT c.id, c.course_name, c.course_description, 
            c.career_prospects, c.program_highlights, er.qualification,
            er.min_percentage, er.accepted_specializations, er.required_subjects,
            er.notes
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
            where_clauses.append("( %(subject)s = ANY(er.required_subjects) OR er.required_subjects IS NULL OR cardinality(er.required_subjects) = 0)")
            params['subject'] = criteria['subject']
        else:
            where_clauses.append("(er.required_subjects IS NULL OR cardinality(er.required_subjects) = 0)")

        if 'specialization' in criteria:
            # This clause handles cases where a rule accepts any specialization
            where_clauses.append("""
                (er.accepted_specializations IS NULL OR 
                 cardinality(er.accepted_specializations) = 0 OR 
                 %(specialization)s = ANY(er.accepted_specializations))
            """)
            params['specialization'] = criteria['specialization']

        # Always get courses which has no requirements
        where_clauses.append("(er.required_subjects IS NULL OR cardinality(er.required_subjects) = 0)")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY c.course_name;"

        try:
            cur.execute(query, params)
            results = [",".join(map(str, row)) for row in cur.fetchall()]
            return results if results else ["No courses found matching your specific eligibility criteria."]
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
            results = [",".join(map(str, row)) for row in cur.fetchall()]
            return results if results else [f"No course found with ID: {course_id}"]
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