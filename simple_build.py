#!/usr/bin/env python3
"""
Simple build script for YouTube Downloader
Uses a minimal approach to ensure yt-dlp is properly included
"""

import os
import subprocess
import sys

def build_simple():
    """Build using a simple PyInstaller command"""
    print("🚀 Building YouTube Downloader (Simple Approach)...")
    
    # Simple PyInstaller command with minimal options and exclusions
    cmd = [
        "pyinstaller",
        "--onedir",
        "--noconsole",
        "--icon=youtube-downloader.ico",
        "--name=youtube-downloader-v1.0",
        "--add-data=youtube-downloader.ico;.",
        "--add-data=config.json;.",
        "--add-data=youtube-downloader-icon.png;.",
        "--add-data=youtube-download-gui-v1.py;.",
        "--add-data=ffmpeg/ffmpeg.exe;ffmpeg",
        "--add-data=ffmpeg/ffprobe.exe;ffmpeg",
        "--paths=.venv/Lib/site-packages",  # Explicitly add site-packages path
        # Exclude all problematic modules
        "--exclude-module=jaraco",
        "--exclude-module=jaraco.text",
        "--exclude-module=jaraco.functools",
        "--exclude-module=jaraco.context",
        "--exclude-module=jaraco.classes",
        "--exclude-module=jaraco.collections",
        "--exclude-module=pkg_resources.extern",
        "--exclude-module=pkg_resources.extern.jaraco",
        "--exclude-module=pkg_resources.extern.packaging",
        "--exclude-module=pkg_resources._vendor",
        "--exclude-module=pkg_resources._vendor.jaraco",
        "--exclude-module=pkg_resources._vendor.packaging",
        "--exclude-module=setuptools._vendor",
        "--exclude-module=setuptools._vendor.jaraco",
        "--exclude-module=setuptools._vendor.packaging",
        "--exclude-module=importlib_metadata",
        "--exclude-module=zipp",
        # Include essential modules directly
        "--hidden-import=pkg_resources",
        "--hidden-import=packaging",
        "--hidden-import=packaging.version",
        "--hidden-import=packaging.specifiers"
        "--clean",
        "--noconfirm",
        "ultimate_launcher.py"
    ]
    
    print("Running command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ Build successful!")
        print("Output:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Build failed!")
        print("Error:", e.stderr)
        return False

if __name__ == "__main__":
    if build_simple():
        print("🎉 Simple build completed successfully!")
        print("Executable location: dist/youtube-downloader-v1.0/")
    else:
        print("❌ Build failed!")
        sys.exit(1)
