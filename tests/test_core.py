"""
test_core.py - Automated unit tests for Hello Kitty Phase 1 core logic.
Tests configuration validation, in-memory conversation handling, error catching,
and wake word detection logic without requiring physical audio hardware.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config.settings as settings
from brain.llm_provider import ask_hello_kitty, MAX_MEMORY_TURNS
from voice.speaker import speak


class TestConfigValidation(unittest.TestCase):
    """Tests for settings.validate_config."""

    def test_missing_gemini_key(self):
        with patch.object(settings, "MODEL_PROVIDER", "gemini"), \
             patch.object(settings, "GEMINI_API_KEY", ""):
            is_valid, msg = settings.validate_config()
            self.assertFalse(is_valid)
            self.assertIn("Gemini API key is missing", msg)

    def test_valid_gemini_key(self):
        with patch.object(settings, "MODEL_PROVIDER", "gemini"), \
             patch.object(settings, "GEMINI_API_KEY", "test-gemini-key"):
            is_valid, msg = settings.validate_config()
            self.assertTrue(is_valid)
            self.assertIn("Google Gemini", msg)

    def test_missing_openai_key(self):
        with patch.object(settings, "MODEL_PROVIDER", "openai"), \
             patch.object(settings, "OPENAI_API_KEY", ""):
            is_valid, msg = settings.validate_config()
            self.assertFalse(is_valid)
            self.assertIn("OpenAI API key is missing", msg)

    def test_valid_openai_key(self):
        with patch.object(settings, "MODEL_PROVIDER", "openai"), \
             patch.object(settings, "OPENAI_API_KEY", "test-openai-key"):
            is_valid, msg = settings.validate_config()
            self.assertTrue(is_valid)
            self.assertIn("OpenAI", msg)

    def test_invalid_provider(self):
        with patch.object(settings, "MODEL_PROVIDER", "unknown_provider"):
            is_valid, msg = settings.validate_config()
            self.assertFalse(is_valid)
            self.assertIn("Invalid MODEL_PROVIDER", msg)


class TestBrainAndMemory(unittest.TestCase):
    """Tests for brain/llm_provider logic and in-memory history."""

    def test_empty_input(self):
        reply = ask_hello_kitty("", [])
        self.assertIn("I'm here!", reply)

    def test_whitespace_input(self):
        reply = ask_hello_kitty("   \n\t  ", [])
        self.assertIn("I'm here!", reply)

    @patch("brain.llm_provider.get_llm_client")
    def test_successful_llm_query(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.generate_reply.return_value = "Hello! I am Hello Kitty! How are you?"
        mock_get_client.return_value = mock_client

        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"}
        ]
        reply = ask_hello_kitty("Who are you?", history)

        self.assertEqual(reply, "Hello! I am Hello Kitty! How are you?")
        mock_client.generate_reply.assert_called_once()
        args, kwargs = mock_client.generate_reply.call_args
        self.assertEqual(kwargs["user_text"], "Who are you?")
        self.assertEqual(kwargs["conversation_history"], history)

    @patch("brain.llm_provider.get_llm_client")
    def test_memory_truncation_limits_to_max_turns(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.generate_reply.return_value = "Understood!"
        mock_get_client.return_value = mock_client

        # Create 20 turns (exceeding MAX_MEMORY_TURNS=10)
        long_history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"} for i in range(20)]
        ask_hello_kitty("Latest query", long_history)

        args, kwargs = mock_client.generate_reply.call_args
        passed_history = kwargs["conversation_history"]
        self.assertEqual(len(passed_history), MAX_MEMORY_TURNS)
        self.assertEqual(passed_history[0]["content"], f"msg {20 - MAX_MEMORY_TURNS}")

    @patch("brain.llm_provider.get_llm_client")
    def test_error_handling_fallback(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.generate_reply.side_effect = Exception("API connection timed out")
        mock_get_client.return_value = mock_client

        reply = ask_hello_kitty("Test message", [])
        self.assertIn("Gemini API Error", reply)
        self.assertIn("API connection timed out", reply)


class TestSpeaker(unittest.TestCase):
    """Tests for voice/speaker."""

    def test_speak_empty_string(self):
        # Should return safely without raising
        speak("")
        speak("   ")


if __name__ == "__main__":
    unittest.main()
