@echo off
chcp 65001 >nul
title JARVIS WhatsApp Bridge - Health Monitor
cd /d "%~dp0"

setlocal enabledelayedexpansion

set PYTHON=python
set NODE=node
set BOT_DIR=%~dp0
set LOG_DIR=%BOT_DIR%logs
set MAX_RETRIES=3
set RETRY_DELAY=5

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo [%date% %time%] Health monitor started" >> "%LOG_DIR%\healthmonitor.log"

:check_loop
set FAIL_COUNT=0

:: Check Flask Handler
curl -s http://localhost:5056/health >nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] Flask Handler down, restarting..." >> "%LOG_DIR%\healthmonitor.log"
    taskkill /F /FI "WINDOWTITLE eq Flask Handler*" >nul 2>&1
    start "Flask Handler" /MIN cmd /c "%PYTHON% "%BOT_DIR%whatsapp_handler.py" --serve --port 5056"
    timeout /t %RETRY_DELAY% /nobreak >nul
    set /a FAIL_COUNT+=1
)

:: Check Baileys Bot
curl -s http://localhost:5057/health >nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] Baileys Bot down, restarting..." >> "%LOG_DIR%\healthmonitor.log"
    taskkill /F /FI "WINDOWTITLE eq Baileys Bot*" >nul 2>&1
    start "Baileys Bot" /MIN cmd /c "%NODE% "%BOT_DIR%bot.js""
    timeout /t %RETRY_DELAY% /nobreak >nul
    set /a FAIL_COUNT+=1
)

:: Check JARVIS AGI
curl -s http://localhost:5052/health >nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] JARVIS AGI down, restarting..." >> "%LOG_DIR%\healthmonitor.log"
    taskkill /F /FI "WINDOWTITLE eq JARVIS AGI*" >nul 2>&1
    start "JARVIS AGI" /MIN cmd /c "%PYTHON% "%BOT_DIR%..\.openclaw\services\jarvis-agi-server.py""
    timeout /t %RETRY_DELAY% /nobreak >nul
    set /a FAIL_COUNT+=1
)

if !FAIL_COUNT! gtr %MAX_RETRIES% (
    echo [%date% %time%] WARNING: %FAIL_COUNT% services failed, pausing..." >> "%LOG_DIR%\healthmonitor.log"
    timeout /t 60 /nobreak >nul
)

timeout /t 30 /nobreak >nul
goto check_loop
