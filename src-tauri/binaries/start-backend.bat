@echo off
REM Launcher para backend con Python embebido
REM Este script inicia el servidor FastAPI usando Python embebido

setlocal

REM Obtener el directorio de este script
set "SCRIPT_DIR=%~dp0"

REM Paths relativos
set "PYTHON_EMBED=%SCRIPT_DIR%python-embed\python.exe"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "MAIN_PY=%BACKEND_DIR%\api-server\main.py"

REM Verificar que Python embebido existe
if not exist "%PYTHON_EMBED%" (
    echo ERROR: Python embebido no encontrado en %PYTHON_EMBED%
    exit /b 1
)

REM Verificar que backend existe
if not exist "%MAIN_PY%" (
    echo ERROR: Backend no encontrado en %MAIN_PY%
    exit /b 1
)

REM Cambiar al directorio del backend
cd /d "%BACKEND_DIR%\api-server"

REM Set PYTHONPATH to include backend directories
set "PYTHONPATH=%BACKEND_DIR%;%BACKEND_DIR%\api-server;%PYTHONPATH%"

REM Ejecutar main.py directamente
"%PYTHON_EMBED%" "%MAIN_PY%"

endlocal
