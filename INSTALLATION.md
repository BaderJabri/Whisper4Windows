# 📦 Installation Guide

Complete setup guide for Whisper4Windows - from first-time installation to GPU acceleration.

---

## 🚀 Quick Start (No GPU Required)

**Minimum Requirements:**
- Windows 10/11
- 8GB RAM
- Microphone

**Steps:**
1. Download/clone the repository
2. Double-click `START_APP.bat`
3. Press **Alt+T** to start recording
4. Speak, then press **Alt+T** again
5. Text appears!

The app works immediately in **CPU mode** (slower but functional).

---

## ⚡ GPU Acceleration Setup (Optional but Recommended)

For 10x faster transcription, follow these steps to enable GPU acceleration.

### **Prerequisites**
- NVIDIA GPU (GTX 1060 or better recommended)
- 4GB+ VRAM

---

## Step 1: Install Python Dependencies

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

## Step 2: Install CUDA Toolkit (for GPU)

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

## Step 3: Install cuDNN (for GPU)

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
- **Model:** Small (recommended for balance)
- **Device:** Auto (tries GPU, falls back to CPU)

### **3. Test It**

**Option A: Global Hotkey (Recommended)**
1. Open Notepad
2. Press **Alt+T**
3. Speak: "Testing Whisper for Windows"
4. Press **Alt+T** again
5. Text appears in Notepad!

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
- Try different key combo if Alt+T conflicts
- Restart app

---

## 📊 Performance Expectations

### **GPU Mode (NVIDIA RTX 4060)**
- Model loading: ~3 seconds (first time only)
- 5s speech → 0.5-2s transcription
- Real-time factor: 5-10x
- Quality: Excellent (float16 precision)

### **CPU Mode**
- Model loading: ~5 seconds (first time only)
- 5s speech → 5-15s transcription
- Real-time factor: 0.5-1x
- Quality: Good (int8 quantization)

---

## 💾 Disk Space Requirements

- **Base app:** ~500MB
- **Python venv:** ~2GB
- **Whisper models:**
  - Tiny: ~150MB
  - Small: ~500MB
  - Medium: ~1.5GB
  - Large-V3: ~3GB
- **CUDA Toolkit:** ~6GB (optional)
- **cuDNN:** ~1GB (optional)

**Total:**
- Minimum (CPU only): ~3GB
- Recommended (GPU): ~12GB

---

## 🎯 Recommended Setup for Best Experience

1. **GPU acceleration** (CUDA + cuDNN) - Worth the 30 minutes!
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

**Ready to go! Press Alt+T and start dictating!** 🎤

