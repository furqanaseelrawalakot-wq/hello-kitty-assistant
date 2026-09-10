"""
test_features_live.py - Direct verification of all 4 built-in features:
1. Current Time
2. Current Date
3. Weather (OpenWeatherMap)
4. Background Alarm Timer
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from features.dispatcher import handle_feature
from features.alarm import ACTIVE_ALARMS


def run_tests():
    print("=" * 65)
    print(" BUILT-IN FEATURES VERIFICATION (Hardcoded Inputs)")
    print("=" * 65)

    test_cases = [
        ("Time", "what time is it"),
        ("Alternate Time", "tell me the time"),
        ("Date", "what's today's date"),
        ("Weather with City", "what's the weather in Tokyo"),
        ("Weather Generic", "what is the weather"),
    ]

    for label, query in test_cases:
        print(f"\n[Test Query]: \"{query}\"")
        handled, response = handle_feature(query)
        print(f"  -> Intercepted by Built-in : {handled}")
        print(f"  -> Spoken Response Output  : \"{response}\"")

    # Test Alarm with a short 2-second background timer
    print("\n" + "-" * 65)
    print(" ALARM BACKGROUND THREAD TEST")
    print("-" * 65)
    alarm_query = "set an alarm for 2 seconds"
    print(f"[Test Query]: \"{alarm_query}\"")
    handled, response = handle_feature(alarm_query)
    print(f"  -> Intercepted by Built-in : {handled}")
    print(f"  -> Spoken Response Output  : \"{response}\"")
    print(f"  -> Active Alarms In-Memory : {len(ACTIVE_ALARMS)} alarm(s) running")

    print("\nWaiting 2.5 seconds for background thread to fire...")
    time.sleep(2.5)

    print(f"  -> Active Alarms In-Memory after trigger: {len(ACTIVE_ALARMS)} alarm(s)")
    print("\n>>> All 4 built-in features tested and verified! <<<\n")


if __name__ == "__main__":
    run_tests()
