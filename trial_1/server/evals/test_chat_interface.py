import asyncio
from httpx import AsyncClient
from httpx_sse import aconnect_sse
import json
import uuid
import re
import operator
import os

# Mark all tests in this file as asyncio tests
#pytestmark = pytest.mark.asyncio

async def test_chat_endpoint():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_cases_path = os.path.join(script_dir, 'test_cases.json')
    with open(test_cases_path, 'r') as f:
        test_cases = json.load(f)

    ops = {
        "<": operator.lt,
        "<=": operator.le,
        "==": operator.eq,
        "!=": operator.ne,
        ">=": operator.ge,
        ">": operator.gt
    }

    all_errors = []

    for test_case in test_cases:
        session_id = str(uuid.uuid4())
        errors = []
        
        query_1 = test_case['query_1']
        match = re.search(r'in ([\w\s]+)\.', query_1)
        expected_stream = match.group(1) if match else None
        
        async with AsyncClient(base_url="http://127.0.0.1:8080", timeout=60.0) as client:
            # First call
            print(f"\n--- Running test for query: {query_1} ---")
            json_data = {
                "text": query_1,
                "sessionId": session_id,
                "courseLevel": "UG"
            }
            async with aconnect_sse(client, "POST", "/chat", json=json_data) as event_source:
                events = [json.loads(event.data) async for event in event_source.aiter_sse()]
                events = [e for e in events if "endOfTurn" not in e]
                print("--- Events from first call ---")
                for event in events:
                    if not event.get("action") == "functionCall":
                        print(json.dumps(event, indent=2))
                print("-----------------------------")

                action_name = None
                has_action = False
                for i in range(len(events) - 1, -1, -1):
                    e = events[i]
                    if isinstance(e, dict) and e.get("action") == "functionCall":
                        has_action = True
                        action_name = e.get("name")
                        print(f"Function call found: {action_name}")
                        results = e.get("results")
                        if len(results) != test_case['count_1']:
                            errors.append(f"First call ({query_1}): Expected {test_case['count_1']} results, but got {len(results)}")
                        events.pop(i)
                        break
                
                if not has_action:
                    errors.append(f"First call ({query_1}): No event with 'action' key found")

                entity_extraction_event = None
                for i in range(len(events) - 1, -1, -1):
                    e = events[i]
                    if isinstance(e, dict) and e.get("agent") == "extract_order_entity":
                        entity_extraction_event = events.pop(i)
                        break
                
                if not entity_extraction_event:
                    errors.append(f"First call ({query_1}): No event from 'extract_order_entity' agent found")
                else:
                    extracted_data = json.loads(entity_extraction_event["text"])
                    if extracted_data.get("program_level") != "UG":
                        errors.append(f"First call ({query_1}): Expected program_level 'UG', got '{extracted_data.get('program_level')}'")
                    if extracted_data.get("qualification") != "10+2":
                        errors.append(f"First call ({query_1}): Expected qualification '10+2', got '{extracted_data.get('qualification')}'")
                    if expected_stream and extracted_data.get("stream") != expected_stream:
                        errors.append(f"First call ({query_1}): Expected stream '{expected_stream}', got '{extracted_data.get('stream')}'")
                    if "percentage" in extracted_data and extracted_data.get("percentage") != 60:
                        errors.append(f"First call ({query_1}): Expected percentage 60, got '{extracted_data.get('percentage')}'")
                    print("Entity extraction validation successful for first call")

                auto_agent_event = None
                for i in range(len(events) - 1, -1, -1):
                    e = events[i]
                    if isinstance(e, dict) and e.get("agent") == "auto_agent":
                        auto_agent_event = events.pop(i)
                        break

                if not auto_agent_event:
                    errors.append(f"First call ({query_1}): No event from 'auto_agent' agent found")
                else:
                    auto_agent_data = json.loads(auto_agent_event["text"])
                    if "reason" not in auto_agent_data:
                        #errors.append(f"First call ({query_1}): 'reason' key not in auto_agent_data")
                        print(f"--------------------> First call ({query_1}): 'reason' key not in auto_agent_data")
                    elif action_name and action_name not in auto_agent_data["reason"]:
                        errors.append(f"First call ({query_1}): action_name '{action_name}' not in reason '{auto_agent_data['reason']}'")
                    print("Auto agent reason validation successful for first call")

            # Second call
            query_2 = test_case['query_2']
            print(f"\n--- Starting second call for query: {query_2} ---")
            json_data = {
                "text": query_2,
                "sessionId": session_id,
                "courseLevel": "UG"
            }
            async with aconnect_sse(client, "POST", "/chat", json=json_data) as event_source:
                events = [json.loads(event.data) async for event in event_source.aiter_sse()]
                events = [e for e in events if "endOfTurn" not in e]
                print("--- Events from second call ---")
                for event in events:
                    if not event.get("action") == "functionCall":
                        print(json.dumps(event, indent=2))
                print("------------------------------")

                action_name = None
                has_action = False
                for i in range(len(events) - 1, -1, -1):
                    e = events[i]
                    if isinstance(e, dict) and e.get("action") == "functionCall":
                        has_action = True
                        action_name = e.get("name")
                        results = e.get("results")
                        op_func = ops[test_case['count_2_operator']]
                        if not op_func(len(results), test_case['count_2']):
                             errors.append(f"Second call ({query_2}): Expected results {test_case['count_2_operator']} {test_case['count_2']}, but got {len(results)}")
                        print(f"Function call found in second call: {action_name}")
                        events.pop(i)
                        break
                
                if not has_action:
                    errors.append(f"Second call ({query_2}): No event with 'action' key found")

                entity_extraction_event = None
                for i in range(len(events) - 1, -1, -1):
                    e = events[i]
                    if isinstance(e, dict) and e.get("agent") == "extract_order_entity":
                        entity_extraction_event = events.pop(i)
                        break
                
                if not entity_extraction_event:
                    errors.append(f"Second call ({query_2}): No event from 'extract_order_entity' agent found")
                else:
                    extracted_data = json.loads(entity_extraction_event["text"])
                    if extracted_data.get("program_level") != "UG":
                        errors.append(f"Second call ({query_2}): Expected program_level 'UG', got '{extracted_data.get('program_level')}'")
                    if extracted_data.get("qualification") != "10+2":
                        errors.append(f"Second call ({query_2}): Expected qualification '10+2', got '{extracted_data.get('qualification')}'")
                    if expected_stream and extracted_data.get("stream") != expected_stream:
                        errors.append(f"Second call ({query_2}): Expected stream '{expected_stream}', got '{extracted_data.get('stream')}'")
                    if "percentage" in extracted_data and extracted_data.get("percentage") != 60:
                        errors.append(f"Second call ({query_2}): Expected percentage 60, got '{extracted_data.get('percentage')}'")
                    
                    match_course = re.search(r'in (.*)', query_2)
                    expected_course = match_course.group(1) if match_course else None
                    if expected_course and not (extracted_data.get("course_stream_type") and extracted_data.get("course_stream_type")[0] == expected_course):
                         errors.append(f"Second call ({query_2}): Expected course_stream_type '{expected_course}', got '{extracted_data.get('course_stream_type')}'")
                    print("Entity extraction validation successful for second call")

                auto_agent_event = None
                for i in range(len(events) - 1, -1, -1):
                    e = events[i]
                    if isinstance(e, dict) and e.get("agent") == "auto_agent":
                        auto_agent_event = events.pop(i)
                        break
                
                if not auto_agent_event:
                    errors.append(f"Second call ({query_2}): No event from 'auto_agent' agent found")
                else:
                    auto_agent_data = json.loads(auto_agent_event["text"])
                    if "reason" not in auto_agent_data:
                        #errors.append(f"Second call ({query_2}): 'reason' key not in auto_agent_data")
                        print(f"--------------------> Second call ({query_2}): 'reason' key not in auto_agent_data")
                    elif action_name and action_name not in auto_agent_data["reason"]:
                        errors.append(f"Second call ({query_2}): action_name '{action_name}' not in reason '{auto_agent_data['reason']}'")
                    print("Auto agent reason validation successful for second call")
        
        if errors:
            all_errors.extend(errors)
            print(f"--- Test failed for query: {query_1} with errors: {errors} ---")
        else:
            print(f"--- Test passed for query: {query_1} ---")

    if all_errors:
        raise AssertionError(f"Test suite failed with {len(all_errors)} errors:\n" + "\n".join(all_errors))
            
            

            

async def test_get_course_endpoint():
    async with AsyncClient(base_url="http://127.0.0.1:8000") as client:
        json_data = {
            "text": "Tell me more about this course",
            "sessionId": "test_session_course",
            "courseId": "12345"
        }
        async with aconnect_sse(client, "POST", "/get_course", json=json_data) as event_source:
            events = [json.loads(event.data) async for event in event_source.aiter_sse()]

            assert any(e.get('progress_spinner') == 'start' for e in events)
            assert any(e.get('progress_spinner') == 'end' for e in events)
            assert any(e.get('action') == 'close' for e in events)

            text_events = [e for e in events if 'text' in e]
            assert len(text_events) > 0, "No text events received"

            # We don't know the exact response, but we can check if it's a non-empty string
            final_text = "".join(e['text'] for e in text_events if 'text' in e)
            assert isinstance(final_text, str) and len(final_text) > 0

if __name__ == "__main__":
    asyncio.run(test_chat_endpoint())
    print("done")
