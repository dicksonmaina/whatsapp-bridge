# OpenClaw + BaileysBot Healthcheck
# Runs on boot via Task Scheduler after a short delay

$logFile = "C:\Users\user\whatsapp-bridge\healthcheck.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$results = @{}

function Check-Service {
    param([string]$Name)
    $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($svc) {
        if ($svc.Status -eq "Running") {
            return "PASS: $Name is running"
        }
        else {
            return "FAIL: $Name is $($svc.Status)"
        }
    }
    else {
        return "FAIL: $Name service not found"
    }
}

function Check-Port {
    param([int]$Port, [string]$Label)
    $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
    if ($conn) { return "PASS: $Label listening on port $Port" }
    else { return "FAIL: $Label NOT listening on port $Port" }
}

function Check-Process {
    param([string]$Name, [string]$Label)
    $proc = Get-Process -Name $Name -ErrorAction SilentlyContinue
    if ($proc) { return "PASS: $Label running (PID $($proc.Id))" }
    else { return "FAIL: $Label process not found" }
}

function Check-WSL {
    param([string]$Label)
    try {
        $output = wsl.exe -d Ubuntu -e systemctl --user is-active openclaw-gateway 2>&1
        if ($output -match "active") { return "PASS: $Label WSL gateway active" }
        else { return "FAIL: $Label WSL status: $($output.Trim())" }
    }
    catch { return "FAIL: $Label WSL check error" }
}

Write-Output "===== Health Check: $timestamp =====" | Tee-Object -Append -FilePath $logFile

$results["BaileysBot"] = Check-Service -Name "BaileysBot"
Write-Output $results["BaileysBot"] | Tee-Object -Append -FilePath $logFile

$results["OpenClaw-Windows"] = Check-Service -Name "OpenClawGateway"
Write-Output $results["OpenClaw-Windows"] | Tee-Object -Append -FilePath $logFile

$results["OpenClaw-Windows-Port"] = Check-Port -Port 18789 -Label "OpenClaw Windows"
Write-Output $results["OpenClaw-Windows-Port"] | Tee-Object -Append -FilePath $logFile

$results["OpenClaw-WSL"] = Check-WSL -Label "WSL"
Write-Output $results["OpenClaw-WSL"] | Tee-Object -Append -FilePath $logFile

$results["FlaskHandler"] = Check-Process -Name "python" -Label "Flask/jarvis_agi"
Write-Output $results["FlaskHandler"] | Tee-Object -Append -FilePath $logFile

$results["Flask-Port"] = Check-Port -Port 5051 -Label "Flask handler"
Write-Output $results["Flask-Port"] | Tee-Object -Append -FilePath $logFile

$results["Baileys-SendAPI"] = Check-Port -Port 5057 -Label "Baileys send API"
Write-Output $results["Baileys-SendAPI"] | Tee-Object -Append -FilePath $logFile

$passCount = ($results.Values | Where-Object { $_ -match "^PASS:" }).Count
$failCount = ($results.Values | Where-Object { $_ -match "^FAIL:" }).Count
$totalCount = $passCount + $failCount

Write-Output "" | Tee-Object -Append -FilePath $logFile
Write-Output "===== SUMMARY: $passCount/$totalCount PASS, $failCount/$totalCount FAIL =====" | Tee-Object -Append -FilePath $logFile
Write-Output "===== End of health check =====" | Tee-Object -Append -FilePath $logFile

Write-Host ""
Write-Host "--- Health Check Summary ---" -ForegroundColor Cyan
$results.GetEnumerator() | ForEach-Object {
    if ($_.Value -match "^PASS:") { Write-Host $_.Value -ForegroundColor Green }
    else { Write-Host $_.Value -ForegroundColor Red }
}
Write-Host "--- $passCount/$totalCount PASS, $failCount/$totalCount FAIL ---" -ForegroundColor Cyan