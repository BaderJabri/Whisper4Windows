"""
Audio Capture Module
Handles microphone and system audio recording using sounddevice (WASAPI)
"""

import logging
import numpy as np
import sounddevice as sd
from typing import List, Dict, Optional, Callable
import queue
import wave
import io

logger = logging.getLogger(__name__)

class AudioDevice:
    """Represents an audio device"""
    def __init__(self, index: int, name: str, channels: int, sample_rate: float, is_default: bool, device_type: str):
        self.index = index
        self.name = name
        self.channels = channels
        self.sample_rate = sample_rate
        self.is_default = is_default
        self.type = device_type  # "input" or "output"

    def to_dict(self) -> Dict:
        return {
            "id": str(self.index),
            "name": self.name,
            "is_default": self.is_default,
            "type": self.type,
            "channels": self.channels,
            "sample_rate": int(self.sample_rate)
        }


class AudioCapture:
    """Handles audio recording and device management"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._is_recording = False
        self.audio_queue = queue.Queue()
        self.stream = None
    
    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self._is_recording
        
    def get_devices(self) -> Dict[str, List[AudioDevice]]:
        """Get all available audio devices"""
        logger.info("Scanning for audio devices...")
        
        try:
            devices = sd.query_devices()
            default_input = sd.default.device[0]
            default_output = sd.default.device[1]
            
            input_devices = []
            output_devices = []
            
            for idx, device in enumerate(devices):
                # Input devices
                if device['max_input_channels'] > 0:
                    audio_dev = AudioDevice(
                        index=idx,
                        name=device['name'],
                        channels=device['max_input_channels'],
                        sample_rate=device['default_samplerate'],
                        is_default=(idx == default_input),
                        device_type="input"
                    )
                    input_devices.append(audio_dev)
                    logger.info(f"Found input device: {device['name']} (index: {idx})")
                
                # Output devices (for loopback)
                if device['max_output_channels'] > 0:
                    audio_dev = AudioDevice(
                        index=idx,
                        name=device['name'],
                        channels=device['max_output_channels'],
                        sample_rate=device['default_samplerate'],
                        is_default=(idx == default_output),
                        device_type="output"
                    )
                    output_devices.append(audio_dev)
                    logger.info(f"Found output device: {device['name']} (index: {idx})")
            
            return {
                "inputs": input_devices,
                "outputs": output_devices
            }
            
        except Exception as e:
            logger.error(f"Error getting audio devices: {e}")
            return {"inputs": [], "outputs": []}
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio stream"""
        if status:
            logger.warning(f"⚠️ Audio callback status: {status}")
        
        try:
            # Put audio data in queue
            self.audio_queue.put(indata.copy())
            # Log occasionally to confirm audio is flowing
            if self.audio_queue.qsize() % 10 == 0:
                logger.info(f"📊 Audio queue size: {self.audio_queue.qsize()}")
        except Exception as e:
            logger.error(f"❌ Audio callback error: {e}")
    
    def start_recording(self, device_index: Optional[int] = None, duration: Optional[float] = None):
        """
        Start recording audio
        
        Args:
            device_index: Index of the device to use (None = default)
            duration: Recording duration in seconds (None = infinite)
        """
        if self._is_recording:
            logger.warning("Already recording!")
            return False
        
        try:
            logger.info(f"Starting recording on device {device_index or 'default'}...")
            
            self.stream = sd.InputStream(
                device=device_index,
                channels=self.channels,
                samplerate=self.sample_rate,
                callback=self._audio_callback,
                dtype=np.float32
            )
            
            self.stream.start()
            self._is_recording = True
            logger.info("✅ Recording started")
            return True
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            self._is_recording = False
            return False
    
    def clear_queue(self):
        """Clear the audio queue"""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        logger.info("✓ Audio queue cleared")
    
    def get_audio_chunk(self, min_duration: float = 0.5) -> Optional[np.ndarray]:
        """
        Get accumulated audio chunks from queue
        
        Args:
            min_duration: Minimum duration in seconds before returning audio
            
        Returns:
            numpy array of audio data, or None if not enough audio
        """
        audio_chunks = []
        
        # Get all available chunks from queue
        while not self.audio_queue.empty():
            try:
                chunk = self.audio_queue.get_nowait()
                audio_chunks.append(chunk)
            except queue.Empty:
                break
        
        if not audio_chunks:
            return None
        
        # Concatenate chunks
        audio_data = np.concatenate(audio_chunks, axis=0)
        
        # Check if we have enough audio
        duration = len(audio_data) / self.sample_rate
        if duration < min_duration:
            # Not enough audio yet, put it back
            self.audio_queue.put(audio_data)
            return None
        
        return audio_data
    
    def stop_recording(self) -> Optional[np.ndarray]:
        """
        Stop recording and return the audio data
        
        Returns:
            numpy array of audio data, or None if error
        """
        if not self._is_recording:
            logger.warning("Not recording!")
            return None
        
        try:
            logger.info("Stopping recording...")
            
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            # Get all audio chunks from queue
            audio_chunks = []
            while not self.audio_queue.empty():
                audio_chunks.append(self.audio_queue.get())
            
            self._is_recording = False
            
            if audio_chunks:
                audio_data = np.concatenate(audio_chunks, axis=0)
                logger.info(f"✅ Recorded {len(audio_data) / self.sample_rate:.2f} seconds of audio")
                return audio_data
            else:
                logger.warning("No audio data captured")
                return None
                
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            self._is_recording = False
            return None
    
    def save_wav(self, audio_data: np.ndarray, filename: str):
        """Save audio data to WAV file"""
        try:
            logger.info(f"Audio data shape: {audio_data.shape}, dtype: {audio_data.dtype}")
            logger.info(f"Audio data range: min={audio_data.min():.4f}, max={audio_data.max():.4f}")
            
            # Flatten if needed (remove extra dimensions)
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            # Ensure audio is in correct format
            if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
                # Convert float32 to int16, ensuring proper scaling
                # Clip to [-1, 1] range first
                audio_data = np.clip(audio_data, -1.0, 1.0)
                # Convert to int16
                audio_data = (audio_data * 32767).astype(np.int16)
            elif audio_data.dtype != np.int16:
                # Convert other types to int16
                audio_data = audio_data.astype(np.int16)
            
            logger.info(f"Converted audio data: shape={audio_data.shape}, dtype={audio_data.dtype}")
            logger.info(f"Converted range: min={audio_data.min()}, max={audio_data.max()}")
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 2 bytes for int16
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
            
            logger.info(f"✅ Saved audio to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving WAV file: {e}")
            return False
    
    def record_for_duration(self, duration: float, device_index: Optional[int] = None) -> Optional[np.ndarray]:
        """
        Record audio for a specific duration
        
        Args:
            duration: Duration in seconds
            device_index: Device to use (None = default)
            
        Returns:
            Audio data as numpy array
        """
        logger.info(f"Recording for {duration} seconds from device {device_index or 'default'}...")
        
        # Log device info
        try:
            if device_index is not None:
                device_info = sd.query_devices(device_index)
                logger.info(f"Using device: {device_info['name']}")
            else:
                default_device = sd.query_devices(kind='input')
                logger.info(f"Using default device: {default_device['name']}")
        except Exception as e:
            logger.warning(f"Could not get device info: {e}")
        
        try:
            # Record audio
            logger.info("Starting recording...")
            recording = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                device=device_index,
                dtype=np.float32
            )
            
            logger.info(f"Recording in progress for {duration} seconds...")
            sd.wait()  # Wait until recording is finished
            
            # Check if we got any audio
            logger.info(f"Recording complete. Shape: {recording.shape}, dtype: {recording.dtype}")
            logger.info(f"Audio level: min={recording.min():.6f}, max={recording.max():.6f}, mean={np.abs(recording).mean():.6f}")
            
            # Check if recording is too quiet
            if np.abs(recording).max() < 0.001:
                logger.warning("⚠️ WARNING: Recording is very quiet or silent! Check microphone permissions and volume.")
            
            return recording
            
        except Exception as e:
            logger.error(f"Error during timed recording: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None


# Global audio capture instance
_audio_capture = None

def get_audio_capture() -> AudioCapture:
    """Get or create the global audio capture instance"""
    global _audio_capture
    if _audio_capture is None:
        _audio_capture = AudioCapture()
    return _audio_capture
