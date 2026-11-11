@echo off
cd /d "%~dp0"
echo ========================================================
echo   Starting Dental Clinic Website (FastAPI + Jinja2)
echo ========================================================
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
pause

