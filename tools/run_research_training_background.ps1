param(
    [string]$BlockFreq = "M",
    [int]$Embargo = 2
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = Join-Path $Root "reports\research_models"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$OutLog = Join-Path $LogDir "train_full_$Timestamp.out.log"
$ErrLog = Join-Path $LogDir "train_full_$Timestamp.err.log"
$PidFile = Join-Path $LogDir "train_full_$Timestamp.pid"
$Py = Join-Path $Root "venv\Scripts\python.exe"

$Psi = [System.Diagnostics.ProcessStartInfo]::new()
$Psi.FileName = $Py
$Psi.Arguments = "tools\train_research_models.py --block-freq $BlockFreq --embargo $Embargo"
$Psi.WorkingDirectory = $Root
$Psi.UseShellExecute = $false
$Psi.CreateNoWindow = $true
$Process = [System.Diagnostics.Process]::Start($Psi)

$Process.Id | Set-Content -Path $PidFile
Write-Output "PID=$($Process.Id)"
Write-Output "OUT=$OutLog"
Write-Output "ERR=$ErrLog"
Write-Output "PID_FILE=$PidFile"
