"""
openai_client.py - Handles interactions with OpenAI API (ChatGPT).
Translates unified in-memory conversation history into OpenAI Chat Completion messages.
"""

from typing import List, Dict
from config.settings import OPENAI_API_KEY, OPENAI_MODEL, HELLO_KITTY_SYSTEM_PROMPT

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class OpenAIClient:
    """Wrapper around OpenAI's official Python SDK."""

    def __init__(self):
        if OpenAI is None:
            raise ImportError(
                "The 'openai' package is not installed.\n"
                "Please run: pip install openai"
            )

        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set. Check your .env file.")
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def generate_reply(self, user_text: str, conversation_history: List[Dict[str, str]]) -> str:
        """
        Sends the user query along with previous in-memory context to OpenAI.

        Args:
            user_text (str): The current message spoken/typed by the user.
            conversation_history (List[Dict[str, str]]): List of previous messages
                formatted as [{'role': 'user'|'assistant', 'content': '...'}, ...]

        Returns:
            str: Hello Kitty's response text.
        """
        # Build messages list starting with system instruction
        messages = [{"role": "system", "content": HELLO_KITTY_SYSTEM_PROMPT}]

        # Append in-memory past conversation turns
        for turn in conversation_history:
            messages.append({
                "role": turn["role"],
                "content": turn["content"]
            })

        # Append current user prompt
        messages.append({"role": "user", "content": user_text})

        # Call OpenAI Chat Completion API
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=250,
        )

        reply = response.choices[0].message.content
        if reply:
            return reply.strip()
        return "I'm sorry, I couldn't generate a response right now."
