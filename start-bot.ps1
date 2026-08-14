# JARVIS WhatsApp Bridge - Isolated Boot Startup
# Starts all components in isolated sessions
# Logs to whatsapp-bridge/logs/

$ErrorActionPreference = "Stop"
$botDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $botDir "logs"
$pidFile = Join-Path $botDir "instance.pid"

# Ensure log directory exists
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logLine = "[$timestamp] $Message"
    Add-Content -Path (Join-Path $logDir "startup.log") -Value $logLine
    Write-Host $logLine
}

# Check if already running
if (Test-Path $pidFile) {
    $oldPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        Write-Log "Already running (PID: $oldPid). Exiting."
        exit 0
    }
}

# Save current PID
$pid = $PID
Set-Content -Path $pidFile -Value $pid
Write-Log "Starting JARVIS WhatsApp Bridge (PID: $pid)"

# Start JARVIS AGI Server (if not running)
$agiRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5052/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        $agiRunning = $true
        Write-Log "JARVIS AGI already running"
    }
} catch {}

if (-not $agiRunning) {
    Write-Log "Starting JARVIS AGI server..."
    $agiScript = Join-Path $botDir "..\.openclaw\services\jarvis-agi-server.py"
    if (Test-Path $agiScript) {
        Start-Process -FilePath "python" -ArgumentList "`"$agiScript`"" -WindowStyle Hidden -WorkingDirectory $botDir
        Start-Sleep -Seconds 3
        Write-Log "JARVIS AGI started"
    } else {
        Write-Log "WARNING: JARVIS AGI script not found at $agiScript"
    }
}

# Start Flask Handler
Write-Log "Starting Flask handler..."
$flaskProc = Start-Process -FilePath "python" -ArgumentList "`"$($botDir)\whatsapp_handler.py`" --serve --port 5056" -WindowStyle Hidden -WorkingDirectory $botDir -PassThru
Start-Sleep -Seconds 3

# Verify Flask
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5056/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Log "Flask Handler started (PID: $($flaskProc.Id))"
    }
} catch {
    Write-Log "WARNING: Flask Handler not responding yet"
}

# Start Baileys Bot
Write-Log "Starting Baileys bot..."
$botProc = Start-Process -FilePath "node" -ArgumentList "`"$($botDir)\bot.js`"" -WindowStyle Hidden -WorkingDirectory $botDir -PassThru
Start-Sleep -Seconds 5

# Verify Bot
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5057/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Log "Baileys Bot started (PID: $($botProc.Id))"
    }
} catch {
    Write-Log "WARNING: Baileys Bot not responding yet"
}

Write-Log "All services started. Monitoring..."
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  JARVIS WhatsApp Bridge Started" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  - Flask Handler:  http://localhost:5056" -ForegroundColor White
Write-Host "  - Baileys Bot:    http://localhost:5057" -ForegroundColor White
Write-Host "  - JARVIS AGI:     http://localhost:5052" -ForegroundColor White
Write-Host ""
Write-Host "Logs: $logDir" -ForegroundColor Gray
Write-Host ""

# Keep script alive and monitor
$checkInterval = 30
while ($true) {
    Start-Sleep -Seconds $checkInterval
    
    # Check if our PIDs are still alive
    $botAlive = $false
    $flaskAlive = $false
    
    try {
        $botResponse = Invoke-WebRequest -Uri "http://localhost:5057/health" -UseBasicParsing -TimeoutSec 2
        $botAlive = $botResponse.StatusCode -eq 200
    } catch {}
    
    try {
        $flaskResponse = Invoke-WebRequest -Uri "http://localhost:5056/health" -UseBasicParsing -TimeoutSec 2
        $flaskAlive = $flaskResponse.StatusCode -eq 200
    } catch {}
    
    if (-not $botAlive -or -not $flaskAlive) {
        Write-Log "WARNING: Service down. Bot: $botAlive, Flask: $flaskAlive"
    }
}
