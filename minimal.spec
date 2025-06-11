
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
