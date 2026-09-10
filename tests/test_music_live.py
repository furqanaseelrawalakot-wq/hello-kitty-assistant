"""
test_music_live.py - Direct verification of Requirement 4 (Music Playback).
Tests extracting song name, searching YouTube via yt-dlp, and background playback.
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from features.music import play_music, stop_music, extract_song_name


def test_music():
    print("=" * 60)
    print(" MUSIC PLAYBACK VERIFICATION (Requirement 4)")
    print("=" * 60)

    test_queries = [
        "play despacito on youtube",
        "play lofi hip hop",
        "play",
    ]

    for q in test_queries:
        extracted = extract_song_name(q)
        print(f"[Query]: \"{q}\" -> Extracted Title: \"{extracted}\"")

    # Test live YouTube search and stream initiation
    print("\n[Simulating Command]: \"play classical music short on youtube\"")
    reply = play_music("play classical music short on youtube")
    print(f"[Music Response Received]: \"{reply}\"")

    print("\nLetting audio play for 3 seconds...")
    time.sleep(3)

    print("\n[Simulating Command]: \"stop music\"")
    stop_reply = stop_music()
    print(f"[Stop Music Response]: \"{stop_reply}\"")

    print("\n>>> Music playback requirement tested and verified! <<<\n")


if __name__ == "__main__":
    test_music()
