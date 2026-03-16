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
            Path(sys._MEIPASS) / "nvidia" / "cuda_runtime" / "bin",
            Path(sys._MEIPASS) / "nvidia" / "cuda_nvrtc" / "bin",
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
            gpu_libs_dir / "nvidia" / "cuda_runtime" / "bin",
            gpu_libs_dir / "nvidia" / "cuda_nvrtc" / "bin",
        ])

    # System CUDA installation (dynamic detection for any device)
    # Check Program Files (x86) and Program Files directories
    program_files_dirs = [
        Path(os.environ.get('ProgramFiles', r'C:\Program Files')),
        Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')),
    ]
    
    for program_files in program_files_dirs:
        if not program_files.exists():
            continue
            
        # Check NVIDIA GPU Computing Toolkit
        cuda_toolkit = program_files / "NVIDIA GPU Computing Toolkit" / "CUDA"
        if cuda_toolkit.exists():
            logger.info(f"🔍 Found CUDA toolkit: {cuda_toolkit}")
            for cuda_version_dir in cuda_toolkit.iterdir():
                if cuda_version_dir.is_dir() and cuda_version_dir.name.startswith('v'):
                    bin_path = cuda_version_dir / "bin"
                    if bin_path.exists():
                        cuda_paths.append(bin_path)
                        logger.info(f"   ✅ Added CUDA version: {cuda_version_dir.name}")
        
        # Check NVIDIA cuDNN - prioritize system installation
        cudnn_dir = program_files / "NVIDIA" / "CUDNN"
        if cudnn_dir.exists():
            logger.info(f"🔍 Found system cuDNN directory: {cudnn_dir}")
            for cudnn_version_dir in cudnn_dir.iterdir():
                if cudnn_version_dir.is_dir() and cudnn_version_dir.name.startswith('v'):
                    bin_path = cudnn_version_dir / "bin"
                    if bin_path.exists():
                        cuda_paths.append(bin_path)
                        logger.info(f"   ✅ Added system cuDNN version: {cudnn_version_dir.name}")
    
    # Also check common alternative locations
    alternative_paths = [
        Path(os.environ.get('CUDA_PATH', '')),
        Path(os.environ.get('CUDA_HOME', '')),
        Path(os.environ.get('CUDNN_PATH', '')),
    ]
    
    for alt_path in alternative_paths:
        if alt_path and alt_path.exists():
            bin_path = alt_path / "bin"
            if bin_path.exists():
                cuda_paths.append(bin_path)
                logger.info(f"✅ Found CUDA in environment variable: {alt_path}")

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

PUNCTUATION_PROMPTS = {
    "en": "Hello, how are you? I'm doing well, thank you. Let me explain: first, we need to analyze the data; second, we must prepare the report. Isn't that right? Yes, absolutely! Let's proceed.",
    "it": "Buongiorno, come stai? Sto bene, grazie. Ti spiego: primo, dobbiamo analizzare i dati; secondo, preparare il report. Non è così? Sì, esattamente! Procediamo.",
    "es": "Buenos días, ¿cómo estás? Estoy bien, gracias. Te explico: primero, debemos analizar los datos; segundo, preparar el informe. ¿No es así? ¡Sí, exactamente! Procedamos.",
    "fr": "Bonjour, comment allez-vous ? Je vais bien, merci. Laissez-moi vous expliquer : premièrement, nous devons analyser les données ; deuxièmement, préparer le rapport. N'est-ce pas ? Oui, absolument ! Procédons.",
    "de": "Guten Tag, wie geht es Ihnen? Mir geht es gut, danke. Lassen Sie mich erklären: Erstens müssen wir die Daten analysieren; zweitens den Bericht vorbereiten. Nicht wahr? Ja, genau! Lassen Sie uns fortfahren.",
    "pt": "Bom dia, como você está? Estou bem, obrigado. Deixe-me explicar: primeiro, precisamos analisar os dados; segundo, preparar o relatório. Não é? Sim, exatamente! Vamos prosseguir.",
    "ja": "こんにちは、お元気ですか？元気です、ありがとうございます。説明させてください。まず、データを分析する必要があります。次に、レポートを準備しなければなりません。そうですよね？はい、その通りです！進めましょう。",
    "zh": "你好，你好吗？我很好，谢谢。让我解释一下：第一，我们需要分析数据；第二，我们必须准备报告。不是吗？是的，没错！我们继续吧。",
    "ko": "안녕하세요, 어떻게 지내세요? 잘 지내고 있습니다, 감사합니다. 설명하겠습니다: 첫째, 데이터를 분석해야 합니다. 둘째, 보고서를 준비해야 합니다. 그렇지 않나요? 네, 맞습니다! 진행합시다.",
    "ru": "Здравствуйте, как дела? Хорошо, спасибо. Позвольте объяснить: во-первых, нам нужно проанализировать данные; во-вторых, подготовить отчёт. Не так ли? Да, именно! Давайте продолжим.",
    "ar": "مرحباً، كيف حالك؟ أنا بخير، شكراً. دعني أوضح: أولاً، نحتاج إلى تحليل البيانات؛ ثانياً، يجب إعداد التقرير. أليس كذلك؟ نعم، بالضبط! لنتابع.",
    "nl": "Goedendag, hoe gaat het? Goed, dank u. Laat me uitleggen: ten eerste moeten we de gegevens analyseren; ten tweede het rapport voorbereiden. Nietwaar? Ja, precies! Laten we doorgaan.",
    "pl": "Dzień dobry, jak się masz? Dobrze, dziękuję. Pozwól, że wyjaśnię: po pierwsze, musimy przeanalizować dane; po drugie, przygotować raport. Czyż nie? Tak, dokładnie! Kontynuujmy.",
    "default": "Hello, how are you? I'm doing well, thank you. Let me explain: first, we need to analyze the data; second, we must prepare the report. Isn't that right? Yes, absolutely! Let's proceed.",
}

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
        task: str = "transcribe",
        transcription_mode: str = "quality",
        enhanced_punctuation: bool = True,
        context_prompt: Optional[str] = None
    ) -> Dict:
        """
        Transcribe audio data

        Args:
            audio_data: Audio data as numpy array (float32, mono, 16kHz)
            language: Language code (e.g., 'en', 'es') or None for auto-detect
            task: 'transcribe' or 'translate'
            transcription_mode: 'fast', 'balanced', or 'quality'
            enhanced_punctuation: inject language-specific punctuation prompt
            context_prompt: custom initial_prompt (overrides enhanced_punctuation)

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

            MODE_PARAMS = {
                "fast":     {"beam_size": 1, "condition_on_previous_text": False},
                "balanced": {"beam_size": 3, "condition_on_previous_text": True},
                "quality":  {"beam_size": 5, "condition_on_previous_text": True},
            }
            params = MODE_PARAMS.get(transcription_mode, MODE_PARAMS["quality"])

            initial_prompt = None
            if context_prompt:
                initial_prompt = context_prompt
            elif enhanced_punctuation:
                initial_prompt = PUNCTUATION_PROMPTS.get(language, PUNCTUATION_PROMPTS["default"])

            logger.info(f"   Mode: {transcription_mode} (beam_size={params['beam_size']}, condition_on_previous={params['condition_on_previous_text']})")
            if initial_prompt:
                logger.info(f"   Initial prompt: {initial_prompt[:60]}...")

            segments, info = self.model.transcribe(
                audio_data,
                language=language,
                task=task,
                beam_size=params["beam_size"],
                condition_on_previous_text=params["condition_on_previous_text"],
                temperature=0.0,
                vad_filter=False,
                initial_prompt=initial_prompt,
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
