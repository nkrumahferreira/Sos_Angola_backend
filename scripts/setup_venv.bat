@echo off
REM SOS Angola Backend - Configurar ambiente virtual (venv) e dependencias
REM Executar na pasta do projeto: scripts\setup_venv.bat

cd /d "%~dp0\.."
set PROJECT_ROOT=%CD%

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Erro: Python nao encontrado. Instale Python 3.10+ e adicione ao PATH.
    exit /b 1
)

set VENV_DIR=%PROJECT_ROOT%\.venv

if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo O ambiente virtual .venv ja existe.
) else (
    echo Criando ambiente virtual em .venv ...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
    echo Ambiente virtual criado.
)

echo Instalando dependencias (requirements.txt) ...
call "%VENV_DIR%\Scripts\activate.bat"
pip install -r requirements.txt -q
if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
echo Dependencias instaladas.

echo.
echo Para ativar o ambiente virtual, execute:
echo   .venv\Scripts\activate.bat
echo Depois, para criar o banco e tabelas:
echo   python -m scripts.create_database
echo Para iniciar a API:
echo   uvicorn main:app --reload
