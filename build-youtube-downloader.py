import os
import subprocess
import shutil

SCRIPT_NAME = "youtube-download-gui-v1.py"
EXE_NAME = "youtube-downloader-v1.0"
ICON_FILE = "youtube-downloader.ico"
CONFIG_FILE = "config.json"
IMAGE_FILE = "youtube-downloader-icon.png"
DIST_DIR = "dist"

# Step 1: Build the .exe file with PyInstaller
def build_exe():
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)

    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        f"--icon={ICON_FILE}",
        f"--name={EXE_NAME}",
        SCRIPT_NAME
    ]
    subprocess.run(pyinstaller_cmd, check=True)
    print("✔ EXE built successfully.")

# Step 2: Create installer script for Inno Setup
def create_inno_script():
    inno_script = f"""
[Setup]
AppName=YouTube Downloader
AppVersion=1.0
DefaultDirName={{pf}}\\YouTube Downloader
OutputDir=installer
OutputBaseFilename=youtube-downloader-installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "{DIST_DIR}\\{EXE_NAME}.exe"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{ICON_FILE}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{CONFIG_FILE}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{IMAGE_FILE}"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\YouTube Downloader"; Filename: "{{app}}\\{EXE_NAME}.exe"
Name: "{{userdesktop}}\\YouTube Downloader"; Filename: "{{app}}\\{EXE_NAME}.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
"""
    with open("youtube-downloader-installer.iss", "w") as f:
        f.write(inno_script.strip())
    print("✔ Inno Setup script generated.")

# Step 3: Compile installer
def compile_installer():
    print("🔧 Compiling installer with Inno Setup...")
    subprocess.run(["ISCC", "youtube-downloader-installer.iss"], check=True)
    print("✔ Installer built successfully.")

if __name__ == "__main__":
    build_exe()
    create_inno_script()
    compile_installer()
