# Building Whisper4Windows MSI Installer

This guide explains how to build a standalone MSI installer for Whisper4Windows that includes both the frontend and backend.

## Prerequisites

### Required Software

1. **Rust** - Install from https://rustup.rs/
2. **Python 3.10+** - Install from https://python.org
3. **Visual Studio Build Tools** - Required for Rust on Windows
   - Install from https://visualstudio.microsoft.com/downloads/
   - Select "Desktop development with C++"

### Optional (for GPU support during development)

4. **CUDA Toolkit 12.6+** - https://developer.nvidia.com/cuda-downloads (only needed for development)
5. **cuDNN 9.x** - https://developer.nvidia.com/cudnn (only needed for development)

**Note:** CUDA libraries are now bundled with the installer, so end users don't need to install CUDA separately!

## Build Process

### Method 1: Automated Build (Recommended)

Simply run the build script:

```bash
BUILD_INSTALLER.bat
```

This will:

1. Build the Python backend as a standalone .exe using PyInstaller (includes bundled CUDA DLLs)
2. Copy it to the Tauri binaries folder
3. Build the Tauri frontend with the bundled backend
4. Create an MSI installer (~660MB with CUDA libraries)

**Output:** `frontend\src-tauri\target\release\bundle\msi\Whisper4Windows_0.1.0_x64_en-US.msi`

### Method 2: Manual Build

#### Step 1: Build the Backend

```bash
cd backend
call venv\Scripts\activate
pip install pyinstaller
python build_backend.py
```

This creates: `backend\dist\whisper-backend.exe`

#### Step 2: Copy Backend to Tauri

```bash
mkdir frontend\src-tauri\binaries
copy backend\dist\whisper-backend.exe frontend\src-tauri\binaries\whisper-backend-x86_64-pc-windows-msvc.exe
```

**Important:** The filename must include the target triple `x86_64-pc-windows-msvc` for Tauri to recognize it.

#### Step 3: Build the MSI

```bash
cd frontend\src-tauri
cargo tauri build
```

## How It Works

### Sidecar Architecture

The app uses Tauri's "sidecar" feature to bundle the Python backend:

1. **PyInstaller** packages the Python backend (`main.py`) and all dependencies into a single executable
2. **Tauri** bundles this executable with the frontend app
3. On app startup, the Rust code automatically launches the backend sidecar
4. When the app closes, the backend is automatically terminated

### Configuration

**tauri.conf.json:**

```json
{
  "bundle": {
    "externalBin": [
      "binaries/whisper-backend"
    ]
  }
}
```

**lib.rs:**

```rust
// Start backend sidecar
let sidecar_command = app.shell().sidecar("whisper-backend")
    .expect("Failed to create sidecar command");

let (_rx, child) = sidecar_command
    .spawn()
    .expect("Failed to spawn backend sidecar");
```

## Distribution

### For End Users

**Single-file distribution:**
The MSI installer includes:

- ✅ Frontend app.exe
- ✅ Backend whisper-backend.exe (bundled)
- ✅ All dependencies
- ✅ Auto-startup of backend
- ✅ System tray integration

**What users DON'T need to install:**

- ❌ Python
- ❌ Rust
- ❌ Node.js
- ❌ Any dependencies

**Installation:**

1. Download the MSI file
2. Run the installer
3. Launch from Start Menu or Desktop shortcut
4. Everything works automatically!

### GPU Support

✅ **CUDA libraries are now bundled with the installer!**

The MSI includes all necessary CUDA DLLs (cublas, cudnn, etc.) from the NVIDIA pip packages. Users with NVIDIA GPUs can use GPU acceleration immediately after installation - no separate CUDA installation required!

The app will automatically:
- Detect NVIDIA GPU
- Use bundled CUDA libraries for GPU acceleration
- Fall back to CPU if no GPU is detected or if GPU loading fails

## Troubleshooting

### Build Fails: "PyInstaller not found"

```bash
cd backend
call venv\Scripts\activate
pip install pyinstaller
```

### Build Fails: "Sidecar not found"

Make sure the backend executable is copied with the correct name:

```
frontend\src-tauri\binaries\whisper-backend-x86_64-pc-windows-msvc.exe
```

### Backend doesn't start in built app

Check the app logs:

- Windows: `%APPDATA%\com.whisper4windows.dev\logs\`
- Look for "Backend server started" message

### Large File Size

The MSI is approximately ~660MB because it includes:

- Python runtime (~50MB)
- FastAPI/Uvicorn backend (~100MB)
- faster-whisper and dependencies (~100MB)
- CUDA libraries (cublas, cudnn, etc.) (~400MB)
- Tauri frontend (~10MB)

**Note:** Whisper models are NOT included in the installer - they download automatically on first use to `%APPDATA%\Whisper4Windows\models\`

To reduce size:
- Remove CUDA bundling (edit `build_backend.py` to exclude NVIDIA DLLs) - saves ~400MB but requires users to install CUDA
- Use `--exclude-module` in `build_backend.py` for unused packages

## Development vs Production

**Development:**

- Run `START_APP.bat` - uses Python virtual environment
- Hot reload with `cargo tauri dev`
- Faster iteration

**Production:**

- Build MSI installer
- Single-file distribution
- No Python required for users

## GitHub Releases

### Creating a Release

1. Build the MSI: `BUILD_INSTALLER.bat`
2. Create a GitHub release
3. Upload the MSI file: `Whisper4Windows_0.1.0_x64_en-US.msi`
4. Users download and install directly

### Release Checklist

- [ ] Update version in `frontend\src-tauri\tauri.conf.json`
- [ ] Build MSI installer: `BUILD_INSTALLER.bat`
- [ ] Test on clean Windows machine (with and without NVIDIA GPU)
- [ ] Verify GPU acceleration works without CUDA installation
- [ ] Create GitHub release with:
  - [ ] MSI installer (~660MB)
  - [ ] Installation instructions
  - [ ] Note about bundled CUDA support
  - [ ] Changelog

## Files Overview

### Build Scripts

- `BUILD_BACKEND.bat` - Builds backend executable only
- `BUILD_INSTALLER.bat` - Builds complete MSI installer
- `backend/build_backend.py` - PyInstaller configuration

### Configuration

- `frontend/src-tauri/tauri.conf.json` - Tauri bundle config
- `frontend/src-tauri/src/lib.rs` - Sidecar startup code

### Output

- `backend/dist/whisper-backend.exe` - Standalone backend
- `frontend/src-tauri/binaries/whisper-backend-*.exe` - Renamed for Tauri
- `frontend/src-tauri/target/release/bundle/msi/*.msi` - Final installer
