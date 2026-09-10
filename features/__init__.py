"""
features package for Hello Kitty.
Contains built-in skills for Time, Date, Weather, Alarms, Music, Translation, and Singing.
"""
from .dispatcher import handle_feature
from .time_date import get_current_time, get_current_date
from .weather import get_weather_for_city
from .alarm import set_alarm_from_command, ACTIVE_ALARMS
from .music import play_music, stop_music
from .translation import is_urdu_text, handle_urdu_pipeline
from .singing import sing_song_about

__all__ = [
    "handle_feature",
    "get_current_time",
    "get_current_date",
    "get_weather_for_city",
    "set_alarm_from_command",
    "ACTIVE_ALARMS",
    "play_music",
    "stop_music",
    "is_urdu_text",
    "handle_urdu_pipeline",
    "sing_song_about",
]
