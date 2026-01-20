@echo off
REM ============================================================
REM Script para iniciar Ollama en modo CPU
REM ============================================================
REM Este script inicia Ollama forzando el uso de CPU en lugar de GPU.
REM Util cuando la GPU tiene poca VRAM o problemas de compatibilidad CUDA.
REM
REM Uso: start_ollama_cpu.bat
REM      El servidor se inicia minimizado en segundo plano.
REM ============================================================

REM Force CPU-only mode (disable CUDA)
set CUDA_VISIBLE_DEVICES=-1
set OLLAMA_GPU_OVERHEAD=0
set OLLAMA_GPU_LAYERS=0
set OLLAMA_KEEP_ALIVE=5m
set OLLAMA_NUM_GPU=0

REM Start minimized in background
start /min "Ollama Server" "C:\Users\pauub\AppData\Local\Programs\Ollama\ollama.exe" serve

echo Ollama iniciado en modo CPU (minimizado)
echo Esperando a que el servidor este listo...

REM Wait for server to be ready (max 30 seconds)
set /a counter=0
:wait_loop
timeout /t 2 /nobreak >nul
curl -s http://localhost:11434/api/tags >nul 2>&1
if not errorlevel 1 goto server_ready
set /a counter+=1
if %counter% lss 15 goto wait_loop
echo Error: Ollama no respondio despues de 30 segundos
exit /b 1

:server_ready
echo Servidor Ollama listo en http://localhost:11434
