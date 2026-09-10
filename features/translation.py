"""
translation.py - Automatic Urdu language detection and bi-directional translation.
Uses langdetect for language identification and deep-translator (GoogleTranslator)
to bridge Urdu queries with the AI brain, returning spoken Urdu via gTTS.
"""

import re
from typing import Tuple, Callable
from langdetect import detect, DetectorFactory
from deep_translator import GoogleTranslator

# Enforce deterministic results from langdetect
DetectorFactory.seed = 0


def is_urdu_text(text: str) -> bool:
    """
    Detects if the given text is in Urdu using both Unicode character range
    and langdetect language scoring.
    """
    if not text or not text.strip():
        return False

    clean_text = text.strip()

    # Fast Check 1: Does the text contain Perso-Arabic / Urdu Unicode characters?
    # Range \u0600-\u06FF covers Urdu/Arabic characters
    if re.search(r'[\u0600-\u06FF]', clean_text):
        return True

    # Check 2: Try statistical language detection with langdetect
    try:
        lang = detect(clean_text)
        return lang == 'ur'
    except Exception:
        return False


def translate_to_english(urdu_text: str) -> str:
    """Translates Urdu text to English using deep-translator."""
    try:
        from deep_translator import MyMemoryTranslator
        translated = MyMemoryTranslator(source='ur-PK', target='en-GB').translate(urdu_text)
        if translated:
            return translated.strip()
    except Exception:
        pass

    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source='ur', target='en').translate(urdu_text)
        if translated:
            return translated.strip()
    except Exception as exc:
        print(f"[Translation Error]: Urdu to English fallback failed ({exc})")

    return urdu_text


def translate_to_urdu(english_text: str) -> str:
    """Translates English text to Urdu using deep-translator."""
    try:
        from deep_translator import MyMemoryTranslator
        translated = MyMemoryTranslator(source='en-GB', target='ur-PK').translate(english_text)
        if translated:
            return translated.strip()
    except Exception:
        pass

    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source='en', target='ur').translate(english_text)
        if translated:
            return translated.strip()
    except Exception as exc:
        print(f"[Translation Error]: English to Urdu fallback failed ({exc})")

    return english_text


def handle_urdu_pipeline(urdu_text: str, ai_func: Callable[[str], str]) -> Tuple[str, str, str]:
    """
    Executes the full Urdu conversation pipeline:
    1. Translates Urdu text to English.
    2. Sends English prompt to AI brain.
    3. Translates AI's English reply back into Urdu.

    Returns:
        Tuple[str, str, str]: (english_query, english_reply, urdu_reply)
    """
    # Step 1: Urdu -> English
    english_query = translate_to_english(urdu_text)

    # Step 2: English query -> AI Brain
    english_reply = ai_func(english_query)

    # Step 3: English AI reply -> Urdu
    urdu_reply = translate_to_urdu(english_reply)

    return english_query, english_reply, urdu_reply
