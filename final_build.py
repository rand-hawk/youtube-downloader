#!/usr/bin/env python3
"""
Final Build Script - Only built-in modules
"""

import os
import subprocess
import sys
import shutil
import urllib.request

def download_ytdlp():
    """Download yt-dlp executable using urllib"""
    try:
        print("📥 Downloading yt-dlp...")
        
        ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        ytdlp_path = "yt-dlp.exe"
        
        urllib.request.urlretrieve(ytdlp_url, ytdlp_path)
        
        print("✓ yt-dlp downloaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to download yt-dlp: {e}")
        return False

def create_final_spec():
    """Create spec file for final version"""
    
    spec_content = '''
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
'''
    
    with open('final.spec', 'w') as f:
        f.write(spec_content)
    
    print("✓ Created final.spec file")

def build_final():
    """Build the final version"""
    
    print("🚀 Building final version with only built-in modules...")
    
    # Download yt-dlp first
    if not download_ytdlp():
        return False
    
    # Create the spec file
    create_final_spec()
    
    # Build using the spec file
    cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "final.spec"
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

def create_installer():
    """Create installer using Inno Setup"""
    try:
        print("\n🔧 Creating installer...")
        
        # Create Inno Setup script
        iss_content = f'''
[Setup]
AppName=YouTube Downloader
AppVersion=1.0
AppPublisher=YouTube Downloader
DefaultDirName=C:\\YouTube Downloader
DefaultGroupName=YouTube Downloader
OutputDir=installer
OutputBaseFilename=youtube-downloader-installer
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Dirs]
Name: "{{app}}"; Permissions: users-full
Name: "{{app}}\\ffmpeg"; Permissions: users-full

[Files]
Source: "dist\\youtube-downloader-v1.0\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "youtube-downloader.ico"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "youtube-downloader-icon.png"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "ffmpeg\\ffmpeg.exe"; DestDir: "{{app}}\\ffmpeg"; Flags: ignoreversion
Source: "ffmpeg\\ffprobe.exe"; DestDir: "{{app}}\\ffmpeg"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\YouTube Downloader"; Filename: "{{app}}\\youtube-downloader-v1.0.exe"; WorkingDir: "{{app}}"; IconFilename: "{{app}}\\youtube-downloader.ico"
Name: "{{commondesktop}}\\YouTube Downloader"; Filename: "{{app}}\\youtube-downloader-v1.0.exe"; WorkingDir: "{{app}}"; IconFilename: "{{app}}\\youtube-downloader.ico"; Tasks: desktopicon

[Registry]
Root: HKLM; Subkey: "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\YouTubeDownloader"; ValueType: string; ValueName: "DisplayName"; ValueData: "YouTube Downloader"
Root: HKLM; Subkey: "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\YouTubeDownloader"; ValueType: string; ValueName: "UninstallString"; ValueData: "{{uninstallexe}}"

[Run]
Filename: "{{app}}\\youtube-downloader-v1.0.exe"; Description: "{{cm:LaunchProgram,YouTube Downloader}}"; Flags: nowait postinstall skipifsilent
'''
        
        # Create installer directory
        os.makedirs("installer", exist_ok=True)
        
        # Write ISS file
        with open("installer.iss", "w") as f:
            f.write(iss_content)
        
        # Compile with Inno Setup
        inno_cmd = [
            "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe",
            "installer.iss"
        ]
        
        result = subprocess.run(inno_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Installer created successfully!")
            return True
        else:
            print("❌ Installer creation failed!")
            print("Error:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Installer creation error: {e}")
        return False

if __name__ == "__main__":
    if build_final():
        print("\n🎉 Final build completed successfully!")
        print("Executable location: dist/youtube-downloader-v1.0/")
        print("\nThis version uses only built-in Python modules and yt-dlp as subprocess!")
        
        # Create installer
        if create_installer():
            print("\n🎉 Installer created successfully!")
            print("Installer location: installer/youtube-downloader-installer.exe")
        else:
            print("\n⚠️ Installer creation failed, but executable is ready")
    else:
        print("\n❌ Build failed")
        sys.exit(1)
