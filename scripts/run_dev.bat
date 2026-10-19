@echo off
title ClipPilot AI — Prompt-to-Video Editing Studio Launcher
echo ================================================================
echo           ClipPilot AI — IncuBrix PS2 Submission Launcher
echo ================================================================
echo.

:: 1. Verify/Set FFmpeg path
set FFMPEG_BIN=%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg.Essentials_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-essentials_build\bin
if exist "%FFMPEG_BIN%\ffmpeg.exe" (
    set "PATH=%FFMPEG_BIN%;%PATH%"
    echo [OK] FFmpeg 9.0 located: %FFMPEG_BIN%\ffmpeg.exe
) else (
    echo [INFO] Using system PATH for FFmpeg...
)

:: 2. Generate sample assets if needed
echo [INFO] Checking sample media assets...
python "%~dp0generate_sample_videos.py"

:: 3. Start Backend in new window
echo [INFO] Starting FastAPI Backend on http://127.0.0.1:8000...
start "ClipPilot Backend API" cmd /k "cd /d "%~dp0..\backend" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

:: Wait 2 seconds for backend to start
timeout /t 2 /nobreak >nul

:: 4. Start Frontend in new window
echo [INFO] Starting Vite Frontend on http://127.0.0.1:5173...
start "ClipPilot Frontend Studio" cmd /k "cd /d "%~dp0..\frontend" && npm run dev -- --host 127.0.0.1 --port 5173"

:: Wait 2 seconds and open browser
timeout /t 2 /nobreak >nul
start http://127.0.0.1:5173

echo.
echo ================================================================
echo ClipPilot AI is now running!
echo   Frontend Studio: http://127.0.0.1:5173
echo   Backend API:     http://127.0.0.1:8000
echo   API Docs:        http://127.0.0.1:8000/docs
echo ================================================================
pause
