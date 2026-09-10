@echo off
title Hello Kitty Web Assistant
cd /d "%~dp0"
echo Starting Hello Kitty Web Server...
echo Open your browser to: http://127.0.0.1:5000
.\venv\Scripts\python.exe web\app.py
pause
