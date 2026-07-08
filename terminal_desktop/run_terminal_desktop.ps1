$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root "venv\Scripts\python.exe"
$App = Join-Path $Root "terminal_desktop\fusion_terminal_desktop.py"

& $Python $App
