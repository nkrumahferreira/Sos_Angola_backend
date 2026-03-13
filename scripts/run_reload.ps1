# Inicia a API com reload, excluindo .venv para evitar loop de reinício
# Uso: a partir da raiz do Sos_Angola_backend: .\scripts\run_reload.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (Test-Path "$root\.venv\Scripts\Activate.ps1") {
    & "$root\.venv\Scripts\Activate.ps1"
}
Set-Location $root
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --reload-exclude ".venv"
