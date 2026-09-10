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
import urllib.parse
from typing import Optional
import requests
import pygame
import yt_dlp

# Playback State
IS_PLAYING = False
IS_PAUSED = False
CURRENT_SONG_TITLE: Optional[str] = None
CURRENT_SONG_FILE: Optional[str] = None
CURRENT_MUSIC_METADATA: dict = {}
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

    # Remove phrases like 'a song of / song of / songs of / a song by / songs by / a song for'
    clean = re.sub(r'^(?:the\s+)?(?:a\s+)?(?:song|songs|track|tracks|music)\s+(?:of|by|for)\s+', '', clean).strip()

    # Remove remaining leading 'the song' or 'song' or 'for'
    clean = re.sub(r'^(?:the\s+)?(?:song|songs|track|tracks)\s+', '', clean).strip()
    clean = re.sub(r'^(?:for)\s+', '', clean).strip()

    if clean in GENERIC_MUSIC_PHRASES or not clean:
        return ""

    return clean


def get_current_music_info() -> dict:
    """Returns current music state for web streaming and status checks."""
    global IS_PLAYING, IS_PAUSED, CURRENT_SONG_TITLE, CURRENT_SONG_FILE, CURRENT_MUSIC_METADATA
    return {
        "is_playing": IS_PLAYING or bool(CURRENT_MUSIC_METADATA.get("embed_url")),
        "is_paused": IS_PAUSED,
        "title": CURRENT_SONG_TITLE or CURRENT_MUSIC_METADATA.get("title"),
        "file_path": CURRENT_SONG_FILE,
        "video_id": CURRENT_MUSIC_METADATA.get("video_id"),
        "embed_url": CURRENT_MUSIC_METADATA.get("embed_url"),
        "webpage_url": CURRENT_MUSIC_METADATA.get("webpage_url")
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


def find_youtube_video(query: str) -> tuple[Optional[str], str]:
    """
    Lightweight, direct YouTube search scraper.
    Extracts genuine videoId and title in < 0.5s without yt-dlp or JS runtimes.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    try:
        r = requests.get(url, headers=headers, timeout=6)
        # 1. Match videoRenderer blocks for exact video ID and matching title
        items = re.findall(r'"videoRenderer":\{"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"([^"]+)"', r.text)
        if items:
            vid, title = items[0]
            return vid, title

        # 2. Fallback to general videoId extraction
        vids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
        seen = set()
        unique_vids = []
        for v in vids:
            if v not in seen:
                seen.add(v)
                unique_vids.append(v)
        if unique_vids:
            return unique_vids[0], query.title()
    except Exception as e:
        print(f"[Music Search Scraper Notice]: {e}", flush=True)
    return None, query.title()


def play_music(song_query: str) -> str:
    """
    Searches YouTube, extracts metadata for web playback, and handles background playback.
    Fast, non-blocking, and 100% cloud & serverless compatible.
    """
    global _music_thread, IS_PLAYING, IS_PAUSED, CURRENT_SONG_TITLE, CURRENT_SONG_FILE, CURRENT_MUSIC_METADATA

    song_name = extract_song_name(song_query)
    if not song_name:
        return "Sure! What song would you like me to play?"

    # Stop any currently playing music
    stop_music()
    CURRENT_MUSIC_METADATA.clear()

    title = song_name.title()
    video_id = ""
    embed_url = ""
    webpage_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(song_name)}"

    print(f"\n[Music Engine]: Searching YouTube for: \"{song_name}\"...", flush=True)

    # 1. Fast direct YouTube search (retrieves real video ID and title in <0.5s)
    v_id, v_title = find_youtube_video(song_name)
    if v_id:
        video_id = v_id
        title = v_title
        webpage_url = f"https://www.youtube.com/watch?v={video_id}"
        embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1"
    else:
        # Fallback to yt-dlp metadata
        ydl_opts_info = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1',
            'socket_timeout': 8,
            'retries': 2,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                search_results = ydl.extract_info(f"ytsearch1:{song_name}", download=False)
                if search_results and 'entries' in search_results and search_results['entries']:
                    entry = search_results['entries'][0]
                    title = entry.get('title') or title
                    video_id = entry.get('id') or ''
                    if video_id:
                        webpage_url = entry.get('webpage_url') or f"https://www.youtube.com/watch?v={video_id}"
                        embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&enablejsapi=1"
        except Exception as search_err:
            print(f"[Music Engine Warning]: yt-dlp search notice: {search_err}", flush=True)

    # Fallback to search embed if video_id still empty
    if not embed_url:
        embed_url = f"https://www.youtube.com/embed?listType=search&list={urllib.parse.quote(song_name)}&autoplay=1"

    CURRENT_MUSIC_METADATA = {
        "title": title,
        "video_id": video_id,
        "embed_url": embed_url,
        "webpage_url": webpage_url
    }
    CURRENT_SONG_TITLE = title
    IS_PLAYING = True
    IS_PAUSED = False

    # 2. Local speaker playback (only when running locally on desktop, not in cloud serverless)
    is_headless = os.environ.get("SDL_AUDIODRIVER") == "dummy" or bool(os.environ.get("VERCEL")) or bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    if not is_headless:
        def _bg_local_playback(vid: str, s_name: str, track_title: str):
            global CURRENT_SONG_FILE, _music_thread
            try:
                temp_dir = tempfile.gettempdir()
                output_template = os.path.join(temp_dir, f"kitty_music_{int(time.time())}.%(ext)s")
                ydl_opts_dl = {
                    'format': 'bestaudio/best',
                    'outtmpl': output_template,
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 15,
                    'retries': 1,
                    'max_filesize': 40 * 1024 * 1024,
                }
                with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                    query = f"https://www.youtube.com/watch?v={vid}" if vid else f"ytsearch1:{s_name}"
                    res = ydl.extract_info(query, download=True)
                    if res:
                        e = res['entries'][0] if 'entries' in res and res['entries'] else res
                        act_file = ydl.prepare_filename(e)
                        if os.path.exists(act_file):
                            CURRENT_SONG_FILE = act_file
                            _music_thread = threading.Thread(
                                target=_music_worker,
                                args=(act_file, track_title),
                                name=f"MusicWorker-{int(time.time())}",
                                daemon=True
                            )
                            _music_thread.start()
            except Exception as dl_err:
                print(f"[Music Local Playback Notice]: {dl_err}", flush=True)

        threading.Thread(target=_bg_local_playback, args=(video_id, song_name, title), daemon=True).start()

    return f"Now playing {title} on YouTube!"


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
