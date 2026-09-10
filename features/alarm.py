"""
alarm.py - In-memory, background-threaded alarm manager for Hello Kitty.
Stores active alarms in Python memory (no database) and alerts the user with
both audible alarm chimes (pygame.mixer.Sound) and spoken voice alerts (gTTS).
"""

import os
import time
import re
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pygame

# In-memory registry of active alarms (resets when program closes)
ACTIVE_ALARMS: List[Dict] = []
ACTIVE_ALARM_THREADS: Dict[int, threading.Thread] = {}
_alarm_id_counter = 1

# Path to the alarm chime sound file
ALARM_SOUND_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "alarm_chime.wav"
)


def ensure_mixer_initialized():
    """Ensures pygame mixer is active and configured for alarm sound playback."""
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            pygame.mixer.set_num_channels(16)
        except Exception as exc:
            print(f"[Alarm Mixer Notice]: {exc}", flush=True)


def parse_alarm_duration(text: str) -> Optional[tuple[int, str]]:
    """
    Parses natural language duration from user command.
    Supports formats like:
      - '10 seconds'
      - '2 minutes'
      - '1 hour'
      - '5 mins'
      - '30 secs'
      - '5:30 pm' or '14:00'

    Returns:
        tuple[int, str]: (seconds_to_wait, human_readable_label)
    """
    clean_text = text.lower().strip()

    # Pattern 1: Relative seconds
    sec_match = re.search(r'(\d+)\s*(?:seconds?|secs?)', clean_text)
    if sec_match:
        secs = int(sec_match.group(1))
        return secs, f"{secs} seconds"

    # Pattern 2: Relative minutes
    min_match = re.search(r'(\d+)\s*(?:minutes?|mins?)', clean_text)
    if min_match:
        mins = int(min_match.group(1))
        return mins * 60, f"{mins} minute{'s' if mins > 1 else ''}"

    # Pattern 3: Relative hours
    hr_match = re.search(r'(\d+)\s*(?:hours?|hrs?)', clean_text)
    if hr_match:
        hrs = int(hr_match.group(1))
        return hrs * 3600, f"{hrs} hour{'s' if hrs > 1 else ''}"

    # Pattern 4: Exact time e.g. "5:30 pm", "14:00"
    clock_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', clean_text)
    if clock_match:
        hr = int(clock_match.group(1))
        minute = int(clock_match.group(2))
        period = clock_match.group(3)

        if period:
            if period == 'pm' and hr < 12:
                hr += 12
            elif period == 'am' and hr == 12:
                hr = 0

        now = datetime.now()
        target = now.replace(hour=hr, minute=minute, second=0, microsecond=0)
        if target <= now:
            # If target time is earlier today, schedule for tomorrow
            target += timedelta(days=1)

        diff_seconds = int((target - now).total_seconds())
        label = target.strftime("%I:%M %p").lstrip("0")
        return diff_seconds, label

    return None


def play_alarm_chime(loops: int = 2):
    """
    Plays the audible alarm chime sound using pygame.mixer.Sound on a dedicated channel.
    Does not conflict with or cut off background music (pygame.mixer.music).
    """
    try:
        ensure_mixer_initialized()

        if os.path.exists(ALARM_SOUND_PATH):
            sound = pygame.mixer.Sound(ALARM_SOUND_PATH)
            sound.set_volume(1.0)
            channel = sound.play(loops=loops)
            print(f"[Alarm Sound]: Playing alarm chime (loops={loops}) on channel {channel}...", flush=True)
            if channel:
                while channel.get_busy():
                    time.sleep(0.04)
        else:
            print(f"[Alarm Sound Notice]: Alarm sound file not found at {ALARM_SOUND_PATH}", flush=True)
    except Exception as exc:
        print(f"[Alarm Sound Error]: Could not play chime: {exc}", flush=True)


def _alarm_worker(seconds: int, label: str, alarm_id: int):
    """
    Background worker that sleeps for the duration and alerts the user:
    1. Prints [ALARM TRIGGERED] marker
    2. Ducks any active background music
    3. Plays audible alarm chime (pygame.mixer.Sound)
    4. Speaks voice alert (gTTS)
    5. Plays closing chime and restores music
    """
    # Sleep until target alarm time
    time.sleep(seconds)

    print("\n" + "*" * 65, flush=True)
    print(f" >>> [ALARM TRIGGERED]: Time's up for your {label} alarm! <<<", flush=True)
    print("*" * 65 + "\n", flush=True)

    music_was_playing = False
    try:
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            music_was_playing = True
            pygame.mixer.music.set_volume(0.1)
    except Exception:
        pass

    try:
        # 1. Play audible alarm chime
        play_alarm_chime(loops=2)

        # 2. Speak voice alert
        from voice.speaker import speak
        speak(f"Time's up! Your alarm for {label} is ringing!")

        # 3. Play closing chime
        play_alarm_chime(loops=1)

    except Exception as exc:
        print(f"[Alarm Alert Error]: {exc}", flush=True)

    finally:
        # Restore background music volume if it was playing
        if music_was_playing:
            try:
                if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                    pygame.mixer.music.set_volume(1.0)
            except Exception:
                pass

        # Remove from in-memory active lists
        global ACTIVE_ALARMS, ACTIVE_ALARM_THREADS
        ACTIVE_ALARMS = [a for a in ACTIVE_ALARMS if a["id"] != alarm_id]
        if alarm_id in ACTIVE_ALARM_THREADS:
            del ACTIVE_ALARM_THREADS[alarm_id]


def set_alarm_from_command(command: str) -> str:
    """
    Parses command, registers alarm in memory, calculates exact target time,
    and launches background thread with active reference tracking.

    Returns:
        str: Hello Kitty's confirmation reply.
    """
    global _alarm_id_counter, ACTIVE_ALARM_THREADS

    parsed = parse_alarm_duration(command)
    if not parsed:
        return "I couldn't tell what time to set the alarm for. Try saying 'set an alarm for 10 seconds' or 'set an alarm for 5 minutes'."

    seconds, label = parsed
    if seconds <= 0:
        return "The alarm time must be in the future!"

    alarm_id = _alarm_id_counter
    _alarm_id_counter += 1

    target_dt = datetime.now() + timedelta(seconds=seconds)
    target_str = target_dt.strftime("%I:%M:%S %p")

    print(f"[Alarm Scheduler]: Alarm #{alarm_id} scheduled for {label} (Target Time: {target_str}, wait: {seconds}s)", flush=True)

    alarm_entry = {
        "id": alarm_id,
        "label": label,
        "seconds": seconds,
        "target_time": target_str,
        "created_at": datetime.now().strftime("%I:%M:%S %p"),
    }
    ACTIVE_ALARMS.append(alarm_entry)

    # Launch timer in background thread with stored reference (prevents GC)
    timer_thread = threading.Thread(
        target=_alarm_worker,
        args=(seconds, label, alarm_id),
        name=f"AlarmThread-{alarm_id}",
        daemon=True
    )
    ACTIVE_ALARM_THREADS[alarm_id] = timer_thread
    timer_thread.start()

    return f"Done! I have set an alarm for {label} from now (at {target_str})."
