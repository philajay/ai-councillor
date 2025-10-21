import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class VerificationTestCase(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("route_handlers.verification.requests.get")
    @patch("route_handlers.verification.db.collection")
    def test_send_verification_code_success(self, mock_collection, mock_get):
        mock_get.return_value.status_code = 200
        mock_doc_ref = MagicMock()
        mock_collection.return_value.document.return_value = mock_doc_ref

        response = self.client.get("/send_verification_code/1234567890")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Verification code sent successfully."})

    @patch("route_handlers.verification.requests.get")
    def test_send_verification_code_failure(self, mock_get):
        mock_get.return_value.status_code = 400

        response = self.client.get("/send_verification_code/1234567890")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"error": "Failed to send verification code."})

    @patch("route_handlers.verification.db.collection")
    @patch("route_handlers.verification.auth.create_custom_token")
    def test_verify_code_success(self, mock_create_custom_token, mock_collection):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "verification_code": "12345",
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        }
        mock_collection.return_value.document.return_value.get.return_value = mock_doc
        mock_create_custom_token.return_value = b"test_token"

        response = self.client.post("/verify_code", json={"phone_number": "1234567890", "code": "12345"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"token": "test_token"})

    @patch("route_handlers.verification.db.collection")
    def test_verify_code_phone_not_found(self, mock_collection):
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_collection.return_value.document.return_value.get.return_value = mock_doc

        response = self.client.post("/verify_code", json={"phone_number": "1234567890", "code": "12345"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"error": "Phone number not found."})

    @patch("route_handlers.verification.db.collection")
    def test_verify_code_wrong_code(self, mock_collection):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "verification_code": "54321",
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        }
        mock_collection.return_value.document.return_value.get.return_value = mock_doc

        response = self.client.post("/verify_code", json={"phone_number": "1234567890", "code": "12345"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"error": "Wrong verification code."})

    @patch("route_handlers.verification.db.collection")
    def test_verify_code_expired(self, mock_collection):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "verification_code": "12345",
            "timestamp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
        }
        mock_collection.return_value.document.return_value.get.return_value = mock_doc

        response = self.client.post("/verify_code", json={"phone_number": "1234567890", "code": "12345"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"error": "Verification code has expired."})

if __name__ == "__main__":
    unittest.main()
