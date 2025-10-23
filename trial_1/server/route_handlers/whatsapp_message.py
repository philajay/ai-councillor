from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
from typing import Dict, List


CGC_UNIVERSITY = "cgc_university"
WELCOMKE = "welcome"

load_dotenv()

router = APIRouter()

class WhatsAppTemplateMessage(BaseModel):
    phone_number: str
    template_name: str
    params: Dict[str, str]

def _build_template_components(template_name: str, params: Dict[str, str]) -> List[Dict]:
    """
    Helper function to build the 'components' object for the WhatsApp API
    based on the provided template name.
    """
    if template_name == CGC_UNIVERSITY or template_name == "welcome":
        # This template expects a body with 4 text parameters.
        # The keys in params should be '1', '2', '3', '4' to ensure order.
        parameters = []
        for key in sorted(params.keys()):
            parameters.append({"type": "text", "text": params[key]})
        
        return [{"type": "body", "parameters": parameters}]

    # Add more template definitions here as needed
    # elif template_name == "another_template":
    #     ...
    else:
        # If the template is not recognized, raise an error.
        raise ValueError(f"Template '{template_name}' is not supported.")

@router.post("/send_template_whatsapp_message")
async def send_template_whatsapp_message(message: WhatsAppTemplateMessage):
    """
    Sends a generic WhatsApp template message.
    """
    return await _send_whatsapp_message(
        phone_number=message.phone_number,
        template_name=message.template_name,
        params=message.params
    )

async def _send_whatsapp_message(phone_number: str, template_name: str, params: Dict[str, str]):
    whatsapp_auth = os.getenv("WHATSAPP_AUTH")
    if not whatsapp_auth:
        raise HTTPException(status_code=500, detail="WHATSAPP_AUTH environment variable not set")

    url = "https://graph.facebook.com/v23.0/738485422671890/messages"
    headers = {
        "Authorization": f"Bearer {whatsapp_auth}",
        "Content-Type": "application/json"
    }
    
    try:
        components = _build_template_components(template_name, params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": f"+91{phone_number}",
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": "en_US"
            },
            "components": components
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Log the error for debugging
        print(f"Error sending WhatsApp message: {e}")
        if 'response' in locals():
            print(f"Response content: {response.content}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import asyncio

    async def test_cgcu_registration():
        print("\n--- Testing 'cgcu_registration' template ---")
        template_name = CGC_UNIVERSITY
        params = {
            "1": "John Doe",
            "2": "2025-10-21",
            "3": "10:00 AM",
            "4": "Introduction to FastAPI"
        }
        try:
            result = await _send_whatsapp_message(
                phone_number="9872722941",
                template_name=template_name,
                params=params
            )
            print("Message sent successfully:")
            print(result)
        except HTTPException as e:
            print(f"Failed to send message: {e.detail}")

    
    async def main():
        print("Running generic test message sender...")
        print("Ensure WHATSAPP_AUTH environment variable is set.")
        await test_cgcu_registration()

    asyncio.run(main())