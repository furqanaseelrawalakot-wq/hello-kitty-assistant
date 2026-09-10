# 🎀 Hello Kitty — Full AI Voice Assistant & Web App

An AI-powered desktop voice assistant and web interface inspired by Google Assistant and Alexa, themed after **Hello Kitty**.
Activated hands-free via wake words (**"Hello Kitty"**, **"Hey Kitty"**, **"Kitty"**), featuring a modular architecture, dual LLM provider support (Google Gemini & OpenAI), offline smart persona fallback, built-in system features (Time, Date, Weather, Alarms, Music, Singing, Urdu translation), full web chat frontend, and zero database overhead (pure in-memory).

---

## 📁 Project Architecture

The codebase strictly follows a clean, modular structure where each folder serves an isolated responsibility:

```text
hello_kitty_assistant/
├── brain/                    # AI logic: Gemini & OpenAI APIs + In-memory context
│   ├── __init__.py
│   ├── llm_provider.py       # AI router, in-memory conversation list & get_ai_response()
│   ├── gemini_client.py      # Google Gemini client (google-generativeai)
│   └── openai_client.py      # OpenAI client (GPT-4o / GPT-4o-mini)
├── voice/                    # Speech I/O layer
│   ├── __init__.py
│   ├── listener.py           # Speech-to-text, wake word listening, Urdu ur-PK fallback
│   └── speaker.py            # Text-to-speech (gTTS) & audio playback (pygame)
├── features/                 # Built-in skills (intercepted before AI brain)
│   ├── __init__.py
│   ├── time_date.py          # Current system time and date
│   ├── weather.py            # OpenWeatherMap API integration
│   ├── alarm.py              # In-memory alarms with background threaded timer
│   ├── music.py              # YouTube search via yt-dlp + background audio stream
│   ├── singing.py            # Song lyric generation & rhythmic vocal delivery
│   ├── translation.py        # Urdu detection & bi-directional translation pipeline
│   └── dispatcher.py         # Master feature interceptor
├── web/                      # Full Flask Web Frontend
│   ├── app.py                # Flask server (/chat, /history, /clear endpoints)
│   ├── templates/
│   │   └── index.html        # Responsive pastel Hello Kitty chat UI
│   └── static/
│       ├── style.css         # Pastel pink aesthetic CSS & animations
│       └── script.js         # Chat client, Enter key support & typing indicator
├── config/                   # Configuration & environment variables
│   ├── __init__.py
│   └── settings.py           # .env loader, persona prompts, and key validation
├── scripts/                  # Executable entry points
│   └── main.py               # Primary voice loop assistant entry point
├── tests/                    # Unit tests & live verification scripts
│   ├── test_core.py          # Core unit test suite (11 tests)
│   ├── test_web.py           # Flask web routes unit test suite (6 tests)
│   ├── test_brain_live.py    # Requirement 2: AI brain & memory live test
│   ├── test_features_live.py # Requirement 3: Time, date, weather, alarm live test
│   ├── test_music_live.py    # Requirement 4: yt-dlp search, mp3 stream & stop test
│   ├── test_urdu_live.py     # Requirement 5: Urdu detection & translation pipeline test
│   └── test_singing_live.py  # Requirement 6: Lyric composition & singing test
├── vercel.json               # Serverless deployment configuration for Vercel
├── .env.example              # Environment variable template
├── requirements.txt          # Python dependencies
└── README.md                 # Complete project documentation
```

---

## 🌟 Features Implemented (All 8 Requirements)

### 1. Wake Word & Voice Loop (Requirement 1)
- Listens for `"Hello Kitty"`, `"Hey Kitty"`, or `"Kitty"` using `speech_recognition`.
- Audio calibration with minimum threshold (`>= 250`) to prevent fan noise locks.
- Real-time feedback: responds with *"Yes? I'm listening!"* or processes immediate commands spoken in the same breath (e.g., *"Hello Kitty what time is it"*).
- Displays real-time `[Mic Heard]: "..."` in the console for complete transparency.

### 2. AI Brain & Memory (Requirement 2)
- Reusable `get_ai_response(text)` function in `brain/llm_provider.py`.
- Integrates with Google Gemini API (`gemini-1.5-flash`) or OpenAI (`gpt-4o-mini`).
- Built-in `MockClient` offline persona that answers identity, hobbies, jokes, and stories even if an API key is not configured.
- Maintains in-memory short-term memory of the last 5 exchanges (10 turns) with zero database.

### 3. Built-in Features (Requirement 3)
- **Time**: *"what time is it"* -> returns formatted 12-hour local time.
- **Date**: *"what's today's date"* -> returns full day, month, date, and year.
- **Weather**: *"what's the weather in Tokyo"* -> queries OpenWeatherMap API using `WEATHER_API_KEY`.
- **Alarm**: *"set an alarm for 10 seconds"* -> launches a background daemon thread that chimes and notifies when time expires.

### 4. YouTube Music Playback (Requirement 4)
- **Play Music**: *"play classical music on youtube"* or *"play lofi hip hop"*.
- Uses `yt-dlp` to search YouTube, downloads audio stream, converts to MP3 using `imageio-ffmpeg`, and plays asynchronously via `pygame.mixer`.
- **Stop Music**: Say *"stop music"*, *"pause music"*, or *"stop the song"* to instantly halt playback.

### 5. Urdu Language Support (Requirement 5)
- Automatically detects Urdu script (`[\u0600-\u06FF]`) or Urdu statistical scoring (`langdetect`).
- Translates Urdu query to English via `deep-translator` (with fallback chains).
- Sends translated English to AI Brain.
- Translates AI reply back into natural Urdu.
- Speaks the response in native Urdu voice using `gTTS(lang='ur')`.

### 6. Sing a Song (Requirement 6)
- **Singing**: Say *"sing a song about red apples"* or *"sing about friendship"*.
- Extracts the topic and queries the AI brain for 4-6 lines of rhyming lyrics.
- Performs the lyrics using `voice/speaker.py` with sing-song pacing.

### 7. Full Flask Web Frontend (Requirement 7)
- Located in `web/app.py` with responsive HTML/CSS/JS in `web/templates/` and `web/static/`.
- Pastel Hello Kitty UI with avatar, online status badge, and clickable suggestion chips.
- Endpoints:
  - `POST /chat`: Receives text, routes to features or AI brain, returns JSON response.
  - `GET /history`: Returns in-memory session history.
  - `POST /clear`: Resets conversation memory.

### 8. Vercel Deployment Ready (Requirement 8)
- `vercel.json` included in root for deploying the Flask app to Vercel Serverless Functions.

---

## 🚀 Getting Started

### 1. Desktop 1-Click Launchers
Two desktop shortcuts have been created on your Windows Desktop:
- **`Start_Hello_Kitty_Voice.bat`**: Double-click to launch the hands-free voice assistant in a terminal.
- **`Start_Hello_Kitty_Web.bat`**: Double-click to launch the Flask web server and open your browser at `http://127.0.0.1:5000`.

### 2. Opening the Project in Visual Studio Code
To open this project in Visual Studio Code:
1. Open VS Code.
2. Go to **File** -> **Open Folder...**
3. Select the folder:
   ```text
   C:\Users\hp\.gemini\antigravity\scratch\hello_kitty_assistant
   ```
4. Open the integrated terminal (`Ctrl + ~`) and select the Python interpreter from `.\venv\Scripts\python.exe`.

---

## ⚙️ Configuration (`.env`)

Edit `C:\Users\hp\.gemini\antigravity\scratch\hello_kitty_assistant\.env` to configure your keys:

```env
# Choose: 'gemini', 'openai', or 'mock'
MODEL_PROVIDER=gemini

# Google Gemini API key (Get free at https://aistudio.google.com/)
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash

# OpenAI API key (if MODEL_PROVIDER=openai)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# OpenWeatherMap API key (Get free at https://openweathermap.org/api)
WEATHER_API_KEY=

WAKE_WORD=hello kitty
VOICE_LANGUAGE=en
```

> **Note**: Even if you do not set an API key, the assistant works immediately using the smart offline `MockClient` persona!

---

## 🧪 Testing & Verification

### Run Full Automated Unit Test Suite (17 Tests)
```powershell
.\venv\Scripts\python.exe -m unittest discover tests
```
*Result: 17/17 tests passing.*

### Run Live Requirement Verification Scripts
```powershell
# Verify AI Brain & Memory (Requirement 2)
.\venv\Scripts\python.exe tests/test_brain_live.py

# Verify Time, Date, Weather & Alarm (Requirement 3)
.\venv\Scripts\python.exe tests/test_features_live.py

# Verify YouTube Music Playback & Stop (Requirement 4)
.\venv\Scripts\python.exe tests/test_music_live.py

# Verify Urdu Language Detection, Translation & Speech (Requirement 5)
.\venv\Scripts\python.exe tests/test_urdu_live.py

# Verify Song Lyric Composition & Singing (Requirement 6)
.\venv\Scripts\python.exe tests/test_singing_live.py

# Verify Flask Web App Endpoints (Requirement 7)
.\venv\Scripts\python.exe -m unittest tests/test_web.py
```

---

## 🌐 Deploying to Vercel (Requirement 8)

To deploy the web frontend to Vercel:

1. Install the Vercel CLI:
   ```powershell
   npm install -g vercel
   ```
2. In the project root directory, run:
   ```powershell
   vercel
   ```
3. Set your environment variables in the Vercel Dashboard:
   - Go to **Project Settings** -> **Environment Variables**.
   - Add `MODEL_PROVIDER`, `GEMINI_API_KEY`, and `WEATHER_API_KEY`.
4. Run `vercel --prod` to deploy to production.
