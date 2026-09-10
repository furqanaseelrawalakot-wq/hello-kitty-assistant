"""
listener.py - Speech-to-Text (STT) module for Hello Kitty.
Uses the SpeechRecognition library to capture microphone input, detect the wake word,
and transcribe spoken user commands into text with robust timing, noise calibration,
and transparent terminal logging.
"""

import time
from typing import Optional
from config.settings import WAKE_WORD, VOICE_LANGUAGE
from voice.speaker import is_currently_speaking

try:
    import speech_recognition as sr
except ImportError:
    sr = None


class VoiceListener:
    """Handles microphone capture and speech recognition."""

    def __init__(self, wake_word: str = WAKE_WORD, language: str = VOICE_LANGUAGE):
        if sr is None:
            raise ImportError(
                "The 'SpeechRecognition' package is not installed.\n"
                "Please run: pip install SpeechRecognition PyAudio"
            )

        self.wake_word = wake_word.strip().lower()
        self.language = language
        self.recognizer = sr.Recognizer()

        # Dynamic sensitivity threshold to adapt to quiet or noisy rooms
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 300
        # Allow natural breathing pauses (0.8s) so speech isn't cut off mid-sentence
        self.recognizer.pause_threshold = 0.8

        # Flexible wake phrase variants (e.g. "hello kitty", "hey kitty", "kitty")
        self.wake_variants = [self.wake_word, "hey kitty", "hi kitty", "kitty", "hello kiti", "hallo kitty"]

    def calibrate_ambient_noise(self, duration: float = 1.0) -> bool:
        """
        Calibrates the microphone energy threshold against background ambient noise.
        Ensures threshold doesn't drop too low (which would cause constant false triggering).
        """
        try:
            print("[Microphone]: Calibrating for ambient room noise, please wait...", flush=True)
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
            # Ensure minimum threshold of 250 to avoid fan/breathing loops
            if self.recognizer.energy_threshold < 250:
                self.recognizer.energy_threshold = 250
            print(f"[Microphone]: Calibrated! Energy threshold set to {int(self.recognizer.energy_threshold)}.", flush=True)
            return True
        except Exception as exc:
            print(f"[Microphone Error]: Failed to calibrate ambient noise: {exc}", flush=True)
            return False

    def listen_for_wake_word(self, timeout: Optional[float] = None) -> tuple[bool, str]:
        """
        Listens in short intervals for the wake phrase.
        If the user says both the wake word AND the command in one breath
        (e.g., 'Hello Kitty what time is it'), it captures both!

        Returns:
            tuple[bool, str]: (is_wake_detected, immediate_command_text)
        """
        # Strictly avoid listening while Hello Kitty is speaking out loud
        if is_currently_speaking():
            return False, ""

        try:
            with sr.Microphone() as source:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=3.5)

            # Transcribe audio using Google Speech Recognition
            text = self.recognizer.recognize_google(audio, language=self.language).lower().strip()
            print(f"[Mic Heard]: \"{text}\"", flush=True)

            # Check if any wake variant is present
            for variant in self.wake_variants:
                if variant in text:
                    parts = text.split(variant, 1)
                    remaining_command = parts[1].strip(" ,.!?") if len(parts) > 1 else ""
                    return True, remaining_command

            return False, ""

        except sr.WaitTimeoutError:
            # Silence during continuous wake word polling is normal
            return False, ""

        except sr.UnknownValueError:
            # Unintelligible ambient sound while waiting for wake word
            return False, ""

        except sr.RequestError as req_err:
            print(f"[STT Network Warning]: Speech recognition service unreachable ({req_err}).", flush=True)
            return False, ""

        except Exception as exc:
            print(f"[Listener Warning]: Wake detection exception: {exc}", flush=True)
            return False, ""

    def listen_for_command(self, timeout: float = 5.0, phrase_limit: float = 8.0) -> Optional[str]:
        """
        Step 1 & 2: Listens for the user's spoken command after the wake word was triggered.

        Args:
            timeout (float): Max seconds to wait for speech to begin (default: 5.0s).
            phrase_limit (float): Max seconds to record once speech starts (default: 8.0s).

        Returns:
            Optional[str]: Recognized text, "UNINTELLIGIBLE", "SERVICE_ERROR", or None.
        """
        # Ensure Hello Kitty has finished speaking completely before opening microphone
        while is_currently_speaking():
            time.sleep(0.08)

        try:
            with sr.Microphone() as source:
                # Step 1.3: Recalibrate briefly for post-greeting room audio/speaker echo
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)

                # Step 1.4: Explicit terminal logs before and after listening
                print("[Listening now...]", flush=True)
                try:
                    audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
                finally:
                    print("[Done listening]", flush=True)

            # Step 2: Speech Recognition with transparent error logging
            try:
                text = self.recognizer.recognize_google(audio, language=self.language).strip()
                return text

            except sr.UnknownValueError:
                # Try fallback Urdu speech recognition
                try:
                    text = self.recognizer.recognize_google(audio, language="ur-PK").strip()
                    print("[Language Recognized]: Urdu (ur-PK)", flush=True)
                    return text
                except sr.UnknownValueError:
                    print("[Recognition Error]: UnknownValueError - Audio recorded but could not be understood.", flush=True)
                    return "UNINTELLIGIBLE"

            except sr.RequestError as req_err:
                print(f"[Recognition Error]: RequestError - Speech recognition network service unreachable ({req_err}).", flush=True)
                return "SERVICE_ERROR"

        except sr.WaitTimeoutError:
            print("[Recognition Error]: Timeout - No speech detected within 5 seconds.", flush=True)
            return None

        except Exception as exc:
            print(f"[Listener Error]: Microphone capture failed: {exc}", flush=True)
            return None
