param([int]$Port = 5173)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv/Scripts/python.exe"
$ApiScript = Join-Path $Root "tools/mt5_live_api.py"

try {
    Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:5000/api/health" -TimeoutSec 2 | Out-Null
}
catch {
    if (-not (Test-Path $Python)) { throw "Python virtual environment not found: $Python" }
    Start-Process -FilePath $Python -ArgumentList $ApiScript -WorkingDirectory $Root -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

Write-Host "Fusion MT5 API: http://127.0.0.1:5000"
Write-Host "Fusion Dashboard: http://127.0.0.1:$Port"
Push-Location $PSScriptRoot
try {
    npm run dev -- --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}