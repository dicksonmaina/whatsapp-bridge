@echo off
chcp 65001 >nul
title JARVIS WhatsApp Bridge
cd /d "%~dp0"

:: Isolated startup - runs in its own process group
:: Won't affect other processes or be affected by them

echo [%date% %time%] Starting JARVIS WhatsApp Bridge..." >> "%~dp0logs\startup.log"

:: Kill any orphaned instances from previous runs
tasklist /FI "WINDOWTITLE eq JARVIS WhatsApp Bridge*" 2>nul | find /I "JARVIS" >nul && taskkill /F /FI "WINDOWTITLE eq JARVIS WhatsApp Bridge*" >nul 2>&1
tasklist /FI "WINDOWTITLE eq Baileys Bot*" 2>nul | find /I "Baileys" >nul && taskkill /F /FI "WINDOWTITLE eq Baileys Bot*" >nul 2>&1
tasklist /FI "WINDOWTITLE eq Flask Handler*" 2>nul | find /I "Flask" >nul && taskkill /F /FI "WINDOWTITLE eq Flask Handler*" >nul 2>&1
tasklist /FI "WINDOWTITLE eq JARVIS AGI*" 2>nul | find /I "JARVIS" >nul && taskkill /F /FI "WINDOWTITLE eq JARVIS AGI*" >nul 2>&1

timeout /t 2 /nobreak >nul

:: Start JARVIS AGI Server
echo Starting JARVIS AGI...
start "JARVIS AGI" /MIN cmd /c "python "%~dp0..\.openclaw\services\jarvis-agi-server.py""
timeout /t 3 /nobreak >nul

:: Start Flask Handler
echo Starting Flask Handler...
start "Flask Handler" /MIN cmd /c "python "%~dp0whatsapp_handler.py" --serve --port 5056"
timeout /t 3 /nobreak >nul

:: Start Baileys Bot
echo Starting Baileys Bot...
start "Baileys Bot" /MIN cmd /c "node "%~dp0bot.js""
timeout /t 5 /nobreak >nul

:: Verify
echo.
echo Verifying services...
curl -s http://localhost:5056/health >nul 2>&1 && echo [OK] Flask Handler || echo [FAIL] Flask Handler
curl -s http://localhost:5057/health >nul 2>&1 && echo [OK] Baileys Bot || echo [FAIL] Baileys Bot
curl -s http://localhost:5052/health >nul 2>&1 && echo [OK] JARVIS AGI || echo [FAIL] JARVIS AGI

echo.
echo [%date% %time%] Startup complete." >> "%~dp0logs\startup.log"

:: Keep window open briefly to show status
timeout /t 5 /nobreak >nul
