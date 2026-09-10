@echo off
title Hello Kitty Live Online
cd /d "%~dp0"
echo Connecting Hello Kitty to the Live Public Internet...
.\venv\Scripts\python.exe run_live.py
pause
