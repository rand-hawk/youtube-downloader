#!/usr/bin/env python3
"""
Hybrid Build Script - Includes yt-dlp but avoids problematic hooks
"""

import os
import subprocess
import sys
import shutil

def create_hybrid_spec():
    """Create a hybrid spec file that includes yt-dlp but avoids problematic modules"""
    
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Custom analysis that includes yt-dlp but excludes problematic modules
a = Analysis(
    ['youtube-download-gui-v1.py'],
    pathex=['.'],
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
        'platform',
        'locale',
        'tempfile',
        'shutil',
        'pathlib',
        'urllib.parse',
        'urllib.request',
        'urllib.error',
        'http.client',
        'http.cookiejar',
        'html.parser',
        'xml.etree.ElementTree',
        'base64',
        'hashlib',
        'hmac',
        'uuid',
        'random',
        'struct',
        'binascii',
        'email.utils',
        'email.message',
        'mimetypes',
        'gzip',
        'zlib',
        'bz2',
        'lzma',
        'zipfile',
        'tarfile',
        
        # Network and image processing
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.cookies',
        'requests.exceptions',
        'requests.models',
        'requests.sessions',
        'requests.utils',
        'requests.structures',
        'requests.status_codes',
        'requests.hooks',
        'requests.packages',
        'requests.packages.urllib3',
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
        'urllib3.util.connection',
        'urllib3.util.ssl_',
        'urllib3.fields',
        'urllib3.filepost',
        'certifi',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageFilter',
        'pyperclip',
        
        # Concurrent processing
        'concurrent.futures',
        'concurrent.futures._base',
        'concurrent.futures.thread',
        
        # yt-dlp - include everything we need
        'yt_dlp',
        'yt_dlp.YoutubeDL',
        'yt_dlp.extractor',
        'yt_dlp.extractor.youtube',
        'yt_dlp.extractor.common',
        'yt_dlp.extractor.generic',
        'yt_dlp.extractor.extractors',
        'yt_dlp.downloader',
        'yt_dlp.downloader.http',
        'yt_dlp.downloader.fragment',
        'yt_dlp.downloader.external',
        'yt_dlp.downloader.common',
        'yt_dlp.postprocessor',
        'yt_dlp.postprocessor.ffmpeg',
        'yt_dlp.postprocessor.common',
        'yt_dlp.utils',
        'yt_dlp.utils._utils',
        'yt_dlp.compat',
        'yt_dlp.compat._legacy',
        'yt_dlp.compat._deprecated',
        'yt_dlp.version',
        
        # Crypto support
        'Cryptodome',
        'Cryptodome.Cipher',
        'Cryptodome.Cipher.AES',
        'Cryptodome.Hash',
        'Cryptodome.Hash.SHA1',
        'Cryptodome.Hash.SHA256',
        'Cryptodome.Util',
        'Cryptodome.Util.Padding',
        
        # Other essentials
        'mutagen',
        'mutagen.mp4',
        'mutagen.mp3',
        'mutagen.flac',
        'brotli',
        'websockets',
        'websockets.client',
        'websockets.exceptions',
        
        # Essential for packaging but safe versions
        'packaging',
        'packaging.version',
        'packaging.specifiers',
        'packaging.requirements',
    ],
    hookspath=[],  # Don't use any automatic hooks
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude all problematic modules completely
        'pkg_resources',
        'pkg_resources.extern',
        'pkg_resources.extern.jaraco',
        'pkg_resources.extern.packaging',
        'pkg_resources._vendor',
        'pkg_resources._vendor.jaraco',
        'pkg_resources._vendor.packaging',
        'setuptools',
        'setuptools._vendor',
        'setuptools._vendor.jaraco',
        'setuptools._vendor.packaging',
        'jaraco',
        'jaraco.text',
        'jaraco.functools',
        'jaraco.context',
        'jaraco.classes',
        'jaraco.collections',
        'importlib_metadata',
        'importlib_metadata._compat',
        'zipp',
        'distutils',
        'distutils.version',
        
        # Exclude other potentially problematic modules
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
    
    with open('hybrid.spec', 'w') as f:
        f.write(spec_content)
    
    print("✓ Created hybrid.spec file")

def build_hybrid():
    """Build using the hybrid spec"""
    
    print("🚀 Building with hybrid approach...")
    
    # Create the spec file
    create_hybrid_spec()
    
    # Build using the spec file
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "hybrid.spec"
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
    if build_hybrid():
        print("\n🎉 Hybrid build completed successfully!")
        print("Executable location: dist/youtube-downloader-v1.0/")
    else:
        print("\n❌ Build failed")
        sys.exit(1)
