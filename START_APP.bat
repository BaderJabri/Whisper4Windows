@echo off
echo ========================================
echo   Whisper4Windows - Quick Start
echo ========================================
echo.

REM Start Backend (with venv activation + CUDA libraries in venv + cuDNN PATH)
echo [1/2] Starting Python Backend...
start "Whisper4Windows Backend" powershell -NoExit -Command "$env:PATH += ';%~dp0backend\venv\Lib\site-packages\nvidia\cublas\bin;%~dp0backend\venv\Lib\site-packages\nvidia\cudnn\bin;C:\Program Files\NVIDIA\CUDNN\v9.13\bin\13.0'; cd '%~dp0backend'; .\venv\Scripts\Activate.ps1; python main.py"
timeout /t 3 /nobreak >nul

REM Start Frontend
echo [2/2] Starting Frontend App...
start "" "%~dp0frontend\src-tauri\target\release\app.exe"

echo.
echo ========================================
echo   App Started!
echo ========================================
echo.
echo Backend: Check "Whisper4Windows Backend" window
echo   Look for: "CUDA is available!" for GPU mode
echo Frontend: System tray icon (bottom-right)
echo   Look for: CPU/GPU selector buttons
echo.
echo Press any key to close this window...
pause >nul