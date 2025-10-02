@echo off
echo Stopping Whisper4Windows...
taskkill /f /im app.exe 2>nul
taskkill /f /im python.exe 2>nul
echo Done!
timeout /t 2 /nobreak >nul


