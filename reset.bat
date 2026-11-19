@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [OYUCMS] virtual environment not found; run start.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" init_db.py
pause
