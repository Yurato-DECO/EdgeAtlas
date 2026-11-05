@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m PyInstaller --noconfirm EdgeAtlas.spec
if errorlevel 1 goto fail
".venv\Scripts\python.exe" package_release.py
if errorlevel 1 goto fail
echo Build complete: dist\EdgeAtlas\EdgeAtlas.exe
exit /b 0
:fail
echo Build failed. See the error above.
pause
exit /b 1
