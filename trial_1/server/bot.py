from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
from google.genai import types
import asyncio
from common.common import update_session_state, LAST_CLIENT_MESSAGE, LAST_DB_RESULTS
from google.genai.types import Part
from google.adk.sessions import InMemorySessionService
import uuid

APP_NAME = "bot"

router = APIRouter()
session_service = InMemorySessionService()

class AppState:
    is_model_loaded = False
    model_loaded_event = asyncio.Event()

app_state = AppState()

class AgentSession:
    def __init__(self, user_id, session_id, is_audio=False):
        self.user_id = user_id
        self.is_audio = is_audio
        self.session = None
        self.runner = None
        self.last_client_text_message = None
        self.session_id = session_id

    async def start(self, course_level):
        """Starts an agent session"""
        from google.adk.runners import Runner
        from agents.autonomous import AutoAgent

        self.runner = Runner(
            app_name=APP_NAME,
            agent=AutoAgent(),
            session_service=session_service
        )

        self.session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=self.user_id,
            session_id=self.session_id
        )
        
        if not self.session:
            self.session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=self.user_id,
                state={
                    "course_level": course_level
                },
                session_id=self.session_id
            )

async def handle_connection(agent_session: AgentSession, client_websocket: WebSocket):
    await app_state.model_loaded_event.wait()
    
    try:
        while True:
            message_json = await client_websocket.receive_text()
            message = json.loads(message_json)
            data = message.get("text", "")
            
            await client_websocket.send_text(json.dumps({'progress_spinner': 'start'}))
            
            await update_session_state(LAST_CLIENT_MESSAGE, data, agent_session.session, agent_session.runner.session_service)
            content = types.Content(role='user', parts=[types.Part(text=data)])
            
            async for event in agent_session.runner.run_async(user_id=agent_session.user_id, session_id=agent_session.session.id, new_message=content):
                if event.error_code:
                    await client_websocket.send_text(json.dumps({"error": event.error_code}))
                    continue

                if event.turn_complete or event.interrupted:
                    await client_websocket.send_text(json.dumps({"endOfTurn": True, "agent": event.author}))
                    continue

                part: Part = (
                    event.content and event.content.parts and event.content.parts[0]
                )
                if not part:
                    continue

                if part.function_response:
                    s = await agent_session.runner.session_service.get_session(app_name=APP_NAME, user_id=agent_session.user_id, session_id=agent_session.session_id)
                    if part.function_response.name in ['find_by_eligibility', 'find_by_discovery']:
                        results = s.state.get(LAST_DB_RESULTS)
                        message = {
                            "action": "functionCall",
                            "name": part.function_response.name,
                            "args": {},
                            "results": results,
                            "agent": event.author
                        }   
                        await client_websocket.send_text(json.dumps(message))

                elif part.text and event.partial:
                    message = {"text": part.text, "agent": event.author}
                    await client_websocket.send_text(json.dumps(message))

                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response_text = event.content.parts[0].text
                        message = {"text": final_response_text, "agent": event.author}
                        await client_websocket.send_text(json.dumps(message))
                        await client_websocket.send_text(json.dumps({"endOfTurn": True, "agent": event.author}))
            
            await client_websocket.send_text(json.dumps({'progress_spinner': 'end'}))

    except WebSocketDisconnect:
        print(f"Client #{agent_session.user_id} disconnected")
    except Exception as e:
        import traceback
        traceback.print_exception(e)
        await client_websocket.send_text(json.dumps({'error': e.__class__.__name__, 'message': str(e)}))

@router.on_event("startup")
async def startup_event():
    from db.search_engine import load_model_async
    print("Going to load model in background for bot")
    
    async def wrapped_load():
        await load_model_async(app_state)
        app_state.model_loaded_event.set()

    asyncio.create_task(wrapped_load())

@router.websocket("/bot")
async def websocket_endpoint(websocket: WebSocket, sessionId: str = None, courseLevel: str = "Beginner"):
    await websocket.accept()
    
    if not sessionId:
        sessionId = str(uuid.uuid4())

    user_id = "John Doe"
    agent_session = AgentSession(user_id, sessionId, False)
    await agent_session.start(courseLevel)

    if not app_state.is_model_loaded:
        await websocket.send_text(json.dumps({
            "text": "The bot is warming up. Please wait a moment...",
            "agent": "system"
        }))
        await app_state.model_loaded_event.wait()
        await websocket.send_text(json.dumps({
            "text": "The bot is ready. How can I help you?",
            "agent": "system"
        }))

    try:
        await handle_connection(agent_session, websocket)
    except Exception as e:
        print(f"Error in WebSocket handler: {e}")
        import traceback
        traceback.print_exception(e)
    finally:
        await websocket.close()
        print(f"WebSocket connection closed for session {sessionId}")
