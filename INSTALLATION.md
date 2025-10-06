# 📦 Installation Guide

Complete setup guide for Whisper4Windows - from first-time installation to GPU acceleration.

---

## 🚀 Quick Start

**Minimum Requirements:**

- Windows 10/11
- 8GB RAM
- Microphone

### Installation Options

**Option 1: MSI Installer (Recommended for End Users)**

1. Download `Whisper4Windows_0.1.0_x64_en-US.msi`
2. Run the installer
3. GPU acceleration is automatically included - no additional setup needed!
4. Launch from Start Menu or Desktop shortcut
5. Press **F9** to start recording
6. Speak, then press **F9** again
7. Text appears!

**Option 2: From Source (For Developers)**

1. Clone the repository
2. Double-click `START_APP.bat`
3. Press **F9** to start recording (customizable in settings)
4. Speak, then press **F9** again
5. Text appears!

The app works immediately in **CPU mode** (slower but functional). GPU acceleration can be enabled for 10x speed improvement.

---

## ⚡ GPU Acceleration (Automatic!)

✅ **CUDA libraries are now bundled with the MSI installer!**

If you have an NVIDIA GPU (GTX 1060 or better recommended), the app will automatically use GPU acceleration for 10x faster transcription - no manual CUDA installation required!

The bundled installer includes:

- CUDA 12.x libraries (cublas, cudnn, etc.)
- Automatic GPU detection
- Automatic CPU fallback if GPU is unavailable

**Just install and it works!** 🚀

---

## 📝 For Developers: Python Environment Setup

### Step 1: Install Python Dependencies

The backend Python environment is already set up, but verify:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Expected packages:

- `faster-whisper` - Whisper implementation
- `fastapi` - Backend API
- `sounddevice` - Audio capture
- `numpy` - Audio processing

---

## Step 2: Install CUDA Toolkit (Optional - for development only)

**Note:** Only needed if you're developing from source. The MSI installer includes CUDA libraries.

**What is it?** Core NVIDIA libraries for GPU computing.

### **Download CUDA Toolkit 12.6**

1. Go to: https://developer.nvidia.com/cuda-downloads
2. Select:
   - Operating System: **Windows**
   - Architecture: **x86_64**
   - Version: **11 or 10** (your Windows version)
   - Installer Type: **exe (local)**
3. Download (~3GB)

### **Install**

1. Run the installer
2. Choose **Express** installation
3. Wait 5-10 minutes
4. Restart PowerShell when done

### **Verify**

Open **NEW** PowerShell:

```powershell
where.exe cublas64_12.dll
```

Should show:

```
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin\cublas64_12.dll
```

**Time:** 15-20 minutes
**Size:** ~6GB installed

---

## Step 3: Install cuDNN (Optional - for development only)

**Note:** Only needed if you're developing from source. The MSI installer includes cuDNN libraries.

**What is it?** NVIDIA's deep learning library, required for Whisper GPU acceleration.

### **Download cuDNN 9.x**

1. Go to: https://developer.nvidia.com/cudnn
2. Click **"Download cuDNN"**
3. Sign in (free NVIDIA Developer account)
4. Select:
   - cuDNN version: **9.x for CUDA 12.x**
   - Operating System: **Windows**
   - Architecture: **x86_64**
5. Download ZIP (~800MB)

### **Extract and Install**

**Option A: Copy to CUDA directory (Recommended)**

1. Extract the downloaded ZIP
2. Copy files to CUDA installation:
   ```
   cudnn/bin/*.dll      → C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin\
   cudnn/include/*.h    → C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\include\
   cudnn/lib/*.lib      → C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\lib\x64\
   ```

**Option B: Separate cuDNN folder**

1. Create: `C:\Program Files\NVIDIA\CUDNN\v9.x\`
2. Copy the extracted folder there
3. Add to System PATH:
   - Press `Win + X` → **System**
   - **Advanced system settings** → **Environment Variables**
   - Under **System variables**, find `Path`, click **Edit**
   - Add: `C:\Program Files\NVIDIA\CUDNN\v9.x\bin`

### **Verify**

Open **NEW** PowerShell:

```powershell
where.exe cudnn_ops64_9.dll
```

Should show the DLL path.

**Time:** 10-15 minutes

---

## Step 4: Install NVIDIA cuBLAS and cuDNN Python Packages

These are already installed via pip in the venv:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

The `START_APP.bat` script automatically adds these to the PATH.

---

## Step 5: Test GPU Setup

### **Quick Test**

```powershell
.\TEST_GPU.bat
```

Should show:

```
✅ CTranslate2 installed
✅ CUDA is available: 1 device(s) found
   Device 0: NVIDIA GeForce RTX 4060 Laptop GPU
```

### **Full Test**

```powershell
.\START_APP.bat
```

Backend console should show:

```
🚀 CUDA is available! Found 1 GPU(s)
✅ Model loaded successfully on cuda: small
```

Record something and check transcription speed:

- **GPU:** 0.5-2 seconds for 5s of speech ⚡
- **CPU:** 5-15 seconds for 5s of speech 🐌

---

## 🎯 First-Time Usage

### **1. Start the App**

```powershell
.\START_APP.bat
```

Two windows will open:

- **Backend** (PowerShell) - Python server logs
- **Frontend** (System tray) - App interface

### **2. Configure Settings**

Left-click the system tray icon to open settings:

- **Model Quality:** Small (recommended for balance)
- **Language:** Select from 99 languages or use Auto-Detect
- **Device:** Auto (tries GPU, falls back to CPU)
- **Keyboard Shortcuts:** Customize toggle and cancel shortcuts
- **Theme:** Choose Light, Dark, or System

### **3. Test It**

**Option A: Global Hotkey (Recommended)**

1. Open Notepad or any text application
2. Press **F9** (or your custom shortcut)
3. Speak: "Testing Whisper for Windows"
4. Press **F9** again (or **Escape** to cancel)
5. Text appears in your application!

**Option B: Manual Buttons**

1. Click **START** in app window
2. Speak into microphone
3. Click **STOP**
4. Text displays and auto-injects

---

## 🔧 Troubleshooting

### **Backend won't start**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

### **"Module not found" errors**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install --upgrade -r requirements.txt
```

### **GPU not detected**

1. Run `nvidia-smi` - should show your GPU
2. Run `.\TEST_GPU.bat` - check for errors
3. Verify CUDA Toolkit installed: `where.exe cublas64_12.dll`
4. Verify cuDNN installed: `where.exe cudnn_ops64_9.dll`

### **Slow transcription on GPU**

- First transcription is slow (model loading)
- Subsequent should be 0.5-2 seconds
- Check GPU usage in Task Manager → Performance → GPU

### **Text injection not working**

- Make sure target window has focus
- Try the manual "Test Injection" button first
- Check Windows permissions/antivirus

### **Hotkey not working**

- App must be running (check system tray)
- Try different key combo if F9 conflicts with another app
- Customize shortcuts in Settings → Keyboard Shortcuts
- Supported formats: `F9`, `Ctrl+Shift+R`, `Alt+\`, etc.
- Restart app if shortcuts don't register

---

## 📊 Performance Expectations

### **GPU Mode (NVIDIA RTX 4060)**

- Model loading: ~3 seconds (first time only)
- 30s speech → 0.5-2s transcription
- Real-time factor: 5-10x
- Quality: Excellent (float16 precision)

### **CPU Mode (Ultra 9 185H)**

- Model loading: ~5 seconds (first time only)
- 30s speech → 5-15s transcription
- Real-time factor: 0.5-1x
- Quality: Good (int8 quantization)

---

## 💾 Disk Space Requirements

**For End Users (MSI Installer):**

- **MSI installer download:** ~660MB
- **Installed app:** ~700MB (includes bundled CUDA libraries)
- **Whisper models (download on first use):**
  - Tiny: ~150MB
  - Small: ~500MB
  - Medium: ~1.5GB
  - Large-V3: ~3GB

**Total (with Small model):** ~1.2GB

**For Developers (from source):**

- **Python venv:** ~2GB
- **CUDA Toolkit:** ~6GB (optional)
- **cuDNN:** ~1GB (optional)
- **Whisper models:** Same as above

**Total:** ~10-12GB

---

## 🎯 Recommended Setup for Best Experience

**For MSI Users:**

1. **Install the MSI** - CUDA libraries already included!
2. **Small model** - Best balance of speed/quality
3. **Auto device** - Automatically uses GPU if available
4. **Global hotkey** - Most convenient workflow (default: F9)

**For Developers:**

1. **Install CUDA Toolkit + cuDNN** - For development/testing
2. **Small model** - Best balance of speed/quality
3. **Auto device** - Tries GPU, falls back gracefully
4. **Global hotkey** - Most convenient workflow

---

## 🔄 Updating

To update the app:

```powershell
# Update Python dependencies
cd backend
.\venv\Scripts\Activate.ps1
pip install --upgrade -r requirements.txt

# Rebuild frontend (if code changed)
cd ..\frontend
cargo-tauri build --no-bundle
```

---

## 📚 Additional Resources

- **CUDA Toolkit:** https://developer.nvidia.com/cuda-downloads
- **cuDNN:** https://developer.nvidia.com/cudnn
- **Whisper:** https://github.com/openai/whisper
- **faster-whisper:** https://github.com/guillaumekln/faster-whisper

---
