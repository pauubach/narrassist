cd d:\repos\tfm\src-tauri\target\release
Write-Host "Iniciando backend..." -ForegroundColor Yellow
Start-Process .\narrative-assistant-server.exe -WindowStyle Hidden
Start-Sleep -Seconds 5

try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8008/api/health" -UseBasicParsing
    Write-Host "Backend respondiendo: $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Backend no responde" -ForegroundColor Red
}

Write-Host "Iniciando aplicacion..." -ForegroundColor Yellow
Start-Process .\narrative-assistant.exe

Write-Host "`n¿Se abrio la ventana de la aplicacion? (Presiona Enter)"
Read-Host
