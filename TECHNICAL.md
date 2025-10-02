# Whisper4Windows - Technical Documentation

**Version:** 1.0
**Last Updated:** 2025-01-02
**Purpose:** Complete technical reference for AI assistants and developers

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Technologies](#technologies)
4. [Component Details](#component-details)
5. [Data Flow](#data-flow)
6. [Key Implementation Details](#key-implementation-details)
7. [File Structure](#file-structure)
8. [Build & Deployment](#build--deployment)
9. [Known Issues & Solutions](#known-issues--solutions)
10. [Design Decisions](#design-decisions)

---

## System Overview

### Purpose
Whisper4Windows is a local, GPU-accelerated speech-to-text application for Windows that allows users to dictate text anywhere using a global hotkey (F9). The transcribed text is automatically injected into the active text field.

### Inspiration
Inspired by SuperWhisper (Mac app), this is a Windows implementation with similar UX but different technical architecture.

### Core Features
- **Global Hotkeys**: F9 (start/stop), Esc (cancel) - OS-level, work anywhere
- **Minimal Overlay**: 616×140px window at top center of screen
- **Live Audio Visualization**: 80 animated bars showing real-time audio levels from backend
- **GPU Acceleration**: NVIDIA CUDA support via faster-whisper
- **Clipboard-based Injection**: Text inserted via Ctrl+V simulation (not character-by-character)
- **State Management**: Auto-resets when window becomes visible

---

## Architecture

### Two-Process Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User's Desktop                        │
│  ┌────────────────┐                  ┌──────────────────┐  │
│  │  Any Text App  │◄─────────────────┤  Clipboard +     │  │
│  │  (Notepad, etc)│  Ctrl+V Inject   │  SendInput API   │  │
│  └────────────────┘                  └──────────────────┘  │
│         ▲                                      ▲            │
│         │                                      │            │
│         │                              ┌───────┴───────┐   │
│         │                              │   Frontend    │   │
│         │                              │   (Tauri)     │   │
│         │                              │               │   │
│         │                              │  - Rust core  │   │
│         │                              │  - WebView UI │   │
│         │                              │  - Global F9  │   │
│         │                              │  - Global Esc │   │
│         │                              └───────┬───────┘   │
│         │                                      │            │
│         │                              HTTP Polling         │
│         │                              /audio_level         │
│         │                                      │            │
│         │                              ┌───────▼───────┐   │
│         │                              │   Backend     │   │
│         │                              │   (FastAPI)   │   │
│         │                              │               │   │
│         │                              │  - Whisper    │   │
│         └──────────────────────────────┤  - Audio Cap  │   │
│               Transcription Result     │  - Port 8000  │   │
│                                        └───────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Communication Flow

1. **User Presses F9 (First Time)**
   - Frontend (Rust) → Backend: POST /start
   - Backend starts audio recording
   - Frontend shows overlay window at top center
   - Frontend polls GET /audio_level every 100ms
   - Visualizer bars animate based on RMS levels

2. **User Presses F9 (Second Time)**
   - Frontend (Rust) → Backend: POST /stop
   - Backend stops recording, runs Whisper transcription
   - Frontend hides window FIRST (to restore focus)
   - Frontend waits 100ms
   - Frontend injects text via clipboard + Ctrl+V
   - Window stays hidden until next F9

3. **User Presses Esc**
   - Frontend (Rust) → Backend: POST /cancel
   - Backend discards recording
   - Frontend hides window immediately

---

## Technologies

### Frontend (Tauri + Rust)

**Framework:** Tauri 2.8.5
- Cross-platform desktop app framework
- Uses system WebView2 (Chromium-based)
- Rust backend, HTML/CSS/JS frontend

**Key Rust Crates:**
```toml
tauri = "2.8.5"                    # Main framework
tauri-plugin-log = "2.7.0"         # Logging to stdout/file
tauri-plugin-global-shortcut = "2.3.0"  # OS-level hotkeys
tokio = "1.0"                      # Async runtime
reqwest = "0.11"                   # HTTP client for backend
windows = "0.52"                   # Windows API bindings
anyhow = "1.0"                     # Error handling
serde_json = "1.0"                 # JSON serialization
```

**Windows APIs Used:**
- `OpenClipboard`, `CloseClipboard`, `EmptyClipboard`, `SetClipboardData` - Clipboard operations
- `GlobalAlloc`, `GlobalLock`, `GlobalUnlock` - Memory allocation for clipboard
- `SendInput` - Keyboard input simulation (Ctrl+V)
- `VK_CONTROL`, `VK_V` - Virtual key codes

### Backend (Python + FastAPI)

**Framework:** FastAPI 0.100+
- Modern async Python web framework
- Auto-generates OpenAPI docs at /docs
- Runs on http://127.0.0.1:8000

**Key Python Packages:**
```
fastapi         # Web framework
uvicorn         # ASGI server
faster-whisper  # Optimized Whisper implementation
sounddevice     # Audio capture (WASAPI on Windows)
numpy           # Audio data processing
torch           # PyTorch (for GPU)
ctranslate2     # Efficient inference engine
```

**CUDA/cuDNN (Optional):**
- CUDA Toolkit 12.6+
- cuDNN 9.x
- Provides 10x speedup on NVIDIA GPUs

### Frontend UI (HTML/CSS/JavaScript)

**No Framework** - Vanilla JavaScript
- Lightweight, fast startup
- Direct DOM manipulation
- Uses Tauri's `__TAURI_INTERNALS__` API

**Key Features:**
- 80 SVG-like bars for audio visualization
- CSS animations for pulsing dot
- JavaScript `setInterval` for polling
- `Math.sin()` for wave animations

---

## Component Details

### Frontend: `src-tauri/src/lib.rs`

**Purpose:** Main Rust application logic

**Key Structures:**

```rust
pub struct AppState {
    pub selected_model: Arc<Mutex<String>>,    // "tiny", "base", "small", "medium", "large-v3"
    pub selected_device: Arc<Mutex<String>>,   // "auto", "cpu", "cuda"
}
```

**Key Functions:**

1. **`inject_text(text: &str) -> Result<()>`**
   - Converts text to UTF-16
   - Opens Windows clipboard
   - Copies text to clipboard
   - Simulates Ctrl+V keypress
   - Uses `SendInput` with KEYEVENTF_EXTENDEDKEY flags
   - **Critical:** Must be called AFTER window is hidden to preserve text field focus

2. **`cmd_start_recording(app, state) -> Result<()>`**
   - Calculates window position: `(screen_width - 616) / 2, 50`
   - Shows window at top center
   - Sends POST /start to backend with model/device
   - **Does NOT** set focus (prevents deselecting text field)

3. **`cmd_stop_recording(app) -> Result<()>`**
   - Sends POST /stop to backend
   - Waits for transcription response
   - **Hides window FIRST** (critical for injection)
   - Waits 100ms for focus to return
   - Injects text via `inject_text()`

4. **`cmd_toggle_recording(app, state) -> Result<()>`**
   - Checks `window.is_visible()`
   - If visible → calls `cmd_stop_recording()`
   - If hidden → calls `cmd_start_recording()`

5. **`cmd_cancel_recording(app) -> Result<()>`**
   - Sends POST /cancel to backend
   - Hides window immediately
   - No text injection

**Global Shortcuts Setup:**

```rust
// F9 shortcut
let f9_shortcut = Shortcut::new(None, Code::F9);

// Esc shortcut
let esc_shortcut = Shortcut::new(None, Code::Escape);

// Handler checks ShortcutState::Pressed only (not Released)
// Prevents double-triggering
```

**Window Configuration:**

```rust
WebviewWindowBuilder::new(app, "recording", ...)
    .inner_size(616.0, 140.0)      // 22:5 aspect ratio
    .position(0.0, 50.0)            // Will be re-centered when shown
    .always_on_top(true)            // Stay above all windows
    .skip_taskbar(true)             // Don't show in taskbar
    .decorations(false)             // No title bar
    .transparent(true)              // Transparent background
    .focused(false)                 // Don't steal focus
```

### Frontend: `dist/recording.html`

**Purpose:** Overlay UI with visualizer and controls

**Structure:**

```html
<div class="container">  <!-- 616px width -->
  <div class="top-section">
    <div class="dot"></div>  <!-- Pulsing blue dot -->
    <select id="modelSelect">...</select>
    <div id="statusText">Recording...</div>
  </div>

  <div id="visualizer">  <!-- 80 bars created dynamically -->
  </div>

  <div class="buttons">
    <button onclick="stopRecording()">Stop   F9</button>
    <button onclick="cancelRecording()">Cancel   Esc</button>
  </div>
</div>
```

**Key CSS:**

```css
.visualizer-bar {
    width: 3px;
    background: #3b82f6;
    transition: height 0.08s ease;
    min-height: 3px;
}

/* Pulsing dot animation */
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.9); }
}
```

**Key JavaScript Variables:**

```javascript
let bars = [];                    // Array of 80 bar elements
let audioLevelInterval = null;    // setInterval ID for polling
let isProcessing = false;         // Flag to prevent polling during transcription
let waveAnimationInterval = null; // setInterval ID for wave animation
let wasVisible = false;           // Track visibility changes
```

**Key JavaScript Functions:**

1. **`initVisualizer()`**
   - Creates 80 `<div class="visualizer-bar">`
   - Appends to `#visualizer`
   - Stores in `bars[]` array

2. **`pollAudioLevels()`**
   - Fetches `http://127.0.0.1:8000/audio_level`
   - Gets `{level: 0.0-1.0, recording: bool}`
   - Calls `updateVisualizerFromLevel(level)`
   - Runs every 100ms when recording

3. **`updateVisualizerFromLevel(level)`**
   - Creates wave pattern: `Math.sin(offset + Date.now() / 200)`
   - Height calculation: `Math.max(3, level * 50 * wave)`
   - Updates each bar's height

4. **`showProcessing()`**
   - Sets `isProcessing = true`
   - Stops audio polling
   - Changes status text to "Processing..."
   - Starts wave animation: `Math.sin(waveOffset + delay) * 12 + 12`
   - Wave travels across bars by incrementing `waveOffset += 0.15`

5. **`resetToRecording()`**
   - Resets `isProcessing = false`
   - Clears wave animation
   - Resets status to "Recording..."
   - Resets all bars to 3px height
   - Starts audio polling
   - **Called automatically when window becomes visible**

6. **`stopRecording()` (button click)**
   - Calls `showProcessing()`
   - Sends POST /stop
   - Gets transcription
   - Injects via `invoke('inject_text_directly')`
   - Hides window
   - Resets state

**Visibility Polling:**

```javascript
setInterval(async () => {
    const isVisible = await currentWindow.isVisible();

    if (isVisible && !wasVisible) {
        resetToRecording();  // Auto-reset on show
    } else if (!isVisible && wasVisible) {
        stopMonitoring();
    }

    wasVisible = isVisible;
}, 500);
```

### Backend: `main.py`

**Purpose:** FastAPI server with Whisper integration

**Global State:**

```python
audio_capture: Optional[AudioCapture] = None
whisper_engine: Optional[WhisperEngine] = None
is_recording = False
```

**Key Endpoints:**

1. **`POST /start`**
   ```python
   Request: {
       "model_size": "small",
       "language": "en",
       "device": "auto"
   }
   Response: {
       "status": "started",
       "model": "small",
       "device": "cuda"  # or "cpu"
   }
   ```
   - Initializes `WhisperEngine` (doesn't load model yet)
   - Creates `AudioCapture` instance
   - Starts audio stream
   - Sets `is_recording = True`

2. **`POST /stop`**
   ```python
   Response: {
       "status": "success",
       "text": "transcribed text here",
       "duration": 5.2,
       "transcription_time": 0.8
   }
   ```
   - Stops audio stream
   - Collects all audio chunks
   - Loads Whisper model (if not loaded)
   - Runs transcription
   - Returns text + metadata

3. **`POST /cancel`**
   ```python
   Response: {
       "status": "success",
       "message": "Recording canceled"
   }
   ```
   - Stops audio stream
   - Discards audio data
   - No transcription

4. **`GET /audio_level`** (NEW)
   ```python
   Response: {
       "level": 0.0-1.0,  # RMS level, normalized
       "recording": bool,
       "queue_size": int
   }
   ```
   - Peeks at audio queue (doesn't remove)
   - Samples last 5 chunks
   - Calculates RMS: `sqrt(mean(audio^2))`
   - Normalizes: `min(1.0, rms * 3.0)`
   - Returns level for visualizer

### Backend: `audio_capture.py`

**Purpose:** Microphone audio recording using sounddevice

**Key Class:**

```python
class AudioCapture:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = 16000  # Whisper requires 16kHz
        self.channels = 1
        self.audio_queue = queue.Queue()
        self.stream = None
```

**Key Methods:**

1. **`start_recording()`**
   - Creates `sounddevice.InputStream`
   - Uses WASAPI backend on Windows
   - Callback puts audio chunks in queue
   - Returns immediately (non-blocking)

2. **`stop_recording() -> np.ndarray`**
   - Stops stream
   - Concatenates all chunks from queue
   - Returns float32 numpy array
   - Shape: `(samples, 1)` or `(samples,)`

3. **`_audio_callback(indata, frames, time_info, status)`**
   - Called by sounddevice for each audio chunk
   - Copies audio data to queue
   - Logs warnings if status != OK

### Backend: `whisper_engine.py`

**Purpose:** Whisper model loading and transcription

**Key Class:**

```python
class WhisperEngine:
    def __init__(self, model_size="small", device="auto"):
        self.model_size = model_size
        self.device = self._detect_device(device)
        self.model = None
        self.is_loaded = False
```

**Device Detection:**

```python
def _detect_device(self, requested):
    if requested == "cuda" or requested == "auto":
        if torch.cuda.is_available():
            return "cuda"
    return "cpu"
```

**Model Loading:**

```python
def load_model():
    from faster_whisper import WhisperModel

    self.model = WhisperModel(
        self.model_size,
        device=self.device,
        compute_type="float16" if self.device == "cuda" else "int8"
    )
```

**Transcription:**

```python
def transcribe_audio(audio_data: np.ndarray, language="en"):
    segments, info = self.model.transcribe(
        audio_data,
        language=language,
        beam_size=5,
        vad_filter=True  # Voice Activity Detection
    )

    text = " ".join([segment.text for segment in segments])
    return {"success": True, "text": text}
```

---

## Data Flow

### Complete Recording Cycle

**Phase 1: Start Recording (F9 pressed, window hidden)**

```
1. User presses F9
2. Rust detects F9 via global shortcut handler
3. Rust checks window.is_visible() → false
4. Rust calls cmd_start_recording()
5. Rust calculates position: x = (screen_width - 616) / 2, y = 50
6. Rust sets window position
7. Rust shows window (does NOT set focus)
8. Rust sends POST http://127.0.0.1:8000/start
   Body: {"model_size": "small", "language": "en", "device": "auto"}
9. Backend creates AudioCapture, starts stream
10. Frontend JS detects window became visible
11. Frontend JS calls resetToRecording()
12. Frontend JS starts polling /audio_level every 100ms
```

**Phase 2: Recording (window visible)**

```
1. Audio flows: Microphone → WASAPI → sounddevice → Queue
2. Every 100ms:
   - Frontend fetches GET /audio_level
   - Backend peeks last 5 chunks, calculates RMS
   - Backend returns {level: 0.0-1.0}
   - Frontend updates 80 bars with sin wave pattern
3. User speaks, visualizer responds in real-time
```

**Phase 3: Stop Recording (F9 pressed again)**

```
1. User presses F9
2. Rust detects F9 via global shortcut handler
3. Rust checks window.is_visible() → true
4. Rust calls cmd_stop_recording()
5. Rust sends POST /stop
6. Backend stops audio stream
7. Backend concatenates all audio chunks
8. Backend loads Whisper model (if not loaded) - takes 3-5 seconds first time
9. Backend runs transcription (0.5-15 seconds depending on GPU/CPU)
10. Backend returns {"status": "success", "text": "..."}
11. Rust hides window FIRST
12. Rust waits 100ms (focus returns to text field)
13. Rust calls inject_text()
14. Rust opens clipboard, copies text
15. Rust simulates Ctrl+V
16. Text appears in active text field!
17. Frontend JS detects window became hidden
18. Frontend JS stops audio polling
```

**Phase 4: Cancel (Esc pressed)**

```
1. User presses Esc
2. Rust detects Esc via global shortcut handler
3. Rust calls cmd_cancel_recording()
4. Rust sends POST /cancel
5. Backend discards audio
6. Rust hides window
7. No text injection
```

---

## Key Implementation Details

### 1. Text Injection via Clipboard (Not Character-by-Character)

**Problem:** Original implementation used `SendInput` with `KEYEVENTF_UNICODE` to send each character individually. This was slow and unreliable.

**Solution:** Copy text to clipboard, then simulate Ctrl+V.

**Code Flow:**
```rust
// Convert to UTF-16 (Windows clipboard format)
let mut text_utf16: Vec<u16> = text.encode_utf16().collect();
text_utf16.push(0);  // Null terminator

// Open clipboard
OpenClipboard(HWND::default())?;
EmptyClipboard()?;

// Allocate global memory
let hmem = GlobalAlloc(GMEM_MOVEABLE, len)?;
let locked = GlobalLock(hmem);

// Copy text to clipboard
std::ptr::copy_nonoverlapping(text_utf16.as_ptr(), locked as *mut u16, text_utf16.len());
GlobalUnlock(hmem);

// Set clipboard data (CF_UNICODETEXT = 13)
SetClipboardData(CF_UNICODETEXT, HANDLE(hmem.0 as _))?;
CloseClipboard()?;

// Wait for clipboard to update
tokio::time::sleep(Duration::from_millis(10)).await;

// Simulate Ctrl+V
let inputs = [
    INPUT { ki: KEYBDINPUT { wVk: VK_CONTROL, dwFlags: KEYEVENTF_EXTENDEDKEY } },
    INPUT { ki: KEYBDINPUT { wVk: VK_V, dwFlags: KEYEVENTF_EXTENDEDKEY } },
    INPUT { ki: KEYBDINPUT { wVk: VK_V, dwFlags: KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP } },
    INPUT { ki: KEYBDINPUT { wVk: VK_CONTROL, dwFlags: KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP } },
];
SendInput(&inputs, size_of::<INPUT>() as i32);
```

**Critical:** Must hide window BEFORE injection so focus returns to text field.

### 2. Global Hotkeys Without Window Focus

**Problem:** Initially tried using window-level keyboard events, but these require focus. This deselected the text field.

**Solution:** Register F9 and Esc as OS-level global shortcuts.

**Implementation:**
```rust
use tauri_plugin_global_shortcut::{Code, Shortcut, ShortcutState};

let f9_shortcut = Shortcut::new(None, Code::F9);
let esc_shortcut = Shortcut::new(None, Code::Escape);

app.handle().plugin(
    tauri_plugin_global_shortcut::Builder::new()
        .with_handler(move |_app, shortcut, event| {
            // Only trigger on PRESS, not RELEASE
            if event.state == ShortcutState::Pressed {
                if shortcut.matches(Modifiers::empty(), Code::F9) {
                    // Handle F9
                } else if shortcut.matches(Modifiers::empty(), Code::Escape) {
                    // Handle Esc
                }
            }
        })
        .build()
)?;

app.global_shortcut().register(f9_shortcut)?;
app.global_shortcut().register(esc_shortcut)?;
```

**Critical:** Filter for `ShortcutState::Pressed` only to prevent double-triggering on key release.

### 3. Audio Visualization from Backend (Not WebView)

**Problem:** Initially tried using WebView's `navigator.mediaDevices.getUserMedia()` but this accessed the mic even when window was hidden.

**Solution:** Poll backend for audio levels from the recording stream.

**Frontend (every 100ms):**
```javascript
async function pollAudioLevels() {
    const response = await fetch('http://127.0.0.1:8000/audio_level');
    const data = await response.json();
    const level = data.level || 0;
    updateVisualizerFromLevel(level);
}
```

**Backend (peek at queue):**
```python
@app.get("/audio_level")
async def get_audio_level():
    if not is_recording or not audio_capture:
        return {"level": 0.0, "recording": False}

    # Sample last 5 chunks
    chunks = []
    temp_chunks = []
    for _ in range(min(5, audio_capture.audio_queue.qsize())):
        chunk = audio_capture.audio_queue.get_nowait()
        temp_chunks.append(chunk)
        chunks.append(chunk)

    # Put them back
    for chunk in temp_chunks:
        audio_capture.audio_queue.put(chunk)

    # Calculate RMS
    audio_data = np.concatenate(chunks)
    rms = np.sqrt(np.mean(audio_data ** 2))
    normalized_level = min(1.0, rms * 3.0)

    return {"level": float(normalized_level), "recording": True}
```

### 4. Wave Loading Animation

**Problem:** User needed visual feedback during transcription processing.

**Solution:** Traveling sine wave animation across bars.

**Implementation:**
```javascript
function showProcessing() {
    isProcessing = true;
    stopMonitoring();  // Stop audio polling
    document.getElementById('statusText').textContent = 'Processing...';

    let waveOffset = 0;
    waveAnimationInterval = setInterval(() => {
        if (!isProcessing) {
            clearInterval(waveAnimationInterval);
            return;
        }

        bars.forEach((bar, index) => {
            const delay = (index / bars.length) * Math.PI * 2;
            const height = 10 + Math.sin(waveOffset + delay) * 12 + 12;
            bar.style.height = `${height}px`;
        });

        waveOffset += 0.15;  // Increment creates traveling wave
    }, 50);
}
```

**Key:** `waveOffset` continuously increases, creating the illusion of a wave traveling from left to right.

### 5. State Management with Auto-Reset

**Problem:** After stopping recording, the window would stay in "Processing..." state when shown again.

**Solution:** Detect window visibility changes and auto-reset to "Recording..." state.

**Implementation:**
```javascript
let wasVisible = false;

setInterval(async () => {
    const isVisible = await currentWindow.isVisible();

    // Window just became visible
    if (isVisible && !wasVisible) {
        resetToRecording();
    }
    // Window just became hidden
    else if (!isVisible && wasVisible) {
        stopMonitoring();
    }

    wasVisible = isVisible;
}, 500);

function resetToRecording() {
    isProcessing = false;
    if (waveAnimationInterval) {
        clearInterval(waveAnimationInterval);
        waveAnimationInterval = null;
    }
    document.getElementById('statusText').textContent = 'Recording...';
    bars.forEach(bar => bar.style.height = '3px');
    startMonitoring();
}
```

### 6. Window Positioning at Top Center

**Problem:** Window needs to be centered horizontally but at top of screen.

**Solution:** Calculate position based on monitor size when showing.

**Implementation:**
```rust
if let Some(monitor) = win.current_monitor()? {
    let screen_size = monitor.size();
    let window_size = win.outer_size()?;

    let x = (screen_size.width as i32 - window_size.width as i32) / 2;
    let y = 50;

    win.set_position(tauri::PhysicalPosition::new(x, y))?;
}
```

**Critical:** Done every time window is shown, not just on creation, in case user changes monitors.

---

## File Structure

```
Whisper4Windows/
├── backend/
│   ├── main.py                 # FastAPI server with endpoints
│   ├── whisper_engine.py       # Whisper model wrapper
│   ├── audio_capture.py        # Microphone recording
│   ├── requirements.txt        # Python dependencies
│   └── venv/                   # Python virtual environment
│       └── Lib/site-packages/
│           ├── nvidia/
│           │   ├── cublas/bin/ # CUDA libraries
│           │   └── cudnn/bin/
│
├── frontend/
│   ├── dist/
│   │   ├── recording.html      # Overlay UI (616×140)
│   │   └── index.html          # Main settings window
│   │
│   └── src-tauri/
│       ├── src/
│       │   └── lib.rs          # Main Rust logic
│       │
│       ├── Cargo.toml          # Rust dependencies
│       ├── tauri.conf.json     # Tauri configuration
│       │
│       └── target/release/
│           └── app.exe         # Compiled application
│
├── START_APP.bat               # Launch script
├── STOP_APP.bat                # Kill all processes
├── TEST_GPU.bat                # GPU diagnostics
│
├── README.md                   # User documentation
├── TECHNICAL.md                # This file
├── INSTALLATION.md             # Setup guide
└── .gitignore
```

### File Responsibilities

**`lib.rs`**
- Global shortcut registration (F9, Esc)
- Window creation and positioning
- Text injection via clipboard
- HTTP requests to backend
- Tray icon and menu
- Tauri command handlers

**`recording.html`**
- Overlay UI layout
- Audio level polling
- Visualizer animation
- Button click handlers
- State management (isProcessing, etc.)
- Model selector

**`main.py`**
- FastAPI endpoints
- Request/response handling
- Audio capture lifecycle
- Whisper engine lifecycle
- Audio level calculation

**`whisper_engine.py`**
- Model loading (lazy)
- Device detection (CUDA vs CPU)
- Transcription execution
- Error handling

**`audio_capture.py`**
- sounddevice stream management
- Audio queue management
- Chunk concatenation
- RMS level calculation

---

## Build & Deployment

### Prerequisites

**System:**
- Windows 10/11
- 8GB+ RAM
- Microphone

**Required Software:**
- Python 3.10+
- Rust 1.77.2+
- Node.js (for Tauri CLI)
- Visual Studio Build Tools

**Optional (GPU):**
- NVIDIA GPU (GTX 1060+)
- CUDA Toolkit 12.6+
- cuDNN 9.x

### Build Commands

**Backend Setup:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend Build:**
```bash
cd frontend
cargo tauri build --no-bundle
```

**Output:** `frontend\src-tauri\target\release\app.exe`

### Running

**Option 1: Batch Script (Recommended)**
```bash
START_APP.bat
```

**Option 2: Manual**
```bash
# Terminal 1: Backend
cd backend
venv\Scripts\activate
python main.py

# Terminal 2: Frontend
frontend\src-tauri\target\release\app.exe
```

### Environment Variables

**For GPU:**
```batch
set PATH=%PATH%;backend\venv\Lib\site-packages\nvidia\cublas\bin
set PATH=%PATH%;backend\venv\Lib\site-packages\nvidia\cudnn\bin
set PATH=%PATH%;C:\Program Files\NVIDIA\CUDNN\v9.13\bin\13.0
```

---

## Known Issues & Solutions

### Issue 1: Text Field Loses Focus

**Symptom:** Text doesn't inject after transcription.

**Cause:** Window steals focus when shown.

**Solution:**
- Set `.focused(false)` on window
- Hide window BEFORE injection
- Wait 100ms for focus to return

**Code:**
```rust
// Hide window FIRST
win.hide()?;

// Wait for focus to return
tokio::time::sleep(Duration::from_millis(100)).await;

// Now inject
inject_text(text)?;
```

### Issue 2: Hotkey Triggers Twice

**Symptom:** F9 press triggers start AND stop immediately.

**Cause:** Handler triggered on both key press and release.

**Solution:** Filter for `ShortcutState::Pressed` only.

**Code:**
```rust
if event.state == ShortcutState::Pressed {
    // Handle hotkey
}
```

### Issue 3: Window Stays in Processing State

**Symptom:** After recording, window still shows "Processing..." when shown again.

**Cause:** State not reset between recordings.

**Solution:** Auto-reset when window becomes visible.

**Code:**
```javascript
if (isVisible && !wasVisible) {
    resetToRecording();  // Clear processing state
}
```

### Issue 4: Microphone Accessed When Window Hidden

**Symptom:** Windows shows mic indicator even when not recording.

**Cause:** WebView's `getUserMedia()` doesn't release on window hide.

**Solution:** Remove WebView audio access, poll backend instead.

**Code:**
```javascript
// DON'T: const stream = await navigator.mediaDevices.getUserMedia({audio: true});

// DO: Poll backend
const response = await fetch('http://127.0.0.1:8000/audio_level');
```

### Issue 5: Visualizer Not Updating

**Symptom:** Bars stay at minimum height during recording.

**Cause:** Backend not returning audio levels.

**Solution:** Ensure backend `/audio_level` endpoint implemented.

**Debug:**
```javascript
console.log('Audio level:', data.level, 'Recording:', data.recording);
```

---

## Design Decisions

### Why Two Processes?

**Decision:** Separate frontend (Tauri/Rust) and backend (Python/FastAPI).

**Rationale:**
- Whisper only available in Python
- Tauri provides native Windows integration
- Allows independent updates
- Backend can be reused by other frontends

**Tradeoff:** More complex deployment, two processes to manage.

### Why Clipboard + Ctrl+V?

**Decision:** Inject via clipboard instead of character-by-character.

**Rationale:**
- Much faster (instant vs 0.5s per 10 chars)
- More reliable
- Handles Unicode better
- Works with all apps

**Tradeoff:** Overwrites user's clipboard.

**Mitigation:** Could save/restore clipboard (not implemented).

### Why Global Hotkeys?

**Decision:** OS-level F9 and Esc, not window-level.

**Rationale:**
- Works from any app
- Doesn't require window focus
- Doesn't deselect text field

**Tradeoff:** Can conflict with other apps using F9.

**Future:** Allow custom hotkey configuration.

### Why Polling for Audio Levels?

**Decision:** Frontend polls GET /audio_level every 100ms.

**Rationale:**
- Simpler than WebSockets
- Stateless
- Easy to debug
- Low overhead (100ms is fine for visualization)

**Tradeoff:** Slight delay (max 100ms).

### Why 616×140 Window?

**Decision:** 22:5 aspect ratio, 616 pixels wide.

**Rationale:**
- Wide enough for 80 bars with spacing
- Narrow enough to not obstruct screen
- 22:5 ratio requested by user
- 140px height fits all UI elements

**Calculation:**
- 22/5 = 4.4 ratio
- 140 * 4.4 = 616

### Why Top Center Position?

**Decision:** Window at (center_x, 50px from top).

**Rationale:**
- Visible without obstructing content
- Consistent position
- Easy to glance at
- Mimics macOS notification style

**Alternative Considered:** Bottom right (like notifications) - rejected as too far from user's focus.

### Why 80 Visualizer Bars?

**Decision:** 80 bars (reduced from 100 for 1200px window).

**Rationale:**
- Fits 616px width: 80 * 3px bars + 79 * 2px gaps = 398px (leaves padding)
- Smooth animation
- Responsive to audio
- Not too dense

**Calculation:**
- Bar width: 3px
- Gap: 2px (CSS gap property)
- Total: 80 * 3 + 79 * 2 = 398px
- Padding: (616 - 398) / 2 = 109px per side

### Why Faster-Whisper?

**Decision:** Use faster-whisper instead of openai-whisper.

**Rationale:**
- 4x faster on CPU
- 2x faster on GPU
- Lower memory usage
- CTranslate2 optimization
- Compatible API

**Tradeoff:** Extra dependency (ctranslate2).

---

## Development Guidelines

### For Future AI Assistants

**When modifying the overlay:**
1. Always test with START_APP.bat (not just cargo run)
2. Check both button clicks AND F9/Esc hotkeys
3. Verify text injection works (test in Notepad)
4. Ensure window doesn't steal focus
5. Check state resets between recordings

**When modifying backend:**
1. Keep /audio_level endpoint fast (<10ms)
2. Don't block on transcription in /start
3. Test with both CPU and GPU
4. Return JSON, not plain text
5. Handle missing audio gracefully

**When modifying Rust:**
1. Always `.map_err(|e| e.to_string())?` for Results
2. Use `tokio::spawn` for async backend calls
3. Log with `log::info!()` not `println!()`
4. Test global shortcuts don't conflict
5. Verify clipboard injection order

**When modifying JavaScript:**
1. Always check `isProcessing` before polling
2. Clear intervals on window hide
3. Reset state on window show
4. Use try-catch for fetch calls
5. Log to console for debugging

### Common Tasks

**Change hotkey:**
```rust
// In lib.rs
let shortcut = Shortcut::new(None, Code::F10);  // Change F9 to F10
```

**Change window size:**
```rust
// In lib.rs
.inner_size(800.0, 160.0)  // New size

// In recording.html
.container { width: 800px; }
```

**Change model:**
```javascript
// In recording.html
<option value="medium" selected>Medium</option>
```

**Add new endpoint:**
```python
# In main.py
@app.get("/new_endpoint")
async def new_endpoint():
    return {"data": "value"}
```

---

## Testing Checklist

**Before Committing Changes:**

- [ ] Build succeeds: `cargo tauri build --no-bundle`
- [ ] Backend starts: `python main.py`
- [ ] Frontend starts: `app.exe`
- [ ] F9 starts recording (window shows)
- [ ] F9 stops recording (window hides)
- [ ] Text appears in Notepad
- [ ] Esc cancels recording
- [ ] Visualizer animates during recording
- [ ] Wave animation shows during processing
- [ ] Window positioned at top center
- [ ] No focus stealing (text field stays selected)
- [ ] State resets on next recording
- [ ] Model selector works
- [ ] GPU/CPU detection works
- [ ] Logs visible in frontend console
- [ ] No mic access when window hidden

---

## Future Enhancements

**High Priority:**
- [ ] Custom hotkey configuration UI
- [ ] Save/restore clipboard before injection
- [ ] Multi-monitor support improvements
- [ ] Error messages to user (not just logs)

**Medium Priority:**
- [ ] Recording history/cache
- [ ] Post-processing options (punctuation, capitalization)
- [ ] Language selection UI
- [ ] Keyboard shortcut hints overlay

**Low Priority:**
- [ ] WebSocket for audio levels (instead of polling)
- [ ] Installer/MSI package
- [ ] Auto-update mechanism
- [ ] Themes/customization

---

## Glossary

**WASAPI** - Windows Audio Session API, low-latency audio interface
**RMS** - Root Mean Square, measure of audio loudness
**Tauri** - Electron alternative using WebView2
**faster-whisper** - Optimized Whisper using CTranslate2
**CTranslate2** - Fast inference engine for Transformer models
**cuDNN** - CUDA Deep Neural Network library
**SendInput** - Windows API for keyboard/mouse simulation
**GlobalAlloc** - Windows API for memory allocation
**WebView2** - Microsoft Edge Chromium-based web control
**ASGI** - Asynchronous Server Gateway Interface (Python)

---

## Contact & Support

**Repository:** (Add GitHub URL)
**Issues:** (Add GitHub Issues URL)
**Docs:** README.md, INSTALLATION.md, TECHNICAL.md

---

**End of Technical Documentation**
