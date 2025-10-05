"""
PyInstaller build script for Whisper4Windows backend
This creates a standalone executable that includes Python and all dependencies
"""

import PyInstaller.__main__
import os
import sys

# Get the directory where this script is located
backend_dir = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    'main.py',
    '--name=whisper-backend',
    '--onefile',
    '--console',  # Show console for debugging
    '--icon=NONE',

    # Include necessary data files
    '--add-data=requirements.txt;.',

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
