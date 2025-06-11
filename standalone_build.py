#!/usr/bin/env python3
"""
Standalone Build Script - No yt-dlp packaging issues
"""

import os
import subprocess
import sys
import shutil
import requests

def download_ytdlp():
    """Download yt-dlp executable"""
    try:
        print("📥 Downloading yt-dlp...")
        
        ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        ytdlp_path = "yt-dlp.exe"
        
        response = requests.get(ytdlp_url, stream=True)
        response.raise_for_status()
        
        with open(ytdlp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print("✓ yt-dlp downloaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to download yt-dlp: {e}")
        return False

def create_standalone_spec():
    """Create spec file for standalone version"""
    
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['youtube-downloader-standalone.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('youtube-downloader.ico', '.'),
        ('config.json', '.'),
        ('youtube-downloader-icon.png', '.'),
        ('ffmpeg/ffmpeg.exe', 'ffmpeg'),
        ('ffmpeg/ffprobe.exe', 'ffmpeg'),
        ('yt-dlp.exe', '.'),  # Include yt-dlp executable
    ],
    hiddenimports=[
        # Only basic modules needed
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'threading',
        'json',
        'subprocess',
        'signal',
        'time',
        're',
        'os',
        'sys',
        'tempfile',
        'shutil',
        'pathlib',
        'requests',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'pyperclip',
        'concurrent.futures',
        'concurrent.futures._base',
        'concurrent.futures.thread',
        'io',
        'urllib.parse',
        'urllib.request',
        'urllib.error',
        'http.client',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude everything we don't need
        'yt_dlp',  # We use subprocess instead
        'pkg_resources',
        'setuptools',
        'jaraco',
        'importlib_metadata',
        'zipp',
        'distutils',
        'numpy',
        'scipy',
        'matplotlib',
        'pandas',
        'sklearn',
        'tensorflow',
        'torch',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='youtube-downloader-v1.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='youtube-downloader.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='youtube-downloader-v1.0',
)
'''
    
    with open('standalone.spec', 'w') as f:
        f.write(spec_content)
    
    print("✓ Created standalone.spec file")

def build_standalone():
    """Build the standalone version"""
    
    print("🚀 Building standalone version...")
    
    # Download yt-dlp first
    if not download_ytdlp():
        return False
    
    # Create the spec file
    create_standalone_spec()
    
    # Build using the spec file
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "standalone.spec"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("✓ Build successful!")
            print("Output:", result.stdout[-500:])  # Last 500 chars
            return True
        else:
            print("❌ Build failed!")
            print("Error:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False

if __name__ == "__main__":
    if build_standalone():
        print("\n🎉 Standalone build completed successfully!")
        print("Executable location: dist/youtube-downloader-v1.0/")
        print("\nThis version uses yt-dlp as a subprocess, avoiding all packaging issues!")
    else:
        print("\n❌ Build failed")
        sys.exit(1)
