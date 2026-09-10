"""
main.py - Entry point for the Hello Kitty AI Voice Assistant.
Executes the terminal voice assistant loop (Core Voice Loop) with transparent
logging, responsive microphone capture, built-in feature routing, and Gemini AI.
"""

import sys
import os
from pathlib import Path

# Ensure immediate unbuffered terminal output on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Ensure the project root is on Python's search path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Explicitly load .env from project root
try:
    from dotenv import load_dotenv
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        load_dotenv(override=True)
except ImportError:
    pass

from config.settings import (
    validate_config,
    MODEL_PROVIDER,
    WAKE_WORD,
    GEMINI_MODEL
)
from voice.speaker import speak
from voice.listener import VoiceListener
from brain.llm_provider import get_ai_response
from features.dispatcher import handle_feature, has_pending_action, clear_pending_action
from features.translation import is_urdu_text, handle_urdu_pipeline

BANNER = r"""
  /\_/\   =================================================
 ( o.o )   HELLO KITTY - AI VOICE ASSISTANT
  > ^ <   =================================================
"""

EXIT_PHRASES = {"exit", "quit", "goodbye", "bye", "stop", "shut down", "go to sleep"}


def print_header(status_msg: str):
    print(BANNER, flush=True)
    print(f"  [Status]   : {status_msg}", flush=True)
    print(f"  [Provider] : {MODEL_PROVIDER.upper()}", flush=True)
    print(f"  [Model]    : {GEMINI_MODEL}", flush=True)
    print(f"  [Wake Word]: \"{WAKE_WORD}\"", flush=True)
    print("  [Memory]   : In-memory conversation history enabled (no database)", flush=True)
    print("  [Control]  : Press Ctrl+C in this terminal anytime to stop", flush=True)
    print("  =================================================\n", flush=True)


def main():
    # 1. Configuration & API Key Validation
    is_valid, status_msg = validate_config()
    print_header(status_msg)

    if not is_valid:
        print("\n" + "=" * 60, flush=True)
        print(" CONFIGURATION WARNING:", flush=True)
        print("=" * 60, flush=True)
        print(status_msg, flush=True)
        print("\nTo fix this:", flush=True)
        print("1. Set GEMINI_API_KEY in your .env file.", flush=True)
        print("2. Restart: python scripts/main.py\n", flush=True)
        sys.exit(1)

    # 2. In-memory conversation context (reset on each run, no database needed)
    conversation_history = []

    # 3. Initialize Voice Listener and Microphone
    try:
        listener = VoiceListener()
    except ImportError as imp_err:
        print("\n" + "=" * 60, flush=True)
        print(" ENVIRONMENT NOTICE:", flush=True)
        print("=" * 60, flush=True)
        print(imp_err, flush=True)
        print("\nRun using the configured virtual environment:", flush=True)
        print("  .\\venv\\Scripts\\python.exe scripts/main.py\n", flush=True)
        sys.exit(1)

    calibrated = listener.calibrate_ambient_noise()
    if not calibrated:
        print("[Microphone Warning]: Could not calibrate. Continuing with default sensitivity.", flush=True)

    # 4. Greet the user upon starting
    initial_greeting = f"Hello! I am Hello Kitty. Say '{WAKE_WORD}' whenever you need me!"
    speak(initial_greeting)

    print(f"\n[Ready]: Waiting for wake phrase: '{WAKE_WORD}'...\n", flush=True)

    # 5. Core Voice Loop
    try:
        while True:
            # If waiting for a follow-up answer (e.g. song name, city, alarm time), listen immediately!
            if has_pending_action():
                print("\n[Hello Kitty]: Listening for your follow-up answer...", flush=True)
                user_command = listener.listen_for_command(timeout=6.0, phrase_limit=8.0)
                if not user_command:
                    clear_pending_action()
                    print(f"[Hello Kitty]: Follow-up timed out. Resuming wake word detection for '{WAKE_WORD}'...\n", flush=True)
                    continue
            else:
                # Step A: Listen for Wake Word
                wake_detected, immediate_command = listener.listen_for_wake_word(timeout=3.0)
                if not wake_detected:
                    continue

                # Step B: Wake word recognized!
                print("\n" + "-" * 50, flush=True)
                print(f">>> [Wake Word Detected]: \"{WAKE_WORD}\" <<<", flush=True)
                print("-" * 50, flush=True)

                if immediate_command:
                    # User spoke command in the same breath (e.g. 'Hello Kitty what time is it')
                    user_command = immediate_command
                else:
                    # Prompt the user that Kitty is ready
                    speak("Yes? I'm listening!")
                    # Step C: Capture the user's spoken command with generous defaults (timeout=5s, limit=8s)
                    user_command = listener.listen_for_command(timeout=5.0, phrase_limit=8.0)

            # Handle silence / timeout
            if not user_command:
                print(f"[Hello Kitty]: Resuming wake word detection for '{WAKE_WORD}'...\n", flush=True)
                continue

            # Handle unclear audio
            if user_command == "UNINTELLIGIBLE":
                speak("Sorry, I didn't catch that. Could you please say it again?")
                continue

            # Handle network/service error
            if user_command == "SERVICE_ERROR":
                speak("I am having trouble connecting to speech recognition. Please check your internet.")
                continue

            # Step 3 Log: Print recognized user speech
            print(f"[Mic Heard]: {user_command}", flush=True)

            # Step D: Check for exit commands
            normalized_command = user_command.lower().strip().rstrip(".!?")
            if normalized_command in EXIT_PHRASES or any(normalized_command.startswith(p) for p in EXIT_PHRASES):
                farewell = "Goodbye! Have a wonderful day!"
                speak(farewell)
                print("\n[Hello Kitty]: Assistant stopped cleanly. See you next time!\n", flush=True)
                break

            # Step E.1: Check Urdu language support (Requirement 5)
            if is_urdu_text(user_command):
                print("\n[Language]: Urdu detected! Running Urdu translation pipeline...", flush=True)
                english_q, english_rep, urdu_rep = handle_urdu_pipeline(user_command, get_ai_response)
                print(f"[AI Reply (Urdu)]: {urdu_rep}", flush=True)
                speak(urdu_rep, language="ur")
                conversation_history.append({"role": "user", "content": user_command})
                conversation_history.append({"role": "assistant", "content": urdu_rep})
                print(f"\n[Ready]: Waiting for wake phrase: '{WAKE_WORD}'...\n", flush=True)
                continue

            # Step E.2: Check built-in features (Time, Date, Weather, Alarm, Music, Singing)
            is_feature, feature_reply = handle_feature(user_command)
            if is_feature:
                print(f"[Hello Kitty (Feature)]: {feature_reply}", flush=True)
                speak(feature_reply)
                conversation_history.append({"role": "user", "content": user_command})
                conversation_history.append({"role": "assistant", "content": feature_reply})
                print(f"\n[Ready]: Waiting for wake phrase: '{WAKE_WORD}'...\n", flush=True)
                continue

            # Step F: Query Central AI Brain (get_ai_response) and print [AI Reply]
            print("[Hello Kitty]: Thinking...", flush=True)
            try:
                reply = get_ai_response(user_command)
                print(f"[AI Reply]: {reply}", flush=True)
                speak(reply)
                conversation_history.append({"role": "user", "content": user_command})
                conversation_history.append({"role": "assistant", "content": reply})
            except Exception as brain_err:
                err_msg = f"I'm sorry, I ran into an issue getting an answer: {brain_err}"
                print(f"[AI Brain Error]: {brain_err}", flush=True)
                speak(err_msg)

            print(f"\n[Ready]: Waiting for wake phrase: '{WAKE_WORD}'...\n", flush=True)

    except KeyboardInterrupt:
        print("\n\n[Hello Kitty]: KeyboardInterrupt received. Exiting gracefully. Goodbye!\n", flush=True)


if __name__ == "__main__":
    main()
