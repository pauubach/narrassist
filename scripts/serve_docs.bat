@echo off
REM Serve MkDocs documentation site locally

cd /d "%~dp0.."
C:\Users\pauub\anaconda3\python.exe -m mkdocs serve

pause
