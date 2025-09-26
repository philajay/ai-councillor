from fastapi import APIRouter, WebSocket
import json
from google.genai import types
import asyncio
from common.common import update_session_state, LAST_CLIENT_MESSAGE, LAST_DB_RESULTS
APP_NAME = "bot"


router = APIRouter()

class AppState:
    is_model_loaded = False

app_state = AppState()

class AgentSession:
    def __init__(self, user_id, is_audio=False):
        self.user_id = user_id
        self.is_audio = is_audio
        self.session = None
        self.runner = None
        self.last_client_text_message = None
        self.session_id = "123"

    async def start(self):
        """Starts an agent session"""
        from agents.routerAgent import RouterAgent
        from google.adk.runners import InMemoryRunner


        # Create a Runner
        self.runner = InMemoryRunner(
            app_name=APP_NAME,
            agent=RouterAgent(),
        )

        # Create a Session
        self.session = await self.runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=self.user_id,  # Replace with actual user ID
            state = {
            },
            session_id=self.session_id
        )
        


    async def handle_connection(self, client_websocket:WebSocket):
        from google.genai.types import (
            Part,
        )
        prompt_count = 0
        candidaye_count = 0
        while True:
            try:
                message_json = await client_websocket.receive_text()
                message = json.loads(message_json)
                data = message.get("text", "")
                print(f"1st --> {data}")
                await update_session_state(LAST_CLIENT_MESSAGE, data, self.session, self.runner.session_service)
                content = types.Content(role='user', parts=[types.Part(text=data)])
                # Key Concept: run_async executes the agent logic and yields Events.
                # We iterate through events to find the final answer.
                async for event in self.runner.run_async(user_id=self.user_id, session_id=self.session.id, new_message=content):

                    try:
                        candidaye_count += event.usage_metadata.candidates_token_count
                        prompt_count += event.usage_metadata.prompt_token_count
                    except:
                        pass

                    if event.error_code:
                        print(f'Failing with {event.error_code}')
                        await client_websocket.send_text(json.dumps({
                                                    "error": event.error_code
                                                }))
                    print('Event fired by -->', event.author)
                    # If the turn complete or interrupted, send it
                    if event.turn_complete or event.interrupted:
                        message = {
                            "endOfTurn": True,
                            "agent": event.author
                        }
                        #await websocket.send_text(json.dumps(message))
                        await client_websocket.send_text(json.dumps({
                                                "endOfTurn": True,
                                                "agent": event.author
                                            }))
                        # print(f"[AGENT TO CLIENT]: {message}")
                        continue
                    
                    # Read the Content and its first Part
                    part: Part = (
                        event.content and event.content.parts and event.content.parts[0]
                    )
                    if not part:
                        continue

                        
                    if part.function_response:
                        print(f'[Function Called]: {part.function_response.name}')
                        s = await self.runner.session_service.get_session(app_name=APP_NAME, user_id= self.user_id, session_id= self.session_id)
                        if part.function_response.name == 'find_by_eligibility' or part.function_response.name == 'find_by_discovery':
                            results = s.state[LAST_DB_RESULTS]
                            await client_websocket.send_text(json.dumps({
                                                    "action": "functionCall",
                                                    "name": part.function_response.name,
                                                    "args": {},
                                                    "results": results,
                                                    "agent": event.author
                                                }))



                    # If it's text and a parial text, send it
                    elif part.text and event.partial:
                        message = {
                            "text": part.text,
                            "agent": event.author
                            }
                        await client_websocket.send_text(json.dumps(message))
                        #print(f"[AGENT TO CLIENT PARTIALTEST]: text/plain: {message}")


                    # Key Concept: is_final_response() marks the concluding message for the turn.
                    if event.is_final_response():
                        if event.content and event.content.parts:
                            # Assuming text response in the first part
                            final_response_text = event.content.parts[0].text
                            message = {
                                "text": final_response_text,
                                "agent": event.author
                            }
                            await client_websocket.send_text(json.dumps(message))
                            # print(f"[AGENT TO CLIENT]: text/plain: {message}")
                            await client_websocket.send_text(json.dumps({
                                "endOfTurn": True,
                                "agent": event.author
                            }))

                    print(f"Candidate count is {candidaye_count}")
                    print(f"prompt_count is {prompt_count}")
            except Exception as e:
                print(f"Caught exception in handle_connection: {e}")
                #print stack trace
                import traceback
                traceback.print_exception(e)

                await client_websocket.send_text(json.dumps({
                    'error': f'exception caught: {e}'
                }))
                continue


@router.on_event("startup")
async def startup_event():
    from db.search_engine import load_model_async
    print("Going to load model in background")
    """Loads the model at startup"""
    asyncio.create_task(load_model_async(app_state))

@router.websocket("/bot")
async def websocket_endpoint(websocket: WebSocket):
    
    try:
        await websocket.accept()

        if not app_state.is_model_loaded:
            await websocket.send_text(json.dumps({
                "text": "The bot is warming up. Please wait a moment...",
                "agent": "system"
            }))
            while not app_state.is_model_loaded:
                await asyncio.sleep(1)
            await websocket.send_text(json.dumps({
                "text": "The bot is ready. How can I help you?",
                "agent": "system"
            }))

        user_id="John Doe"
        agent_session = AgentSession(user_id, False)
        await agent_session.start()

        await agent_session.handle_connection(websocket)

        # Disconnected
        print(f"Client #{user_id} disconnected")
    except Exception as e:
        print(f"Error in WebSocket handler: {e}")
        import traceback
        traceback.print_exception(e)

    finally:
        await websocket.close()
        print("WebSocket connection closed")
