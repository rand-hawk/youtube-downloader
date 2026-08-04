# YouTube Downloader v2.2

A professional YouTube video and audio downloader with a modern CustomTkinter GUI interface, optimized for lower resolution screens.

## 🆕 What's New in v2.2

- **Broader URL Support**: Handles Shorts, Live, mobile (`m.youtube.com`), legacy `/v/` and share links with tracking parameters
- **SABR Workaround**: Uses `default` + `android_vr` player clients to bypass YouTube SABR enforcement that caused `Requested format is not available` errors
- **Friendly Parse Errors**: Actionable messages for SABR, format, age-restricted, private, and unavailable videos instead of raw tracebacks
- **Version Metadata Bumped**: Portable EXE renamed to `youtube-downloader-v2.2-portable.exe`; installer version `2.2.0.0`

## 🎉 Core Features (v2.0 Foundation)

- **Modern UI**: Complete redesign with CustomTkinter for a sleek, modern interface
- **Enhanced Filenames**: Videos saved with format: `"Title [Quality] [VideoID].ext"`
- **Improved Stability**: Fixed yt-dlp integration and download reliability
- **Better Error Handling**: Comprehensive error reporting and recovery
- **Portable Version**: Single executable with proper "portable" naming
- **Professional Packaging**: Both portable and installer versions available

## ✨ Features

- **Optimized Interface**: Compact layout perfect for 1024x768+ screens with dark/light themes
- **Multiple Formats**: Download videos (144p to 4K) or extract audio as MP3
- **Smart Queue System**: Add multiple videos with individual quality selection
- **Resume Downloads**: Automatic resume for interrupted downloads with .part files
- **Enhanced Filenames**: User-friendly filenames with title, quality, and video ID
- **Progress Tracking**: Real-time progress with speed, ETA, and download phase indicators
- **Built-in FFmpeg**: Integrated video/audio processing (no separate installation needed)
- **Clipboard Monitoring**: Automatic URL detection from clipboard
- **Professional Distribution**: Both portable executable and installer available
- **Lower Resolution Support**: Optimized for laptops, netbooks, and smaller monitors

## 📁 Project Structure

```
youtube-download/
├── 📄 README.md                                    # Project documentation
├── 📄 RELEASE_NOTES_v1.0.md                       # Release notes
├── 🐍 youtube-download-gui-v1.py                  # Original working version (v1.0)
├── 🐍 youtube-download-gui-modern.py              # Modern version (v2.2) - Main source
├── 🔧 build-youtube-downloader.py                 # Build script for both versions
├── 📄 config.json                                 # Default application configuration
├── 📄 youtube-downloader.spec                     # PyInstaller specification file
├── 🖼️ youtube-downloader.ico                       # Application icon (ICO format)
├── 🖼️ youtube-downloader-icon.png                  # UI icon (PNG format)
├── 📂 ffmpeg/                                     # FFmpeg binaries (bundled)
│   ├── ffmpeg.exe                                 # FFmpeg executable
│   └── ffprobe.exe                                # FFprobe executable
├── 📂 dist/                                       # Distribution files
│   ├── youtube-downloader-v2.2-portable.exe      # Portable executable
│   ├── README.txt                                 # User documentation
│   └── YouTube-Downloader-v2.2-Portable.zip      # Portable package
├── 📂 installer/                                  # Installer package
│   └── youtube-downloader-installer.exe          # Professional installer
├── 📂 build/                                      # Build artifacts (auto-generated)
└── 📂 .venv/                                      # Python virtual environment
```

## 🔧 Building from Source

### Prerequisites
- Python 3.9+ installed
- Virtual environment recommended

### Build Steps
1. **Clone the repository**:
   ```bash
   git clone https://github.com/rand-hawk/youtube-downloader.git
   cd youtube-downloader
   ```

2. **Set up virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt  # If requirements.txt exists
   ```

3. **Run the build script**:
   ```bash
   python build-youtube-downloader.py
   ```

4. **Build outputs**:
   - Portable executable: `dist/youtube-downloader-v2.2-portable.exe`
   - Professional installer: `installer/youtube-downloader-installer.exe`

## 📦 Installation Options

### Option 1: Portable Version (Recommended for Testing)
- Download `YouTube-Downloader-v2.2-Portable.zip` from releases
- Extract and run `youtube-downloader-v2.2-portable.exe`
- No installation required - completely portable

### Option 2: Professional Installer (Recommended for Regular Use)
- Download `youtube-downloader-installer.exe` from releases
- Run the installer and follow the wizard
- Default installation: `C:\YouTube Downloader`
- Creates Start Menu shortcuts and uninstaller

## 💻 System Requirements

- **OS**: Windows 10/11 (64-bit)
- **Screen Resolution**: 1024x768 or higher (optimized for lower resolutions)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 200MB for application + space for downloads
- **Network**: Internet connection for downloads
- **Dependencies**: All bundled (yt-dlp, FFmpeg, CustomTkinter)

## 🎯 Usage

1. **Launch** the application
2. **Paste** a YouTube URL in the input field
3. **Select** quality and format (MP4 video or MP3 audio)
4. **Add to Queue** for batch downloading
5. **Start Download** and monitor progress
6. **Find files** in the configured download directory

## 🐛 Troubleshooting

- **Downloads fail immediately**: Check internet connection and URL validity
- **No audio in video**: Ensure FFmpeg is properly bundled (automatic in releases)
- **Permission errors**: Run as administrator or change download directory
- **Antivirus warnings**: Add exception for the executable (false positive)
- **Interface too large**: v2.1+ is optimized for 1024x768+ screens; use scroll wheel if needed
- **Text too small**: Interface is optimized for space efficiency while maintaining readability
- **`Requested format is not available` / SABR errors**: v2.2 mitigates most cases; if it still fails, update yt-dlp inside the source venv with `pip install -U yt-dlp` and rebuild

## 📝 Version History

- **v2.2**: Broader URL support (Shorts/Live/mobile), SABR player-client fallback, friendlier parse errors
- **v2.1**: Optimized layout for lower resolution screens (1024x768+), compact design
- **v2.0**: Modern CustomTkinter UI, enhanced filenames, improved stability
- **v1.0**: Initial release with basic functionality

## ⚖️ License

This project is for educational and personal use only. Please respect YouTube's Terms of Service and copyright laws. Only download content you have permission to download or content that is in the public domain.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## 📞 Support

For issues and support, please use the GitHub Issues page.
