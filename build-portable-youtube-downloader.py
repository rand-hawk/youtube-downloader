import os
import subprocess
import shutil
import urllib.request
import zipfile

SCRIPT_NAME = "youtube-download-gui-modern.py"
PORTABLE_EXE_NAME = "youtube-downloader-portable"
ICON_FILE = "youtube-downloader.ico"
CONFIG_FILE = "config.json"
IMAGE_FILE = "youtube-downloader-icon.png"
DIST_DIR = "portable"
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

def create_portable_spec_file():
    """Create a custom PyInstaller spec file for portable version"""
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
        ('{FFMPEG_DIR}/ffmpeg.exe', 'ffmpeg'),
        ('{FFMPEG_DIR}/ffprobe.exe', 'ffmpeg'),
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
    name='{PORTABLE_EXE_NAME}',
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

    with open('youtube-downloader-portable.spec', 'w') as f:
        f.write(spec_content)

    print("✔ Portable PyInstaller spec file created.")

def build_portable_exe():
    """Build the portable executable"""
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)

    # Download FFmpeg if needed
    download_ffmpeg()

    # Create spec file for portable version
    create_portable_spec_file()

    pyinstaller_cmd = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        "--distpath", DIST_DIR,
        "youtube-downloader-portable.spec"
    ]

    try:
        subprocess.run(pyinstaller_cmd, check=True)
        print("✔ Portable EXE built successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        raise

def create_portable_package():
    """Create a complete portable package with all necessary files"""
    portable_package_dir = os.path.join(DIST_DIR, "YouTube-Downloader-Portable")

    # Create package directory
    os.makedirs(portable_package_dir, exist_ok=True)

    # Copy the executable
    exe_source = os.path.join(DIST_DIR, f"{PORTABLE_EXE_NAME}.exe")
    exe_dest = os.path.join(portable_package_dir, "YouTube-Downloader.exe")
    if os.path.exists(exe_source):
        shutil.copy2(exe_source, exe_dest)
        print("✔ Copied executable to portable package.")

    # Create a README file for the portable version
    readme_content = """# YouTube Downloader - Portable Version

## What is this?
This is a portable version of YouTube Downloader that doesn't require installation.
You can run it directly from any location on your computer or even from a USB drive.

## How to use:
1. Double-click "YouTube-Downloader.exe" to start the application
2. Copy any YouTube URL to your clipboard (automatic detection)
3. Select format (MP4 video or MP3 audio) and quality
4. Add to queue or download immediately
5. Your downloads will be saved to a "downloaded_media" folder next to this executable

## Features:
✅ No installation required
✅ Runs from any location
✅ FFmpeg included for video/audio processing
✅ Download queue system
✅ Resume interrupted downloads
✅ Clipboard monitoring
✅ Concurrent downloads
✅ Thumbnail preview

## System Requirements:
- Windows 10/11 (64-bit)
- 4GB RAM minimum
- Internet connection for downloads

## Folder Structure:
- YouTube-Downloader.exe - Main application
- downloaded_media/ - Your downloaded videos/audio (created automatically)
- config.json - Settings file (created automatically)
- .partial_downloads/ - Temporary files for resume functionality (created automatically)

## Support:
For issues or questions, visit: https://github.com/rand-hawk/youtube-downloader

Enjoy your portable YouTube downloading experience!
"""

    readme_path = os.path.join(portable_package_dir, "README.txt")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("✔ Created README.txt for portable package.")

    print(f"✔ Portable package created at: {portable_package_dir}")

def create_portable_zip():
    """Create a ZIP file of the portable package for easy distribution"""
    portable_package_dir = os.path.join(DIST_DIR, "YouTube-Downloader-Portable")
    zip_filename = os.path.join(DIST_DIR, "YouTube-Downloader-Portable-v2.0.zip")

    if os.path.exists(portable_package_dir):
        try:
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(portable_package_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Create archive path relative to the package directory
                        archive_path = os.path.relpath(file_path, portable_package_dir)
                        zipf.write(file_path, archive_path)

            # Get file size for display
            zip_size = os.path.getsize(zip_filename)
            zip_size_mb = zip_size / (1024 * 1024)

            print(f"✔ Created portable ZIP package: {zip_filename}")
            print(f"✔ ZIP file size: {zip_size_mb:.1f} MB")

        except Exception as e:
            print(f"❌ Error creating ZIP file: {e}")
    else:
        print("❌ Portable package directory not found")

def main():
    print("🚀 Building YouTube Downloader Portable Version...")
    print("=" * 60)

    try:
        build_portable_exe()
        print("\n" + "=" * 60)
        create_portable_package()
        print("\n" + "=" * 60)
        create_portable_zip()
        print("\n" + "=" * 60)
        print("🎉 Portable build completed successfully!")
        print(f"📁 Portable Package: {DIST_DIR}\\YouTube-Downloader-Portable\\")
        print(f"📱 Executable: YouTube-Downloader.exe")
        print(f"📦 ZIP Package: {DIST_DIR}\\YouTube-Downloader-Portable-v2.0.zip")
        print("🎯 No installation required - run from anywhere!")
        print("✅ FFmpeg included and configured automatically")
        print("📋 README.txt included with usage instructions")
        print("🚀 Ready for distribution!")

    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
