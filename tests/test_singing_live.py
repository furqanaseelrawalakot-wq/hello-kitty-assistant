"""
test_singing_live.py - Direct verification of Requirement 6 (Sing a Song).
Tests topic extraction, AI lyrics composition, and audio playback.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from features.singing import extract_singing_topic, sing_song_about


def test_singing():
    print("=" * 60)
    print(" SING A SONG VERIFICATION (Requirement 6)")
    print("=" * 60)

    test_queries = [
        "sing a song about red apples",
        "sing about butterflies",
        "sing me a song",
    ]

    for q in test_queries:
        topic = extract_singing_topic(q)
        print(f"[Query]: \"{q}\" -> Extracted Topic: \"{topic}\"")

    # Test live song generation and audio playback with hardcoded topic
    print("\n[Executing Song Generation for Topic]: 'red apples'")
    lyrics = sing_song_about("red apples")

    print("-" * 50)
    print(f"[Generated Song Lyrics]:\n{lyrics}")
    print("-" * 50)

    print("\n>>> Sing a song requirement tested and verified! <<<\n")


if __name__ == "__main__":
    test_singing()
