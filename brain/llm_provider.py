"""
llm_provider.py - Central AI router and manager for Hello Kitty.
Selects and queries the configured LLM provider (Gemini or OpenAI) with fallback error handling.
"""

from typing import List, Dict, Optional
from config.settings import MODEL_PROVIDER
from .gemini_client import GeminiClient
from .openai_client import OpenAIClient

# Cache clients for efficiency across interactions
_gemini_client: Optional[GeminiClient] = None
_openai_client: Optional[OpenAIClient] = None

# Maximum number of previous dialogue turns (user + assistant) to retain in memory
MAX_MEMORY_TURNS = 10


def get_llm_client():
    """
    Lazily initializes and returns the active LLM client based on MODEL_PROVIDER.
    Defaults to Gemini.
    """
    global _gemini_client, _openai_client

    provider = MODEL_PROVIDER.lower() if MODEL_PROVIDER else "gemini"
    if provider == "openai":
        if _openai_client is None:
            _openai_client = OpenAIClient()
        return _openai_client
    else:
        # Default to Gemini for all AI queries
        if _gemini_client is None:
            _gemini_client = GeminiClient()
        return _gemini_client


def ask_hello_kitty(user_text: str, conversation_history: List[Dict[str, str]]) -> str:
    """
    Dispatches the user's message to the real Gemini AI provider and returns Hello Kitty's reply.
    Never returns fake/canned scripted fallback responses.

    Args:
        user_text (str): The user's input.
        conversation_history (List[Dict[str, str]]): In-memory conversation turns.

    Returns:
        str: Real AI response or actual API error message.
    """
    if not user_text or not user_text.strip():
        return "I'm here! What can I help you with today?"

    # Truncate history to the most recent turns to stay within budget
    recent_history = conversation_history[-MAX_MEMORY_TURNS:] if conversation_history else []

    try:
        client = get_llm_client()
        reply = client.generate_reply(user_text=user_text.strip(), conversation_history=recent_history)
        return reply

    except Exception as exc:
        # Print actual raw error in terminal as explicitly requested
        print(f"\n========================================================")
        print(f" [REAL GEMINI API CALL FAILED]:")
        print(f" {exc}")
        print(f"========================================================\n")
        return f"[Gemini API Error]: {str(exc)}"

# Global in-memory conversation list maintaining the last 5 exchanges (10 turns)
IN_MEMORY_CONVERSATION: List[Dict[str, str]] = []


def get_ai_response(text: str) -> str:
    """
    Requirement 2: Single reusable function that sends user text to the AI Brain
    (Gemini or configured provider), maintains the last 5 exchanges in-memory,
    and returns Hello Kitty's response string.
    """
    global IN_MEMORY_CONVERSATION

    reply = ask_hello_kitty(user_text=text, conversation_history=IN_MEMORY_CONVERSATION)

    # Record turn in memory
    IN_MEMORY_CONVERSATION.append({"role": "user", "content": text})
    IN_MEMORY_CONVERSATION.append({"role": "assistant", "content": reply})

    # Keep only the last 5 exchanges (10 turns: 5 user, 5 assistant)
    if len(IN_MEMORY_CONVERSATION) > MAX_MEMORY_TURNS:
        IN_MEMORY_CONVERSATION = IN_MEMORY_CONVERSATION[-MAX_MEMORY_TURNS:]

    return reply
