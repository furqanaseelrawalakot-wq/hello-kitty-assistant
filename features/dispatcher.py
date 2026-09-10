"""
dispatcher.py - Flexible command dispatcher with multi-turn follow-up state.
Intercepts built-in feature commands (Google Maps & Climate, Music, Weather, Alarms, Time, Date, Singing)
with natural phrasing variations before querying the central AI brain.
"""

import re
from typing import Tuple, Optional
from .time_date import get_current_time, get_current_date
from .weather import get_weather_for_city, get_climate_and_map
from .alarm import set_alarm_from_command, parse_alarm_duration
from .music import play_music, stop_music, pause_music, resume_music
from .singing import extract_singing_topic, sing_song_about
from config.settings import DEFAULT_CITY

# Multi-turn Pending Conversational State
PENDING_ACTION: Optional[str] = None

GENERIC_MUSIC_PHRASES = {
    "", "some music", "a song", "music", "something", "songs",
    "any song", "anything", "some songs", "youtube", "youtube for me",
    "a song for me", "some music for me", "music for me", "something for me",
    "a song please", "some music please", "music please", "a track for me",
    "a song to me", "some songs for me", "songs for me", "a tune", "some tunes",
    "a track", "track", "tracks", "the song"
}

CANCEL_PHRASES = {
    "cancel", "never mind", "nevermind", "stop", "abort",
    "forget it", "no thanks", "no"
}


def has_pending_action() -> bool:
    """Returns True if the assistant is currently waiting for a follow-up answer."""
    global PENDING_ACTION
    return PENDING_ACTION is not None


def get_pending_action() -> Optional[str]:
    """Returns the current pending action name, or None."""
    global PENDING_ACTION
    return PENDING_ACTION


def clear_pending_action():
    """Clears any active follow-up state."""
    global PENDING_ACTION
    PENDING_ACTION = None


def extract_music_request(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detects if command is a music request and extracts the song name if present.
    Supports varied conversational forms like:
    - 'play 295'
    - 'I want to song of Sidhu Moose wala'
    - 'I would have a song of Sidhu Moose wala can you play it please'
    - 'can you play song of attaullah khan'
    - 'put on believer'

    Returns:
        Tuple[bool, Optional[str]]: (is_music, song_name_or_none)
    """
    clean = text.lower().strip().rstrip(".!?")

    # 0. Strip leading wake words, polite greetings, and question starters
    clean = re.sub(
        r'^(?:(?:hello\s+)?kitty\s+)?(?:please\s+)?(?:can you\s+|could you\s+|would you\s+)?(?:i\s+want\s+you\s+to\s+)?',
        '', clean
    ).strip()

    # Strip conversational desire / intent prefixes
    clean = re.sub(
        r'^(?:i\s+(?:just\s+)?(?:want|would\s+like|would\s+have|would\s+love)\s+(?:to\s+(?:hear|listen\s+to|play)|a\s+)?(?:to\s+)?)',
        '', clean
    ).strip()

    # Strip conversational suffixes like 'can you play it please', 'play it please', 'on youtube'
    clean = re.sub(
        r'\b(?:can\s+you\s+play\s+it(?:\s+please)?|could\s+you\s+play\s+it(?:\s+please)?|play\s+it\s+please|play\s+it|on\s+youtube|for\s+me|for\s+us|to\s+me|to\s+us|please)\b',
        '', clean
    ).strip()

    # 1. Look anywhere in the sentence for 'song/songs/music/track of/by <artist>'
    match_of = re.search(r'(?:the\s+)?(?:song|songs|music|track|tracks)\s+(?:of|by)\s+(.*)', clean)
    if match_of:
        song = match_of.group(1).strip()
        song = re.sub(r'\b(?:can\s+you\s+play\s+it|play\s+it|on\s+youtube|please|for\s+me)\b', '', song).strip()
        if song and song not in GENERIC_MUSIC_PHRASES:
            return True, song
        return True, None

    # 2. Check general music trigger verbs or phrases
    is_music_trigger = (
        clean.startswith("play") or 
        clean.startswith("put on") or 
        "want to listen to" in clean or 
        "listen to" in clean or 
        "hear" in clean or
        "open youtube" in clean or
        clean.startswith("song") or
        clean.startswith("music")
    )
    if not is_music_trigger:
        return False, None

    # Exclude non-music verbs like 'play with me', 'play a game'
    if any(non in clean for non in ["play with", "play a game", "play game", "play tag"]):
        return False, None

    target = clean

    # Strip command verbs from the beginning
    target = re.sub(
        r'^(?:open\s+youtube\s+(?:and|to)\s+play|open\s+youtube|i\s+want\s+to\s+listen\s+to|want\s+to\s+listen\s+to|listen\s+to|put\s+on|play\s+me|play|hear)\s*',
        '', target
    ).strip()

    # Strip leading phrases like 'a song of / song of / songs of / a song by / songs by'
    target = re.sub(r'^(?:a\s+)?(?:song|songs|track|tracks)\s+(?:of|by)\s+', '', target).strip()
    target = re.sub(r'^(?:a\s+)?(?:song|songs|track|tracks|music)\s+', '', target).strip()

    if not target or target in GENERIC_MUSIC_PHRASES:
        return True, None

    return True, target


def extract_map_or_climate_request(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detects Google Maps, region mapping, and comprehensive climate requests.

    Returns:
        Tuple[bool, Optional[str]]: (is_map_or_climate, location_or_none)
    """
    clean = text.lower().strip().rstrip(".!?")
    clean = re.sub(
        r'^(?:(?:hello\s+)?kitty\s+)?(?:please\s+)?(?:can you\s+|could you\s+|would you\s+)?(?:(?:to\s+know\s+)?i\s+(?:just\s+)?want\s+to\s+know(?:\s+about)?\s*|want\s+to\s+know(?:\s+about)?\s*|i\s+would\s+like\s+to\s+know(?:\s+about)?\s*|i\s+want\s+(?:you\s+)?to\s+)?(?:check\s+|show(?:\s+me)?\s+|tell\s+me\s+|open\s+)?',
        '', clean
    ).strip()

    map_triggers = [
        "google map", "google maps", "open google map", "show map", "show the map",
        "on google map", "on google maps", "on the map", "view map", "satellite map",
        "map of", "maps of", "map for", "map in"
    ]
    climate_triggers = [
        "climate", "climate of", "climate in", "climate for", "climate details",
        "climate and map", "map and climate", "detailed weather"
    ]

    is_matched = any(trig in clean for trig in (map_triggers + climate_triggers))
    if not is_matched:
        return False, None

    if clean in ["google map", "google maps", "map", "maps", "climate", "check climate", "show map"]:
        return True, None

    m_where = re.search(r'where\s+is\s+([a-zA-Z\s]+?)\s+(?:on\s+google\s+map|on\s+the\s+map|located)', clean)
    if m_where:
        loc = m_where.group(1).strip()
        loc = re.sub(r'\b(right\s+now|right|now|today|outside|currently|please|in\s+detail|detail|detailed)\b', '', loc).strip()
        return True, loc

    m_of = re.search(
        r'(?:google\s+map|map|climate|climate\s+and\s+map|map\s+and\s+climate|detailed\s+weather)\s+(?:of|for|in|about)\s+([a-zA-Z\s]+)',
        clean
    )
    if m_of:
        loc = m_of.group(1).strip()
        loc = re.sub(r'\b(right\s+now|right|now|today|outside|currently|please|in\s+detail|detail|detailed)\b', '', loc).strip()
        if loc:
            return True, loc

    m_trail = re.search(r'^([a-zA-Z\s]+?)\s+(?:google\s+map|google\s+maps|climate|map)$', clean)
    if m_trail:
        loc = m_trail.group(1).strip()
        loc = re.sub(r'\b(right\s+now|right|now|today|outside|currently|please|in\s+detail|detail|detailed)\b', '', loc).strip()
        if loc and loc not in ["the", "a", "show", "open", "check"]:
            return True, loc

    return True, None


def extract_weather_request(text: str) -> Tuple[bool, Optional[str]]:
    """
    Detects if command is a weather request and extracts the city name if present.

    Returns:
        Tuple[bool, Optional[str]]: (is_weather, city_name_or_none)
    """
    clean = text.lower().strip().rstrip(".!?")

    weather_triggers = [
        "what's the weather", "what is the weather", "how's the weather", "how is the weather",
        "weather today", "weather outside", "weather forecast", "tell me the weather",
        "is it going to rain", "is it raining", "will it rain", "rain today",
        "how hot is it", "how cold is it", "temperature outside", "temperature today"
    ]

    is_weather = any(trig in clean for trig in weather_triggers) or clean.startswith("weather in ") or clean.startswith("weather for ")
    if not is_weather:
        return False, None

    # Extract city if explicitly mentioned
    match = re.search(r'(?:in|for|at|of)\s+([a-zA-Z\s]+)', clean)
    if match:
        city = match.group(1).strip()
        city = re.sub(r'\b(today|outside|now|currently|please|like|is|the|tomorrow|this morning|this afternoon)\b', '', city).strip()
        if city and len(city) > 1:
            return True, city

    return True, None


def handle_feature(user_command: str) -> Tuple[bool, str]:
    """
    Checks if user command matches any built-in features, handling both
    flexible natural language phrasing and multi-turn clarifying follow-ups.

    Args:
        user_command (str): Spoken or typed user input.

    Returns:
        Tuple[bool, str]: (is_handled, response_string)
    """
    global PENDING_ACTION

    if not user_command:
        return False, ""

    text = user_command.lower().strip().rstrip(".!?")

    # =============================================================
    # 0. RESOLVE PENDING MULTI-TURN ACTIONS (Follow-ups)
    # =============================================================
    if PENDING_ACTION:
        # Check if user wants to cancel
        if any(c == text or text.startswith(c) for c in CANCEL_PHRASES):
            clear_pending_action()
            return True, "No problem! I've cancelled that request."

        # A. Waiting for Song Name
        if PENDING_ACTION == "WAITING_FOR_SONG":
            if any(t in text for t in ["what time", "what's the time", "what day", "what date", "alarm", "weather", "climate", "map"]):
                clear_pending_action()
            else:
                clear_pending_action()
                song_to_play = text
                is_m, parsed_song = extract_music_request(text)
                if is_m and parsed_song:
                    song_to_play = parsed_song
                else:
                    song_to_play = re.sub(
                        r'^(?:did\s+you\s+want\s+|i\s+want\s+(?:to\s+hear\s+)?|can\s+you\s+play\s+|play\s+|the\s+song\s+of\s+|song\s+of\s+|songs\s+of\s+)',
                        '', song_to_play
                    ).strip()
                print(f"[Dispatcher]: Resolving song follow-up with: '{song_to_play}'", flush=True)
                return True, play_music(song_to_play)

        # B. Waiting for City / Map / Climate Location
        elif PENDING_ACTION in ["WAITING_FOR_CITY", "WAITING_FOR_MAP_LOCATION"]:
            if any(t in text for t in ["what time", "what's the time", "play", "alarm"]):
                clear_pending_action()
            else:
                clear_pending_action()
                clean_loc = re.sub(r'^(?:the\s+weather\s+in|weather\s+in|the\s+climate\s+of|climate\s+of|map\s+of|google\s+map\s+of|in|for|about)\s+', '', text).strip()
                print(f"[Dispatcher]: Resolving climate/map follow-up for location: '{clean_loc}'", flush=True)
                spoken, _ = get_climate_and_map(clean_loc)
                return True, spoken

        # C. Waiting for Alarm Time
        elif PENDING_ACTION == "WAITING_FOR_ALARM_TIME":
            if any(t in text for t in ["what time", "what's the time", "play", "weather"]):
                clear_pending_action()
            else:
                parsed = parse_alarm_duration(text)
                if parsed:
                    clear_pending_action()
                    return True, set_alarm_from_command(f"set an alarm for {text}")
                else:
                    return True, "I couldn't tell what time to set the alarm for. Please say for example '10 seconds' or '5 minutes', or say 'cancel'."

    # =============================================================
    # 1. MUSIC CONTROLS (Pause, Resume, Stop)
    # =============================================================
    # A. PAUSE MUSIC
    if any(k == text or text.startswith(k) for k in [
        "pause music", "pause the music", "pause song", "pause the song",
        "pause it", "hold the music", "pause"
    ]):
        clear_pending_action()
        return True, pause_music()

    # B. RESUME MUSIC
    if any(k == text or text.startswith(k) for k in [
        "resume music", "resume the music", "resume song", "resume the song",
        "continue music", "unpause music", "unpause", "play again", "resume"
    ]):
        clear_pending_action()
        return True, resume_music()

    # C. STOP MUSIC
    if any(k == text or text.startswith(k) for k in [
        "stop music", "stop the music", "stop song", "stop the song",
        "stop playing", "turn off music", "end music", "stop"
    ]):
        clear_pending_action()
        return True, stop_music()

    # =============================================================
    # 2. PLAY MUSIC Feature (Natural Phrasing + Follow-Up)
    # =============================================================
    is_music, song_name = extract_music_request(text)
    if is_music:
        if song_name:
            clear_pending_action()
            return True, play_music(song_name)
        else:
            PENDING_ACTION = "WAITING_FOR_SONG"
            return True, "Sure! What song would you like me to play?"

    # =============================================================
    # 3. GOOGLE MAPS & DETAILED CLIMATE Feature (Priority handler)
    # =============================================================
    is_map_climate, location = extract_map_or_climate_request(text)
    if is_map_climate:
        if location:
            clear_pending_action()
            spoken, _ = get_climate_and_map(location)
            return True, spoken
        elif DEFAULT_CITY:
            clear_pending_action()
            spoken, _ = get_climate_and_map(DEFAULT_CITY)
            return True, spoken
        else:
            PENDING_ACTION = "WAITING_FOR_MAP_LOCATION"
            return True, "Which city, region, or country would you like to see on Google Maps and check the climate for?"

    # =============================================================
    # 4. GENERAL WEATHER Feature (Natural Phrasing + DEFAULT_CITY / Follow-Up)
    # =============================================================
    is_weather, city_name = extract_weather_request(text)
    if is_weather:
        if city_name:
            clear_pending_action()
            spoken, _ = get_climate_and_map(city_name)
            return True, spoken
        elif DEFAULT_CITY:
            clear_pending_action()
            spoken, _ = get_climate_and_map(DEFAULT_CITY)
            return True, spoken
        else:
            PENDING_ACTION = "WAITING_FOR_CITY"
            return True, "Which city would you like the weather for?"

    # =============================================================
    # 5. ALARM Feature (Natural Phrasing + Follow-Up)
    # =============================================================
    if "alarm" in text or "timer" in text or "wake me" in text:
        parsed_duration = parse_alarm_duration(text)
        if parsed_duration:
            clear_pending_action()
            return True, set_alarm_from_command(text)
        else:
            PENDING_ACTION = "WAITING_FOR_ALARM_TIME"
            return True, "What time should I set the alarm for?"

    # =============================================================
    # 6. SING A SONG Feature
    # =============================================================
    if "sing" in text and ("song" in text or "about" in text):
        clear_pending_action()
        topic = extract_singing_topic(text)
        return True, sing_song_about(topic)

    # =============================================================
    # 7. TIME Feature
    # =============================================================
    time_triggers = [
        "what time is it",
        "what's the time",
        "what is the time",
        "tell me the time",
        "current time",
        "what time",
    ]
    if any(t in text for t in time_triggers):
        clear_pending_action()
        return True, get_current_time()

    # =============================================================
    # 8. DATE Feature
    # =============================================================
    date_triggers = [
        "what's the date",
        "what is the date",
        "what's today's date",
        "what is today's date",
        "today's date",
        "what day is it",
        "what day is today",
    ]
    if any(d in text for d in date_triggers):
        clear_pending_action()
        return True, get_current_date()

    return False, ""
