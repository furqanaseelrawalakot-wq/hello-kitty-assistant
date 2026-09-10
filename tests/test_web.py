"""
test_web.py - Automated tests for the Flask Web Interface.
Tests template rendering (GET /) and the /chat endpoint (POST /chat) for both
built-in features and AI brain queries.
"""

import sys
import unittest
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.app import app


class TestWebInterface(unittest.TestCase):
    """Tests for web/app.py routes."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_index_route(self):
        """Verify GET / renders the HTML chat and landing screen."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Hello Kitty", html)
        self.assertIn("chat-wrapper", html)
        self.assertIn("user-input", html)
        self.assertIn("landing-screen", html)
        self.assertIn("start-chat-btn", html)

    def test_chat_feature_route(self):
        """Verify POST /chat routes to built-in features."""
        payload = {"message": "what time is it"}
        response = self.client.post(
            "/chat",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("is_feature"))
        self.assertIn("The current time is", data.get("reply"))

    def test_chat_ai_route(self):
        """Verify POST /chat routes to AI brain for general questions."""
        payload = {"message": "Who are you?"}
        response = self.client.post(
            "/chat",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("reply", data)
        self.assertTrue(len(data["reply"]) > 0)

    def test_chat_urdu_route(self):
        """Verify POST /chat routes Urdu text to translation pipeline."""
        payload = {"message": "آپ کا نام کیا ہے؟"}
        response = self.client.post(
            "/chat",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("is_urdu"))
        self.assertIn("reply", data)

    def test_empty_message(self):
        """Verify POST /chat handles empty message validation."""
        payload = {"message": ""}
        response = self.client.post(
            "/chat",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_clear_and_history_routes(self):
        """Verify /history and /clear endpoints."""
        hist_resp = self.client.get("/history")
        self.assertEqual(hist_resp.status_code, 200)

        clear_resp = self.client.post("/clear")
        self.assertEqual(clear_resp.status_code, 200)
        self.assertEqual(clear_resp.get_json()["status"], "cleared")


if __name__ == "__main__":
    unittest.main()
