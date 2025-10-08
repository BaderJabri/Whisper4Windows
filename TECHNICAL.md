# 🔧 Technical Documentation

Comprehensive technical guide for Whisper4Windows developers and contributors.

## 🏗️ Architecture Overview

Whisper4Windows uses a **sidecar architecture** with a Rust frontend and Python backend:

```
┌─────────────────┐    HTTP/JSON    ┌─────────────────┐
│   Rust Frontend │ ◄─────────────► │  Python Backend │
│   (Tauri App)   │                 │  (FastAPI)      │
└─────────────────┘                 └─────────────────┘
         │                                   │
         │                                   │
    ┌─────────┐                        ┌─────────┐
    │ System  │                        │ Whisper │
    │ Tray    │                        │ Engine  │
    └─────────┘                        └─────────┘
```

### Frontend (Rust/Tauri)

- **Framework:** Tauri 2.8.5
- **UI:** HTML/CSS/JavaScript (vanilla, no framework)
- **Platform:** Windows (x64)
- **Key Features:**
  - System tray integration
  - Global hotkey handling
  - Text injection via clipboard
  - Settings management
  - Recording window overlay

### Backend (Python/FastAPI)

- **Framework:** FastAPI 0.115.0+
- **AI Engine:** faster-whisper 1.0.0+
- **Audio:** sounddevice 0.4.6+
- **Key Features:**
  - Audio capture and processing
  - Whisper model management
  - GPU/CPU device detection
  - Real-time transcription

## 📁 Project Structure

```
Whisper4Windows/
├── frontend/                    # Tauri frontend
│   ├── src-tauri/              # Rust source
│   │   ├── src/
│   │   │   ├── lib.rs          # Main Rust code
│   │   │   └── main.rs         # Entry point
│   │   ├── tauri.conf.json     # Tauri configuration
│   │   ├── Cargo.toml          # Rust dependencies
│   │   └── binaries/           # Backend executable
│   └── dist/                   # Built frontend
├── backend/                     # Python backend
│   ├── main.py                 # FastAPI server
│   ├── whisper_engine.py       # Whisper AI engine
│   ├── audio_capture.py        # Audio handling
│   ├── gpu_manager.py          # GPU library management
│   ├── requirements.txt        # Python dependencies
│   └── build/                  # PyInstaller build
├── images/                     # UI screenshots
├── logo_backup/               # Original logo files
└── scripts/                   # Build scripts
```

## 🔧 Core Components

### 1. WhisperEngine (`backend/whisper_engine.py`)

**Purpose:** Manages Whisper AI model loading and transcription

**Key Features:**
- Model size selection (tiny, base, small, medium, large-v3)
- Device detection (CUDA/CPU with automatic fallback)
- Compute type optimization (float16, int8_float16, int8)
- CUDA library path management
- Model caching in AppData

**API:**
```python
class WhisperEngine:
    def __init__(self, model_size: str, device: str, compute_type: str)
    def load_model(self) -> bool
    def transcribe_audio(self, audio_data: np.ndarray, language: str) -> Dict
    def is_model_downloaded(self, model_size: str) -> bool
```

### 2. AudioCapture (`backend/audio_capture.py`)

**Purpose:** Handles microphone input and audio processing

**Key Features:**
- WASAPI audio capture via sounddevice
- Device enumeration and selection
- Real-time audio level monitoring
- Queue-based audio buffering
- WAV file export

**API:**
```python
class AudioCapture:
    def __init__(self, sample_rate: int = 16000, channels: int = 1)
    def start_recording(self, device_index: Optional[int] = None)
    def stop_recording(self) -> Optional[np.ndarray]
    def get_devices(self) -> Dict[str, List[AudioDevice]]
    def get_audio_level(self) -> float
```

### 3. GPU Manager (`backend/gpu_manager.py`)

**Purpose:** Downloads and manages CUDA/cuDNN libraries

**Key Features:**
- NVIDIA GPU detection
- Library installation via pip
- CUDA library verification
- Download progress tracking
- Automatic cleanup

**API:**
```python
def is_gpu_available() -> bool
def are_gpu_libs_installed() -> bool
def install_gpu_libs(progress_callback=None) -> bool
def get_gpu_info() -> Dict
```

### 4. Frontend State (`frontend/src-tauri/src/lib.rs`)

**Purpose:** Manages application state and UI interactions

**Key Features:**
- Settings persistence
- Global hotkey registration
- Text injection via clipboard
- Window management
- Backend communication

**State Structure:**
```rust
pub struct AppState {
    pub selected_model: Arc<Mutex<String>>,
    pub selected_device: Arc<Mutex<String>>,
    pub selected_microphone: Arc<Mutex<Option<i32>>>,
    pub use_clipboard: Arc<Mutex<bool>>,
    pub selected_language: Arc<Mutex<String>>,
    pub toggle_shortcut: Arc<Mutex<String>>,
    pub cancel_shortcut: Arc<Mutex<String>>,
    pub backend_child: Arc<Mutex<Option<CommandChild>>>,
}
```

## 🌐 API Endpoints

### Backend API (FastAPI)

**Base URL:** `http://127.0.0.1:8000`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Health check |
| `/health` | GET | System status |
| `/start` | POST | Start recording |
| `/stop` | POST | Stop and transcribe |
| `/cancel` | POST | Cancel recording |
| `/audio_level` | GET | Get audio input level |
| `/devices` | GET | List audio devices |
| `/gpu/info` | GET | GPU status |
| `/gpu/install` | POST | Install GPU libraries |
| `/gpu/uninstall` | POST | Remove GPU libraries |

### Frontend Commands (Tauri)

| Command | Purpose |
|---------|---------|
| `cmd_start_recording` | Start recording session |
| `cmd_stop_recording` | Stop and transcribe |
| `cmd_cancel_recording` | Cancel recording |
| `cmd_toggle_recording` | Toggle recording state |
| `inject_text_directly` | Inject text via clipboard |
| `set_model_and_device` | Update settings |
| `set_microphone_device` | Select microphone |
| `set_clipboard_paste` | Configure clipboard behavior |
| `save_shortcuts` | Update keyboard shortcuts |

## 🎛️ Configuration

### Tauri Configuration (`frontend/src-tauri/tauri.conf.json`)

```json
{
  "productName": "Whisper4Windows",
  "version": "0.1.0",
  "identifier": "com.whisper4windows.dev",
  "app": {
    "trayIcon": {
      "iconPath": "icons/256x256.png",
      "iconAsTemplate": false,
      "menuOnLeftClick": false
    }
  },
  "bundle": {
    "externalBin": ["binaries/whisper-backend"]
  }
}
```

### Backend Dependencies (`backend/requirements.txt`)

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
faster-whisper>=1.0.0
sounddevice>=0.4.6
numpy>=1.26.0
scipy>=1.12.0
pydantic>=2.10.0
```

### Rust Dependencies (`frontend/src-tauri/Cargo.toml`)

```toml
[dependencies]
tauri = { version = "2.8.5", features = ["tray-icon"] }
tauri-plugin-global-shortcut = "2.3.0"
tauri-plugin-shell = "2"
tauri-plugin-single-instance = "2"
reqwest = { version = "0.11", features = ["json"] }
tokio = { version = "1.0", features = ["full"] }
```

## 🔄 Data Flow

### Recording Workflow

1. **User presses F9** → Frontend calls `cmd_toggle_recording`
2. **Frontend** → Shows recording window, calls backend `/start`
3. **Backend** → Initializes WhisperEngine, starts AudioCapture
4. **AudioCapture** → Captures audio in real-time, stores in queue
5. **User presses F9 again** → Frontend calls `cmd_stop_recording`
6. **Backend** → Stops recording, transcribes audio with WhisperEngine
7. **Frontend** → Receives transcription, injects text via clipboard

### GPU Detection Flow

1. **App startup** → `setup_cuda_paths()` adds CUDA library paths
2. **WhisperEngine init** → `_detect_device()` checks for CUDA availability
3. **Model loading** → Tries GPU compute types, falls back to CPU if needed
4. **Runtime** → Automatic fallback if CUDA libraries fail

## 🎯 Performance Characteristics

### Model Performance

| Model | Size | Speed (GPU) | Speed (CPU) | Quality |
|-------|------|-------------|-------------|---------|
| tiny | ~150MB | 0.2-0.5s | 2-5s | Basic |
| base | ~300MB | 0.3-0.8s | 3-8s | Good |
| small | ~500MB | 0.5-1.5s | 5-15s | Very Good |
| medium | ~1.5GB | 1-3s | 10-30s | Excellent |
| large-v3 | ~3GB | 2-5s | 20-60s | Best |

### Memory Usage

- **Frontend:** ~50MB
- **Backend (CPU):** ~200-500MB (depending on model)
- **Backend (GPU):** ~1-2GB VRAM + 200-500MB RAM
- **CUDA Libraries:** ~400MB disk space

## 🛠️ Development Workflow

### Running from Source

```bash
# Start backend
cd backend
.\venv\Scripts\Activate.ps1
python main.py

# Start frontend (separate terminal)
cd frontend/src-tauri
cargo tauri dev
```

### Building for Distribution

```bash
# Build everything
BUILD_INSTALLER.bat

# Or step by step
cd backend
python build_backend.py
cd ../frontend/src-tauri
cargo tauri build
```

### Testing

```bash
# Test GPU setup
cd backend
.\venv\Scripts\Activate.ps1
python -c "from whisper_engine import WhisperEngine; print(WhisperEngine('small', 'auto')._detect_device())"

# Test audio devices
python -c "from audio_capture import AudioCapture; print(AudioCapture().get_devices())"
```

## 🐛 Common Issues

### Backend Issues

**"Module not found" errors:**
```bash
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**CUDA library errors:**
- Check GPU detection: `nvidia-smi`
- Verify CUDA paths in `whisper_engine.py`
- Try CPU fallback: set device to "cpu"

**Audio device issues:**
- Check microphone permissions
- Verify device index in settings
- Test with different sample rates

### Frontend Issues

**Hotkey not working:**
- Check if app is running (system tray)
- Verify shortcut registration in logs
- Try different key combinations

**Text injection failing:**
- Ensure target window has focus
- Check Windows permissions
- Test with manual injection button

**Window not showing:**
- Check system tray for app icon
- Verify window positioning code
- Check for multiple instances

## 📊 Logging and Debugging

### Backend Logs

- **Console:** Real-time output during development
- **File:** `%APPDATA%\com.whisper4windows.dev\logs\app.log`

### Frontend Logs

- **Console:** Browser dev tools (F12)
- **File:** `%APPDATA%\com.whisper4windows.dev\logs\app.log`

### Debug Commands

```bash
# Check GPU status
cd backend
python -c "import gpu_manager; print(gpu_manager.get_gpu_info())"

# Test audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Verify CUDA libraries
where.exe cublas64_12.dll
where.exe cudnn_ops64_9.dll
```

## 🔒 Security Considerations

- **No network calls** during transcription
- **Local processing only** - audio never leaves the device
- **No telemetry** or data collection
- **Open source** - all code is auditable
- **Minimal permissions** - only microphone access required

## 🚀 Future Enhancements

### Planned Features

- **Real-time transcription** - Live text streaming
- **Custom models** - Support for fine-tuned Whisper models
- **Batch processing** - Transcribe multiple audio files
- **Export options** - Save transcriptions to files
- **Voice commands** - Control app with voice
- **Multi-language** - Simultaneous language detection

### Technical Improvements

- **WebRTC VAD** - Better voice activity detection
- **Streaming API** - Real-time audio processing
- **Model quantization** - Smaller model sizes
- **Cross-platform** - Linux and macOS support
- **Mobile apps** - iOS and Android versions

## 📚 References

- **Whisper Paper:** https://arxiv.org/abs/2212.04356
- **faster-whisper:** https://github.com/guillaumekln/faster-whisper
- **Tauri Documentation:** https://tauri.app/
- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **CUDA Toolkit:** https://developer.nvidia.com/cuda-toolkit