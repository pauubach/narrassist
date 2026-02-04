# Diagnostico de Narrative Assistant
Write-Host '===== DIAGNOSTICO DE NARRATIVE ASSISTANT =====' -ForegroundColor Cyan

# 1. Verificar instalacion
Write-Host '1. Verificando instalacion...' -ForegroundColor Yellow
$paths = @(
    "$env:LOCALAPPDATA\Programs\narrative-assistant",
    "${env:ProgramFiles}\Narrative Assistant"
)

foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "   Encontrado: $p" -ForegroundColor Green
        Get-ChildItem $p -File | Select-Object Name, Length
    }
}

# 2. Verificar procesos
Write-Host '2. Verificando procesos...' -ForegroundColor Yellow
Get-Process | Where-Object { $_.ProcessName -like '*narrative*' } | Select-Object ProcessName, Id

# 3. Verificar Python
Write-Host '3. Verificando Python...' -ForegroundColor Yellow
try {
    $pyVer = python --version 2>&1
    Write-Host "   Python: $pyVer" -ForegroundColor Green
} catch {
    Write-Host '   Python no encontrado' -ForegroundColor Red
}

# 4. Logs de eventos
Write-Host '4. Verificando logs de Windows...' -ForegroundColor Yellow
Get-WinEvent -FilterHashtable @{LogName='Application'; Level=2} -MaxEvents 10 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -like '*narrative*' -or $_.Message -like '*tauri*' } |
    Select-Object TimeCreated, Message | Format-List

Write-Host 'Diagnostico completado' -ForegroundColor Cyan
