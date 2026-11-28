@echo off
setlocal
cd /d "%~dp0"
title TaskDesk server check
set PY=%LOCALAPPDATA%\Programs\TaskDesk\python\python.exe
if not exist "%PY%" set PY=python
"%PY%" "%~dp0check_server.py" %*
echo.
pause
