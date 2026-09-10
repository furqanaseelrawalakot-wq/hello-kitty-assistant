"""
gemini_client.py - Handles interactions with Google Gemini API.
Translates unified in-memory conversation history into Gemini chat sessions.
Includes automatic multi-model fallback to bypass 429 free tier quota limits
and optional Google Search grounding support for time-sensitive questions.
"""

import warnings
from typing import List, Dict
from config.settings import GEMINI_API_KEY, GEMINI_MODEL, HELLO_KITTY_SYSTEM_PROMPT

# Suppress deprecation/future warnings for clean assistant CLI output
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Preferred order of candidate models for automatic quota failover
FALLBACK_MODELS = [
    GEMINI_MODEL,
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash"
]


class GeminiClient:
    """Wrapper around Google's Gemini Generative AI SDK with auto-quota failover."""

    def __init__(self):
        if genai is None:
            raise ImportError(
                "The 'google-generativeai' package is not installed.\n"
                "Please run: pip install google-generativeai"
            )

        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set. Check your .env file.")

        genai.configure(api_key=GEMINI_API_KEY)

    def _get_model(self, model_name: str, enable_search: bool = False):
        """Initializes a GenerativeModel with Hello Kitty's system persona and optional search grounding."""
        tools = [{"google_search_retrieval": {}}] if enable_search else None
        try:
            return genai.GenerativeModel(
                model_name=model_name,
                system_instruction=HELLO_KITTY_SYSTEM_PROMPT,
                tools=tools
            )
        except TypeError:
            try:
                return genai.GenerativeModel(model_name=model_name, tools=tools)
            except TypeError:
                return genai.GenerativeModel(model_name=model_name)

    def generate_reply(self, user_text: str, conversation_history: List[Dict[str, str]]) -> str:
        """
        Sends the user query along with previous in-memory context to Gemini.
        Automatically retries with fallback models if 429 quota is exceeded.

        Args:
            user_text (str): The current message spoken/typed by the user.
            conversation_history (List[Dict[str, str]]): List of previous messages
                formatted as [{'role': 'user'|'assistant', 'content': '...'}, ...]

        Returns:
            str: Hello Kitty's response text.
        """
        gemini_history = []
        for turn in conversation_history:
            role = "user" if turn["role"] == "user" else "model"
            content = turn.get("content", "").strip()
            if content:
                gemini_history.append({
                    "role": role,
                    "parts": [content]
                })

        # Deduplicate candidate models while preserving order
        candidate_models = []
        for m in FALLBACK_MODELS:
            if m and m not in candidate_models:
                candidate_models.append(m)

        # Detect if query might benefit from Google Search grounding
        time_keywords = ("news", "today", "yesterday", "latest", "recent", "score", "who won")
        wants_search = any(kw in user_text.lower() for kw in time_keywords)

        last_error = None

        # First pass: try with search if time-sensitive; second pass: standard generation
        search_attempts = [True, False] if wants_search else [False]

        for enable_search in search_attempts:
            for model_name in candidate_models:
                try:
                    model = self._get_model(model_name, enable_search=enable_search)
                    chat = model.start_chat(history=gemini_history)
                    response = chat.send_message(user_text)

                    if response and response.text:
                        return response.text.strip()
                    elif response and response.candidates:
                        first_cand = response.candidates[0]
                        if first_cand.content and first_cand.content.parts:
                            return "".join(p.text for p in first_cand.content.parts if hasattr(p, "text")).strip()

                except Exception as exc:
                    last_error = exc
                    err_str = str(exc)
                    if enable_search and ("429" in err_str or "quota" in err_str.lower() or "not supported" in err_str.lower()):
                        print(f"[Search Grounding Notice]: Search retrieval quota limited on current tier. Falling back to direct model...", flush=True)
                        break  # Break out of search loop to proceed to direct model without search
                    elif "429" in err_str or "quota" in err_str.lower() or "404" in err_str:
                        print(f"\n[Gemini Notice]: Model '{model_name}' hit rate limit/quota. Retrying with next available model...", flush=True)
                        continue
                    else:
                        print(f"\n[Gemini Warning]: Error with '{model_name}': {exc}. Trying fallback...", flush=True)
                        continue

        if last_error:
            raise last_error

        return "I'm sorry, I couldn't generate a response right now."
