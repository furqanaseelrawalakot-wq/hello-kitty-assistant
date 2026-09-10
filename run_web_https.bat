@echo off
title Hello Kitty Web & Mobile Assistant (HTTPS)
cd /d "%~dp0"
echo Starting Hello Kitty Web Server with HTTPS for Mobile Phones...
.\venv\Scripts\python.exe web\app.py --https
pause
