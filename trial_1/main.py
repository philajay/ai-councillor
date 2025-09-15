import psycopg2
from sentence_transformers import SentenceTransformer
from pgvector.psycopg2 import register_vector

# Import the search functions from our other file
import search_engine

# --- Model Configuration ---
#MODEL_NAME = 'all-MiniLM-L6-v2'
import os
MODEL_NAME = os.path.join(os.path.dirname(__file__), '..', 'models', 'all-MiniLM-L6-v2')

# --- Helper Functions for Normalization ---

def normalize_term(term, canonical_table, model, conn):
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

def find_closest_course(course_name, model, conn):
    """
    Finds the single closest course ID for a given course name.
    
    Args:
        course_name (str): The user-provided course name.
        model: The loaded sentence transformer model.
        conn: An active database connection.
        
    Returns:
        int: The ID of the closest matching course.
    """
    if not course_name:
        return None
        
    with conn.cursor() as cur:
        try:
            embedding = model.encode(course_name)
            cur.execute(
                "SELECT id FROM courses ORDER BY 1 - (course_embedding <=> %s) DESC LIMIT 1",
                (embedding,)
            )
            result = cur.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"Error finding closest course for '{course_name}': {e}")
            return None

# --- Main Application Logic ---

def process_query(llm_output, model, conn):
    """
    Processes the structured output from an LLM, normalizes it,
    and routes it to the correct search engine function.
    """
    intent = llm_output.get("intent")
    
    if intent == "check_eligibility":
        print("\n--- Intent: Check Eligibility ---")
        criteria = {}
        # Normalize each entity before adding to the final criteria
        if 'qualification' in llm_output:
            criteria['qualification'] = normalize_term(llm_output['qualification'], 'canonical_qualifications', model, conn)
        if 'subject' in llm_output:
            criteria['subject'] = normalize_term(llm_output['subject'], 'canonical_subjects', model, conn)
        if 'specialization' in llm_output:
            criteria['specialization'] = normalize_term(llm_output['specialization'], 'canonical_specializations', model, conn)
        if 'percentage' in llm_output:
            # Clean percentage value
            try:
                criteria['percentage'] = int(str(llm_output['percentage']).replace('%', ''))
            except (ValueError, TypeError):
                criteria['percentage'] = None
        if 'stream' in llm_output:
            criteria['stream'] = llm_output['stream']

        print(f"Normalized Criteria: {criteria}")
        results = search_engine.find_by_eligibility(criteria)
        return results

    elif intent == "get_course_requirements":
        print("\n--- Intent: Get Course Requirements ---")
        course_name = llm_output.get("course_name")
        print(f"Searching for course similar to: '{course_name}'")
        course_id = find_closest_course(course_name, model, conn)
        
        if course_id:
            print(f"Found matching course with ID: {course_id}")
            results = search_engine.get_course_requirements(course_id)
            return results
        else:
            return ["Could not find a matching course."]

    elif intent == "discovery_search":
        print("\n--- Intent: Discovery Search ---")
        query_text = llm_output.get("query_text")
        print(f"Searching for courses related to: '{query_text}'")
        results = search_engine.find_by_discovery(query_text, model)
        return results
        
    else:
        return ["Unknown intent provided by LLM."]

def main():
    """
    Main function to initialize the application and run test queries.
    """
    print("--- Initializing Search Application ---")
    
    # Load the model once
    print(f"Loading sentence transformer model: {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)
    
    # Establish a single connection to be used by normalization functions
    conn = search_engine.get_db_connection()
    if not conn:
        print("Application cannot start without a database connection.")
        return

    # --- Test Queries (Simulating LLM Output) ---

    # Test Case 1: Eligibility Query with synonyms
    query1 = {
      "intent": "check_eligibility",
      "percentage": "60%",
      "qualification": "+12th",
      "stream": "arts"
    }
    
    # Test Case 2: Discovery Query
    query2 = {
        "intent": "discovery_search",
        "query_text": "courses about business and marketing"
    }

    # Test Case 3: Get Requirements for a specific course
    query3 = {
        "intent": "get_course_requirements",
        "course_name": "B.Sc. forensic"
    }

    # Test Case 4: Eligibility with a specific subject synonym
    query4 = {
        "intent": "check_eligibility",
        "qualification": "+2",
        "subject": "maths"
    }

    # Test Case 5: More specific discovery search
    query5 = {
        "intent": "discovery_search",
        "query_text": "courses about forensic science and investigation"
    }

    # Test Case 6: Eligibility with a synonym from the map
    query6 = {
        "intent": "check_eligibility",
        "qualification": "higher secondary school",
        "percentage": "50"
    }

    

    test_queries = [query1, query2, query3, query4, query5, query6]

    for i, query in enumerate(test_queries):
        print(f"\n==================\nExecuting Test Query {i+1}\n==================")
        print(f"LLM Output: {query}")
        results = process_query(query, model, conn)
        
        print("\n--- Results ---")
        if isinstance(results, list):
            for item in results:
                print(item)
        else:
            print(results)

    # Close the connection at the end
    conn.close()
    print("\n--- Application Finished ---")


if __name__ == "__main__":
    main()
