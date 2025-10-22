from fastapi import APIRouter, Request, HTTPException, Response
import os
from dotenv import load_dotenv
import json
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from urllib.parse import quote
import requests
from common.common import APP_NAME


load_dotenv()

DB_NAME = os.getenv("DB_NAME", "councillor-assistant")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "1234")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_PASS = quote(DB_PASS)
session_service = DatabaseSessionService(db_url=f'postgresql+psycopg2://postgres:{DB_PASS}@{DB_HOST}/postgres')
from google.adk.planners import BuiltInPlanner
from google.genai import types

async def send_user_response(phone_number, txt):
    from google.cloud import firestore
    db = firestore.Client()
    doc_ref = db.collection("users").document(phone_number)
    doc = doc_ref.get()
    data = doc.to_dict()
    session_id = data["session"]
    final_response_content = ''

    instructions  = '''
Answer the question of the user based on chat history.
'''

    agent = LlmAgent(
            name="auto_agent",
            model="gemini-2.5-flash",
            instruction=instructions,
            sub_agents=[],
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=False,
                    thinking_budget=-1 
                )
            ),
            generate_content_config=types.GenerateContentConfig(
                temperature=1
            ),
        )
    user_id = "John Doe"
    session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id
        )


    runner = Runner(
            app_name=APP_NAME,
            agent=agent,
            session_service=session_service
        )
    user_content = types.Content(role='user', parts=[types.Part(text=txt)])
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=user_content):
        if event.is_final_response() and event.content and event.content.parts:
            # For output_schema, the content is the JSON string itself
            final_response_content = event.content.parts[0].text
    
    await send_template_whatsapp_message(phone_number, final_response_content)



async def send_template_whatsapp_message(phone_number, text):
    whatsapp_auth = os.getenv("WHATSAPP_AUTH")
    if not whatsapp_auth:
        raise HTTPException(status_code=500, detail="WHATSAPP_AUTH environment variable not set")

    url = "https://graph.facebook.com/v23.0/738485422671890/messages"
    headers = {
        "Authorization": f"Bearer {whatsapp_auth}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": f"+91{phone_number}",
        "type": "text",
        "text": {
            "body": text
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))



router = APIRouter()

# This is the verification token you'll set in your Meta Developer Portal
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

@router.get("/whatsapp-webhook")
async def verify_webhook(request: Request):
    """
    Handles the webhook verification request from WhatsApp.
    """
    # WhatsApp sends these query parameters to your endpoint
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    # Check if the mode and token are correct
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        # Respond with the challenge token from the request
        return Response(content=challenge, status_code=200)
    else:
        # Respond with 403 Forbidden if tokens do not match
        print("Webhook verification failed.")
        raise HTTPException(status_code=403, detail="Failed to verify webhook token")

@router.post("/whatsapp-webhook")
async def receive_message(request: Request):
    """
    Handles incoming messages and other events from WhatsApp.
    """
    try:
        data = await request.json()
        print("Received WhatsApp payload:")
        # Safely parse the nested structure
        if (
            data.get("entry")
            and data["entry"][0].get("changes")
            and data["entry"][0]["changes"][0].get("value")
            and data["entry"][0]["changes"][0]["value"].get("messages")
        ):
            message_object = data["entry"][0]["changes"][0]["value"]["messages"][0]

            # Check if it's a text message
            if message_object.get("type") == "text":
                from_number = message_object["from"]
                text_body = message_object["text"]["body"]
                print(f"Message being sent to {from_number}")
                await send_user_response(from_number, text_body)
        # Acknowledge the event immediately with a 200 OK response
        return Response(status_code=200)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON received")
    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


