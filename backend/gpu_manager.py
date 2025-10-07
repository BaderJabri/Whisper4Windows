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

    # Check for BOTH cublas AND cudnn (both are required for GPU acceleration)
    critical_dlls = {
        "cublas": "nvidia/cublas/bin/cublas64*.dll",
        "cudnn": "nvidia/cudnn/bin/cudnn_ops64*.dll",  # Most critical cuDNN DLL
    }

    missing_libs = []
    found_dlls = {}

    for lib_name, pattern in critical_dlls.items():
        matching = list(gpu_dir.glob(pattern))
        if matching:
            found_dlls[lib_name] = str(matching[0])
            logger.info(f"✅ Found {lib_name}: {matching[0].name}")
        else:
            missing_libs.append(lib_name)
            logger.warning(f"❌ Missing {lib_name}: no DLLs matching {pattern}")

    if missing_libs:
        logger.warning(f"Missing critical CUDA libraries: {', '.join(missing_libs)}")
        return False

    logger.info(f"✅ All required GPU libraries present: {', '.join(found_dlls.keys())}")
    return True


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

            # Find pip executable - prefer system Python's pip over bundled app
            pip_cmd = None

            # Try to find pip in common locations
            pip_locations = [
                "pip",  # PATH
                sys.executable.replace(".exe", "") + "-m pip" if not getattr(sys, 'frozen', False) else None,
                "python -m pip",  # Fallback to python -m pip
                "py -m pip",  # Windows Python Launcher
            ]

            for pip_test in pip_locations:
                if pip_test is None:
                    continue
                try:
                    test_cmd = pip_test.split() + ["--version"]
                    result = subprocess.run(test_cmd, capture_output=True, timeout=5)
                    if result.returncode == 0:
                        pip_cmd = pip_test.split()
                        logger.info(f"✅ Found pip: {pip_test}")
                        break
                except Exception as e:
                    logger.debug(f"pip test failed for {pip_test}: {e}")
                    continue

            if not pip_cmd:
                logger.error("❌ Could not find pip executable")
                return False

            packages = list(CUDA_PACKAGES.keys())
            total_packages = len(packages)

            for idx, package in enumerate(packages):
                if progress_callback:
                    percent = 10 + (idx * 80 // total_packages)
                    progress_callback(percent, f"Downloading {package}...")

                logger.info(f"Installing {package}...")

                # Download package using pip with timeout (10 min for large cuDNN download)
                cmd = pip_cmd + [
                    "install",
                    "--target", str(temp_dir),
                    "--no-deps",
                    "--no-warn-script-location",
                    package
                ]

                logger.info(f"Running: {' '.join(cmd)}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout for large downloads
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )

                if result.returncode != 0:
                    logger.error(f"Failed to install {package}:")
                    logger.error(f"  stdout: {result.stdout}")
                    logger.error(f"  stderr: {result.stderr}")
                    return False

                logger.info(f"✅ {package} installed successfully")
                logger.debug(f"  stdout: {result.stdout[:200]}")

            if progress_callback:
                progress_callback(90, "Organizing libraries...")

            # Move nvidia folder from temp to gpu_libs
            temp_nvidia = temp_dir / "nvidia"
            target_nvidia = gpu_dir / "nvidia"

            if temp_nvidia.exists():
                if target_nvidia.exists():
                    shutil.rmtree(target_nvidia)
                shutil.move(str(temp_nvidia), str(target_nvidia))
                logger.info(f"✅ Moved libraries to: {target_nvidia}")
            else:
                logger.error(f"❌ nvidia folder not found in temp: {temp_nvidia}")
                return False

            # Verify installation before marking as complete
            if progress_callback:
                progress_callback(95, "Verifying installation...")

            if not are_gpu_libs_installed():
                logger.error("❌ Installation verification failed - missing required DLLs")
                logger.error("   This usually means cuDNN download failed (630MB file)")
                logger.error("   Try again with a stable internet connection")
                return False

            # Create marker file only after verification succeeds
            (gpu_dir / ".installed").touch()

            if progress_callback:
                progress_callback(100, "Installation complete!")

            logger.info("✅ GPU libraries installed and verified successfully")
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
