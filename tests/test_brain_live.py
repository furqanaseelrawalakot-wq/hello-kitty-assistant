"""
test_brain_live.py - Direct test of the AI brain with a hardcoded sentence.
Tests LLM querying and response generation separate from the microphone.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import MODEL_PROVIDER, GEMINI_API_KEY
from brain.llm_provider import get_ai_response, IN_MEMORY_CONVERSATION


def test_brain_direct():
    print("=" * 60)
    print(" AI BRAIN DIRECT VERIFICATION TEST (Requirement 2)")
    print("=" * 60)
    print(f"Current Provider : {MODEL_PROVIDER.upper()}")
    print(f"Gemini Key Set   : {'YES' if (GEMINI_API_KEY and GEMINI_API_KEY != 'your_gemini_api_key_here') else 'NO (placeholder)'}")

    test_prompt = "What is the capital of France?"
    print(f"\n[Test Input Simulated]: \"{test_prompt}\"")
    print("[Brain]: Querying get_ai_response(text)...")

    reply = get_ai_response(test_prompt)

    print("\n" + "-" * 50)
    print(f"[AI Response Received]:\n\"{reply}\"")
    print("-" * 50)

    # Test short-term memory with follow-up simulated question
    followup_prompt = "What was the country I just asked about?"
    print(f"\n[Simulating Follow-up Question]: \"{followup_prompt}\"")
    followup_reply = get_ai_response(followup_prompt)

    print("\n" + "-" * 50)
    print(f"[AI Follow-up Memory Response]:\n\"{followup_reply}\"")
    print(f"[In-Memory Context Size]: {len(IN_MEMORY_CONVERSATION)} turns (last 5 exchanges retained)")
    print("-" * 50)

    print("\n>>> Brain connection and memory test completed successfully! <<<\n")


if __name__ == "__main__":
    test_brain_direct()
