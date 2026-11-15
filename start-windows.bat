@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 (
    echo Python 3.12 or later is required. Try the manual commands in README.md.
    pause
    exit /b 1
  )
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Package installation failed. Check your internet connection and README.md.
  pause
  exit /b 1
)
echo.
echo Open http://127.0.0.1:8000 in your browser. Keep this window open.
echo.
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
pause
