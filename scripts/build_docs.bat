@echo off
REM Build MkDocs static HTML and copy to Tauri public folder

echo [1/3] Building MkDocs static site...
cd /d "%~dp0.."
C:\Users\pauub\anaconda3\python.exe -m mkdocs build --clean

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: MkDocs build failed!
    exit /b 1
)

echo [2/3] Copying to frontend public/docs...
if exist "frontend\public\docs" (
    rmdir /s /q "frontend\public\docs"
)
xcopy /E /I /Y "site" "frontend\public\docs"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to copy docs to public folder!
    exit /b 1
)

echo [3/3] Cleaning up build artifacts...
rmdir /s /q "site"

echo.
echo ✅ Documentation built and copied successfully!
echo    Location: frontend/public/docs/index.html
echo    Accessible in app at: /docs/index.html
echo.

pause
