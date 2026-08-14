@echo off
chcp 65001 >nul
title JARVIS WhatsApp Bridge - Manager
cd /d "%~dp0"

:menu
cls
echo ========================================
echo   JARVIS WhatsApp Bridge - Manager
echo ========================================
echo.
echo [1] Start Bot Stack
echo [2] Stop Bot Stack
echo [3] Restart Bot Stack
echo [4] Status
echo [5] View Logs
echo [6] Test Connection
echo [7] Exit
echo.
set /p choice="Select option (1-7): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto restart
if "%choice%"=="4" goto status
if "%choice%"=="5" goto logs
if "%choice%"=="6" goto test
if "%choice%"=="7" goto end
goto menu

:start
echo Starting JARVIS WhatsApp Bridge...
call "%~dp0auto-start.bat"
pause
goto menu

:stop
echo Stopping JARVIS WhatsApp Bridge...
taskkill /F /FI "WINDOWTITLE eq JARVIS WhatsApp Bridge*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Baileys Bot*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Flask Handler*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS AGI*" >nul 2>&1
echo All services stopped.
pause
goto menu

:restart
call :stop
timeout /t 2 /nobreak >nul
call :start
goto menu

:status
echo.
echo Checking services...
curl -s http://localhost:5052/health >nul 2>&1 && echo [OK] JARVIS AGI || echo [FAIL] JARVIS AGI
curl -s http://localhost:5056/health >nul 2>&1 && echo [OK] Flask Handler || echo [FAIL] Flask Handler
curl -s http://localhost:5057/health >nul 2>&1 && echo [OK] Baileys Bot || echo [FAIL] Baileys Bot
echo.
pause
goto menu

:logs
echo.
echo Recent log entries (last 20 lines):
echo ----------------------------------------
if exist "%~dp0logs\startup.log" (
    powershell -Command "Get-Content '%~dp0logs\startup.log' -Tail 20"
) else (
    echo No logs found.
)
echo.
pause
goto menu

:test
echo.
echo Testing webhook...
echo.
echo Test 1: /start command
curl -s -X POST http://localhost:5056/webhook -H "Content-Type: application/json" -d "{\"message\":\"/start\",\"sender\":\"test\"}"
echo.
echo.
echo Test 2: Free text
curl -s -X POST http://localhost:5056/webhook -H "Content-Type: application/json" -d "{\"message\":\"Hello JARVIS\",\"sender\":\"test\"}"
echo.
echo.
pause
goto menu

:end
exit
