from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

class WhatsAppTemplateMessage(BaseModel):
    phonenumber: str
    name: str
    date: str
    time: str
    course_name: str

@router.post("/send_template_whatsapp_message")
async def send_template_whatsapp_message(message: WhatsAppTemplateMessage):
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
        "to": f"+91{message.phonenumber}",
        "type": "template",
        "template": {
            "name": "cgc_university",
            "language": {
                "code": "en_US"
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": message.name},
                        {"type": "text", "text": message.date},
                        {"type": "text", "text": message.time},
                        {"type": "text", "text": message.course_name}
                    ]
                }
            ]
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import asyncio

    async def main():
        print("Running test message sender...")
        print("Ensure WHATSAPP_AUTH environment variable is set.")
        
        test_data = WhatsAppTemplateMessage(
            phonenumber="9872722941",
            name="John Doe",
            date="2025-10-21",
            time="10:00 AM",
            course_name="Introduction to FastAPI"
        )
        
        try:
            result = await send_template_whatsapp_message(test_data)
            print("Message sent successfully:")
            print(result)
        except HTTPException as e:
            print(f"Failed to send message: {e.detail}")

    asyncio.run(main())
