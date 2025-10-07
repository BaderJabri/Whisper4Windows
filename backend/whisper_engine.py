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

# Add CUDA library paths for bundled executables
def setup_cuda_paths():
    """Add CUDA library paths to PATH for all environments"""
    logger.info("🔍 Setting up CUDA paths...")
    logger.info(f"   sys.frozen = {getattr(sys, 'frozen', False)}")

    cuda_paths = []

    # Check if running as bundled executable
    if getattr(sys, 'frozen', False):
        logger.info(f"   Running as bundled app, MEIPASS = {sys._MEIPASS}")

        # Add the executable's own directory first (where user might copy DLLs)
        exe_dir = Path(sys.executable).parent
        logger.info(f"   Executable directory: {exe_dir}")
        cuda_paths.append(exe_dir)

        # Also add MEIPASS temporary extraction directory
        cuda_paths.append(Path(sys._MEIPASS))

        # NVIDIA pip packages (bundled with PyInstaller)
        cuda_paths.extend([
            Path(sys._MEIPASS) / "nvidia" / "cublas" / "bin",
            Path(sys._MEIPASS) / "nvidia" / "cudnn" / "bin",
            Path(sys._MEIPASS) / "nvidia" / "cufft" / "bin",
            Path(sys._MEIPASS) / "nvidia" / "curand" / "bin",
            Path(sys._MEIPASS) / "nvidia" / "cusolver" / "bin",
            Path(sys._MEIPASS) / "nvidia" / "cusparse" / "bin",
        ])

    # Add downloaded GPU libraries from AppData (for optional GPU install)
    appdata = Path(os.getenv('APPDATA') or os.path.expanduser('~'))
    gpu_libs_dir = appdata / 'Whisper4Windows' / 'gpu_libs'
    if gpu_libs_dir.exists():
        logger.info(f"   Found downloaded GPU libraries: {gpu_libs_dir}")
        cuda_paths.extend([
            gpu_libs_dir / "nvidia" / "cublas" / "bin",
            gpu_libs_dir / "nvidia" / "cudnn" / "bin",
            gpu_libs_dir / "nvidia" / "cufft" / "bin",
            gpu_libs_dir / "nvidia" / "curand" / "bin",
            gpu_libs_dir / "nvidia" / "cusolver" / "bin",
            gpu_libs_dir / "nvidia" / "cusparse" / "bin",
        ])

    # System CUDA installation (check all versions)
    cuda_paths.extend([
        Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin"),
        Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.7\bin"),
        Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin"),
        Path(r"C:\Program Files\NVIDIA\CUDNN\v9.3\bin"),
        Path(r"C:\Program Files\NVIDIA\CUDNN\v9.4\bin"),
        Path(r"C:\Program Files\NVIDIA\CUDNN\v9.5\bin"),
    ])

    # Also check if CUDA is in the CUDA toolkit's nested bin
    cuda_toolkit = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA")
    if cuda_toolkit.exists():
        for cuda_version_dir in cuda_toolkit.iterdir():
            if cuda_version_dir.is_dir():
                bin_path = cuda_version_dir / "bin"
                if bin_path.exists():
                    cuda_paths.append(bin_path)

    # Add to PATH environment variable
    current_path = os.environ.get('PATH', '')
    paths_added = 0

    for cuda_path in cuda_paths:
        if cuda_path.exists():
            logger.info(f"✅ Found CUDA path: {cuda_path}")

            # Add to PATH
            if str(cuda_path) not in current_path:
                current_path = str(cuda_path) + os.pathsep + current_path
                paths_added += 1

            # Also add to Windows DLL search path (Python 3.8+)
            try:
                os.add_dll_directory(str(cuda_path))
                logger.info(f"   ✅ Added to DLL directory: {cuda_path}")
            except (AttributeError, OSError) as e:
                logger.warning(f"   ⚠️ Could not add DLL directory: {e}")
        else:
            logger.debug(f"⚠️ CUDA path not found: {cuda_path}")

    os.environ['PATH'] = current_path
    logger.info(f"✅ CUDA paths configured ({paths_added} paths added to PATH)")

    # Debug: Try to find cublas64_12.dll manually
    import ctypes.util
    cublas_dll = ctypes.util.find_library("cublas64_12")
    if cublas_dll:
        logger.info(f"✅ cublas64_12.dll found at: {cublas_dll}")
    else:
        logger.warning("⚠️ cublas64_12.dll NOT found by ctypes.util.find_library()")

# Setup CUDA paths before importing torch/ctranslate2
setup_cuda_paths()

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
        self._cuda_detected = False
        self._original_device = device  # Store original device setting

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
                # Store that we detected CUDA for potential fallback
                self._cuda_detected = True
                return "cuda"
        except Exception as e:
            logger.warning(f"⚠️ CUDA check failed: {e}")
            logger.info("💻 Falling back to CPU")

        self._cuda_detected = False
        logger.info("💻 Using CPU")
        return "cpu"
    
    def _detect_compute_type(self) -> str:
        """Auto-detect best compute type based on device"""
        if self.device == "cuda":
            # Return first option - we'll try fallbacks during load_model
            # Order: float16 (best quality) -> int8_float16 (good compatibility) -> int8 (fallback)
            return "float16"
        else:
            return "int8"  # Best for CPU

    def _get_cuda_compute_type_fallbacks(self) -> List[str]:
        """Get ordered list of compute types to try for CUDA, from best to worst"""
        return ["float16", "int8_float16", "int8"]
    
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
        Load the Whisper model with automatic GPU compute type fallback, then CPU fallback

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

            # If using CUDA, try compute types in order of efficiency
            if self.device == "cuda":
                compute_types_to_try = self._get_cuda_compute_type_fallbacks()

                # If user specified a specific compute type, try that first
                if self.compute_type != "auto" and self.compute_type not in compute_types_to_try:
                    compute_types_to_try.insert(0, self.compute_type)

                for compute_type in compute_types_to_try:
                    try:
                        logger.info(f"🔄 Trying CUDA with compute type: {compute_type}")
                        self.model = WhisperModel(
                            self.model_size,
                            device=self.device,
                            compute_type=compute_type,
                            download_root=str(models_dir)
                        )

                        # Success! Cache this compute type
                        self.compute_type = compute_type
                        self.is_loaded = True
                        logger.info(f"✅ Model loaded successfully on CUDA with {compute_type}: {self.model_size}")
                        return True

                    except Exception as compute_error:
                        logger.warning(f"⚠️ CUDA with {compute_type} failed: {compute_error}")
                        # Continue to next compute type
                        continue

                # All CUDA compute types failed, fall back to CPU
                logger.warning("⚠️ All CUDA compute types failed")
                logger.info("🔄 Falling back to CPU...")
                self.device = "cpu"
                self.compute_type = "int8"

            # Try loading with current device/compute_type (either CPU from start, or CPU fallback)
            try:
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=str(models_dir)
                )

                self.is_loaded = True
                if self._cuda_detected and self.device == "cpu":
                    logger.info(f"✅ Model loaded successfully on CPU (GPU fallback): {self.model_size}")
                else:
                    logger.info(f"✅ Model loaded successfully on {self.device.upper()}: {self.model_size}")
                return True

            except Exception as final_error:
                logger.error(f"❌ Final loading attempt failed: {final_error}")
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
            error_str = str(e)
            logger.error(f"❌ Transcription failed: {error_str}")
            import traceback
            logger.error(traceback.format_exc())

            # Check if this is a CUDA library error - if so, fall back to CPU
            if "cublas64_12.dll" in error_str or "cudnn" in error_str.lower() or "cuda" in error_str.lower():
                logger.warning("⚠️ CUDA library error detected - falling back to CPU...")

                # Force reload model on CPU and update both instance and original device
                self.device = "cpu"
                self.compute_type = "int8"
                self.is_loaded = False
                self._original_device = "cpu"  # Permanently switch to CPU
                self._cuda_detected = False  # Mark CUDA as unavailable

                try:
                    # Reload model on CPU
                    if self.load_model():
                        logger.info("✅ Model reloaded on CPU - retrying transcription...")
                        logger.info("💡 Device permanently switched to CPU due to missing CUDA libraries")
                        # Retry transcription on CPU
                        return self.transcribe_audio(audio_data, language, task)
                    else:
                        logger.error("❌ Failed to reload model on CPU")
                except Exception as cpu_error:
                    logger.error(f"❌ CPU fallback also failed: {cpu_error}")

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
