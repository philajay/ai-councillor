import psycopg2
from pgvector.psycopg2 import register_vector
import json

from common.common import LAST_CLIENT_MESSAGE, LAST_DB_RESULTS, remove_json_tags, SEND_INTERMEDIATE_RESULT
import google.genai as genai
from google.genai import types
from google.adk.tools import ToolContext
from google.adk.tools.base_tool import BaseTool
from typing import Optional, Dict
from copy import deepcopy
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Database Configuration ---
# It's recommended to use environment variables for these in a real application
DB_NAME = os.getenv("DB_NAME", "councillor-assistant")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "1234")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")


import asyncio
import threading

TOP_K = 5 
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

def normalize_term(term: str, term_type: str, conn, tenant_id: str) -> str:
    """
    Finds the canonical term for a given user synonym using vector similarity.
    
    Args:
        term (str): The user-provided term (e.g., "maths").
        term_type (str): The type of term to search for (e.g., "subject", "qualification").
        conn: An active database connection.
        tenant_id (str): The ID of the client tenant.
        
    Returns:
        str: The canonical term (e.g., "Mathematics") or the original term if not found.
    """
    if not term:
        return None
    
    with conn.cursor() as cur:
        try:
            model = getModel()
            term_vector = model.encode(term).tolist()
            cur.execute(
                """
                SELECT canonical_term
                FROM synonyms
                WHERE tenant_id = %s AND category = %s
                ORDER BY synonyms_vector <=> %s
                LIMIT 1
                """,
                (tenant_id, term_type, str(term_vector))
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


def _prepare_fts_query(query_text: str) -> str:
    """
    Prepares a query string for PostgreSQL's to_tsquery function.
    - Splits terms by dots or spaces.
    - Joins them with the AND operator (&).
    - Adds a prefix search (':*') to the last term.
    """
    if not query_text:
        return ''
    
    # Special case for "D.Pharmacy"
    if query_text.upper() == 'D.PHARMACY':
        return 'Diploma & in & Pharmacy:*'
    
    # Treat dots as spaces and split into parts
    parts = query_text.replace('.', ' ').split()
    
    if not parts:
        return ''
        
    # Join all parts with '&' and add a prefix match to the last one
    # This handles single-word queries correctly as well.
    processed_query = ' & '.join(parts[:-1])
    if processed_query:
        processed_query += f' & {parts[-1]}:*'
    else:
        processed_query = f'{parts[-1]}:*'
        
    return processed_query




def find_by_discovery(criteria: dict, tenant_id: str):
    """
    Finds courses by semantic similarity.
    Example: 
    1) Show me engg courses. 
    2) What is the placement of the BCA program
    3) Compare BSc and Bca

    Args:
        criteria (dict): 
            Compulsory Keys:         
                query_text (str): The user's natural language query.
                program_level (str): level for which course is being discovered. Must be either UG or PG
                course_stream_type (list[str], optional): A list of program types the user is searching for.

            Optional Keys: 'qualification', 'percentage', 'stream', 'subjects' (list), 'specialization'.
        tenant_id (str): The ID of the client tenant.

    Returns:
        list: A ranked list of the most relevant courses.
    """

    tenant_id = 'cgc_university'
    
    query_text = criteria.get('query_text', criteria.get('topic', ''))
    program_level = criteria.get('program_level')
    course_stream_type = criteria.get('course_stream_type')


    conn = get_db_connection()
    if not conn:
        return [["Error: Could not connect to the database."]]

    # Normalize eligibility criteria first
    criteria = normalize_criteria(criteria, conn, tenant_id)

    with conn.cursor() as cur:
        try:
            query_vector = getModel().encode(query_text).tolist()
            fts_search_term = _prepare_fts_query(query_text)

            base_query = "FROM courses c"
            # Join with eligibility rules only if needed
            if any(k in criteria for k in ['qualification', 'percentage', 'subjects']):
                 base_query += ", jsonb_array_elements(c.eligibility_rules) AS rule"

            # FTS and Vector search CTEs
            fts_cte = f"""
                SELECT c.id, ROW_NUMBER() OVER (ORDER BY ts_rank(c.text_tsv, to_tsquery('english', %(search_term)s)) DESC) as rank
                {base_query}
                WHERE c.tenant_id = %(tenant_id)s AND c.text_tsv @@ to_tsquery('english', %(search_term)s)
            """
            vector_cte = f"""
                SELECT c.id, ROW_NUMBER() OVER (ORDER BY c.text_vector <=> %(query_vector)s ASC) as rank
                {base_query}
                WHERE c.tenant_id = %(tenant_id)s
            """
            
            params = {
                'tenant_id': tenant_id,
                'search_term': fts_search_term,
                'query_vector': str(query_vector)
            }

            # Add filters
            filters = []
            if program_level:
                filters.append("c.level = %(level)s")
                params['level'] = program_level.upper()
            if course_stream_type and isinstance(course_stream_type, list) and len(course_stream_type) > 0:
                categories = [cat for cs in course_stream_type for cat in cs.split('/')]
                filters.append("c.course_category = ANY(%(course_category)s)")
                params['course_category'] = categories

            # Add eligibility filters only if qualification exist
            if 'qualification' in criteria and criteria['qualification']:
                filters.append("rule ->> 'qualification' = %(qualification)s")
                params['qualification'] = criteria['qualification']
                if 'percentage' in criteria and criteria['percentage']:
                    filters.append("((rule ->> 'min_percentage') IS NULL OR (rule ->> 'min_percentage')::int <= %(percentage)s)")
                    params['percentage'] = criteria['percentage']
                if 'subjects' in criteria and criteria['subjects']:
                    filters.append("""((rule -> 'mandatory') IS NULL OR 
                                    jsonb_array_length(rule -> 'mandatory') = 0 OR 
                                    (rule -> 'mandatory') <@ %(subjects)s::jsonb)""")
                    params['subjects'] = json.dumps(criteria['subjects'])
                else:
                    filters.append("( (rule -> 'mandatory') IS NULL OR jsonb_array_length(rule -> 'mandatory') = 0 )")
            
            if filters:
                filter_str = " AND " + " AND ".join(filters)
                fts_cte += filter_str
                vector_cte += filter_str

            fts_cte += " LIMIT 10"
            vector_cte += " ORDER BY c.text_vector <=> %(query_vector)s LIMIT 10"
            
            # Final RRF query remains the same
            sql_query = f"""
                WITH ranked_ids AS (
                    WITH config (k) AS (VALUES (60.0)),
                    fts_results AS ({fts_cte}),
                    vector_results AS ({vector_cte}),
                    combined_results AS (
                        SELECT id, rank FROM fts_results
                        UNION ALL
                        SELECT id, rank FROM vector_results
                    )
                    SELECT
                        cr.id,
                        SUM(1.0 / (config.k + cr.rank)) as rrf_score
                    FROM
                        combined_results cr, config
                    GROUP BY
                        cr.id, config.k
                    ORDER BY
                        rrf_score DESC
                    LIMIT 10
                )
                SELECT
                    c.id,
                    c.structured_data,
                    c.name,
                    c.stream
                FROM
                    courses c
                JOIN
                    ranked_ids ri ON c.id = ri.id
                ORDER BY
                    ri.rrf_score DESC;
            """

            cur.execute(sql_query, params)
            rows = cur.fetchall()

            if not rows or len(rows) == 0:
                return []
            
            header = [desc[0] for desc in cur.description]
            results = [header]
            results.extend([list(row) for row in rows])
            return results
        except Exception as e:
            print(f"An error occurred during discovery search: {e}")
            return [[f"Error during search: {e}"]]
        finally:
            conn.close()




def normalize_criteria(llm_output, conn, tenant_id):
    criteria = {}
    if llm_output.get('qualification'):
        criteria['qualification'] = normalize_term(llm_output['qualification'], 'qualification', conn, tenant_id)
    
    # Handle a list of subjects for subset matching, with a fallback for a single subject.
    if llm_output.get('subjects') and isinstance(llm_output.get('subjects'), list):
        normalized_subjects = [normalize_term(s, 'subject', conn, tenant_id) for s in llm_output['subjects']]
        criteria['subjects'] = normalized_subjects
    elif llm_output.get('subject'): # Fallback for a single subject
        criteria['subjects'] = [normalize_term(llm_output['subject'], 'subject', conn, tenant_id)]

    if llm_output.get('specialization'):
        criteria['specialization'] = normalize_term(llm_output['specialization'], 'specialization', conn, tenant_id)
    if llm_output.get('stream'):
        criteria['stream'] = normalize_term(llm_output['stream'], 'stream', conn, tenant_id)
        
    if 'percentage' in llm_output:
        try:
            criteria['percentage'] = int(str(llm_output['percentage']).replace('%', ''))
        except (ValueError, TypeError):
            criteria['percentage'] = None

    return criteria

def find_by_eligibility(criteria:dict, tenant_id: str) -> list:
    tenant_id = 'cgc_university'
    """
    Call this function to find all the types of courses which user can apply to based on the eligibility critera given by user.
    
    Examples:
        1) What course can I apply to after doing my +2 in arts.

    Args:
        criteria (dict): A dictionary with keys 'qualification', 
                         'percentage', 'stream', 'subjects' (list), 'specialization'.
        tenant_id (str): The ID of the client tenant.
    
    Returns:
        list: A list of course names that match the criteria.
    """
    conn = get_db_connection()
    if not conn:
        return ["Error: Could not connect to the database."]
    
    criteria = normalize_criteria(criteria, conn, tenant_id)


    with conn.cursor() as cur:
        query = """
            SELECT DISTINCT c.course_category
            FROM courses c, jsonb_array_elements(c.eligibility_rules) AS rule
        """
        where_clauses = ["c.tenant_id = %(tenant_id)s"]
        params = {'tenant_id': tenant_id}

        if 'qualification' in criteria and criteria['qualification']:
            where_clauses.append("rule ->> 'qualification' = %(qualification)s")
            params['qualification'] = criteria['qualification']

        if 'percentage' in criteria and criteria['percentage']:
            where_clauses.append("( (rule ->> 'min_percentage') IS NULL OR (rule ->> 'min_percentage')::int <= %(percentage)s )")
            params['percentage'] = criteria['percentage']

        if 'subjects' in criteria and criteria['subjects']:
            # Student must have all subjects in 'mandatory'
            where_clauses.append(
                """( (rule -> 'mandatory') IS NULL OR 
                     jsonb_array_length(rule -> 'mandatory') = 0 OR 
                     (rule -> 'mandatory') <@ %(subjects)s::jsonb )"""
            )
            params['subjects'] = json.dumps(criteria['subjects'])
        else:
            # If student provides no subjects, only match courses with no subject requirements
            where_clauses.append("( (rule -> 'mandatory') IS NULL OR jsonb_array_length(rule -> 'mandatory') = 0 )")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY c.course_category;"

        try:
            cur.execute(query, params)
            rows = cur.fetchall()
            if not rows:
                return ["No courses found matching your specific eligibility criteria."]
            results = [",".join(map(str, row)) for row in rows]
            return results
        except Exception as e:
            print(f"An error occurred during eligibility search: {e}")
            return [f"Error during search: {e}"]
        finally:
            conn.close()




def get_course_details_by_id(course_id: int, tenant_id: str):
    """
    Retrieves course and eligibility details for a specific course ID.

    Args:
        course_id (int): The ID of the course to retrieve.
        tenant_id (str): The ID of the client tenant.

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
                SELECT id, name, text, eligibility_rules
                FROM courses
                WHERE id = %s AND tenant_id = %s;
            """, (course_id, tenant_id))
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


def vector_search(query: str, tenant_id:str):
    """
    Retrieves chunks of text which matches the query. This tool should be used for information regarding
    a) campus/hostel facilites
    b) scholarships 
    c) loans
    d) admissions
    e) sports
    f) venture facilities

    Args:
        query (str): user query
        tenant_id (str): The ID of the client tenant.

    Returns:
        list: A list of strings, where each string returns the chunk of text which matches user query
        similarity score and url from where text was scraped. 
        Returns an error message if the connection fails or the course is not found.
    """

    tenant_id = 'cgc_university'
    # 1. Encode the search query
    model = getModel()
    query_vector = model.encode(query).tolist()
    conn = get_db_connection()
    
    # 2. Construct and run the search query
    with conn.cursor() as cur:
        try:
            sql_query = """
                SELECT
                    chunk_text,
                    1 - (content_vector <=> %s) as similarity,
                    p.url
                FROM
                    content_chunks c
                JOIN
                    scraped_pages p ON c.page_id = p.id
                WHERE
                    c.tenant_id = %s
                ORDER BY
                    similarity DESC
                LIMIT %s;
            """
        
            params = (
                str(query_vector),
                tenant_id,
                TOP_K
            )
        
            cur.execute(sql_query, params)
            rows = cur.fetchall()
            
            if not rows:
                print("  No results found.")
                return
            results = [",".join(map(str, row)) for row in rows]
            return results
        except Exception as e:
            print(f"An error occurred during course detail retrieval: {e}")
            return [f"Error retrieving course details: {e}"]
        finally:
            conn.close()


def modify_course_result(
        tool:BaseTool, args:Dict[str, any], tool_context:ToolContext, 
        tool_response: list
    ) -> Optional[list]:
        
        if not tool.name == "find_by_discovery" or not tool_response or len(tool_response) <= 1:
            try:
                tool_context.state[LAST_DB_RESULTS] = tool_response 
                return tool_response
            except:
                return tool_response
 
        try:
            from google import genai
            client = genai.Client()

            original_header = tool_response[0]
            original_data_rows = tool_response[1:]

            try:
                id_index = original_header.index('id')
                name_index = original_header.index('name')
            except ValueError:
                # If essential columns are missing, return original response
                tool_context.state[LAST_DB_RESULTS] = tool_response
                return tool_response

            # Create a simplified list with only id and name for the LLM prompt
            simplified_list = [['id', 'name']]
            for row in original_data_rows:
                simplified_list.append([row[id_index], row[name_index]])

            prompt = f'''You are given a user question and a list of courses with their IDs and names. Your task is to identify the broader topic from the user's question and then filter the list to return only the courses that are most relevant to that topic.

For example:
User Query: "courses in ai"
Broader Topic: "computers"

User Query: "courses in culinary"
Broader Topic: "Service industry"

Input:
    Question: {tool_context.state.get(LAST_CLIENT_MESSAGE, "")}
    list_of_rows: {simplified_list}

Output:
    Your response must always be a JSON object with two keys: "json" and "explanation".
    - "json": A list containing the filtered courses. The first element must be the header ['id', 'name'].
    - "explanation": A brief explanation of why these courses were selected based on the broader topic.
'''
            
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=prompt,
                    config={
                        "response_mime_type":"application/json"
                    }
                )
                
                llm_response_data = json.loads(response.text)
                llm_filtered_list = llm_response_data.get("json", [])
                
                if not llm_filtered_list or len(llm_filtered_list) <= 1:
                    tool_context.state[LAST_DB_RESULTS] = tool_response
                    return tool_response

                # Extract IDs from the LLM's filtered list
                llm_header = llm_filtered_list[0]
                llm_id_index = llm_header.index('id')
                returned_ids = {row[llm_id_index] for row in llm_filtered_list[1:]}

                # Filter the original tool_response based on the returned IDs
                final_result = [original_header]
                for row in original_data_rows:
                    if row[id_index] in returned_ids:
                        final_result.append(row)
                
                tool_context.state[LAST_DB_RESULTS] = final_result
                tool_context.actions.state_delta[SEND_INTERMEDIATE_RESULT] = f"Almost done! Just a moment while I get the final results ready for you."
                return final_result
            except Exception as ex:
                print(f"Error processing LLM response: {ex}") 
                tool_context.state[LAST_DB_RESULTS] = tool_response 
                return tool_response 
        except Exception as e:
            print(f"An error occurred in modify_course_result: {e}")
            return None