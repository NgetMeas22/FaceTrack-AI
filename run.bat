@echo off
cd /d "%~dp0"
echo ========================================================
echo   Starting FaceTrack AI (FastAPI + OpenCV + Tailwind)
echo ========================================================
echo.
call .venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause

