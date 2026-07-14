param(
    [switch]$NoMt5Bridge,
    [switch]$StartMt5Bridge,
    [double]$BridgeIntervalSeconds = 1.0,
    [int]$BridgeBars = 200,
    [string]$BridgeSymbols = "",
    [string]$BridgeTimeframes = "M5,M15,M30,H1,H4,D1"
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================================="
Write-Host "FUSION TERMINAL WINDOWS - INICIALIZACAO"
Write-Host "=================================================================================="

$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if (-not $dotnet -and (Test-Path "C:\Program Files\dotnet\dotnet.exe")) {
    $dotnet = Get-Item "C:\Program Files\dotnet\dotnet.exe"
}

if (-not $dotnet) {
    Write-Host "dotnet nao encontrado. Instale o .NET SDK 8+ antes de executar este terminal."
    Write-Host "Download: https://dotnet.microsoft.com/download"
    exit 1
}

Write-Host "dotnet encontrado: $($dotnet.Source)"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = Join-Path $Root "venv\Scripts\python.exe"
}
$BridgeScript = Join-Path $Root "tools\export_mt5_candles_for_terminal.py"
$BridgeProcess = $null

if ($StartMt5Bridge -and -not $NoMt5Bridge) {
    if ((Test-Path $Python) -and (Test-Path $BridgeScript)) {
        $BridgeArgs = @(
            $BridgeScript,
            "--timeframes", $BridgeTimeframes,
            "--bars", $BridgeBars.ToString(),
            "--interval", $BridgeIntervalSeconds.ToString([Globalization.CultureInfo]::InvariantCulture)
        )
        if (-not [string]::IsNullOrWhiteSpace($BridgeSymbols)) {
            $BridgeArgs += @("--symbols", $BridgeSymbols)
        }

        Write-Host "Iniciando ponte MT5 live para candles (barras=$BridgeBars)..."
        Write-Host "Comando: $Python $BridgeScript ..."
        $BridgeProcess = Start-Process -FilePath $Python -ArgumentList $BridgeArgs -WindowStyle Hidden -PassThru -ErrorAction SilentlyContinue

        if ($BridgeProcess) {
            Write-Host "Ponte MT5 iniciada (PID: $($BridgeProcess.Id))"
            Start-Sleep -Milliseconds 500
            if ($BridgeProcess.HasExited) {
                Write-Host "Ponte MT5 finalizou rapidamente. Exit code: $($BridgeProcess.ExitCode)"
            }
        }
        else {
            Write-Host "Falha ao iniciar ponte MT5."
        }
    }
    else {
        Write-Host "Ponte MT5 nao iniciada: python/script nao encontrado."
    }
}

Write-Host ""
Write-Host "=================================================================================="
Write-Host "Iniciando Fusion Terminal Windows..."
Write-Host "Projeto: FusionTerminalWindows.csproj"
Write-Host "Diretorio: $PSScriptRoot"
Write-Host "=================================================================================="
Write-Host ""

Push-Location $PSScriptRoot
try {
    & $dotnet.Source run --project .\FusionTerminalWindows.csproj
}
finally {
    Pop-Location
    if ($BridgeProcess -and -not $BridgeProcess.HasExited) {
        Write-Host ""
        Write-Host "Encerrando ponte MT5 live..."
        Stop-Process -Id $BridgeProcess.Id -Force
    }
}