@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [OYUCMS] creating virtual environment...
  python -m venv .venv
  if errorlevel 1 goto :err
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :err
)

if not exist "instance\oyucms.db" (
  echo [OYUCMS] initializing database...
  ".venv\Scripts\python.exe" init_db.py
  if errorlevel 1 goto :err
)

echo.
echo [OYUCMS] http://127.0.0.1:5000/
echo [OYUCMS] admin: http://127.0.0.1:5000/oyu/
echo.
".venv\Scripts\python.exe" oyucms.py
goto :eof

:err
echo [OYUCMS] startup failed.
pause
exit /b 1
