# 🎙️ Whisper4Windows

**100% Local & Private Speech-to-Text for Windows**

A free, local, GPU-accelerated speech-to-text app inspired by Superwhisper. Record anywhere with a global hotkey, and text appears instantly - **no internet required, your data never leaves your device**.

![Whisper4Windows Recording Overlay](image/README/1759288431699.png)

---

## ✨ Features

- **🔒 100% Local & Private** - No internet required, your data never leaves your device
- **🔥 Global Hotkey (F9)** - Record from anywhere, no need to switch windows
- **🎨 Minimal Recording UI** - Sleek dark interface positioned at top center (616×140)
- **⚡ GPU Acceleration** - 10x faster transcription with NVIDIA GPU
- **🎯 Auto Text Injection** - Text pastes directly into any app via clipboard
- **📊 Live Visualizer** - Real-time audio feedback with 80 animated bars
- **🌊 Processing Animation** - Smooth wave animation during transcription
- **⚙️ Flexible** - Choose CPU/GPU, multiple model sizes in-window
- **⌨️ Esc to Cancel** - Global Esc hotkey cancels recording anytime

---

## 🚀 Quick Start

### **1. Start the App**

```bash
# Double-click or run:
START_APP.bat
```

**First time only:** The app will automatically download the Whisper "small" model (~500MB). This takes 1-3 minutes depending on your internet speed. Subsequent launches are instant!

### **2. Use the Global Hotkey (Recommended)**

1. Open any text editor (Notepad, Word, etc.)
2. Press **F9** - A minimal recording window appears at top center
3. Speak your text (watch the live visualizer respond!)
4. Press **F9** again - Window shows processing animation, then text appears
5. Press **Esc** anytime to cancel recording

![Live Audio Visualization](image/README/1759288431699.png)
*Real-time audio visualization with 80 animated bars - all processing happens locally on your device*

### **3. Configure Settings**

- Left-click system tray icon to open settings
- Select model quality and processing device
- Settings apply to all recordings

---

## 📋 Requirements

- **Windows 10/11**
- **8GB+ RAM**
- **Microphone**

**Optional (for 10x faster GPU acceleration):**

- NVIDIA GPU (GTX 1060+ recommended)
- CUDA Toolkit 12.6+ & cuDNN 9.x

📖 **[See detailed installation guide →](INSTALLATION.md)**

---

## ⚙️ Configuration

### **Model Selection**

- **Tiny** - Fastest, lower accuracy
- **Base** - Fast, decent accuracy
- **Small** - ⭐ Recommended - Balanced speed/quality
- **Medium** - Slower, high accuracy
- **Large V3** - Best quality, slowest

### **Device Selection**

- **Auto** - Tries GPU first, falls back to CPU
- **GPU** - Force NVIDIA GPU (requires cuDNN)
- **CPU** - Always works, slower

---

## 📁 Project Structure

```
Whisper4Windows/
├── backend/                    # Python FastAPI backend
│   ├── main.py                # API endpoints
│   ├── whisper_engine.py      # Whisper model handling
│   ├── audio_capture.py       # Audio recording
│   ├── requirements.txt       # Python dependencies
│   └── venv/                  # Python virtual environment
├── frontend/                   # Tauri frontend
│   ├── dist/index.html        # Web UI
│   └── src-tauri/
│       ├── src/lib.rs         # Rust logic (hotkey, injection)
│       └── target/release/
│           └── app.exe        # Built app
├── START_APP.bat              # Main launcher
├── STOP_APP.bat               # Stop all processes
├── TEST_GPU.bat               # Test GPU setup
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

---

## 🎮 Usage

### **Global Hotkey Workflow (Recommended)**

```
Type in Word → Press F9 → Recording window appears → Speak → Press F9 → Processing animation → Text appears!
```

The minimal recording window (616×140, top center) shows:

- ✅ Live audio visualizer (80 animated bars from backend audio stream)
- ✅ Recording status with animated blue dot
- ✅ Model selector dropdown (Tiny/Base/Small/Medium/Large)
- ✅ Stop button (F9) and Cancel button (Esc)
- ✅ Wave loading animation during transcription

### **Settings Window**

```
Left-click tray icon → Choose model → Select device → Close
```

Settings are saved and apply to future recordings

---

## 🔧 Troubleshooting

### **Backend won't start**

```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### **GPU not detected**

- Run `TEST_GPU.bat` to diagnose
- See **[INSTALLATION.md](INSTALLATION.md)** for GPU setup

### **Hotkey not working**

- Make sure app is running (check system tray)
- Try restarting the app
- Check backend console for errors

### **Text injection not working**

- Focus the text window first
- Wait for transcription to complete

📖 **[Full troubleshooting guide →](INSTALLATION.md#-troubleshooting)**

---

## 📖 Documentation

- **[INSTALLATION.md](INSTALLATION.md)** - Complete setup guide (GPU, dependencies, troubleshooting)
- **[instructions.md](instructions.md)** - Original design document & architecture reference
- **[README.md](README.md)** - This file (quick start & usage)

---

## 🛠️ Development

### **Rebuild Frontend**

```bash
cd frontend
cargo-tauri build --no-bundle
```

### **Run Backend Manually**

```bash
cd backend
venv\Scripts\activate
python main.py
```

---

## 📊 Performance

### **GPU Mode (NVIDIA RTX 4060)**

- 5 seconds of speech → **0.5-2 seconds** transcription
- Model loading: ~3 seconds (first time)

### **CPU Mode**

- 5 seconds of speech → **5-15 seconds** transcription
- Model loading: ~5 seconds (first time)

---

## 🎯 Roadmap

- [X] GPU acceleration
- [X] Global hotkey (F9) with press-only detection
- [X] Auto text injection via clipboard paste
- [X] System tray integration
- [X] In-window model selector
- [X] Minimal recording UI (616×140, top center)
- [X] Live visualizer from backend audio stream
- [X] Cancel recording with global Esc hotkey
- [X] Wave loading animation during processing
- [X] State management with auto-reset
- [X] Backend audio level endpoint
- [ ] Custom hotkey configuration
- [ ] Multiple language support
- [ ] Post-processing presets
- [ ] Recording history

---

## 📝 License

MIT License - Free to use and modify

---

## 🙏 Credits

- **Whisper** - OpenAI
- **faster-whisper** - Systran
- **CTranslate2** - OpenNMT
- **Tauri** - Tauri Apps
- **FastAPI** - Sebastián Ramírez

---

## 🎉 Getting Started

**The fastest way:**

1. Double-click `START_APP.bat`
2. Open Notepad
3. Press **F9** - Recording window appears at top
4. Say "Testing Whisper for Windows"
5. Press **F9** - Watch the wave animation process
6. Text appears in Notepad! ✨

**That's it!** Enjoy your local, private, GPU-accelerated dictation! 🎤

**Tips:**
- Press **Esc** during recording to cancel
- Change model in the recording window dropdown
- Check tray icon for main settings
