@echo off
echo ============================================
echo Building Whisper4Windows Backend Executable
echo ============================================
echo.

REM Activate virtual environment
cd backend
call venv\Scripts\activate

REM Install PyInstaller if not already installed
echo Installing PyInstaller...
pip install pyinstaller

REM Build the backend executable
echo.
echo Building backend executable...
python build_backend.py

REM Check if build was successful
if exist "dist\whisper-backend.exe" (
    echo.
    echo ============================================
    echo Build successful!
    echo Backend executable: backend\dist\whisper-backend.exe
    echo ============================================

    REM Copy to Tauri binaries folder
    if not exist "..\frontend\src-tauri\binaries" mkdir "..\frontend\src-tauri\binaries"
    copy /Y "dist\whisper-backend.exe" "..\frontend\src-tauri\binaries\whisper-backend-x86_64-pc-windows-msvc.exe"
    echo Copied to Tauri binaries folder
) else (
    echo.
    echo ============================================
    echo Build failed! Check the output above for errors.
    echo ============================================
)

echo.
pause
