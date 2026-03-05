# SOS Angola Backend - Configurar ambiente virtual (venv) e dependências
# Executar na pasta do projeto: .\scripts\setup_venv.ps1

$ErrorActionPreference = "Stop"
# Se o script está em scripts\setup_venv.ps1, a raiz é o pai da pasta scripts
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $projectRoot "main.py"))) {
    $projectRoot = Get-Location
}
Set-Location $projectRoot

$venvDir = Join-Path $projectRoot ".venv"
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Host "Erro: Python nao encontrado. Instale Python 3.10+ e adicione ao PATH." -ForegroundColor Red
    exit 1
}

Write-Host "Projeto: $projectRoot" -ForegroundColor Cyan
Write-Host "Python: $($pythonCmd.Source)" -ForegroundColor Cyan

if (Test-Path $venvDir) {
    Write-Host "O ambiente virtual .venv ja existe." -ForegroundColor Yellow
} else {
    Write-Host "Criando ambiente virtual em .venv ..." -ForegroundColor Green
    & $pythonCmd.Source -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Ambiente virtual criado." -ForegroundColor Green
}

$pip = Join-Path $venvDir "Scripts\pip.exe"
$activate = Join-Path $venvDir "Scripts\Activate.ps1"

Write-Host "Instalando dependencias (requirements.txt) ..." -ForegroundColor Green
& $pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Dependencias instaladas." -ForegroundColor Green

Write-Host ""
Write-Host "Para ativar o ambiente virtual, execute:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "Depois, para criar o banco e tabelas:" -ForegroundColor Cyan
Write-Host "  python -m scripts.create_database" -ForegroundColor White
Write-Host "Para iniciar a API:" -ForegroundColor Cyan
Write-Host "  uvicorn main:app --reload" -ForegroundColor White
