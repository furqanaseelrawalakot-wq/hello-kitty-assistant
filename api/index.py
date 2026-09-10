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
from web.app import app as flask_app


class VercelWSGIMiddleware:
    """
    Normalizes PATH_INFO when Vercel's edge router rewrites requests to /api/index.py.
    Ensures that routes like '/', '/chat', and '/static/...' resolve correctly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched = environ.get("HTTP_X_MATCHED_PATH") or environ.get("HTTP_X_FORWARDED_URI")
        path_info = environ.get("PATH_INFO", "")

        if path_info in ("/api/index.py", "/api/index", "/api", ""):
            environ["PATH_INFO"] = "/"
        elif path_info.startswith("/api/index.py/"):
            environ["PATH_INFO"] = path_info[len("/api/index.py"):]
        elif path_info.startswith("/api/index/"):
            environ["PATH_INFO"] = path_info[len("/api/index"):]
        elif path_info.startswith("/api/"):
            environ["PATH_INFO"] = path_info[len("/api"):]

        if matched and matched != "/api/index.py" and not matched.startswith("/api"):
            environ["PATH_INFO"] = matched

        return self.wsgi_app(environ, start_response)


# Vercel's Python runtime requires `app` to be exposed at module level
app = VercelWSGIMiddleware(flask_app)

