@echo off
echo ============================================
echo Building Whisper4Windows MSI Installer
echo ============================================
echo.

REM Step 1: Build the backend executable
echo Step 1: Building backend executable...
call BUILD_BACKEND.bat

REM Check if backend was built successfully
if not exist "frontend\src-tauri\binaries\whisper-backend-x86_64-pc-windows-msvc.exe" (
    echo ❌ Backend build failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Building Tauri MSI installer...
cd frontend\src-tauri

REM Build the MSI installer
cargo tauri build

REM Check if build was successful
if exist "target\release\bundle\msi\*.msi" (
    echo.
    echo ============================================
    echo ✅ Build successful!
    echo.
    echo MSI installer created at:
    dir /b target\release\bundle\msi\*.msi
    echo.
    echo Full path: %CD%\target\release\bundle\msi\
    echo ============================================
) else (
    echo.
    echo ============================================
    echo ❌ MSI build failed! Check the output above.
    echo ============================================
)

cd ..\..
echo.
pause
