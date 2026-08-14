@echo off
chcp 65001 >nul
title Setup JARVIS WhatsApp Bridge Auto-Start
echo ========================================
echo   JARVIS WhatsApp Bridge - Auto-Start Setup
echo ========================================
echo.
echo This script will create a Windows Scheduled Task to auto-start
echo the WhatsApp bot stack when your computer boots.
echo.
echo The task will:
echo   - Start automatically on boot
echo   - Run in isolated mode (won't affect other processes)
echo   - Restart services if they crash
echo   - Log all activity to logs/startup.log
echo.
pause
echo.

:: Create the scheduled task
echo Creating scheduled task...
schtasks /Create /TN "JARVIS WhatsApp Bridge" /TR "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File \"C:\Users\user\whatsapp-bridge\start-bot.ps1\"" /SC ONSTART /DELAY 0000:30 /F /RL HIGHEST /RU "%USERNAME%" 2>&1

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Scheduled task created!
    echo.
    echo The bot will now start automatically when you boot your computer.
    echo.
    echo To test it:
    echo   1. Run: schtasks /Run /TN "JARVIS WhatsApp Bridge"
    echo   2. Check logs: whatsapp-bridge\logs\startup.log
    echo.
    echo To remove the auto-start:
    echo   schtasks /Delete /TN "JARVIS WhatsApp Bridge" /F
    echo.
) else (
    echo.
    echo [ERROR] Failed to create scheduled task.
    echo This usually means you need to run this script as Administrator.
    echo.
    echo Please:
    echo   1. Right-click this file
    echo   2. Select "Run as administrator"
    echo   3. Try again
    echo.
)

pause
