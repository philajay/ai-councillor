import re
import json


def remove_json_tags(llm_output_str: str) -> str:
    """
    Cleans a string from an LLM to extract a valid JSON object.

    This function handles cases where the LLM might wrap the JSON in
    markdown-style code blocks (e.g., ```json ... ```) or add
    extra text, newlines, or control characters before or after the
    actual JSON content.

    Args:
        llm_output_str: The raw string output from the language model.

    Returns:
        A clean string that should be parsable as JSON.
        Returns an empty JSON object string '{}' if no JSON is found.
    """
    if not isinstance(llm_output_str, str):
        return '{}'

    # Find the start of the JSON object
    start_brace_index = llm_output_str.find('{')
    if start_brace_index == -1:
        return '{}'

    # Find the end of the JSON object
    end_brace_index = llm_output_str.rfind('}')
    if end_brace_index == -1:
        return '{}'

    # Extract the potential JSON string
    json_str = llm_output_str[start_brace_index : end_brace_index + 1]

    # Clean up common control characters that might invalidate JSON
    # This removes characters like \n, \t, \r within the string values
    # by replacing them with their escaped versions.
    json_str = json_str.replace('\\', '\\\\') # Escape backslashes first
    json_str = json_str.replace('"', '\"')
    json_str = json_str.replace('\n', '\\n')
    json_str = json_str.replace('\t', '\\t')
    json_str = json_str.replace('\r', '\\r')


    # A more robust way to handle internal quotes and newlines is to
    # attempt parsing and cleaning iteratively. However, the above slice
    # is generally the most reliable first step. Let's try to validate.
    try:
        # Reloading it ensures it's valid JSON format
        parsed_json = json.loads(llm_output_str[start_brace_index : end_brace_index + 1])
        return json.dumps(parsed_json)
    except json.JSONDecodeError:
        # If the direct slice fails, it might be due to nested text or noise.
        # The initial substring extraction is often the best bet.
        # A simple regex can also be a good fallback.
        match = re.search(r'\{.*\}', llm_output_str, re.DOTALL)
        if match:
            return match.group(0)
        return '{}' # Return empty JSON if all else fails
    
EXTRACTED_ENTITY = "extracted_entity"
DB_RESULTS = "db_results"
GIST_OUTPUT_KEY = "turn_gist"
NEXT_AGENT = "next_agent"
SHOW_SUGGESTED_QUESTIONS = "show_suggested_questions"


async def update_session_state(key, value, session, session_service):
    from google.adk.events import Event, EventActions
    import time
    current_time = time.time()
    state_changes = {
        key: value
    }

    # --- Create Event with Actions ---
    actions_with_update = EventActions(state_delta=state_changes)
    # This event might represent an internal system action, not just an agent response
    system_event = Event(
        invocation_id="session_update",
        author="system", # Or 'agent', 'tool' etc.
        actions=actions_with_update,
        timestamp=current_time
    )

    # --- Append the Event (This updates the state) ---
    await session_service.append_event(session, system_event)
