"""
speaker.py - Text-to-Speech (TTS) module for Hello Kitty.
Uses Google Text-to-Speech (gTTS) to synthesize speech and pygame to play audio.
Includes state tracking, acoustic echo buffer, and clean separation between
speaking and listening to prevent microphone feedback loops.
"""

import io
import os
import sys
import time
import threading
from config.settings import VOICE_LANGUAGE

# Suppress pygame startup welcome message
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Ensure Windows terminal can print unicode characters cleanly
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import pygame
except ImportError:
    pygame = None

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

# Global Speech State to prevent microphone from listening while speaking
_SPEECH_LOCK = threading.Lock()
IS_SPEAKING: bool = False


def is_currently_speaking() -> bool:
    """Returns True if Hello Kitty is currently outputting speech."""
    global IS_SPEAKING
    return IS_SPEAKING


def ensure_mixer_initialized():
    """Initializes pygame mixer once with optimal settings if not already active."""
    if pygame is None:
        return
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            pygame.mixer.set_num_channels(16)
        except Exception as exc:
            print(f"[Speaker Notice]: Pygame mixer init note: {exc}", flush=True)


def speak(text: str, language: str = VOICE_LANGUAGE) -> None:
    """
    Synthesizes speech from text using gTTS and plays it via pygame.mixer.Sound.
    Uses an in-memory buffer (BytesIO) and an independent sound channel so that
    background music (pygame.mixer.music) is never killed.

    Guarantees:
    1. Sets IS_SPEAKING = True and prints [Speaking...]
    2. Ducks background music during speech and restores afterwards
    3. Blocks until audio playback completes
    4. Waits an extra 0.45s acoustic settling buffer to prevent mic feedback
    5. Prints [Done speaking, now listening] and resets IS_SPEAKING = False
    """
    global IS_SPEAKING

    if not text or not text.strip():
        return

    clean_text = text.strip()
    print(f"\n[Hello Kitty]: {clean_text}\n", flush=True)

    if gTTS is None or pygame is None:
        print("[Speaker Notice]: 'gTTS' or 'pygame' is not installed. Spoken text shown above.", flush=True)
        return

    with _SPEECH_LOCK:
        IS_SPEAKING = True
        print("[Speaking...]", flush=True)

        music_was_busy = False
        try:
            # 1. Synthesize audio into in-memory BytesIO buffer
            fp = io.BytesIO()
            tts = gTTS(text=clean_text, lang=language, slow=False)
            tts.write_to_fp(fp)
            fp.seek(0)

            # 2. Ensure pygame mixer is initialized
            ensure_mixer_initialized()

            # 3. Duck background music volume if active
            try:
                if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                    music_was_busy = True
                    pygame.mixer.music.set_volume(0.15)
            except Exception:
                pass

            # 4. Load sound and play on a dedicated mixer channel
            sound = pygame.mixer.Sound(fp)
            channel = sound.play()

            # 5. Wait until speech playback completes
            if channel:
                while channel.get_busy():
                    time.sleep(0.03)
            else:
                # Fallback: estimate duration based on word count
                word_count = len(clean_text.split())
                time.sleep(max(1.0, word_count * 0.28))

            # 6. Restore background music volume if it was playing
            if music_was_busy:
                try:
                    if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                        pygame.mixer.music.set_volume(1.0)
                except Exception:
                    pass

            # 7. Acoustic Echo Buffer: Wait 0.45s for room reverb and speaker echo to die down
            time.sleep(0.45)

        except Exception as exc:
            print(f"[Speaker Warning]: Could not play audio ({exc}).", flush=True)

        finally:
            IS_SPEAKING = False
            print("[Done speaking, now listening]", flush=True)
