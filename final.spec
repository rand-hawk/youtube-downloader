
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['youtube-downloader-final.py'],
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
        # Only built-in modules
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
        'urllib.request',
        'urllib.error',
        'urllib.parse',
        'concurrent.futures',
        'concurrent.futures._base',
        'concurrent.futures.thread',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude everything we don't need
        'yt_dlp',
        'requests',
        'PIL',
        'pyperclip',
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
        'certifi',
        'charset_normalizer',
        'idna',
        'urllib3',
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
