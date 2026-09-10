"""
api/index.py - Vercel Serverless Function Entrypoint for Hello Kitty Assistant.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path so modules like `brain`, `features`, `web` are importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Fallback audio driver for headless cloud serverless environments
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Import the Flask application instance
from web.app import app

# Vercel's Python runtime requires `app` to be exposed at module level
