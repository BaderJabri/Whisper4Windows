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
# Added CUDA runtime packages for full GPU support (fixes CUDNN_STATUS_EXECUTION_FAILED on GTX 1060)
CUDA_PACKAGES = {
    "nvidia-cublas-cu12": "https://pypi.org/pypi/nvidia-cublas-cu12/json",
    "nvidia-cudnn-cu12": "https://pypi.org/pypi/nvidia-cudnn-cu12/json",
    "nvidia-cufft-cu12": "https://pypi.org/pypi/nvidia-cufft-cu12/json",
    "nvidia-curand-cu12": "https://pypi.org/pypi/nvidia-curand-cu12/json",
    "nvidia-cusolver-cu12": "https://pypi.org/pypi/nvidia-cusolver-cu12/json",
    "nvidia-cusparse-cu12": "https://pypi.org/pypi/nvidia-cusparse-cu12/json",
    "nvidia-cuda-runtime-cu12": "https://pypi.org/pypi/nvidia-cuda-runtime-cu12/json",
    "nvidia-cuda-nvrtc-cu12": "https://pypi.org/pypi/nvidia-cuda-nvrtc-cu12/json",
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
    """Check if GPU (CUDA) is available on this system.

    Uses multiple detection methods with fallback chain:
    1. PowerShell Get-CimInstance (works on all modern Windows)
    2. nvidia-smi (works if NVIDIA drivers are installed)
    3. wmic (legacy fallback for older Windows versions)
    """
    import subprocess

    def _check_nvidia(output: str) -> bool:
        text = output.lower()
        return 'nvidia' in text or 'geforce' in text or 'quadro' in text or 'rtx' in text

    # Method 1: PowerShell Get-CimInstance (recommended, works on Windows 10/11)
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             '(Get-CimInstance Win32_VideoController).Name'],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        if result.returncode == 0 and _check_nvidia(result.stdout):
            logger.info(f"GPU detected via Get-CimInstance: {result.stdout.strip()}")
            return True
    except Exception as e:
        logger.debug(f"Get-CimInstance GPU check failed: {e}")

    # Method 2: nvidia-smi (works if NVIDIA drivers are installed)
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        if result.returncode == 0 and result.stdout.strip():
            logger.info(f"GPU detected via nvidia-smi: {result.stdout.strip()}")
            return True
    except Exception as e:
        logger.debug(f"nvidia-smi GPU check failed: {e}")

    # Method 3: wmic (legacy fallback, removed in Windows 11 24H2+)
    try:
        result = subprocess.run(
            ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        if result.returncode == 0 and _check_nvidia(result.stdout):
            logger.info(f"GPU detected via wmic: {result.stdout.strip()}")
            return True
    except Exception as e:
        logger.debug(f"wmic GPU check failed: {e}")

    logger.warning("No NVIDIA GPU detected by any method")
    return False


def check_library_status() -> Dict[str, any]:
    """Check detailed status of each GPU library

    Returns:
        Dict with library names as keys and status info as values
    """
    gpu_dir = get_gpu_libs_dir()
    nvidia_dir = gpu_dir / "nvidia"

    # Map package names to their subdirectory and DLL patterns
    # Using broader patterns to catch all DLL variants (e.g., cudnn_ops64_9.dll, cudnn64_9.dll)
    library_checks = {
        "nvidia-cublas-cu12": ("cublas", "cublas*.dll"),
        "nvidia-cudnn-cu12": ("cudnn", "cudnn*.dll"),
        "nvidia-cufft-cu12": ("cufft", "cufft*.dll"),
        "nvidia-curand-cu12": ("curand", "curand*.dll"),
        "nvidia-cusolver-cu12": ("cusolver", "cusolver*.dll"),
        "nvidia-cusparse-cu12": ("cusparse", "cusparse*.dll"),
        "nvidia-cuda-runtime-cu12": ("cuda_runtime", "cudart*.dll"),
        "nvidia-cuda-nvrtc-cu12": ("cuda_nvrtc", "nvrtc*.dll"),
    }

    status = {}
    for package_name, (subdir, dll_pattern) in library_checks.items():
        # Check multiple possible locations for DLLs
        lib_subdir = nvidia_dir / subdir

        if not lib_subdir.exists():
            logger.warning(f"❌ Missing {package_name} (checked pip and file system)")
            status[package_name] = {"installed": False, "reason": "not_found"}
            continue

        # Look for DLLs in common locations: bin/, lib/, or root of subdir
        dlls = []
        search_paths = [
            lib_subdir / "bin",
            lib_subdir / "lib",
            lib_subdir
        ]

        for search_path in search_paths:
            if search_path.exists():
                found_dlls = list(search_path.glob(dll_pattern))
                if found_dlls:
                    dlls.extend(found_dlls)
                    break

        # Also recursively search for DLLs as fallback
        if not dlls:
            dlls = list(lib_subdir.rglob(dll_pattern))

        if dlls:
            logger.info(f"✅ Found {package_name} DLLs: {', '.join(d.name for d in dlls)}")
            status[package_name] = {
                "installed": True,
                "dlls": [d.name for d in dlls]
            }
        else:
            logger.warning(f"❌ Missing {package_name} (directory exists but no DLLs matching {dll_pattern})")
            status[package_name] = {"installed": False, "reason": "no_dlls"}

    return status


def are_gpu_libs_installed() -> bool:
    """Check if GPU libraries are already installed"""
    status = check_library_status()

    # All libraries must be installed
    all_installed = all(lib["installed"] for lib in status.values())

    if not all_installed:
        missing = [name for name, info in status.items() if not info["installed"]]
        logger.warning(f"❌ Missing GPU libraries: {', '.join(missing)}")
        return False

    logger.info(f"✅ All required GPU libraries present")
    return True


def get_download_size() -> int:
    """Get estimated download size in bytes (approximate)"""
    # Approximate sizes for CUDA libraries (8 packages total)
    return 700 * 1024 * 1024  # ~700MB


def _get_wheel_url(pypi_json_url: str, package_name: str) -> Optional[str]:
    """Query PyPI JSON API to find the Windows x86_64 wheel download URL.

    Args:
        pypi_json_url: PyPI JSON API endpoint (e.g. https://pypi.org/pypi/nvidia-cublas-cu12/json)
        package_name: Package name for logging

    Returns:
        Download URL for the .whl file, or None if not found
    """
    import json

    try:
        logger.info(f"🔍 Querying PyPI for {package_name}...")
        req = urllib.request.Request(pypi_json_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())

        # Get the latest version's files
        latest_version = data.get("info", {}).get("version", "")
        releases = data.get("releases", {})
        files = releases.get(latest_version, [])

        if not files:
            # Fallback: try urls from the root level
            files = data.get("urls", [])

        # Find the Windows x86_64 wheel
        for file_info in files:
            filename = file_info.get("filename", "")
            if filename.endswith(".whl") and ("win_amd64" in filename or "win64" in filename):
                url = file_info.get("url", "")
                size_mb = file_info.get("size", 0) / (1024 * 1024)
                logger.info(f"   Found: {filename} ({size_mb:.1f} MB)")
                return url

        # If no platform-specific wheel, try any wheel (some packages are pure Python)
        for file_info in files:
            filename = file_info.get("filename", "")
            if filename.endswith(".whl") and "any" in filename:
                url = file_info.get("url", "")
                logger.info(f"   Found (universal): {filename}")
                return url

        logger.error(f"❌ No Windows wheel found for {package_name} v{latest_version}")
        return None

    except Exception as e:
        logger.error(f"❌ Failed to query PyPI for {package_name}: {e}")
        return None


def _download_file(url: str, dest: Path, progress_callback=None, progress_label: str = "") -> bool:
    """Download a file from URL to dest with optional progress reporting.

    Args:
        url: URL to download
        dest: Destination file path
        progress_callback: Optional callback function(percent, message)
        progress_label: Label to show in progress messages

    Returns:
        True if successful, False otherwise
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Whisper4Windows/1.0"})
        with urllib.request.urlopen(req, timeout=600) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 256 * 1024  # 256 KB chunks

            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0 and progress_callback and progress_label:
                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        logger.debug(f"   {progress_label}: {mb_done:.1f}/{mb_total:.1f} MB")

        logger.info(f"   ✅ Downloaded {dest.name} ({downloaded / (1024 * 1024):.1f} MB)")
        return True

    except Exception as e:
        logger.error(f"   ❌ Download failed: {e}")
        if dest.exists():
            dest.unlink()
        return False


def install_gpu_libs(progress_callback=None) -> bool:
    """
    Download and install GPU libraries directly from PyPI.

    Downloads NVIDIA CUDA wheel packages (.whl) via HTTP, extracts the DLLs,
    and places them in the gpu_libs directory. Does NOT require pip or Python
    to be installed on the system — works from within a PyInstaller bundle.

    Args:
        progress_callback: Optional callback function(percent, message)

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("📦 Checking which GPU libraries need to be installed...")
        gpu_dir = get_gpu_libs_dir()

        # Check which libraries are already installed
        current_status = check_library_status()
        packages_to_install = [pkg for pkg, status in current_status.items() if not status.get("installed", False)]

        if not packages_to_install:
            logger.info("✅ All GPU libraries already installed")
            return True

        logger.info(f"📦 Need to install {len(packages_to_install)} libraries: {', '.join(packages_to_install)}")

        if progress_callback:
            progress_callback(5, "Preparing installation...")

        # Create temporary directory for downloads
        temp_dir = gpu_dir / "temp"
        temp_dir.mkdir(exist_ok=True)

        try:
            total_packages = len(packages_to_install)

            # Download and extract each package
            package_dirs = []

            for idx, package in enumerate(packages_to_install):
                if progress_callback:
                    percent = 5 + (idx * 75 // total_packages)
                    progress_callback(percent, f"Downloading {package}...")

                logger.info(f"📥 [{idx + 1}/{total_packages}] Downloading {package}...")

                # Step 1: Get wheel URL from PyPI
                pypi_url = CUDA_PACKAGES.get(package)
                if not pypi_url:
                    logger.error(f"❌ No PyPI URL configured for {package}")
                    return False

                wheel_url = _get_wheel_url(pypi_url, package)
                if not wheel_url:
                    logger.error(f"❌ Could not find download URL for {package}")
                    return False

                # Step 2: Download the .whl file
                whl_filename = wheel_url.split("/")[-1].split("#")[0]
                whl_path = temp_dir / whl_filename

                if not _download_file(wheel_url, whl_path, progress_callback, package):
                    logger.error(f"❌ Failed to download {package}")
                    return False

                # Step 3: Extract the wheel (it's a ZIP file)
                extract_dir = temp_dir / f"pkg_{idx}_{package.replace('-', '_')}"
                extract_dir.mkdir(exist_ok=True)
                package_dirs.append(extract_dir)

                try:
                    with zipfile.ZipFile(whl_path, 'r') as zf:
                        zf.extractall(extract_dir)
                    logger.info(f"   ✅ Extracted {whl_filename}")
                except zipfile.BadZipFile:
                    logger.error(f"   ❌ Corrupted download for {package}")
                    return False

                # Remove the .whl file to free disk space
                whl_path.unlink()

                logger.info(f"✅ {package} downloaded and extracted")

            if progress_callback:
                progress_callback(85, "Organizing libraries...")

            # Merge all package nvidia directories into target
            target_nvidia = gpu_dir / "nvidia"
            target_nvidia.mkdir(parents=True, exist_ok=True)

            logger.info(f"📦 Merging libraries from {len(package_dirs)} packages to {target_nvidia}")

            # Process each package directory
            for pkg_dir in package_dirs:
                pkg_nvidia = pkg_dir / "nvidia"

                if not pkg_nvidia.exists():
                    logger.warning(f"⚠️ No nvidia folder in {pkg_dir.name}, skipping")
                    continue

                # Log what we're about to merge
                subdirs = [item.name for item in pkg_nvidia.iterdir() if item.is_dir()]
                logger.info(f"   From {pkg_dir.name}: {', '.join(subdirs) if subdirs else 'no subdirectories'}")

                # Collect all subdirectories from this package
                for item in pkg_nvidia.iterdir():
                    if not item.is_dir():
                        continue

                    src = item
                    dst = target_nvidia / item.name

                    try:
                        if dst.exists():
                            logger.info(f"      Replacing existing {item.name}")
                            shutil.rmtree(dst)
                        # Copy the directory (use copytree instead of move)
                        shutil.copytree(str(src), str(dst))
                        logger.info(f"   ✅ Copied: {item.name}")
                    except Exception as e:
                        logger.error(f"   ❌ Failed to copy {item.name}: {e}")
                        return False

            logger.info(f"✅ Merged all libraries to: {target_nvidia}")

            # Log final library structure
            logger.info(f"📋 Final library structure:")
            for subdir in target_nvidia.iterdir():
                if subdir.is_dir():
                    bin_dir = subdir / "bin"
                    if bin_dir.exists():
                        dll_count = len(list(bin_dir.glob("*.dll")))
                        logger.info(f"   {subdir.name}: {dll_count} DLLs")
                    else:
                        logger.info(f"   {subdir.name}: NO BIN DIRECTORY!")

            # Verify installation before marking as complete
            if progress_callback:
                progress_callback(95, "Verifying installation...")

            # Re-check library status
            final_status = check_library_status()
            missing = [pkg for pkg, status in final_status.items() if not status.get("installed", False)]

            if missing:
                logger.error("❌ Installation verification failed - some libraries still missing")
                logger.error(f"   Missing: {', '.join(missing)}")
                logger.error("   Try running the installation again")
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
    gpu_available = is_gpu_available()
    library_status = check_library_status() if gpu_available else {}
    all_installed = are_gpu_libs_installed() if gpu_available else False

    # Get list of missing libraries
    missing_libraries = [name for name, info in library_status.items() if not info.get("installed", False)]

    return {
        "gpu_available": gpu_available,
        "libs_installed": all_installed,
        "library_status": library_status,
        "missing_libraries": missing_libraries,
        "libs_dir": str(get_gpu_libs_dir()),
        "estimated_download_size_mb": get_download_size() // (1024 * 1024)
    }
