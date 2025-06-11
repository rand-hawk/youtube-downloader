#!/usr/bin/env python3
"""
Minimal Build Script - Completely bypasses PyInstaller hooks
"""

import os
import subprocess
import sys
import shutil

def create_minimal_spec():
    """Create a minimal spec file that doesn't use any hooks"""
    
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Manually specify all imports without using hooks
a = Analysis(
    ['youtube-download-gui-v1.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('youtube-downloader.ico', '.'),
        ('config.json', '.'),
        ('youtube-downloader-icon.png', '.'),
        ('ffmpeg/ffmpeg.exe', 'ffmpeg'),
        ('ffmpeg/ffprobe.exe', 'ffmpeg'),
    ],
    hiddenimports=[
        # Core Python modules
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
        'io',
        
        # Network and image processing
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.cookies',
        'requests.exceptions',
        'requests.models',
        'requests.sessions',
        'requests.utils',
        'urllib3',
        'urllib3.connection',
        'urllib3.connectionpool',
        'urllib3.exceptions',
        'urllib3.poolmanager',
        'urllib3.response',
        'urllib3.util',
        'urllib3.util.retry',
        'urllib3.util.timeout',
        'urllib3.util.url',
        'certifi',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'pyperclip',
        
        # Concurrent processing
        'concurrent.futures',
        'concurrent.futures._base',
        
        # yt-dlp core (manually specified)
        'yt_dlp',
        'yt_dlp.extractor',
        'yt_dlp.downloader',
        'yt_dlp.postprocessor',
        'yt_dlp.utils',
        'yt_dlp.compat',
        
        # Essential yt-dlp extractors
        'yt_dlp.extractor.youtube',
        'yt_dlp.extractor.common',
        'yt_dlp.extractor.generic',
        
        # Essential downloaders
        'yt_dlp.downloader.http',
        'yt_dlp.downloader.fragment',
        'yt_dlp.downloader.external',
        
        # Essential postprocessors
        'yt_dlp.postprocessor.ffmpeg',
        'yt_dlp.postprocessor.common',
        
        # Crypto support
        'Cryptodome',
        'Cryptodome.Cipher',
        'Cryptodome.Cipher.AES',
        
        # Other essentials
        'mutagen',
        'brotli',
        'websockets',
    ],
    hookspath=[],  # Don't use any hooks
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude all problematic modules
        'pkg_resources',
        'pkg_resources.extern',
        'pkg_resources._vendor',
        'setuptools',
        'setuptools._vendor',
        'jaraco',
        'importlib_metadata',
        'zipp',
        'distutils',
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
    
    with open('minimal.spec', 'w') as f:
        f.write(spec_content)
    
    print("✓ Created minimal.spec file")

def build_minimal():
    """Build using the minimal spec"""
    
    print("🚀 Building with minimal approach...")
    
    # Create the spec file
    create_minimal_spec()
    
    # Build using the spec file
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "minimal.spec"
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
    if build_minimal():
        print("\n🎉 Minimal build completed successfully!")
        print("Executable location: dist/youtube-downloader-v1.0/")
    else:
        print("\n❌ Build failed")
        sys.exit(1)
