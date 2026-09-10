"""
Configuration package for Hello Kitty AI Voice Assistant.
"""
from .settings import (
    MODEL_PROVIDER,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    WAKE_WORD,
    VOICE_LANGUAGE,
    validate_config,
)

__all__ = [
    "MODEL_PROVIDER",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "WAKE_WORD",
    "VOICE_LANGUAGE",
    "validate_config",
]
