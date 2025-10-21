import random
import datetime
from google.cloud import firestore
import requests

db = firestore.Client()

def send_verification_code(phone_number: str):
    """
    Generates a 5-digit verification code, sends it to the user's phone number,
    and stores it in Firestore.
    """
    verification_code = str(random.randint(10000, 99999))
    
    # Send the verification code using the SmartPing API
    url = f"https://pgapi.smartping.ai/fe/api/v1/send?username=Testprepgpt.trans&password=sW2gV&unicode=false&from=TSTGPT&to={phone_number}&dltContentId=1707175152949044040&dltPrincipalEntityId=1701172845816093698&text={verification_code}%20is%20your%20verification%20code%20for%20TestprepGPT%20AI"
    response = requests.get(url)
    
    if response.status_code == 200:
        # Store the verification code in Firestore
        doc_ref = db.collection("sms_verification").document(phone_number)
        doc_ref.set({
            "verification_code": verification_code,
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        })
        return {"message": "Verification code sent successfully."}
    else:
        return {"error": "Failed to send verification code."}

import firebase_admin
from firebase_admin import credentials, auth

# Initialize Firebase Admin SDK
# Note: Replace 'path/to/your/serviceAccountKey.json' with the actual path to your service account key.
# It's recommended to use environment variables for the key's path in a production environment.
try:
    firebase_admin.initialize_app()
except Exception as e:
    print(f"Firebase Admin SDK initialization failed: {e}")


def verify_code(phone_number: str, code: str):
    """
    Verifies the provided verification code against the one stored in Firestore.
    If successful, it generates a Firebase custom token.
    """
    doc_ref = db.collection("sms_verification").document(phone_number)
    doc = doc_ref.get()

    if not doc.exists:
        return {"error": "Phone number not found."}

    data = doc.to_dict()
    stored_code = data.get("verification_code")
    timestamp = data.get("timestamp")

    if stored_code != code:
        return {"error": "Wrong verification code."}

    # Check if the code has expired (more than 3 minutes)
    time_difference = datetime.datetime.now(datetime.timezone.utc) - timestamp
    if time_difference.total_seconds() > 180:
        return {"error": "Verification code has expired."}

    try:
        custom_token = auth.create_custom_token(phone_number)
        return {"token": custom_token.decode('utf-8')}
    except Exception as e:
        return {"error": f"Failed to create custom token: {e}"}

