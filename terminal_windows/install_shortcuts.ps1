param(
    [switch]$DesktopOnly,
    [switch]$StartMenuOnly
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$ExePath = Join-Path $Root "dist\FusionTerminalWindows\FusionTerminalWindows.exe"
$IconPath = $ExePath
$AppName = "Fusion Terminal Windows"

if (-not (Test-Path $ExePath)) {
    Write-Host "Executavel nao encontrado:"
    Write-Host $ExePath
    Write-Host ""
    Write-Host "Gere primeiro com:"
    Write-Host ".\terminal_windows\build_terminal_exe.ps1"
    exit 1
}

function New-FusionShortcut {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ShortcutPath
    )

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $ExePath
    $shortcut.WorkingDirectory = $Root
    $shortcut.IconLocation = $IconPath
    $shortcut.Description = "Abrir painel Fusion e controlar o robo"
    $shortcut.Save()
}

if (-not $StartMenuOnly) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $desktopShortcut = Join-Path $desktop "$AppName.lnk"
    New-FusionShortcut -ShortcutPath $desktopShortcut
    Write-Host "Atalho criado na Area de Trabalho:"
    Write-Host $desktopShortcut
}

if (-not $DesktopOnly) {
    $programs = [Environment]::GetFolderPath("Programs")
    $fusionFolder = Join-Path $programs "Fusion"
    if (-not (Test-Path $fusionFolder)) {
        New-Item -ItemType Directory -Path $fusionFolder | Out-Null
    }
    $startShortcut = Join-Path $fusionFolder "$AppName.lnk"
    New-FusionShortcut -ShortcutPath $startShortcut
    Write-Host "Atalho criado no Menu Iniciar:"
    Write-Host $startShortcut
}
