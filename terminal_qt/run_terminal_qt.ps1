$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "venv\Scripts\python.exe"
$App = Join-Path $Root "terminal_qt\fusion_terminal_qt.py"
& $Python $App
