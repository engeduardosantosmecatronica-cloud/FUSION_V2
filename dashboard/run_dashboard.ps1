$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root "venv\Scripts\python.exe"
$Streamlit = Join-Path $Root "venv\Scripts\streamlit.exe"

if (-not (Test-Path $Streamlit)) {
    Write-Host "Streamlit nao encontrado no venv."
    Write-Host "Instale com: $Python -m pip install -r dashboard\requirements.txt"
    exit 1
}

& $Streamlit run (Join-Path $Root "dashboard\fusion_dashboard.py") --server.port 8501 --server.address 127.0.0.1 --server.headless true
