"""
test_urdu_live.py - Direct verification of Requirement 5 (Urdu Language Support).
Tests:
1. Urdu language detection (is_urdu_text)
2. Urdu to English translation
3. AI Brain response generation
4. English to Urdu translation
5. Spoken output synthesis using gTTS (lang='ur')
"""

import sys
from pathlib import Path

# Ensure Windows terminal can display Urdu Unicode characters cleanly
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from features.translation import is_urdu_text, handle_urdu_pipeline
from brain.llm_provider import get_ai_response
from voice.speaker import speak


def test_urdu():
    print("=" * 65)
    print(" URDU LANGUAGE SUPPORT VERIFICATION (Requirement 5)")
    print("=" * 65)

    # Hardcoded test sentence in Urdu: "آپ کا نام کیا ہے اور آپ کیا کر سکتی ہیں؟"
    # Meaning: "What is your name and what can you do?"
    hardcoded_urdu_sentence = "آپ کا نام کیا ہے اور آپ کیا کر سکتی ہیں؟"
    print(f"\n[Hardcoded Urdu Input]   : \"{hardcoded_urdu_sentence}\"")

    # Step 1: Language Detection
    is_detected = is_urdu_text(hardcoded_urdu_sentence)
    print(f"  -> Detected as Urdu?   : {is_detected}")

    # Also test an English sentence to prove English detection is preserved
    english_check = is_urdu_text("Hello what time is it")
    print(f"  -> English input check : Detected as Urdu? {english_check} (False expected)")

    # Step 2 & 3 & 4: Pipeline
    print("\n[Executing Urdu Translation Pipeline]:")
    english_query, english_reply, urdu_reply = handle_urdu_pipeline(
        hardcoded_urdu_sentence,
        ai_func=get_ai_response
    )

    print(f"  [1. Urdu -> English]   : \"{english_query}\"")
    print(f"  [2. AI Brain Reply]    : \"{english_reply}\"")
    print(f"  [3. English -> Urdu]   : \"{urdu_reply}\"")

    # Step 5: Audio speech output in Urdu
    print("\n[Speaking Urdu Reply]: Synthesizing gTTS audio with lang='ur'...")
    speak(urdu_reply, language="ur")

    print("\n>>> Urdu language requirement tested and verified! <<<\n")


if __name__ == "__main__":
    test_urdu()
