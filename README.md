# YouTube Downloader

A professional YouTube video and audio downloader with a modern GUI interface.

## Features

- Download YouTube videos in various qualities (144p to 4K)
- Extract audio as MP3 files
- Download queue system with concurrent downloads
- Resume interrupted downloads
- Clipboard monitoring for automatic URL detection
- Video thumbnails display
- Progress tracking with speed and ETA
- FFmpeg integration for video/audio processing
- Professional installer with automatic setup

## Project Structure

```
youtube-download/
├── youtube-download-gui-v1.py          # Main application source code
├── build-youtube-downloader.py         # Build script for creating executable
├── config.json                         # Application configuration
├── youtube-downloader.ico              # Application icon (ICO format)
├── youtube-downloader-icon.png         # Application icon (PNG format)
├── ffmpeg/                             # FFmpeg binaries
│   ├── ffmpeg.exe                      # FFmpeg executable
│   └── ffprobe.exe                     # FFprobe executable
├── dist/                               # Built executable
│   └── youtube-downloader-v1.0.exe     # Final standalone executable
├── installer/                          # Installer package
│   └── youtube-downloader-installer.exe # Professional installer
└── .venv/                              # Python virtual environment (hidden)
```

## Building the Application

1. Ensure Python 3.9+ is installed
2. Run the build script:
   ```bash
   python build-youtube-downloader.py
   ```
3. The executable will be created in `dist/`
4. The installer will be created in `installer/`

## Installation

### Option 1: Use the Installer (Recommended)
- Run `installer/youtube-downloader-installer.exe`
- Follow the installation wizard
- Default installation: `C:\YouTube Downloader`

### Option 2: Standalone Executable
- Run `dist/youtube-downloader-v1.0.exe` directly
- No installation required

## Requirements

- Windows 10/11
- Internet connection for downloads
- FFmpeg (bundled with installer)

## License

This project is for educational and personal use.
