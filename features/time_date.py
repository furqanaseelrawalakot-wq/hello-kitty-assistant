"""
time_date.py - Handles time and date queries without needing an LLM call.
"""

from datetime import datetime


def get_current_time() -> str:
    """Returns the current system time in a 12-hour spoken format."""
    now = datetime.now()
    # Format e.g., "11:15 AM"
    time_str = now.strftime("%I:%M %p").lstrip("0")
    return f"The current time is {time_str}."


def get_current_date() -> str:
    """Returns today's date in a human-friendly spoken format."""
    now = datetime.now()
    # Format e.g., "Wednesday, September 10, 2026"
    date_str = now.strftime("%A, %B %d, %Y")
    return f"Today is {date_str}."
