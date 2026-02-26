"""
Whisper4Windows Backend Server
FastAPI server for local speech-to-text processing
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, List
import numpy as np

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import our modules
from audio_capture import AudioCapture
from whisper_engine import WhisperEngine
import gpu_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
audio_capture: Optional[AudioCapture] = None
whisper_engine: Optional[WhisperEngine] = None
is_recording = False
transcription_task: Optional[asyncio.Task] = None
last_transcribed_text = ""
is_model_loading = False
model_loading_info = {"model": "", "status": ""}
current_language: Optional[str] = None  # Store language from start request


# Pydantic models
class StartRequest(BaseModel):
    model_size: str = "small"  # tiny, base, small, medium, large-v3
    language: Optional[str] = None  # Language code or None for auto-detect
    device: str = "auto"  # auto, cpu, cuda
    device_index: Optional[int] = None  # Microphone device index (None = default)


class StopRequest(BaseModel):
    pass


class TranscriptionResponse(BaseModel):
    success: bool
    text: str = ""
    is_final: bool = False
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    backend: str
    model: str
    recording: bool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app"""
    logger.info("=" * 60)
    logger.info("🚀 Whisper4Windows Backend Starting...")
    logger.info("=" * 60)
    logger.info(f"Server: http://127.0.0.1:8000")
    logger.info(f"API Docs: http://127.0.0.1:8000/docs")
    logger.info(f"Health Check: http://127.0.0.1:8000/health")
    logger.info("=" * 60)

    # Check GPU libraries at startup
    logger.info("🔍 Checking GPU libraries...")
    gpu_info = gpu_manager.get_gpu_info()

    if gpu_info["gpu_available"]:
        logger.info("✅ NVIDIA GPU detected")
        if gpu_info["libs_installed"]:
            logger.info("✅ GPU libraries installed - GPU acceleration available")
        else:
            logger.warning("⚠️ GPU detected but libraries not installed")
            if gpu_info["missing_libraries"]:
                logger.warning(f"   Missing: {', '.join(gpu_info['missing_libraries'])}")
            logger.warning("   Use 'Install GPU Libraries' in settings to enable GPU acceleration")
    else:
        logger.info("ℹ️ No NVIDIA GPU detected - will use CPU mode")

    logger.info("=" * 60)

    yield

    # Cleanup on shutdown
    logger.info("Shutting down...")
    global audio_capture
    if is_recording and audio_capture:
        try:
            audio_capture.stop_recording()
        except:
            pass


# Create FastAPI app
app = FastAPI(
    title="Whisper4Windows Backend",
    description="Local speech-to-text processing server",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": "Whisper4Windows Backend",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    global whisper_engine

    backend = "cpu"
    model = "not_loaded"

    if whisper_engine and whisper_engine.is_loaded:
        backend = whisper_engine.device
        model = whisper_engine.model_size

    return HealthResponse(
        status="ok",
        backend=backend,
        model=model,
        recording=is_recording
    )


@app.get("/model/status")
async def get_model_status(model_size: str = "small"):
    """Check if a model is downloaded and get loading status"""
    global is_model_loading, model_loading_info, whisper_engine

    try:
        # Check if model is currently loading
        if is_model_loading:
            return {
                "success": True,
                "is_loading": True,
                "loading_model": model_loading_info.get("model", ""),
                "status": model_loading_info.get("status", "Downloading...")
            }

        # Check if this specific model is downloaded
        temp_engine = WhisperEngine(model_size=model_size)
        is_downloaded = temp_engine.is_model_downloaded(model_size)

        # Check if model is currently loaded in memory
        is_loaded = whisper_engine is not None and whisper_engine.model_size == model_size and whisper_engine.is_loaded

        return {
            "success": True,
            "is_loading": False,
            "is_downloaded": is_downloaded,
            "is_loaded": is_loaded,
            "model": model_size
        }

    except Exception as e:
        logger.error(f"Error checking model status: {e}")
        return {
            "success": False,
            "error": str(e),
            "is_loading": False,
            "is_downloaded": False
        }


@app.post("/load_model")
async def load_model(request: StartRequest):
    """Pre-load a Whisper model without starting recording"""
    global whisper_engine, is_model_loading, model_loading_info, current_language

    try:
        logger.info(f"📥 Loading model: {request.model_size} on {request.device}")

        # Store language
        current_language = None if request.language in (None, "auto") else request.language

        # Check if we can reuse existing engine
        if whisper_engine is not None and \
           whisper_engine.model_size == request.model_size and \
           whisper_engine._original_device == request.device and \
           whisper_engine.is_loaded:
            logger.info(f"♻️ Model already loaded: {request.model_size} on {whisper_engine.device}")
            return {
                "status": "success",
                "message": "Model already loaded",
                "model": request.model_size,
                "device": whisper_engine.device
            }

        # Create new engine if needed
        if whisper_engine is None or \
           whisper_engine.model_size != request.model_size or \
           whisper_engine._original_device != request.device:
            whisper_engine = WhisperEngine(
                model_size=request.model_size,
                device=request.device
            )
            logger.info(f"✓ Whisper engine created (device: {whisper_engine.device})")

        # Load the model if not already loaded
        if not whisper_engine.is_loaded:
            is_model_loading = True
            model_loading_info = {
                "model": whisper_engine.model_size,
                "status": "Downloading model..." if not whisper_engine.is_model_downloaded() else "Loading model..."
            }

            logger.info("📥 Loading Whisper model into memory...")
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, whisper_engine.load_model)

            is_model_loading = False
            model_loading_info = {"model": "", "status": ""}

            if not success:
                return {
                    "status": "error",
                    "message": "Failed to load Whisper model"
                }

            logger.info(f"✅ Model loaded: {request.model_size} on {whisper_engine.device}")

        return {
            "status": "success",
            "message": "Model loaded successfully",
            "model": request.model_size,
            "device": whisper_engine.device
        }

    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        import traceback
        logger.error(traceback.format_exc())

        is_model_loading = False
        model_loading_info = {"model": "", "status": ""}

        return {
            "status": "error",
            "message": str(e)
        }


@app.post("/start")
async def start_recording(request: StartRequest):
    """Start recording audio (no transcription until stop)"""
    global audio_capture, whisper_engine, is_recording, current_language

    try:
        if is_recording:
            return {"status": "error", "message": "Already recording"}

        # Store language for use in /stop
        # Convert "auto" string to None for Whisper's auto-detection
        current_language = None if request.language in (None, "auto") else request.language
        logger.info(f"🎙️ Starting recording (will transcribe on STOP)")
        logger.info(f"📋 Requested device: {request.device}")
        logger.info(f"🌐 Language from request: '{request.language}' → effective: '{current_language or 'auto-detect'}'")
        if current_language:
            logger.info(f"   Will force transcription in: {current_language}")
        else:
            logger.info(f"   Will auto-detect language (Whisper decides)")

        # Reuse existing engine if model/device match, otherwise create new one
        if whisper_engine is not None and \
           whisper_engine.model_size == request.model_size and \
           whisper_engine._original_device == request.device:
            logger.info(f"♻️ Reusing existing Whisper engine (device: {whisper_engine.device})")
        else:
            # Initialize new Whisper engine (model will load on transcription)
            whisper_engine = WhisperEngine(
                model_size=request.model_size,
                device=request.device
            )
            logger.info(f"✓ Whisper engine created (device: {whisper_engine.device})")
        
        # Initialize audio capture
        audio_capture = AudioCapture()
        audio_capture.clear_queue()

        # Start audio stream with selected device
        device_index = request.device_index if request.device_index is not None else None
        if device_index is not None:
            logger.info(f"🎤 Using microphone device index: {device_index}")
        else:
            logger.info(f"🎤 Using default microphone device")

        audio_capture.start_recording(device_index=device_index)
        await asyncio.sleep(0.1)
        
        is_recording = True
        
        logger.info("✅ Recording started! Speak now...")
        
        return {
            "status": "started",
            "message": "Recording... Press Alt+T when done",
            "model": request.model_size,
            "device": whisper_engine.device
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to start recording: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        is_recording = False
        if audio_capture:
            try:
                audio_capture.stop_recording()
            except:
                pass
        
        return {"status": "error", "message": str(e)}


@app.post("/stop")
async def stop_recording():
    """Stop recording and transcribe everything"""
    global is_recording, audio_capture, whisper_engine
    
    try:
        if not is_recording:
            return {"status": "error", "message": "Not recording"}
        
        logger.info("🛑 Stopping recording and transcribing...")
        
        # Stop recording flag first
        is_recording = False
        
        # Stop audio capture and get ALL audio
        loop = asyncio.get_event_loop()
        audio_data = await loop.run_in_executor(None, audio_capture.stop_recording)
        
        if audio_data is None or len(audio_data) == 0:
            logger.warning("No audio captured")
            return {
                "status": "success",
                "text": "",
                "message": "No audio recorded"
            }
        
        logger.info(f"📼 Captured {len(audio_data) / 16000:.1f} seconds of audio")

        # Load model if not loaded
        if not whisper_engine.is_loaded:
            global is_model_loading, model_loading_info

            is_model_loading = True
            model_loading_info = {
                "model": whisper_engine.model_size,
                "status": "Downloading model..." if not whisper_engine.is_model_downloaded() else "Loading model..."
            }

            logger.info("📥 Loading Whisper model...")
            try:
                success = whisper_engine.load_model()
                if not success:
                    is_model_loading = False
                    return {"status": "error", "message": "Failed to load Whisper model"}
            finally:
                is_model_loading = False
                model_loading_info = {"model": "", "status": ""}
        
        # Transcribe ALL audio at once with timing
        import time
        logger.info("🎙️ Transcribing full recording...")
        logger.info(f"   Language setting: {current_language if current_language else 'auto-detect'}")

        # Determine task and language for Whisper:
        # - If English selected: translate any language TO English (language=None, task="translate")
        # - Otherwise: transcribe in specified/detected language (language=current_language, task="transcribe")
        if current_language == "en":
            task = "translate"
            whisper_language = None  # Auto-detect source language, translate to English
            logger.info(f"   Task: translate to English (auto-detect source)")
        else:
            task = "transcribe"
            whisper_language = current_language  # None for auto-detect, or specific language code
            logger.info(f"   Task: transcribe in {whisper_language if whisper_language else 'detected language'}")

        transcription_start = time.time()

        result = await loop.run_in_executor(
            None,
            whisper_engine.transcribe_audio,
            audio_data,
            whisper_language,  # None for auto-detect, language code for specific language, or None when translating
            task  # "translate" for English, "transcribe" for all others
        )
        
        transcription_time = time.time() - transcription_start
        logger.info(f"⏱️ Transcription took: {transcription_time:.2f} seconds")
        
        if not result["success"]:
            logger.error(f"Transcription failed: {result.get('error')}")
            return {
                "status": "error",
                "message": result.get('error', 'Transcription failed')
            }
        
        final_text = result["text"].strip()
        logger.info(f"✅ Transcription complete!")
        logger.info(f"📝 Final text: {final_text[:100]}..." if len(final_text) > 100 else f"📝 Final text: {final_text}")
        
        return {
            "status": "success",
            "text": final_text,
            "language": result.get("language", "en"),
            "duration": len(audio_data) / 16000,
            "transcription_time": transcription_time,
            "model": whisper_engine.model_size,
            "device": whisper_engine.device  # Return actual device used
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to stop/transcribe: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}


@app.post("/cancel")
async def cancel_recording():
    """Cancel recording without transcribing"""
    global is_recording, audio_capture

    try:
        if not is_recording:
            return {"status": "error", "message": "Not recording"}

        logger.info("❌ Canceling recording...")

        # Stop recording flag
        is_recording = False

        # Stop audio capture without transcribing
        if audio_capture:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, audio_capture.stop_recording)

        logger.info("✅ Recording canceled")

        return {
            "status": "success",
            "message": "Recording canceled"
        }

    except Exception as e:
        logger.error(f"❌ Failed to cancel: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/audio_level")
async def get_audio_level():
    """Get current audio input level (0.0 to 1.0)"""
    global is_recording, audio_capture

    try:
        if not is_recording or not audio_capture:
            return {"level": 0.0, "recording": False}

        # Peek at recent audio without removing from queue
        if audio_capture.audio_queue.empty():
            return {"level": 0.0, "recording": True}

        # Get queue size to know how much audio we have
        queue_size = audio_capture.audio_queue.qsize()

        # Sample a few recent chunks to calculate level
        chunks = []
        temp_chunks = []

        # Get up to 5 most recent chunks
        for _ in range(min(5, queue_size)):
            try:
                chunk = audio_capture.audio_queue.get_nowait()
                temp_chunks.append(chunk)
                chunks.append(chunk)
            except:
                break

        # Put them back in the queue
        for chunk in temp_chunks:
            audio_capture.audio_queue.put(chunk)

        if not chunks:
            return {"level": 0.0, "recording": True}

        # Calculate RMS level
        audio_data = np.concatenate(chunks, axis=0)
        rms = np.sqrt(np.mean(audio_data ** 2))

        # Normalize to 0-1 range (typical speech is around 0.1-0.3 RMS)
        normalized_level = min(1.0, rms * 3.0)

        return {
            "level": float(normalized_level),
            "recording": True,
            "queue_size": queue_size
        }

    except Exception as e:
        logger.error(f"Error getting audio level: {e}")
        return {"level": 0.0, "recording": False, "error": str(e)}


# Removed /get_live_chunk endpoint - using simple record/stop flow now


@app.get("/devices")
async def list_devices():
    """List available audio devices"""
    try:
        import sounddevice as sd
        devices = sd.query_devices()

        input_devices = []
        output_devices = []

        for i, dev in enumerate(devices):
            device_info = {
                "id": i,
                "name": dev["name"],
                "channels": dev["max_input_channels"] if dev["max_input_channels"] > 0 else dev["max_output_channels"],
                "sample_rate": int(dev["default_samplerate"])
            }

            if dev["max_input_channels"] > 0:
                input_devices.append(device_info)
            if dev["max_output_channels"] > 0:
                output_devices.append(device_info)

        return {
            "success": True,
            "inputs": input_devices,
            "outputs": output_devices
        }

    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        return {
            "success": False,
            "error": str(e),
            "inputs": [],
            "outputs": []
        }


@app.get("/gpu/info")
async def get_gpu_info():
    """Get GPU and library installation status"""
    try:
        info = gpu_manager.get_gpu_info()
        return {
            "success": True,
            **info
        }
    except Exception as e:
        logger.error(f"Error getting GPU info: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/gpu/install")
async def install_gpu_libs():
    """Download and install GPU libraries (blocking operation)"""
    try:
        logger.info("🚀 Starting GPU library installation...")

        # Run installation synchronously (this will take a while)
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            gpu_manager.install_gpu_libs
        )

        if success:
            logger.info("✅ GPU libraries installed successfully")
            return {
                "success": True,
                "message": "GPU libraries installed successfully. Restart may be required."
            }
        else:
            logger.error("❌ GPU library installation failed")
            return {
                "success": False,
                "error": "Installation failed. Check logs for details."
            }

    except Exception as e:
        logger.error(f"❌ GPU installation error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/gpu/uninstall")
async def uninstall_gpu_libs():
    """Remove installed GPU libraries"""
    try:
        success = gpu_manager.uninstall_gpu_libs()
        if success:
            return {
                "success": True,
                "message": "GPU libraries removed successfully"
            }
        else:
            return {
                "success": False,
                "error": "Failed to remove GPU libraries"
            }
    except Exception as e:
        logger.error(f"Error uninstalling GPU libs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Run the server
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
