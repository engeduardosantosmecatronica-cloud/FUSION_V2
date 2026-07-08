param(
    [ValidateSet('start','stop','status')]
    [string]$Action = 'status'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    $Python = Join-Path $Root 'venv\Scripts\python.exe'
}
$Script = Join-Path $Root 'tools\mt5_live_api.py'

function Get-Proc {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @('python.exe','pythonw.exe') -and $_.CommandLine -like "*mt5_live_api.py*" }
}

function Show-Status {
    $proc = @(Get-Proc)
    if ($proc.Count -gt 0) {
        $proc | ForEach-Object { Write-Host "api: pid=$($_.ProcessId) cmd=$($_.CommandLine)" }
    } else {
        Write-Host "api: not running"
    }
    try {
        $resp = & $Python -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:5000/api/health').read().decode())" 2>$null
        if ($resp) { Write-Host "health: $resp" }
    } catch {
        Write-Host "health: unavailable"
    }
}

function Stop-Api {
    $proc = @(Get-Proc)
    if ($proc.Count -gt 0) {
        Stop-Process -Id ($proc.ProcessId | Sort-Object -Unique) -Force
        Start-Sleep -Milliseconds 300
    }
    Show-Status
}

function Start-Api {
    if (-not (Test-Path $Python)) { throw "Python nao encontrado no venv." }
    if (-not (Test-Path $Script)) { throw "Script nao encontrado: $Script" }

    $existing = @(Get-Proc)
    if ($existing.Count -gt 0) {
        Write-Host "API ja esta rodando."
        Show-Status
        return
    }

    Start-Process -FilePath $Python -ArgumentList $Script -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 2
    Show-Status
}

switch ($Action) {
    'start' { Start-Api }
    'stop' { Stop-Api }
    'status' { Show-Status }
}
