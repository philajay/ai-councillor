from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
from google.genai import types
import asyncio
from common.common import update_session_state, LAST_CLIENT_MESSAGE, LAST_DB_RESULTS
from google.genai.types import Part
from pydantic import BaseModel
from google.adk.sessions import InMemorySessionService, DatabaseSessionService

#session_service = DatabaseSessionService(db_url='postgresql+psycopg2://postgres:1234@localhost/councillor-assistant')
session_service = DatabaseSessionService(db_url='postgresql+psycopg2://postgres:Supabase%40123@db.tenztfzbcvypmjhsrfpo.supabase.co/postgres')
#session_service = InMemorySessionService()

APP_NAME = "http_bot"

router = APIRouter()

class AppState:
    is_model_loaded = False
    model_loaded_event = asyncio.Event()

app_state = AppState()

class ChatRequest(BaseModel):
    text: str

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
            session_service = session_service
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

async def event_stream(agent_session: AgentSession, data: str):
    # Wait for the model to be loaded before processing the request.
    await app_state.model_loaded_event.wait()
    
    try:
        yield f"data: {json.dumps({'progress_spinner': 'start'})}\n\n"
        await update_session_state(LAST_CLIENT_MESSAGE, data, agent_session.session, agent_session.runner.session_service)
        content = types.Content(role='user', parts=[types.Part(text=data)])
        
        async for event in agent_session.runner.run_async(user_id=agent_session.user_id, session_id=agent_session.session.id, new_message=content):
            if event.error_code:
                yield f"data: {json.dumps({'error': event.error_code})}\n\n"
                continue

            if event.turn_complete or event.interrupted:
                yield f"data: {json.dumps({'endOfTurn': True, 'agent': event.author})}\n\n"
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
                    yield f"data: {json.dumps(message)}\n\n"

            elif part.text and event.partial:
                message = {"text": part.text, "agent": event.author}
                yield f"data: {json.dumps(message)}\n\n"

            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                    message = {"text": final_response_text, "agent": event.author}
                    yield f"data: {json.dumps(message)}\n\n"
                    yield f"data: {json.dumps({'endOfTurn': True, 'agent': event.author})}\n\n"

    except Exception as e:
        import traceback
        traceback.print_exception(e)
        yield f"data: {json.dumps({'error': e.__class__.__name__, 'message': str(e)})}\n\n"
    finally:
        yield f"data: {json.dumps({'progress_spinner': 'end'})}\n\n"
        yield f"data: {json.dumps({'action': 'close'})}\n\n"


@router.on_event("startup")
async def startup_event():
    from db.search_engine import load_model_async
    print("Going to load model in background for http_bot")
    
    async def wrapped_load():
        await load_model_async(app_state)
        app_state.model_loaded_event.set()

    asyncio.create_task(wrapped_load())


agent_session = None

@router.get("/hello_world")
async def hello_world():
    return {"message": "Hello, World!"}

@router.get("/chat")
async def chat_endpoint(request: Request, text: str, sessionId: str, courseLevel: str):
    user_id = "John Doe"  # In a real app, you'd get this from the request/session
    agent_session = AgentSession(user_id, sessionId, False)
    await agent_session.start(courseLevel)
    
    return StreamingResponse(event_stream(agent_session, text), media_type="text/event-stream")