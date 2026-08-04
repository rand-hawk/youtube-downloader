# YouTube Downloader v2.2 Release Notes

## 🛠️ URL Compatibility & SABR Workaround

**Release Date**: August 4, 2026
**Version**: 2.2.0
**Build**: Stable

---

## 🌟 What's New in v2.2

### 🔗 **Broader YouTube URL Support**
The single-video URL detector now accepts modern link shapes that previously fell through to the playlist parser or were rejected outright:

- `youtube.com/shorts/<id>` — YouTube Shorts links
- `youtube.com/live/<id>` — Live and post-live stream links
- `youtube.com/v/<id>` — Legacy embed-style links
- `m.youtube.com/...` — Mobile subdomain variants
- Share links with tracking parameters such as `?si=`, `?t=`, `&feature=`, and percent-encoded query values

Playlist detection is unchanged — URLs with a `list=` parameter still route to the playlist tab.

### 🧩 **SABR / Player-Client Fallback**
YouTube has been enforcing SABR streaming on a growing number of videos, which caused `Requested format is not available` and *"page needs to be reloaded"* errors during parse and download.

v2.2 now requests the `default` and `android_vr` player clients from yt-dlp for **every** parse, single download, and playlist scan, which restores extraction for the majority of affected videos.

### 💬 **Friendlier Parse Errors**
Raw yt-dlp tracebacks are replaced with actionable messages for the most common failure modes:

- **Requested format is not available** → suggests `pip install -U yt-dlp`
- **SABR / page needs to be reloaded** → explains the SABR situation and links to the tracking issue
- **Age-restricted** → notes that sign-in is required
- **Private video** / **Video unavailable** → clear one-line explanations

The original yt-dlp message is still shown under `Details:` for troubleshooting.

---

## 🔧 Technical Changes

- Added module-level `YOUTUBE_PLAYER_CLIENTS` / `YOUTUBE_EXTRACTOR_ARGS` and wired them into the parse, download, and playlist `ydl_opts`.
- New `_friendly_parse_error()` helper that strips ANSI escape sequences and pattern-matches known yt-dlp errors.
- Expanded single-video regexes to allow `m.` subdomain, `shorts/`, `live/`, `v/` paths, and `%` / `.` characters in query strings.
- Version metadata bumped to `2.2` / `2.2.0.0` in the build script (`AppVersion`, `UninstallDisplayName`, `VersionInfoVersion`) and portable EXE name changed to `youtube-downloader-v2.2-portable.exe`.
- Window titles, header label, and settings dialog title updated to **v2.2**.

---

## 🔄 Migration from v2.1

- **No migration needed** — settings, `config.json`, and download queue are fully compatible.
- The portable executable is renamed to `youtube-downloader-v2.2-portable.exe`; delete the old v2.1 file if you keep them side by side.
- The installer keeps the same `AppId`, so it upgrades a v2.1 installation in place.

---

## 📦 Distribution Packages

### 🎯 **Portable Version**
- **File**: `youtube-downloader-v2.2-portable.exe`
- **Features**: Single executable, no installation required
- **Perfect for**: USB drives, temporary use, testing on various systems

### 🏠 **Installer Version**
- **File**: `youtube-downloader-installer.exe`
- **Version**: 2.2.0.0
- **Installation**: `C:\YouTube Downloader` (default)
- **Features**: Start Menu shortcuts, uninstaller, auto-configuration

---

## 💻 System Requirements

- **OS**: Windows 10/11 (64-bit)
- **Screen Resolution**: 1024x768 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 200MB for application + space for downloads
- **Network**: Internet connection for downloads
- **Dependencies**: All bundled (yt-dlp, FFmpeg, CustomTkinter)

---

## 🐛 Bug Fixes

- ✅ Fixed Shorts / Live / mobile / share-tracking URLs being rejected or misrouted as playlists.
- ✅ Fixed `Requested format is not available` on videos where YouTube enforces SABR.
- ✅ Replaced noisy raw yt-dlp tracebacks in the parse-error dialog with human-readable guidance.

---

## ✨ Inherited from v2.1

All v2.1 features remain:

- Modern CustomTkinter UI with dark/light theme
- Compact layout optimized for 1024x768+ screens
- Filename format: `Title [Quality] [VideoID].ext`
- Video qualities 144p → 4K plus MP3 extraction
- Download queue with per-item quality
- Stop / resume with `.part` files
- Real-time progress with speed and phase indicators
- Bundled FFmpeg
- Clipboard URL monitoring
- Portable and installer distributions

---

## 🔮 Future Plans

- Optional PO token / cookies support for videos that still fail with SABR
- Playlist item selection UI
- Download history with re-download
- Subtitle download support
