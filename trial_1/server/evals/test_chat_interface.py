import asyncio
from httpx import AsyncClient
from httpx_sse import aconnect_sse
import json
import uuid

# Mark all tests in this file as asyncio tests
#pytestmark = pytest.mark.asyncio

async def test_chat_endpoint():
    session_id = str(uuid.uuid4())
    errors = []
    async with AsyncClient(base_url="http://127.0.0.1:8080", timeout=60.0) as client:
        # First call
        json_data = {
            "text": "I have done my 12th with 60% in arts.",
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
                    if len(results) != 8:
                        errors.append(f"First call: Expected 8 results, but got {len(results)}")
                    events.pop(i)
                    break
            
            if not has_action:
                errors.append("First call: No event with 'action' key found")

            entity_extraction_event = None
            for i in range(len(events) - 1, -1, -1):
                e = events[i]
                if isinstance(e, dict) and e.get("agent") == "extract_order_entity":
                    entity_extraction_event = events.pop(i)
                    break
            
            if not entity_extraction_event:
                errors.append("First call: No event from 'extract_order_entity' agent found")
            else:
                extracted_data = json.loads(entity_extraction_event["text"])
                if extracted_data.get("program_level") != "UG":
                    errors.append(f"First call: Expected program_level 'UG', got '{extracted_data.get('program_level')}'")
                if extracted_data.get("qualification") != "10+2":
                    errors.append(f"First call: Expected qualification '10+2', got '{extracted_data.get('qualification')}'")
                if extracted_data.get("stream") != "arts":
                    errors.append(f"First call: Expected stream 'arts', got '{extracted_data.get('stream')}'")
                if extracted_data.get("percentage") != 60:
                    errors.append(f"First call: Expected percentage 60, got '{extracted_data.get('percentage')}'")
                print("Entity extraction validation successful")

            auto_agent_event = None
            for i in range(len(events) - 1, -1, -1):
                e = events[i]
                if isinstance(e, dict) and e.get("agent") == "auto_agent":
                    auto_agent_event = events.pop(i)
                    break

            if not auto_agent_event:
                errors.append("First call: No event from 'auto_agent' agent found")
            else:
                auto_agent_data = json.loads(auto_agent_event["text"])
                if "reason" not in auto_agent_data:
                    errors.append("First call: 'reason' key not in auto_agent_data")
                elif action_name and action_name not in auto_agent_data["reason"]:
                    errors.append(f"First call: action_name '{action_name}' not in reason '{auto_agent_data['reason']}'")
                print("Auto agent reason validation successful")

        # Second call
        print("\n--- Starting second call ---")
        json_data = {
            "text": "Show me courses in B.Sc",
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
                    if not len(results) <= 5:
                         errors.append(f"Second call: Expected results to be <= 5, but got {len(results)}")
                    print(f"Function call found in second call: {action_name}")
                    events.pop(i)
                    break
            
            if not has_action:
                errors.append("Second call: No event with 'action' key found")

            entity_extraction_event = None
            for i in range(len(events) - 1, -1, -1):
                e = events[i]
                if isinstance(e, dict) and e.get("agent") == "extract_order_entity":
                    entity_extraction_event = events.pop(i)
                    break
            
            if not entity_extraction_event:
                errors.append("Second call: No event from 'extract_order_entity' agent found")
            else:
                extracted_data = json.loads(entity_extraction_event["text"])
                if extracted_data.get("program_level") != "UG":
                    errors.append(f"Second call: Expected program_level 'UG', got '{extracted_data.get('program_level')}'")
                if extracted_data.get("qualification") != "10+2":
                    errors.append(f"Second call: Expected qualification '10+2', got '{extracted_data.get('qualification')}'")
                if extracted_data.get("stream") != "arts":
                    errors.append(f"Second call: Expected stream 'arts', got '{extracted_data.get('stream')}'")
                if extracted_data.get("percentage") != 60:
                    errors.append(f"Second call: Expected percentage 60, got '{extracted_data.get('percentage')}'")
                if not (extracted_data.get("course_stream_type") and extracted_data.get("course_stream_type")[0] == "B.Sc"):
                     errors.append(f"Second call: Expected course_stream_type 'B.Sc', got '{extracted_data.get('course_stream_type')}'")
                print("Entity extraction validation successful")

            auto_agent_event = None
            for i in range(len(events) - 1, -1, -1):
                e = events[i]
                if isinstance(e, dict) and e.get("agent") == "auto_agent":
                    auto_agent_event = events.pop(i)
                    break
            
            if not auto_agent_event:
                errors.append("Second call: No event from 'auto_agent' agent found")
            else:
                auto_agent_data = json.loads(auto_agent_event["text"])
                if "reason" not in auto_agent_data:
                    errors.append("Second call: 'reason' key not in auto_agent_data")
                elif action_name and action_name not in auto_agent_data["reason"]:
                    errors.append(f"Second call: action_name '{action_name}' not in reason '{auto_agent_data['reason']}'")
                print("Auto agent reason validation successful")

    if errors:
        raise AssertionError(f"Test failed with {len(errors)} errors:\n" + "\n".join(errors))
            
            

            

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
