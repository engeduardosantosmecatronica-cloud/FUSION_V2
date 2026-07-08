param(
    [string]$Url = "http://127.0.0.1:5173/",
    [int]$Port = 5173
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$FrontendDir = Join-Path $Root "fusion-frontend"
$Npm = "E:\Program Files\nodejs\npm.cmd"

function Test-PortListening {
    param([int]$Port)
    $lines = netstat -ano | Select-String (":" + $Port)
    return [bool]($lines | Where-Object { $_ -match "LISTENING" })
}

if (-not (Test-PortListening -Port $Port)) {
    if (-not (Test-Path $Npm)) {
        throw "npm.cmd nao encontrado em $Npm"
    }
    Write-Host "Frontend nao estava ativo. Iniciando Vite em $Url ..."
    Start-Process -FilePath $Npm -ArgumentList "run","dev","--","--host","127.0.0.1","--port",$Port -WorkingDirectory $FrontendDir -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

$browsers = @(
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe"
)

$browser = $browsers | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $browser) {
    throw "Nao encontrei Edge nem Chrome instalado para abrir em modo app."
}

Write-Host "Abrindo Fusion Frontend em janela exclusiva: $Url"
Start-Process -FilePath $browser -ArgumentList @("--app=$Url", "--new-window")
