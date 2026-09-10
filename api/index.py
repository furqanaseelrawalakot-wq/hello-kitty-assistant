"""
api/index.py - Vercel Serverless Function Entrypoint for Hello Kitty Assistant.
"""

import os
import sys
import urllib.parse
from pathlib import Path

# Add project root to sys.path so modules like `brain`, `features`, `web` are importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Fallback audio driver for headless cloud serverless environments
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Import the Flask application instance
from web.app import app as flask_app


class VercelWSGIMiddleware:
    """
    Normalizes PATH_INFO when Vercel's edge router rewrites requests to /api/index.py.
    Ensures that routes like '/', '/chat', and '/static/...' resolve correctly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query = environ.get("QUERY_STRING", "")
        qs = urllib.parse.parse_qs(query, keep_blank_values=True)
        vercel_path = qs.pop("_vercel_path", [None])[0]

        if vercel_path:
            # Rebuild clean query string without _vercel_path
            environ["QUERY_STRING"] = urllib.parse.urlencode(qs, doseq=True)
            if not vercel_path.startswith("/"):
                vercel_path = "/" + vercel_path
            environ["PATH_INFO"] = vercel_path
        elif environ.get("PATH_INFO") in ("/api/index.py", "/api/index", "/api", ""):
            environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)


# Vercel's Python runtime requires `app` to be exposed at module level
app = VercelWSGIMiddleware(flask_app)

