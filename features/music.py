"""
music.py - YouTube Music Search & Playback using yt-dlp, FFmpeg, and pygame.
Streams and plays audio in a background thread so the voice assistant remains responsive.
Includes transparent logging, mixer initialization validation, disk verification,
and anti-feedback controls.
"""

import os
import re
import time
import tempfile
import threading
import traceback
from typing import Optional
import pygame
import yt_dlp

# Playback State
IS_PLAYING = False
IS_PAUSED = False
CURRENT_SONG_TITLE: Optional[str] = None
CURRENT_SONG_FILE: Optional[str] = None
_music_thread: Optional[threading.Thread] = None
_current_temp_file: Optional[str] = None

GENERIC_MUSIC_PHRASES = {
    'a song', 'some music', 'music', 'a track', 'songs', 'tracks',
    'a song for me', 'some music for me', 'music for me', 'a song please',
    'some songs', 'something', 'anything', 'any song', 'a good song'
}


def ensure_music_mixer_initialized():
    """Initializes pygame mixer with standard high-quality audio settings if not active."""
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            pygame.mixer.set_num_channels(16)
        except Exception as init_err:
            print(f"[Music Mixer Init Error]: {init_err}", flush=True)
    return pygame.mixer.get_init()


def extract_song_name(command: str) -> str:
    """
    Extracts clean song title or artist from natural user command.
    Handles 'play despacito on youtube', 'song of attaullah khan',
    'did you want the song of attaullah khan', 'can you play a song for me', etc.
    Returns empty string if generic request requiring follow-up prompt.
    """
    if not command:
        return ""
    clean = command.lower().strip().rstrip(".!?")

    # Remove 'on youtube', 'from youtube'
    clean = re.sub(r'\b(?:on|from)\s+youtube\b', '', clean).strip()

    # Remove trailing polite or filler phrases
    clean = re.sub(r'\b(?:for\s+me|for\s+us|to\s+me|to\s+us|please)\b', '', clean).strip()

    # Remove leading conversational / command verbs
    clean = re.sub(
        r'^(?:did\s+you\s+want\s+to\s+play|did\s+you\s+want|can\s+you\s+please\s+play|can\s+you\s+play|could\s+you\s+play|please\s+play|open\s+youtube\s+(?:and|to)\s+play|open\s+youtube|i\s+want\s+to\s+listen\s+to|want\s+to\s+listen\s+to|listen\s+to|put\s+on|play\s+me|play)\s*',
        '', clean
    ).strip()

    # Remove phrases like 'a song of / song of / songs of / a song by / songs by'
    clean = re.sub(r'^(?:the\s+)?(?:a\s+)?(?:song|songs|track|tracks|music)\s+(?:of|by)\s+', '', clean).strip()

    # Remove remaining leading 'the song' or 'song'
    clean = re.sub(r'^(?:the\s+)?(?:song|songs|track|tracks)\s+', '', clean).strip()

    if clean in GENERIC_MUSIC_PHRASES or not clean:
        return ""

    return clean


def get_current_music_info() -> dict:
    """Returns current music state for web streaming and status checks."""
    global IS_PLAYING, IS_PAUSED, CURRENT_SONG_TITLE, CURRENT_SONG_FILE
    return {
        "is_playing": IS_PLAYING,
        "is_paused": IS_PAUSED,
        "title": CURRENT_SONG_TITLE,
        "file_path": CURRENT_SONG_FILE
    }


def _music_worker(temp_file_path: str, title: str):
    """
    Background worker that plays audio with pygame.mixer.music.
    Monitors playback status and safely handles unloads.
    """
    global IS_PLAYING, IS_PAUSED, CURRENT_SONG_TITLE, _current_temp_file, CURRENT_SONG_FILE
    try:
        mixer_stat = ensure_music_mixer_initialized()
        print(f"[Music Worker]: Initializing playback for \"{title}\" (mixer: {mixer_stat})", flush=True)

        if not os.path.exists(temp_file_path):
            print(f"[Music Worker ERROR]: Audio file does not exist at {temp_file_path}", flush=True)
            return

        print(f"[Music Worker]: Loading audio track: {temp_file_path} ...", flush=True)
        pygame.mixer.music.load(temp_file_path)
        pygame.mixer.music.set_volume(1.0)

        print(f"[Music Worker]: Calling pygame.mixer.music.play() ...", flush=True)
        pygame.mixer.music.play()

        # Brief verification of active playback
        time.sleep(0.15)
        is_busy = pygame.mixer.music.get_busy()
        print(f"[Music Playback]: Playback active! (get_busy = {is_busy}) Playing: \"{title}\"\n", flush=True)

        IS_PLAYING = True
        IS_PAUSED = False
        CURRENT_SONG_TITLE = title
        CURRENT_SONG_FILE = temp_file_path
        _current_temp_file = temp_file_path

        # Playback monitoring loop
        while (IS_PLAYING or IS_PAUSED):
            if not IS_PAUSED and not pygame.mixer.music.get_busy():
                print(f"[Music Worker]: \"{title}\" reached end of track naturally.", flush=True)
                break
            time.sleep(0.3)

    except Exception as exc:
        print(f"[Music Playback ERROR]: {exc}", flush=True)
        traceback.print_exc()

    finally:
        IS_PLAYING = False
        IS_PAUSED = False
        CURRENT_SONG_TITLE = None


def play_music(song_query: str) -> str:
    """
    Searches YouTube with yt-dlp, converts to MP3 via imageio-ffmpeg,
    and launches background thread playback via pygame.mixer.music.

    Returns:
        str: Hello Kitty spoken confirmation.
    """
    global _music_thread, IS_PLAYING, CURRENT_SONG_FILE

    song_name = extract_song_name(song_query)
    if not song_name:
        return "Sure! What song would you like me to play?"

    # Stop any currently playing music
    stop_music()

    # Pre-check mixer initialization
    mixer_init = ensure_music_mixer_initialized()
    print(f"\n[Music Engine]: Mixer status before search: {mixer_init}", flush=True)
    print(f"[Music Engine]: Searching YouTube for: \"{song_name}\"...", flush=True)

    temp_dir = tempfile.gettempdir()
    output_template = os.path.join(temp_dir, f"kitty_music_{int(time.time())}.%(ext)s")

    # Locate ffmpeg from imageio_ffmpeg
    ffmpeg_exe = None
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        print(f"[Music Engine]: FFmpeg found at: {ffmpeg_exe}", flush=True)
    except Exception as ff_err:
        print(f"[Music Engine Warning]: Could not locate imageio_ffmpeg ({ff_err})", flush=True)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch1',
        'socket_timeout': 15,
        'retries': 3,
        'max_filesize': 60 * 1024 * 1024,
    }

    if ffmpeg_exe:
        ydl_opts['ffmpeg_location'] = ffmpeg_exe
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch1:{song_name}", download=True)
            if not search_results or 'entries' not in search_results or not search_results['entries']:
                return f"Sorry, I couldn't find '{song_name}' on YouTube."

            entry = search_results['entries'][0]
            title = entry.get('title', song_name)

            # Determine actual downloaded file path on disk
            base_filename = ydl.prepare_filename(entry)
            if ffmpeg_exe:
                mp3_filename = os.path.splitext(base_filename)[0] + ".mp3"
                actual_file = mp3_filename if os.path.exists(mp3_filename) else base_filename
            else:
                actual_file = base_filename

            if not os.path.exists(actual_file):
                print(f"[Music Engine ERROR]: Expected audio file not found at: {actual_file}", flush=True)
                return f"Sorry, could not save the audio file for {song_name}."

            file_size = os.path.getsize(actual_file)
            print(f"[Music Engine]: Audio file verified on disk: {actual_file} ({file_size} bytes)", flush=True)

            CURRENT_SONG_FILE = actual_file

            # Start playback in background thread (retaining reference)
            _music_thread = threading.Thread(
                target=_music_worker,
                args=(actual_file, title),
                name=f"MusicWorker-{int(time.time())}",
                daemon=True
            )
            _music_thread.start()

            return f"Now playing {title} on YouTube!"

    except Exception as exc:
        print(f"[Music Search ERROR]: {exc}", flush=True)
        traceback.print_exc()
        return f"Sorry, I ran into an error while trying to play {song_name}."


def pause_music() -> str:
    """Pauses the currently playing music."""
    global IS_PLAYING, IS_PAUSED, CURRENT_SONG_TITLE
    if IS_PAUSED:
        return "Music is already paused. Say 'resume' to continue playing."
    if IS_PLAYING or (pygame.mixer.get_init() and pygame.mixer.music.get_busy()):
        try:
            pygame.mixer.music.pause()
            IS_PAUSED = True
            title = CURRENT_SONG_TITLE or "the music"
            print(f"[Music Control]: Paused \"{title}\".", flush=True)
            return f"I've paused {title}. Say 'resume' whenever you want to continue listening!"
        except Exception as err:
            return f"Could not pause music: {err}"
    return "No music is currently playing to pause."


def resume_music() -> str:
    """Resumes currently paused music."""
    global IS_PLAYING, IS_PAUSED, CURRENT_SONG_TITLE
    if IS_PAUSED:
        try:
            pygame.mixer.music.unpause()
            IS_PAUSED = False
            IS_PLAYING = True
            title = CURRENT_SONG_TITLE or "the music"
            print(f"[Music Control]: Resumed \"{title}\".", flush=True)
            return f"Resuming {title}!"
        except Exception as err:
            return f"Could not resume music: {err}"
    if IS_PLAYING:
        return "The music is already playing!"
    return "There is no paused music to resume."


def stop_music() -> str:
    """Stops the currently playing or paused music."""
    global IS_PLAYING, IS_PAUSED, CURRENT_SONG_TITLE
    if IS_PLAYING or IS_PAUSED or (pygame.mixer.get_init() and pygame.mixer.music.get_busy()):
        IS_PLAYING = False
        IS_PAUSED = False
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            print("[Music Control]: Stopped and unloaded music playback.", flush=True)
        except Exception as stop_err:
            pass
        title = CURRENT_SONG_TITLE or "the song"
        CURRENT_SONG_TITLE = None
        return f"I've stopped playing {title}."
    return "No music is currently playing."
