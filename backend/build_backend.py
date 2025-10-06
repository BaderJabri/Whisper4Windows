"""
PyInstaller build script for Whisper4Windows backend
This creates a standalone executable that includes Python and all dependencies
"""

import PyInstaller.__main__
import os
import sys
from pathlib import Path

# Get the directory where this script is located
backend_dir = os.path.dirname(os.path.abspath(__file__))

# Find NVIDIA CUDA libraries in site-packages
venv_site_packages = Path(backend_dir) / "venv" / "Lib" / "site-packages"
nvidia_dir = venv_site_packages / "nvidia"

# Build list of binary includes for CUDA libraries
binary_includes = []
if nvidia_dir.exists():
    for lib_name in ['cublas', 'cudnn', 'cufft', 'curand', 'cusolver', 'cusparse']:
        lib_bin = nvidia_dir / lib_name / "bin"
        if lib_bin.exists():
            # Add all DLLs from this library's bin folder
            for dll in lib_bin.glob("*.dll"):
                # Format: source;destination
                binary_includes.append(f'--add-binary={dll};nvidia/{lib_name}/bin')
                print(f"Including CUDA DLL: {dll.name}")

PyInstaller.__main__.run([
    'main.py',
    '--name=whisper-backend',
    '--onefile',
    '--console',  # Show console for debugging
    '--icon=NONE',

    # Include necessary data files
    '--add-data=requirements.txt;.',

    # Include NVIDIA CUDA DLLs
    *binary_includes,

    # Hidden imports that PyInstaller might miss
    '--hidden-import=faster_whisper',
    '--hidden-import=ctranslate2',
    '--hidden-import=sounddevice',
    '--hidden-import=numpy',
    '--hidden-import=uvicorn',
    '--hidden-import=fastapi',
    '--hidden-import=pydantic',

    # Exclude unnecessary packages to reduce size
    '--exclude-module=matplotlib',
    '--exclude-module=tkinter',

    # Output directory
    f'--distpath={os.path.join(backend_dir, "dist")}',
    f'--workpath={os.path.join(backend_dir, "build")}',
    f'--specpath={backend_dir}',
])
