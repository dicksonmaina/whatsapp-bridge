@echo off
chcp 65001 >nul
title JARVIS WhatsApp Bridge - Boot Startup
cd /d "%~dp0"

echo ========================================
echo   JARVIS WhatsApp Bridge - Starting...
echo ========================================
echo.

set PYTHON=python
set NODE=node
set BOT_DIR=%~dp0
set LOG_DIR=%BOT_DIR%logs
set PID_FILE=%BOT_DIR%instance.pid

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo [%date% %time%] Starting JARVIS WhatsApp Bridge..." >> "%LOG_DIR%\startup.log"

:: Check if already running
if exist "%PID_FILE%" (
    set /p OLD_PID=<"%PID_FILE%"
    tasklist /FI "PID eq %OLD_PID%" 2>nul | find /I "%OLD_PID%" >nul
    if not errorlevel 1 (
        echo [%date% %time%] Already running (PID: %OLD_PID%). Exiting." >> "%LOG_DIR%\startup.log"
        echo Already running. Exiting.
        pause
        exit /b 0
    )
)

echo %PPID% > "%PID_FILE%"

:: Start JARVIS AGI Server (if not already running)
echo Checking JARVIS AGI server...
netstat -ano | findstr :5052 | findstr LISTENING >nul
if errorlevel 1 (
    echo Starting JARVIS AGI server...
    start "JARVIS AGI" /MIN cmd /c "%PYTHON% "%BOT_DIR%..\.openclaw\services\jarvis-agi-server.py"" 
    timeout /t 3 /nobreak >nul
) else (
    echo JARVIS AGI already running.
)

:: Start Flask Handler
echo Starting Flask handler...
start "Flask Handler" /MIN cmd /c "%PYTHON% "%BOT_DIR%whatsapp_handler.py" --serve --port 5056"
timeout /t 3 /nobreak >nul

:: Start Baileys Bot
echo Starting Baileys bot...
start "Baileys Bot" /MIN cmd /c "%NODE% "%BOT_DIR%bot.js""
timeout /t 5 /nobreak >nul

:: Verify startup
echo.
echo Verifying services...
curl -s http://localhost:5056/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Flask Handler: http://localhost:5056
) else (
    echo [FAIL] Flask Handler not responding
)

curl -s http://localhost:5057/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Baileys Bot: http://localhost:5057
) else (
    echo [FAIL] Baileys Bot not responding
)

echo.
echo ========================================
echo   JARVIS WhatsApp Bridge Started
echo ========================================
echo.
echo Services:
echo   - Flask Handler:  http://localhost:5056
echo   - Baileys Bot:    http://localhost:5057
echo   - JARVIS AGI:     http://localhost:5052
echo.
echo Logs: %LOG_DIR%
echo.
timeout /t 5 /nobreak >nul
