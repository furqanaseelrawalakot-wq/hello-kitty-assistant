"""
app.py - Flask Web Application for Hello Kitty Assistant.
Provides a ChatGPT-style web interface connected directly to the same AI brain
and built-in features without database persistence (pure in-memory).
"""

import os
import sys
import time
import tempfile
import subprocess
import mimetypes
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory

mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")

# Ensure immediate unbuffered terminal output on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# Ensure the project root is on Python's search path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Step 3: Explicitly load .env file from project root
try:
    from dotenv import load_dotenv
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        load_dotenv(override=True)
except ImportError:
    pass

from brain.llm_provider import get_ai_response, IN_MEMORY_CONVERSATION
from features.dispatcher import handle_feature, clear_pending_action
from features.music import get_current_music_info, stop_music, pause_music, resume_music
from features.weather import get_last_climate_map_info, clear_last_climate_map_info
from features.translation import is_urdu_text, handle_urdu_pipeline
from config.settings import MODEL_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static")
)

# Disable caching for development so script.js and style.css updates reflect immediately
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.after_request
def add_header(response):
    """Add no-cache headers to all responses to prevent stale browser assets."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def get_local_ip() -> str:
    """Returns the computer's local network IP address for mobile phone connection."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            import socket
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


# In-memory chat history for the web session (no database needed)
chat_history = []


@app.route("/")
@app.route("/api")
@app.route("/api/index")
@app.route("/api/index.py")
def index():
    """Renders the main Hello Kitty web chat interface with cache-buster timestamp and mobile URL."""
    cache_id = int(time.time())
    local_ip = get_local_ip()
    use_https = request.is_secure or (request.headers.get("X-Forwarded-Proto") == "https")
    return render_template(
        "index.html",
        provider=MODEL_PROVIDER.upper(),
        cache_id=cache_id,
        local_ip=local_ip,
        protocol="https" if use_https else "http"
    )


@app.route("/static/<path:filename>")
def serve_static(filename):
    """Explicitly serves static files with strict correct MIME types for cloud deployment."""
    static_dirs = [
        Path(__file__).parent / "static",
        PROJECT_ROOT / "public" / "static",
        PROJECT_ROOT / "static"
    ]
    for s_dir in static_dirs:
        target = s_dir / filename
        if target.exists():
            mime = "text/css" if filename.endswith(".css") else ("application/javascript" if filename.endswith(".js") else None)
            return send_from_directory(str(s_dir), filename, mimetype=mime)
    return "File not found", 404


@app.route("/chat", methods=["POST"])
def chat():
    """
    POST endpoint that receives user message, processes it via features or AI brain,
    and returns Hello Kitty's reply as JSON.
    Logs every request and reply to the terminal in real time.
    """
    try:
        data = request.get_json(silent=True) or {}
        user_message = data.get("message", "").strip()

        # Step 2.2: Terminal logging of incoming message
        print(f"\n[Web /chat] Incoming: '{user_message}'", flush=True)

        if not user_message:
            print("[Web /chat] Rejected: empty message.", flush=True)
            return jsonify({"reply": "Please enter a message!", "is_feature": False}), 400

        # 1. Check Urdu language support (Requirement 5)
        if is_urdu_text(user_message):
            english_q, english_rep, urdu_rep = handle_urdu_pipeline(user_message, get_ai_response)
            chat_history.append({"role": "user", "content": user_message})
            chat_history.append({"role": "assistant", "content": urdu_rep})
            print(f"[Web /chat] Outgoing (Urdu): '{urdu_rep}'\n", flush=True)
            return jsonify({
                "reply": urdu_rep,
                "english_translation": english_rep,
                "is_feature": False,
                "is_urdu": True
            })

        # 2. Check built-in features first (Time, Date, Weather, Climate, Maps, Alarms, Music, Singing)
        clear_last_climate_map_info()
        is_feature, feature_reply = handle_feature(user_message)
        if is_feature:
            chat_history.append({"role": "user", "content": user_message})
            chat_history.append({"role": "assistant", "content": feature_reply})
            print(f"[Web /chat] Outgoing (Feature): '{feature_reply}'\n", flush=True)

            music_info = get_current_music_info()
            climate_info = get_last_climate_map_info()
            is_music = "Now playing" in feature_reply and bool(music_info.get("file_path"))
            resp_data = {
                "reply": feature_reply,
                "is_feature": True,
                "is_music": is_music,
                "music_status": music_info,
                "is_weather_map": bool(climate_info and climate_info.get("success")),
                "weather_map": climate_info
            }
            if is_music:
                resp_data["music"] = {
                    "title": music_info.get("title") or "YouTube Music Track",
                    "stream_url": f"/music/stream?t={int(time.time() * 1000)}"
                }
            elif "paused" in feature_reply.lower():
                resp_data["is_music_pause"] = True
            elif "resuming" in feature_reply.lower():
                resp_data["is_music_resume"] = True
            elif "stopped playing" in feature_reply.lower() or "no music is currently playing" in feature_reply.lower():
                resp_data["is_music_stop"] = True

            return jsonify(resp_data)

        # 3. Query the exact same AI Brain (get_ai_response) as required by Step 2.1 & Step 3
        reply = get_ai_response(user_message)

        # Store in in-memory session history
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": reply})

        # Step 2.2: Terminal logging of outgoing reply
        print(f"[Web /chat] Outgoing (Gemini AI): '{reply}'\n", flush=True)

        return jsonify({
            "reply": reply,
            "is_feature": False
        })

    except Exception as exc:
        # Step 4: Robust error reporting without silent swallows
        traceback.print_exc()
        error_msg = f"Something went wrong, please try again: {str(exc)}"
        print(f"[Web /chat ERROR]: {error_msg}\n", flush=True)
        return jsonify({"reply": error_msg, "error": True}), 500


@app.route("/voice", methods=["POST"])
def voice():
    """
    Receives recorded audio from browser MediaRecorder (webm/ogg/wav),
    converts it to 16kHz WAV using imageio_ffmpeg, transcribes it via Google Speech,
    and returns transcript and Hello Kitty response.
    """
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided", "reply": "No audio was received."}), 400

    audio_file = request.files["audio"]
    lang = request.form.get("lang", "en-US")

    temp_dir = tempfile.gettempdir()
    timestamp = int(time.time() * 1000)
    input_path = os.path.join(temp_dir, f"browser_mic_{timestamp}.webm")
    output_wav = os.path.join(temp_dir, f"browser_mic_{timestamp}.wav")

    try:
        raw_bytes = audio_file.read()
        if len(raw_bytes) < 100:
            return jsonify({
                "reply": "I couldn't hear any words. Tap the microphone 🎙️ and speak clearly, or type your question below!",
                "transcript": "",
                "is_feature": False
            }), 200

        with open(input_path, "wb") as f:
            f.write(raw_bytes)

        is_wav = len(raw_bytes) > 12 and raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WAVE"

        if is_wav:
            output_wav = input_path
        else:
            # Try to convert webm/ogg to wav using ffmpeg if available
            try:
                import imageio_ffmpeg
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                cmd = [
                    ffmpeg_exe, "-y", "-i", input_path,
                    "-ar", "16000", "-ac", "1", output_wav
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except Exception as conv_err:
                print(f"[Web /voice conversion notice]: {conv_err}", flush=True)

        user_text = ""

        # Step 1: Transcribe with speech_recognition if WAV is available
        if os.path.exists(output_wav):
            try:
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                with sr.AudioFile(output_wav) as source:
                    audio_data = recognizer.record(source)
                    user_text = recognizer.recognize_google(audio_data, language=lang).strip()
            except Exception as sr_err:
                print(f"[Web /voice speech_recognition notice]: {sr_err}", flush=True)

        # Step 2: Fallback to Gemini multimodal audio transcription if needed
        if not user_text and raw_bytes:
            try:
                import google.generativeai as genai
                from config.settings import GEMINI_API_KEY
                if GEMINI_API_KEY:
                    genai.configure(api_key=GEMINI_API_KEY)
                    for model_name in ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"]:
                        try:
                            g_model = genai.GenerativeModel(model_name)
                            mime = "audio/wav" if is_wav else "audio/webm"
                            prompt = (
                                f"Listen to this audio spoken in {'Urdu' if 'ur' in lang.lower() else 'English'}. "
                                "Transcribe the spoken words accurately. If silent or no words spoken, reply with: [SILENCE]. "
                                "Return ONLY the transcription text, nothing else."
                            )
                            g_res = g_model.generate_content([
                                {"mime_type": mime, "data": raw_bytes},
                                prompt
                            ])
                            txt = (g_res.text or "").strip()
                            if txt and "[silence]" not in txt.lower():
                                user_text = txt
                                break
                        except Exception:
                            continue
            except Exception as gemini_err:
                print(f"[Web /voice gemini transcribe error]: {gemini_err}", flush=True)

        print(f"\n[Web /voice] Transcribed Audio ({lang}): '{user_text}'", flush=True)

        if not user_text:
            return jsonify({
                "reply": "I couldn't hear any words. Tap the microphone 🎙️ and speak clearly, or type your question below!",
                "transcript": "",
                "is_feature": False
            }), 200

        # Process through Urdu pipeline if Urdu text
        if is_urdu_text(user_text):
            english_q, english_rep, urdu_rep = handle_urdu_pipeline(user_text, get_ai_response)
            chat_history.append({"role": "user", "content": user_text})
            chat_history.append({"role": "assistant", "content": urdu_rep})
            print(f"[Web /voice] Outgoing (Urdu): '{urdu_rep}'\n", flush=True)
            return jsonify({
                "transcript": user_text,
                "reply": urdu_rep,
                "english_translation": english_rep,
                "is_feature": False,
                "is_urdu": True
            })

        # Process through Feature dispatcher
        clear_last_climate_map_info()
        is_feature, feature_reply = handle_feature(user_text)
        if is_feature:
            chat_history.append({"role": "user", "content": user_text})
            chat_history.append({"role": "assistant", "content": feature_reply})
            print(f"[Web /voice] Outgoing (Feature): '{feature_reply}'\n", flush=True)

            music_info = get_current_music_info()
            climate_info = get_last_climate_map_info()
            is_music = "Now playing" in feature_reply and bool(music_info.get("file_path"))
            resp_voice = {
                "transcript": user_text,
                "reply": feature_reply,
                "is_feature": True,
                "is_music": is_music,
                "music_status": music_info,
                "is_weather_map": bool(climate_info and climate_info.get("success")),
                "weather_map": climate_info
            }
            if is_music:
                resp_voice["music"] = {
                    "title": music_info.get("title") or "YouTube Music Track",
                    "stream_url": f"/music/stream?t={int(time.time() * 1000)}"
                }
            elif "paused" in feature_reply.lower():
                resp_voice["is_music_pause"] = True
            elif "resuming" in feature_reply.lower():
                resp_voice["is_music_resume"] = True
            elif "stopped playing" in feature_reply.lower() or "no music is currently playing" in feature_reply.lower():
                resp_voice["is_music_stop"] = True

            return jsonify(resp_voice)

        # Process through Central AI brain
        reply = get_ai_response(user_text)
        chat_history.append({"role": "user", "content": user_text})
        chat_history.append({"role": "assistant", "content": reply})
        print(f"[Web /voice] Outgoing (AI): '{reply}'\n", flush=True)
        return jsonify({
            "transcript": user_text,
            "reply": reply,
            "is_feature": False
        })

    except Exception as exc:
        print(f"[Web /voice Notice]: {exc}", flush=True)
        return jsonify({
            "error": str(exc),
            "reply": "I couldn't hear any words clearly. Tap the microphone 🎙️ and speak, or type your question below!",
            "transcript": ""
        }), 200

    finally:
        for p in [input_path, output_wav]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


@app.route("/music/stream", methods=["GET"])
def music_stream():
    """Streams the active downloaded music track to the web browser with range support."""
    info = get_current_music_info()
    file_path = info.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "No music file currently available"}), 404
    return send_file(
        file_path,
        mimetype="audio/mpeg",
        as_attachment=False,
        conditional=True
    )


@app.route("/music/pause", methods=["POST"])
def pause_music_endpoint():
    """Endpoint for web interface to pause music playback."""
    result = pause_music()
    return jsonify({"success": True, "reply": result, "is_paused": True, "music_status": get_current_music_info()})


@app.route("/music/resume", methods=["POST"])
def resume_music_endpoint():
    """Endpoint for web interface to resume music playback."""
    result = resume_music()
    return jsonify({"success": True, "reply": result, "is_playing": True, "music_status": get_current_music_info()})


@app.route("/music/stop", methods=["POST"])
def stop_music_endpoint():
    """Endpoint for web interface to stop music playback."""
    result = stop_music()
    return jsonify({"success": True, "reply": result, "is_stopped": True, "music_status": get_current_music_info()})


@app.route("/music/status", methods=["GET"])
def music_status_endpoint():
    """Returns current music playback status."""
    return jsonify(get_current_music_info())


@app.route("/history", methods=["GET"])
def get_history():
    """Returns the in-memory chat history as JSON."""
    return jsonify({"history": chat_history})


@app.route("/clear", methods=["POST"])
def clear_history():
    """Resets the in-memory conversation context for both web and AI brain."""
    global chat_history
    chat_history.clear()
    IN_MEMORY_CONVERSATION.clear()
    clear_pending_action()
    clear_last_climate_map_info()
    print("[Web /clear] Conversation memory and follow-up state reset.\n")
    return jsonify({"status": "cleared", "history": []})


def generate_self_signed_cert(ssl_dir: Path, local_ip: str):
    """Generates a self-signed TLS/SSL certificate for HTTPS on mobile devices."""
    try:
        import datetime
        import ipaddress
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        ssl_dir.mkdir(exist_ok=True)
        cert_file = ssl_dir / "cert.pem"
        key_file = ssl_dir / "key.pem"

        if cert_file.exists() and key_file.exists():
            return str(cert_file), str(key_file)

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "HelloKittyAssistant")])

        san_list = [x509.DNSName("localhost"), x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]
        try:
            san_list.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))
        except Exception:
            pass

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
            .sign(key, hashes.SHA256())
        )

        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        with open(key_file, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        return str(cert_file), str(key_file)
    except Exception as exc:
        print(f"[SSL Generation Notice]: {exc}", flush=True)
        return None


if __name__ == "__main__":
    local_ip = get_local_ip()
    use_https = os.getenv("USE_HTTPS", "false").strip().lower() == "true" or "--https" in sys.argv
    proto = "https" if use_https else "http"

    print("\n" + "=" * 65)
    print(" 🎀 HELLO KITTY WEB & MOBILE INTERFACE SERVER RUNNING 🎀")
    print("=" * 65)
    print(f" Provider : {MODEL_PROVIDER.upper()}")
    print(f" Model    : {GEMINI_MODEL}")
    print(f" Protocol : {proto.upper()}")
    print("\n 💻 On this Computer (Browser):")
    print(f" >>> {proto}://127.0.0.1:5000 <<<")
    print("\n 📱 On your Mobile Phone (iPhone & Android on same Wi-Fi):")
    print(f" >>> {proto}://{local_ip}:5000 <<<")
    print("\n Press Ctrl+C in this terminal to stop the web server.")
    print("=" * 65 + "\n")

    ssl_ctx = None
    if use_https:
        ssl_ctx = generate_self_signed_cert(PROJECT_ROOT / "ssl", local_ip)

    app.run(host="0.0.0.0", port=5000, debug=False, ssl_context=ssl_ctx)
