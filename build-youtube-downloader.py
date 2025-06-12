import os
import subprocess
import shutil
import urllib.request
import zipfile

SCRIPT_NAME = "youtube-download-gui-modern.py"
EXE_NAME = "youtube-downloader-v2.0-portable"
ICON_FILE = "youtube-downloader.ico"
CONFIG_FILE = "config.json"
IMAGE_FILE = "youtube-downloader-icon.png"
DIST_DIR = "dist"
FFMPEG_DIR = "ffmpeg"

def download_ffmpeg():
    """Download and extract FFmpeg if not present"""
    if os.path.exists(FFMPEG_DIR):
        print("✔ FFmpeg directory already exists.")
        return

    print("📥 Downloading FFmpeg...")
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    ffmpeg_zip = "ffmpeg-release-essentials.zip"

    try:
        urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip)
        print("✔ FFmpeg downloaded successfully.")

        print("📦 Extracting FFmpeg...")
        with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
            zip_ref.extractall("temp_ffmpeg")

        # Find the extracted folder (it has a version number in the name)
        temp_dir = "temp_ffmpeg"
        extracted_folders = [f for f in os.listdir(temp_dir) if f.startswith("ffmpeg-")]
        if extracted_folders:
            extracted_folder = os.path.join(temp_dir, extracted_folders[0])
            ffmpeg_bin_source = os.path.join(extracted_folder, "bin")

            # Create our ffmpeg directory and copy binaries
            os.makedirs(FFMPEG_DIR, exist_ok=True)
            if os.path.exists(ffmpeg_bin_source):
                for file in ["ffmpeg.exe", "ffprobe.exe"]:
                    src = os.path.join(ffmpeg_bin_source, file)
                    dst = os.path.join(FFMPEG_DIR, file)
                    if os.path.exists(src):
                        shutil.copy2(src, dst)
                        print(f"✔ Copied {file}")

        # Clean up
        os.remove(ffmpeg_zip)
        shutil.rmtree(temp_dir)
        print("✔ FFmpeg setup completed.")

    except Exception as e:
        print(f"❌ Error downloading FFmpeg: {e}")
        print("Please download FFmpeg manually and place ffmpeg.exe and ffprobe.exe in the 'ffmpeg' folder.")

def create_spec_file():
    """Create a custom PyInstaller spec file for better control"""
    spec_content = f'''
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
    ['{SCRIPT_NAME}'],
    pathex=['.', '.venv/Lib/site-packages'],
    binaries=[],
    datas=[
        ('{ICON_FILE}', '.'),
        ('{CONFIG_FILE}', '.'),
        ('{IMAGE_FILE}', '.'),
        ('{FFMPEG_DIR}', 'ffmpeg'),
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
    hooksconfig={{}},
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
    name='{EXE_NAME}',
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
    icon='{ICON_FILE}',
)
'''

    with open('youtube-downloader.spec', 'w') as f:
        f.write(spec_content)

    print("✔ PyInstaller spec file created.")

# Step 1: Build the .exe file with PyInstaller
def build_exe():
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)

    # Download FFmpeg if needed
    download_ffmpeg()

    # Create spec file for better control
    create_spec_file()

    # Use the virtual environment's PyInstaller
    import sys
    venv_python = sys.executable

    pyinstaller_cmd = [
        venv_python, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "youtube-downloader.spec"
    ]

    try:
        subprocess.run(pyinstaller_cmd, check=True)
        print("✔ EXE built successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        raise

# Step 2: Create installer script for Inno Setup
def create_inno_script():
    inno_script = f"""
[Setup]
AppName=YouTube Downloader
AppVersion=2.0
AppPublisher=YouTube Downloader Team
AppPublisherURL=https://github.com/rand-hawk/youtube-downloader
AppSupportURL=https://github.com/rand-hawk/youtube-downloader/issues
AppUpdatesURL=https://github.com/rand-hawk/youtube-downloader/releases
AppId={{{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}}}
DefaultDirName=C:\\YouTube Downloader
DefaultGroupName=YouTube Downloader
OutputDir=installer
OutputBaseFilename=youtube-downloader-installer
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayName=YouTube Downloader v2.0
UninstallDisplayIcon={{app}}\\youtube-downloader.ico
VersionInfoVersion=2.0.0.0
VersionInfoCompany=YouTube Downloader Team
VersionInfoDescription=Professional YouTube Video Downloader with Modern UI
VersionInfoCopyright=Copyright (C) 2025 YouTube Downloader Team

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Dirs]
Name: "{{app}}"; Permissions: users-full
Name: "{{app}}\\ffmpeg"; Permissions: users-full

[Files]
Source: "{DIST_DIR}\\{EXE_NAME}.exe"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{ICON_FILE}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{CONFIG_FILE}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{IMAGE_FILE}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{FFMPEG_DIR}\\ffmpeg.exe"; DestDir: "{{app}}\\ffmpeg"; Flags: ignoreversion
Source: "{FFMPEG_DIR}\\ffprobe.exe"; DestDir: "{{app}}\\ffmpeg"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\YouTube Downloader"; Filename: "{{app}}\\{EXE_NAME}.exe"; WorkingDir: "{{app}}"; IconFilename: "{{app}}\\{ICON_FILE}"
Name: "{{commondesktop}}\\YouTube Downloader"; Filename: "{{app}}\\{EXE_NAME}.exe"; WorkingDir: "{{app}}"; IconFilename: "{{app}}\\{ICON_FILE}"; Tasks: desktopicon



[Run]
Filename: "{{app}}\\{EXE_NAME}.exe"; Description: "{{cm:LaunchProgram,YouTube Downloader}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: string;
  ConfigContent: string;
begin
  if CurStep = ssPostInstall then
  begin
    // Update config.json with correct FFmpeg path
    ConfigPath := ExpandConstant('{{app}}\\{CONFIG_FILE}');
    ConfigContent := '{{' + #13#10 +
      '    "output_dir": "' + ExpandConstant('{{userdocs}}') + '\\YouTube Downloads",' + #13#10 +
      '    "ffmpeg_path": "' + ExpandConstant('{{app}}') + '\\ffmpeg",' + #13#10 +
      '    "clipboard_monitoring": true,' + #13#10 +
      '    "max_concurrent_downloads": 2,' + #13#10 +
      '    "download_speed_limit": null,' + #13#10 +
      '    "download_queue": []' + #13#10 +
      '}}';
    SaveStringToFile(ConfigPath, ConfigContent, False);
  end;
end;
"""

    # Create installer directory
    os.makedirs("installer", exist_ok=True)

    with open("youtube-downloader-installer.iss", "w") as f:
        f.write(inno_script.strip())
    print("✔ Inno Setup script generated.")

# Step 3: Compile installer
def compile_installer():
    print("🔧 Compiling installer with Inno Setup...")
    try:
        # Try different possible paths for Inno Setup
        inno_paths = [
            "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe",
            "C:\\Program Files\\Inno Setup 6\\ISCC.exe",
            "ISCC"  # If it's in PATH
        ]

        success = False
        for inno_path in inno_paths:
            try:
                subprocess.run([inno_path, "youtube-downloader-installer.iss"], check=True)
                success = True
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        if success:
            print("✔ Installer built successfully.")
        else:
            print("❌ Could not find Inno Setup. Please install Inno Setup 6 or add it to PATH.")
            print("Installer script created at: youtube-downloader-installer.iss")
            print("You can compile it manually with Inno Setup.")

    except Exception as e:
        print(f"❌ Error creating installer: {e}")

def main():
    print("🚀 Building YouTube Downloader with FFmpeg integration...")
    print("=" * 60)

    try:
        build_exe()
        print("\n" + "=" * 60)
        create_inno_script()
        print("\n" + "=" * 60)
        compile_installer()
        print("\n" + "=" * 60)
        print("🎉 Build completed successfully!")
        print(f"📁 Executable: {DIST_DIR}\\{EXE_NAME}.exe")
        print("📦 Installer: installer\\youtube-downloader-installer.exe")
        print("🎯 Installation directory: C:\\YouTube Downloader")
        print("✅ FFmpeg included and configured automatically")

    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
