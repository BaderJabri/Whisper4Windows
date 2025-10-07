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


# Pydantic models
class StartRequest(BaseModel):
    model_size: str = "small"  # tiny, base, small, medium, large-v3
    language: Optional[str] = "en"
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


@app.post("/start")
async def start_recording(request: StartRequest):
    """Start recording audio (no transcription until stop)"""
    global audio_capture, whisper_engine, is_recording
    
    try:
        if is_recording:
            return {"status": "error", "message": "Already recording"}
        
        logger.info(f"🎙️ Starting recording (will transcribe on STOP)")
        logger.info(f"📋 Requested device: {request.device}")

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
            logger.info("📥 Loading Whisper model...")
            success = whisper_engine.load_model()
            if not success:
                return {"status": "error", "message": "Failed to load Whisper model"}
        
        # Transcribe ALL audio at once with timing
        import time
        logger.info("🎙️ Transcribing full recording...")
        transcription_start = time.time()
        
        result = await loop.run_in_executor(
            None,
            whisper_engine.transcribe_audio,
            audio_data,
            "en"
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
