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

# CUDA libraries are now downloaded on-demand by gpu_manager.py
# We no longer bundle them to keep installer small (~200MB instead of ~1.3GB)
print("INFO: CUDA libraries will be downloaded on first run if GPU is detected")
print("INFO: This keeps the installer size small (~200MB vs ~1.3GB)")

binary_includes = []

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
