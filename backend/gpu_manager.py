"""
GPU Library Manager
Downloads and manages CUDA/cuDNN libraries for GPU acceleration
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict
import urllib.request
import zipfile
import shutil

logger = logging.getLogger(__name__)

# CUDA library download URLs (using nvidia-pyindex packages)
CUDA_PACKAGES = {
    "nvidia-cublas-cu12": "https://pypi.org/pypi/nvidia-cublas-cu12/json",
    "nvidia-cudnn-cu12": "https://pypi.org/pypi/nvidia-cudnn-cu12/json",
    "nvidia-cufft-cu12": "https://pypi.org/pypi/nvidia-cufft-cu12/json",
    "nvidia-curand-cu12": "https://pypi.org/pypi/nvidia-curand-cu12/json",
    "nvidia-cusolver-cu12": "https://pypi.org/pypi/nvidia-cusolver-cu12/json",
    "nvidia-cusparse-cu12": "https://pypi.org/pypi/nvidia-cusparse-cu12/json",
}


def get_gpu_libs_dir() -> Path:
    """Get the directory where GPU libraries are stored"""
    if getattr(sys, 'frozen', False):
        # Running as bundled executable - use AppData
        appdata = Path(os.getenv('APPDATA') or os.path.expanduser('~'))
        gpu_dir = appdata / 'Whisper4Windows' / 'gpu_libs'
    else:
        # Running from source - use local directory
        gpu_dir = Path("gpu_libs")

    gpu_dir.mkdir(parents=True, exist_ok=True)
    return gpu_dir


def is_gpu_available() -> bool:
    """Check if GPU (CUDA) is available on this system"""
    try:
        # Don't import ctranslate2 here - it triggers CUDA loading
        # Instead, check if NVIDIA GPU exists via Windows
        import subprocess
        result = subprocess.run(
            ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout.lower()
        return 'nvidia' in output or 'geforce' in output or 'quadro' in output
    except Exception as e:
        logger.debug(f"GPU check failed: {e}")
        return False


def are_gpu_libs_installed() -> bool:
    """Check if GPU libraries are already installed"""
    gpu_dir = get_gpu_libs_dir()

    # Check for marker file that indicates successful installation
    marker_file = gpu_dir / ".installed"
    if not marker_file.exists():
        return False

    # Verify nvidia directory exists and has content
    nvidia_dir = gpu_dir / "nvidia"
    if not nvidia_dir.exists():
        logger.warning(f"Missing nvidia directory")
        return False

    # Check for at least one critical DLL (cublas is most important)
    critical_patterns = [
        "nvidia/cublas/bin/cublas64*.dll",
        "nvidia/cudnn/bin/cudnn*.dll",
    ]

    found_dlls = []
    for pattern in critical_patterns:
        matching = list(gpu_dir.glob(pattern))
        if matching:
            found_dlls.append(pattern)
        else:
            logger.warning(f"No DLLs matching pattern: {pattern}")

    # Need at least cublas
    has_cublas = any("cublas" in p for p in found_dlls)

    if has_cublas:
        logger.info(f"✅ Found GPU libraries: {found_dlls}")
        return True
    else:
        logger.warning(f"Missing critical CUDA libraries")
        return False


def get_download_size() -> int:
    """Get estimated download size in bytes (approximate)"""
    # Approximate sizes for CUDA libraries
    return 600 * 1024 * 1024  # ~600MB


def install_gpu_libs(progress_callback=None) -> bool:
    """
    Download and install GPU libraries using pip

    Args:
        progress_callback: Optional callback function(percent, message)

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("📦 Installing GPU libraries...")
        gpu_dir = get_gpu_libs_dir()

        if progress_callback:
            progress_callback(5, "Preparing installation...")

        # Create temporary directory for pip downloads
        temp_dir = gpu_dir / "temp"
        temp_dir.mkdir(exist_ok=True)

        try:
            # Use pip to download packages
            import subprocess

            # Find pip executable - use python from PATH, not sys.executable (which might be bundled app)
            pip_cmd = "pip" if not getattr(sys, 'frozen', False) else "pip"

            packages = list(CUDA_PACKAGES.keys())
            total_packages = len(packages)

            for idx, package in enumerate(packages):
                if progress_callback:
                    percent = 10 + (idx * 80 // total_packages)
                    progress_callback(percent, f"Downloading {package}...")

                logger.info(f"Installing {package}...")

                # Download package using pip
                # Use 'pip' from PATH instead of sys.executable to avoid running the app .exe
                result = subprocess.run(
                    [pip_cmd, "install",
                     "--target", str(temp_dir),
                     "--no-deps",
                     "--no-warn-script-location",
                     package],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )

                if result.returncode != 0:
                    logger.error(f"Failed to install {package}:")
                    logger.error(f"  stdout: {result.stdout}")
                    logger.error(f"  stderr: {result.stderr}")
                    return False

                logger.info(f"✅ {package} installed successfully")

            if progress_callback:
                progress_callback(90, "Organizing libraries...")

            # Move nvidia folder from temp to gpu_libs
            temp_nvidia = temp_dir / "nvidia"
            target_nvidia = gpu_dir / "nvidia"

            if temp_nvidia.exists():
                if target_nvidia.exists():
                    shutil.rmtree(target_nvidia)
                shutil.move(str(temp_nvidia), str(target_nvidia))

            # Create marker file
            (gpu_dir / ".installed").touch()

            if progress_callback:
                progress_callback(100, "Installation complete!")

            logger.info("✅ GPU libraries installed successfully")
            return True

        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        logger.error(f"❌ Failed to install GPU libraries: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def uninstall_gpu_libs() -> bool:
    """Remove installed GPU libraries"""
    try:
        gpu_dir = get_gpu_libs_dir()
        if gpu_dir.exists():
            shutil.rmtree(gpu_dir)
            logger.info("✅ GPU libraries removed")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Failed to remove GPU libraries: {e}")
        return False


def get_gpu_info() -> Dict:
    """Get information about GPU and library status"""
    return {
        "gpu_available": is_gpu_available(),
        "libs_installed": are_gpu_libs_installed(),
        "libs_dir": str(get_gpu_libs_dir()),
        "estimated_download_size_mb": get_download_size() // (1024 * 1024)
    }
