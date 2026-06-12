@echo off
rem Double-clickable launcher for the U-Haul Space Optimizer (Windows).
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo Python 3 is required - install it from python.org and try again.
    pause
    exit /b 1
)
python launch_uhaul.py %*
pause
