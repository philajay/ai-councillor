import re
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
#session_service = DatabaseSessionService(db_url='postgresql+psycopg2://postgres:Supabase%40123@db.tenztfzbcvypmjhsrfpo.supabase.co/postgres')
session_service = InMemorySessionService()

APP_NAME = "http_bot"

router = APIRouter()

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

    async def start(self, agent, initial_state={}):
        """Starts an agent session"""
        from google.adk.runners import Runner

        self.runner = Runner(
            app_name=APP_NAME,
            agent=agent,
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
                state=initial_state,
                session_id=self.session_id
            )

async def event_stream(agent_session: AgentSession, data: str):
    # Wait for the model to be loaded before processing the request.
    await app_state.model_loaded_event.wait()
    
    candidates_token_count = 0
    prompt_token_count = 0
    try:
        yield f"data: {json.dumps({'progress_spinner': 'start'})}\n\n"
        await update_session_state(LAST_CLIENT_MESSAGE, data, agent_session.session, agent_session.runner.session_service)
        content = types.Content(role='user', parts=[types.Part(text=data)])
        

        async for event in agent_session.runner.run_async(user_id=agent_session.user_id, session_id=agent_session.session.id, new_message=content):
            
            try:
                if event.usage_metadata:
                    candidates_token_count += event.usage_metadata.candidates_token_count
                    prompt_token_count += event.usage_metadata.prompt_token_count
            except:
                pass
            
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
                    if event.author == 'auto_agent' or event.author == 'course_sales_agent':
                        try:
                            markdown = re.search(r'<Markdown>(.*?)</Markdown>', final_response_text, re.DOTALL).group(1).strip()
                            reason = re.search(r'<Reason>(.*?)</Reason>', final_response_text, re.DOTALL).group(1).strip()
                            js = {"markdown": markdown, "reason": reason}
                            message = {"text": json.dumps(js), "agent": event.author}
                        except Exception as ex:
                            print(ex)
                            message = {"text": json.dumps({"markdown": final_response_text}), "agent": event.author}
                    else:
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
        print(f'Token Count --- > prompt_token_count: {prompt_token_count} and candidates_token_count: {candidates_token_count}')


@router.on_event("startup")
async def startup_event():
    from db.search_engine import load_model_async
    print("Going to load model in background for http_bot")
    
    async def wrapped_load():
        await load_model_async(app_state)
        app_state.model_loaded_event.set()

    asyncio.create_task(wrapped_load())


from agents.autonomous import AutoAgent, CourseSaleAgent
agent_session = None

@router.get("/hello_world")
async def hello_world():
    return {"message": "Hello, World!"}

class ChatRequest(BaseModel):
    text: str
    sessionId: str
    courseLevel: str

class CourseRequest(BaseModel):
    text: str
    sessionId: str
    courseId: str

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_id = "John Doe"  # In a real app, you'd get this from the request/session
    agent_session = AgentSession(user_id, request.sessionId, False)
    await agent_session.start(AutoAgent(), initial_state={"course_level": request.courseLevel})
    
    # Replace '%' with 'percent' in the request text
    request.text = request.text.replace('%', ' percent')
    
    return StreamingResponse(event_stream(agent_session, request.text), media_type="text/event-stream")

from route_handlers.verification import send_verification_code, verify_code

@router.post("/get_course")
async def get_course_endpoint(request: CourseRequest):
    user_id = "John Doe"
    agent_session = AgentSession(user_id, request.sessionId, False)
    await agent_session.start(CourseSaleAgent(), initial_state={"course_id": request.courseId})

    return StreamingResponse(event_stream(agent_session, request.text), media_type="text/event-stream")

@router.get("/send_verification_code/{phone_number}")
async def send_verification_code_endpoint(phone_number: str):
    return send_verification_code(phone_number)

class VerifyCodeRequest(BaseModel):
    phone_number: str
    code: str

@router.post("/verify_code")
async def verify_code_endpoint(request: VerifyCodeRequest):
    return verify_code(request.phone_number, request.code)

from route_handlers.data_extraction import extract_data_from_urls
from typing import List, Dict

class DataExtractionRequest(BaseModel):
    urls_and_tags: List[Dict[str, str]]

@router.post("/extract-data")
async def extract_data_endpoint(request: DataExtractionRequest):
    return extract_data_from_urls(request.urls_and_tags)
