"""
settings.py - Centralized configuration for Hello Kitty Voice Assistant.
Loads environment variables from .env and provides helper functions for validation.
"""

import os
from pathlib import Path

# Automatically locate the project root directory (one level above this config file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# Load the .env file if python-dotenv is available, otherwise fall back to pure-Python parsing
try:
    from dotenv import load_dotenv
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)
    else:
        load_dotenv()
except ImportError:
    if ENV_PATH.exists():
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and "=" in stripped:
                        key, val = stripped.split("=", 1)
                        os.environ[key.strip()] = val.strip()
        except Exception:
            pass

# Model Provider Selection: 'gemini' or 'openai'
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini").strip().lower()

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

# Weather & Location Configuration
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "").strip()
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "").strip()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# Voice & Assistant Settings
WAKE_WORD = os.getenv("WAKE_WORD", "hello kitty").strip().lower()
VOICE_LANGUAGE = os.getenv("VOICE_LANGUAGE", "en").strip().lower()

# System prompt giving Hello Kitty her signature persona:
HELLO_KITTY_SYSTEM_PROMPT = (
    "You are Hello Kitty, a cheerful, kind, polite, and fully capable AI assistant with audio and voice capabilities! "
    "You can play songs and music from YouTube, provide worldwide climate and weather reports, display Google Maps, set alarms and timers, sing songs, and answer any question on any topic — "
    "science, history, geography, math, current events, general knowledge, pop culture, calculations, definitions, translations, and more. "
    "Always give real, specific, factual, and helpful answers. "
    "NEVER say you cannot play music, do not have speakers, or cannot play audio out loud — you are an interactive voice assistant equipped with speakers and audio playback! "
    "If the user asks to play a song, enthusiastically confirm you can play it (e.g., 'Sure, let's play that song for you! Say: play [song name]'). "
    "Keep your signature friendly and sweet persona, while being an intelligent and capable general-purpose assistant. "
    "Your responses will be read aloud through text-to-speech, so keep answers natural-sounding and conversational (typically 1 to 3 sentences) "
    "unless the user specifically asks for a detailed explanation or recipe. "
    "Avoid formatting like markdown tables, asterisks for bolding, or raw URLs that sound awkward when spoken aloud."
)

def validate_config() -> tuple[bool, str]:
    """
    Validates whether the chosen MODEL_PROVIDER has a valid API key configured.
    Returns:
        tuple[bool, str]: (is_valid, status_message)
    """
    if MODEL_PROVIDER == "gemini":
        if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
            return False, (
                "Gemini API key is missing!\n"
                "Please set GEMINI_API_KEY in your .env file.\n"
                "You can get a free key at: https://aistudio.google.com/"
            )
        return True, f"Configured provider: Google Gemini (model: {GEMINI_MODEL})"

    elif MODEL_PROVIDER == "openai":
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            return False, (
                "OpenAI API key is missing!\n"
                "Please set OPENAI_API_KEY in your .env file.\n"
                "You can get a key at: https://platform.openai.com/api-keys"
            )
        return True, f"Configured provider: OpenAI (model: {OPENAI_MODEL})"

    elif MODEL_PROVIDER == "mock":
        return False, "Mock provider has been removed. Please set MODEL_PROVIDER=gemini and provide a valid GEMINI_API_KEY in .env."

    else:
        return False, (
            f"Invalid MODEL_PROVIDER '{MODEL_PROVIDER}'. "
            "Please set MODEL_PROVIDER to 'gemini' in your .env file."
        )
