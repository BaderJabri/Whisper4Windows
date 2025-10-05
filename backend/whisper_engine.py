"""
Whisper Speech-to-Text Engine
Handles model loading and transcription using faster-whisper
"""

import logging
import os
import sys
from typing import Optional, Dict, List
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

# Get the appropriate models directory
def get_models_dir() -> Path:
    """Get the models directory, using AppData for bundled apps"""
    if getattr(sys, 'frozen', False):
        # Running as bundled executable
        appdata = Path(os.getenv('APPDATA') or os.path.expanduser('~'))
        models_dir = appdata / 'Whisper4Windows' / 'models'
    else:
        # Running from source
        models_dir = Path("models")

    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir

# Try to import faster-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
    logger.info("✅ faster-whisper is available")
except ImportError as e:
    WHISPER_AVAILABLE = False
    logger.warning(f"⚠️ faster-whisper not available: {e}")
    WhisperModel = None


class WhisperEngine:
    """Whisper speech-to-text engine"""
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto"
    ):
        """
        Initialize Whisper engine
        
        Args:
            model_size: Model size (tiny, base, small, medium, large-v3, large-v3-turbo)
            device: Device to use (cpu, cuda, auto)
            compute_type: Compute type (int8, float16, float32, auto)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self.is_loaded = False
        
        # Auto-detect device and compute type
        if device == "auto":
            self.device = self._detect_device()
        
        if compute_type == "auto":
            self.compute_type = self._detect_compute_type()
    
    def _detect_device(self) -> str:
        """Auto-detect best device (CUDA, CPU)"""
        # Try GPU first, fall back to CPU if it fails
        try:
            import ctranslate2
            cuda_count = ctranslate2.get_cuda_device_count()
            if cuda_count > 0:
                logger.info(f"🚀 CUDA is available! Found {cuda_count} GPU(s)")
                return "cuda"
        except Exception as e:
            logger.warning(f"CUDA check failed: {e}")
        
        logger.info("💻 Using CPU")
        return "cpu"
    
    def _detect_compute_type(self) -> str:
        """Auto-detect best compute type based on device"""
        if self.device == "cuda":
            # Use float16 for best quality with cuDNN installed
            # Falls back to int8_float16 if cuDNN has issues
            return "float16"
        else:
            return "int8"  # Best for CPU
    
    def is_model_downloaded(self, model_size: str = None) -> bool:
        """
        Check if a model is already downloaded
        
        Args:
            model_size: Model size to check (uses self.model_size if None)
            
        Returns:
            True if model is downloaded, False otherwise
        """
        if model_size is None:
            model_size = self.model_size
            
        models_dir = get_models_dir()
        model_path = models_dir / f"models--Systran--faster-whisper-{model_size}"
        
        # Check if model directory exists and has required files
        if model_path.exists():
            snapshot_dir = model_path / "snapshots"
            if snapshot_dir.exists() and any(snapshot_dir.iterdir()):
                logger.info(f"✅ Model '{model_size}' is already downloaded")
                return True
        
        logger.warning(f"⚠️ Model '{model_size}' is not downloaded")
        return False
    
    def load_model(self) -> bool:
        """
        Load the Whisper model with automatic GPU -> CPU fallback
        
        Returns:
            True if successful, False otherwise
        """
        if not WHISPER_AVAILABLE:
            logger.error("❌ faster-whisper is not installed!")
            return False
        
        if self.is_loaded:
            logger.info("Model already loaded")
            return True
        
        try:
            logger.info(f"📥 Loading Whisper model: {self.model_size}")
            logger.info(f"   Device: {self.device}")
            logger.info(f"   Compute type: {self.compute_type}")
            
            # Create models directory if it doesn't exist
            models_dir = get_models_dir()
            
            # Try to load model
            try:
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=str(models_dir)
                )
                
                self.is_loaded = True
                logger.info(f"✅ Model loaded successfully: {self.model_size}")
                return True
                
            except Exception as gpu_error:
                # If GPU failed and we were trying GPU, fall back to CPU
                if self.device == "cuda":
                    logger.warning(f"⚠️ GPU loading failed: {gpu_error}")
                    logger.info("🔄 Falling back to CPU...")
                    
                    self.device = "cpu"
                    self.compute_type = "int8"
                    
                    self.model = WhisperModel(
                        self.model_size,
                        device=self.device,
                        compute_type=self.compute_type,
                        download_root=str(models_dir)
                    )
                    
                    self.is_loaded = True
                    logger.info(f"✅ Model loaded successfully on CPU (GPU fallback): {self.model_size}")
                    return True
                else:
                    # CPU also failed, re-raise
                    raise
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def transcribe_audio(
        self,
        audio_data: np.ndarray,
        language: Optional[str] = None,
        task: str = "transcribe"
    ) -> Dict:
        """
        Transcribe audio data
        
        Args:
            audio_data: Audio data as numpy array (float32, mono, 16kHz)
            language: Language code (e.g., 'en', 'es') or None for auto-detect
            task: 'transcribe' or 'translate'
            
        Returns:
            Dictionary with transcription results
        """
        if not self.is_loaded:
            logger.warning("Model not loaded, loading now...")
            if not self.load_model():
                return {
                    "success": False,
                    "error": "Failed to load model",
                    "text": ""
                }
        
        try:
            logger.info(f"🎙️ Transcribing audio...")
            logger.info(f"   Audio shape: {audio_data.shape}")
            logger.info(f"   Audio dtype: {audio_data.dtype}")
            logger.info(f"   Language: {language or 'auto-detect'}")
            
            # Ensure audio is float32 and 1D
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            # Transcribe with optimized settings for speed
            segments, info = self.model.transcribe(
                audio_data,
                language=language,
                task=task,
                beam_size=1,  # Greedy decoding for speed (was 5)
                best_of=1,  # Single pass for speed
                temperature=0.0,  # Deterministic
                vad_filter=False,  # DISABLED - was removing all speech
                # vad_parameters=dict(
                #     min_silence_duration_ms=300
                # ),
                condition_on_previous_text=False  # Don't wait for context
            )
            
            # Collect segments
            transcription_segments = []
            full_text = ""
            
            for segment in segments:
                segment_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                }
                transcription_segments.append(segment_dict)
                full_text += segment.text
            
            full_text = full_text.strip()
            
            logger.info(f"✅ Transcription complete!")
            logger.info(f"   Detected language: {info.language}")
            logger.info(f"   Language probability: {info.language_probability:.2%}")
            logger.info(f"   Text: {full_text[:100]}..." if len(full_text) > 100 else f"   Text: {full_text}")
            
            return {
                "success": True,
                "text": full_text,
                "segments": transcription_segments,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration if hasattr(info, 'duration') else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }
    
    def transcribe_file(self, audio_file: str, language: Optional[str] = None) -> Dict:
        """
        Transcribe an audio file
        
        Args:
            audio_file: Path to audio file
            language: Language code or None
            
        Returns:
            Transcription results
        """
        try:
            import soundfile as sf
            
            # Load audio file
            audio_data, sample_rate = sf.read(audio_file)
            
            # Resample if needed (Whisper expects 16kHz)
            if sample_rate != 16000:
                logger.info(f"Resampling from {sample_rate}Hz to 16000Hz")
                from scipy import signal
                num_samples = int(len(audio_data) * 16000 / sample_rate)
                audio_data = signal.resample(audio_data, num_samples)
            
            # Transcribe
            return self.transcribe_audio(audio_data, language)
            
        except Exception as e:
            logger.error(f"❌ Failed to transcribe file: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }


# Global engine instance
_whisper_engine = None

def get_whisper_engine(model_size: str = "base") -> WhisperEngine:
    """Get or create the global Whisper engine"""
    global _whisper_engine
    if _whisper_engine is None or _whisper_engine.model_size != model_size:
        _whisper_engine = WhisperEngine(model_size=model_size)
    return _whisper_engine
