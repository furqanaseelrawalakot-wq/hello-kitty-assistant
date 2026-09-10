"""
singing.py - Generates and sings short themed song lyrics.
Uses the AI brain to compose 4-6 cheerful rhyming lines and plays them
via gTTS with slow=True for a musical, sing-song cadence.
"""

import re
from typing import Optional
from brain.llm_provider import get_ai_response
from voice.speaker import speak


def extract_singing_topic(command: str) -> str:
    """Extracts topic from commands like 'sing a song about apples'."""
    clean = command.lower().strip()
    match = re.search(r'(?:sing\s+a\s+song\s+about|sing\s+about|sing\s+me\s+a\s+song\s+about|sing\s+a\s+song\s+on)\s+(.+)', clean)
    if match:
        topic = match.group(1).strip(" .!?")
        return topic
    return "friendship and sunshine"


def sing_song_about(topic: str) -> str:
    """
    Composes 4-6 lines of rhyming lyrics on the given topic and reads them in a sing-song way.

    Returns:
        str: The generated lyrics.
    """
    clean_topic = topic.strip()
    print(f"\n[Singing]: Composing a song about '{clean_topic}'...")

    prompt = (
        f"Compose 4 short, cute, cheerful, rhyming lines of song lyrics about '{clean_topic}'. "
        "Make it sound sweet and musical like a Hello Kitty song. "
        "Do not include any headers like [Verse] or labels, just the 4 rhyming lines."
    )

    lyrics = get_ai_response(prompt)

    # Clean up any potential markdown asterisks
    clean_lyrics = lyrics.replace("*", "").replace("#", "").strip()

    # Announce and sing
    intro = f"Here is a little song for you about {clean_topic}!"
    print(f"\n[Hello Kitty Singing]:\n{clean_lyrics}\n")

    # Speak lyrics aloud with a musical pace
    speak(f"{intro} ... {clean_lyrics}")

    return clean_lyrics
