from fastapi import APIRouter, Request, HTTPException, Response
import os
from dotenv import load_dotenv
import json
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, DatabaseSessionService
from urllib.parse import quote
import requests
from google.genai.types import Part
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




async def get_llm_response(phone_number, txt, instruction = 'Answer the question of the user based on chat history.'):
    print(f"Args are {phone_number} and {txt}")
    
    doc_phone_number = phone_number
    if len(phone_number) > 10:
        doc_phone_number = phone_number[-10:]
        
    from google.cloud import firestore
    db = firestore.Client()
    doc_ref = db.collection("users").document(doc_phone_number)
    doc = doc_ref.get()
    data = doc.to_dict()
    session_id = data["session"]
    final_response_content = ''


    agent = LlmAgent(
            name="watsapp_agent",
            model="gemini-2.5-flash",
            instruction=instruction,
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

    if session:
        print("Session found for user")

    runner = Runner(
            app_name=APP_NAME,
            agent=agent,
            session_service=session_service
        )
    user_content = types.Content(role='user', parts=[types.Part(text=txt)])
    try:  
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=user_content):
            try:
                print(f"event fired 1--> {json.dumps(event)}")
            except:
                print(f"event fired 2--> {event.actions}")


            if event.error_code:
                print(f"data: {json.dumps({'error': event.error_code})}\n\n")
                continue

            if event.turn_complete or event.interrupted:
                print(f"data: {json.dumps({'endOfTurn': True, 'agent': event.author})}\n\n")
                continue


            part: Part = (
                event.content and event.content.parts and event.content.parts[0]
            )

            if not part:
                continue

            if part.text and event.partial:
                final_response_content += part.text

            if event.is_final_response() and event.content and event.content.parts:
                # For output_schema, the content is the JSON string itself
                final_response_content += event.content.parts[0].text
                print(f"LLM Response is {phone_number}: '{final_response_content}'")      
    except Exception as ex:
        print(f"--- ERROR DURING LLM AGENT EXECUTION ---")
        print(f"An exception occurred: {ex}")
        import traceback   
        traceback.print_exc()   
    return final_response_content



async def send_user_response(phone_number, txt, instruction = 'Answer the question of the user based on chat history.'):
    
    final_response_content = await get_llm_response(phone_number, txt, instruction)
    # --- DIAGNOSTIC LOGGING ---
    print(f"Final response from LLM Agent for {phone_number}: '{final_response_content}'")
    # --------------------------
    await send_template_whatsapp_message(phone_number, final_response_content)



async def send_template_whatsapp_message(phone_number, text):
    # --- GUARD CLAUSE ---
    if not text or not text.strip():
        print(f"WARNING: Attempted to send an empty message to {phone_number}. Aborting.")
        return
    # --------------------

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
        "to": f"+{phone_number}",
        "type": "text",
        "text": {
            "body": text
        }
    }
    print(json.dumps(headers))
    print(json.dumps(data))

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
                print(f"received message {from_number} and message is '{text_body}'")
                try:
                    await send_user_response(from_number, text_body, "Answer the question of the user based on chat history.")
                except Exception as ex:
                    import traceback
                    traceback.print_exception(ex)

        # Acknowledge the event immediately with a 200 OK response
        return Response(status_code=200)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON received")
    except Exception as e:
        print(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")



@router.post("/summarize_session")
async def categorize_lead(request: Request):
    """
    Analyzes a conversation and categorizes the user as a 'hot' or 'cold' lead.
    """
    try:
        data = await request.json()
        phone_number = data.get("phone_number")
        user_question = data.get("user_question")
        prompt = data.get("prompt", "")

        res = await get_llm_response(phone_number, user_question, instruction=prompt)

        # Send the response back
        return {"response": res, "status": "success"}

    except HTTPException as he:
        # Re-raise HTTP exceptions directly
        raise he
    except Exception as e:
        print(f"Error during lead categorization: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")



@router.get("/categorize_lead/{phone_number}")
async def categorize_lead(phone_number: str):
    """
    Analyzes a conversation and categorizes the user as a 'hot' or 'cold' lead.
    """
    try:
        

        # 4. Create the prompt and call the LLM
        prompt = f"""
Phone Number: {phone_number}
You are an expert sales analyst for a university. Your task is to analyze a conversation between a prospective student (User) and a university assistant (Assistant) to determine if the student is a 'hot lead' or a 'cold lead'.

- **Hot Lead**: A user showing strong buying signals. They ask specific questions about admission deadlines, fee structures, application processes, specific course details, or express a clear intent to apply.
- **Cold Lead**: A user who is just browsing. They ask very general questions, are unresponsive, or show little engagement or interest in taking the next steps.


Based on the analysis, classify the user. 
1. "classification": Either "hot" or "cold".
2. Phone Number: The phone number of the user.
3. Course of Interest: The course the user is interested.
4. "reason": A brief, one-sentence explanation for your classification.
"""
        await send_user_response(phone_number, "Categorize the conversation", instruction=prompt)

         # Acknowledge the request
        return Response(status_code=200)

    except HTTPException as he:
        # Re-raise HTTP exceptions directly
        raise he
    except Exception as e:
        print(f"Error during lead categorization: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


