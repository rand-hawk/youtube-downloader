
# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Add the virtual environment site-packages to the path
venv_site_packages = os.path.abspath('.venv/Lib/site-packages')
if os.path.exists(venv_site_packages):
    sys.path.insert(0, venv_site_packages)

# Add the current directory to the path to ensure all modules are found
sys.path.insert(0, os.path.abspath('.'))

a = Analysis(
    ['youtube-download-gui-modern.py'],
    pathex=['.', '.venv/Lib/site-packages'],
    binaries=[],
    datas=[
        ('youtube-downloader.ico', '.'),
        ('config.json', '.'),
        ('youtube-downloader-icon.png', '.'),
        ('ffmpeg', 'ffmpeg'),
    ],
    hiddenimports=[
        # CustomTkinter and modern UI
        'customtkinter',
        'darkdetect',
        'packaging',

        # Core yt-dlp modules
        'yt_dlp',
        'yt_dlp.YoutubeDL',
        'yt_dlp.extractor',
        'yt_dlp.extractor.youtube',
        'yt_dlp.extractor.common',
        'yt_dlp.extractor.generic',
        'yt_dlp.downloader',
        'yt_dlp.downloader.http',
        'yt_dlp.downloader.fragment',
        'yt_dlp.downloader.common',
        'yt_dlp.postprocessor',
        'yt_dlp.postprocessor.ffmpeg',
        'yt_dlp.postprocessor.common',
        'yt_dlp.utils',
        'yt_dlp.compat',
        'yt_dlp.version',

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
        'certifi',
        # Include PIL for thumbnail support
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageFilter',
        # pyperclip for clipboard monitoring
        'pyperclip',

        # Concurrent processing
        'concurrent.futures',
        'concurrent.futures._base',
        'concurrent.futures.thread',

        # Other essentials - only include what's actually available
        'brotli',
        # Note: Cryptodome, mutagen, websockets are optional and will be included by yt-dlp hook if available
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude problematic modules that cause issues
        'matplotlib',
        'numpy',
        'scipy',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='youtube-downloader-v2.2-portable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='youtube-downloader.ico',
)
