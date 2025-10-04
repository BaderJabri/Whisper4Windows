# Whisper4Windows Backend

Python FastAPI server for local speech-to-text processing.

## Quick Start

### Windows
```bash
# Double-click to start
start_backend.bat
```

### Manual Setup
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python main.py
```

## Test the Server

Once running, visit:
- **Server**: http://127.0.0.1:8000
- **API Docs**: http://127.0.0.1:8000/docs (Interactive Swagger UI)
- **Health Check**: http://127.0.0.1:8000/health

## API Endpoints

### Core Endpoints
- `GET /` - Server info
- `GET /health` - Health check with backend status
- `GET /devices` - List audio input/output devices
- `POST /start` - Start recording/transcription
- `POST /stop` - Stop recording
- `POST /transcribe` - Transcribe audio data
- `POST /benchmark` - Run backend performance benchmark
- `WS /stream` - WebSocket for real-time streaming

## Current Status

✅ **Phase 1: Mock Server** (Current)
- FastAPI server running
- Mock responses for all endpoints
- Ready for frontend integration

🚧 **Phase 2: Audio Capture** (Next)
- WASAPI integration
- Real device detection
- Audio recording to buffer

🚧 **Phase 3: Whisper Integration** (Future)
- Model loading (CUDA/DirectML/CPU)
- Real transcription
- VAD integration

## Development

```bash
# Run with auto-reload
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Run with custom port
uvicorn main:app --port 8001
```

## Dependencies

- **FastAPI** - Web framework
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation
- **WebSockets** - Real-time streaming

Future: faster-whisper, sounddevice, onnxruntime-directml, webrtcvad



