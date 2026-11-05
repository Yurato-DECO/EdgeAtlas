@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -c "import PySide6.QtWebEngineWidgets, requests" >nul 2>&1
if errorlevel 1 (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo Installation or launch failed. See the error above.
pause
exit /b 1
