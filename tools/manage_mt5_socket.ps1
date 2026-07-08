param(
    [ValidateSet('start','test','stop','status')]
    [string]$Action = 'status'
)

$ErrorActionPreference = 'Stop'





$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    $Python = Join-Path $Root 'venv\Scripts\python.exe'
}

$BridgeScript = Join-Path $Root 'tools\mt5_snapshot_api.py'
$TestScript = Join-Path $Root 'tools\test_mt5_socket_port.py'
$BridgePort = 45678
$HttpPort = 5000

function Get-ProcByScript {
    param([Parameter(Mandatory=$true)][string]$ScriptName)
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @('python.exe', 'pythonw.exe') -and $_.CommandLine -like "*$ScriptName*" }
}

function Get-PortLines {
    param([Parameter(Mandatory=$true)][int]$Port)
    $pattern = ":$Port"
    @(netstat -ano -p tcp 2>$null | Select-String $pattern)
}

function Show-Status {
    Write-Host "== MT5 Socket Status =="
    foreach ($port in @($BridgePort, $HttpPort)) {
        $lines = Get-PortLines -Port $port
        if ($lines.Count -gt 0) {
            Write-Host "Port ${port}:"
            foreach ($line in $lines) {
                Write-Host "  $line"
            }
        } else {
            Write-Host "Port ${port}: free"
        }
    }

    Write-Host ""
    Write-Host "== Python listeners =="
    $bridge = Get-ProcByScript -ScriptName 'mt5_snapshot_api.py'
    $test = Get-ProcByScript -ScriptName 'test_mt5_socket_port.py'
    if ($bridge) {
        $bridge | ForEach-Object { Write-Host "bridge: pid=$($_.ProcessId) cmd=$($_.CommandLine)" }
    } else {
        Write-Host "bridge: not running"
    }
    if ($test) {
        $test | ForEach-Object { Write-Host "test:   pid=$($_.ProcessId) cmd=$($_.CommandLine)" }
    } else {
        Write-Host "test:   not running"
    }
}

function Stop-Mt5Sockets {
    for ($attempt = 0; $attempt -lt 3; $attempt++) {
        $targets = @(Get-ProcByScript -ScriptName 'mt5_snapshot_api.py') + @(Get-ProcByScript -ScriptName 'test_mt5_socket_port.py')
        if (-not $targets -or $targets.Count -eq 0) {
            if ($attempt -eq 0) {
                Write-Host "Nada para parar."
            }
            break
        }
        $pids = $targets.ProcessId | Sort-Object -Unique
        Write-Host "Parando: $($pids -join ', ')"
        Stop-Process -Id $pids -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    }
}

function Start-Bridge {
    if (-not (Test-Path $Python)) {
        throw "Python nao encontrado em .venv/venv."
    }
    if (-not (Test-Path $BridgeScript)) {
        throw "Bridge nao encontrado: $BridgeScript"
    }

    $existing = @(Get-ProcByScript -ScriptName 'mt5_snapshot_api.py')
    if ($existing.Count -gt 0) {
        Write-Host "Bridge ja esta rodando."
        Show-Status
        return
    }

    $conflicts = @(Get-ProcByScript -ScriptName 'test_mt5_socket_port.py')
    if ($conflicts.Count -gt 0) {
        Write-Host "Listener de teste encontrado. Parando antes de subir o bridge..."
        Stop-Mt5Sockets
    }

    Write-Host "Subindo bridge em modo oculto..."
    Start-Process -FilePath $Python -ArgumentList $BridgeScript -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 2
    Show-Status
}

function Start-TestListener {
    if (-not (Test-Path $Python)) {
        throw "Python nao encontrado em .venv/venv."
    }
    if (-not (Test-Path $TestScript)) {
        throw "Script de teste nao encontrado: $TestScript"
    }

    $targets = @(Get-ProcByScript -ScriptName 'mt5_snapshot_api.py') + @(Get-ProcByScript -ScriptName 'test_mt5_socket_port.py')
    if ($targets.Count -gt 0) {
        Write-Host "Parando bridge/listener atuais para liberar a porta $BridgePort..."
        Stop-Mt5Sockets
    }

    Write-Host "Iniciando listener de teste na porta $BridgePort..."
    & $Python $TestScript
}

switch ($Action) {
    'start' { Start-Bridge }
    'test'  { Start-TestListener }
    'stop'  { Stop-Mt5Sockets; Show-Status }
    'status' { Show-Status }
}


