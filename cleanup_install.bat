@echo off
echo Limpiando instalacion anterior...

:: Kill processes
taskkill /F /IM "narrative-assistant.exe" 2>nul
taskkill /F /IM "backend.exe" 2>nul
taskkill /F /IM "python.exe" 2>nul

:: Wait a bit
timeout /t 2 /nobreak >nul

:: Remove folders
rmdir /S /Q "%LOCALAPPDATA%\com.tfm.narrative-assistant" 2>nul
rmdir /S /Q "%APPDATA%\com.tfm.narrative-assistant" 2>nul
rmdir /S /Q "%LOCALAPPDATA%\Narrative Assistant" 2>nul
rmdir /S /Q "%APPDATA%\Narrative Assistant" 2>nul
rmdir /S /Q "%LOCALAPPDATA%\Programs\Narrative Assistant" 2>nul
rmdir /S /Q "C:\Program Files\Narrative Assistant" 2>nul

:: Remove registry entries
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\Narrative Assistant" /f 2>nul
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\Narrative Assistant" /f 2>nul

:: Clean temp
del /F /Q "%TEMP%\*narrative*" 2>nul

echo.
echo Limpieza completada. Ejecutando instalador...
timeout /t 2 /nobreak >nul

start "" "D:\repos\tfm\src-tauri\target\release\bundle\nsis\Narrative Assistant_0.4.44_x64-setup.exe"
