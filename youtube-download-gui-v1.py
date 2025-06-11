import os
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from yt_dlp import YoutubeDL
import time
import requests
from PIL import Image, ImageTk
from io import BytesIO

CONFIG_FILE = "config.json"
ICON_FILE = "youtube-downloader-icon.png"


class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        try:
            if os.path.exists(ICON_FILE):
                self.root.iconphoto(False, tk.PhotoImage(file=ICON_FILE))
        except Exception as e:
            print(f"Could not load icon: {e}")

        self.cancel_requested = False
        self.video_info = None
        self.available_formats = []
        self.download_start_time = None
        self.thumbnail_image = None
        self.current_download_phase = ""
        self.load_config()

        self.setup_widgets()

    def load_config(self):
        default_output = os.path.abspath("downloaded_media")
        default_ffmpeg = "c:/ffmpeg/bin"

        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
            except Exception as e:
                print(f"Error loading config file: {e}")

        output_dir = config.get("output_dir", default_output)
        if not os.path.isdir(output_dir):
            output_dir = default_output

        ffmpeg_path = config.get("ffmpeg_path", default_ffmpeg)
        if not os.path.isdir(ffmpeg_path):
            ffmpeg_path = default_ffmpeg

        self.output_dir = output_dir
        self.ffmpeg_path = ffmpeg_path

        os.makedirs(self.output_dir, exist_ok=True)

    def save_config(self):
        config = {
            "output_dir": self.output_dir,
            "ffmpeg_path": self.ffmpeg_path
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)

    def setup_widgets(self):
        # URL input section
        url_frame = tk.Frame(self.root)
        url_frame.pack(pady=(10, 5), fill="x", padx=10)

        self.url_label = ttk.Label(url_frame, text="YouTube Video URL:")
        self.url_label.pack(anchor="w")

        url_input_frame = tk.Frame(url_frame)
        url_input_frame.pack(fill="x", pady=5)

        self.url_entry = tk.Entry(url_input_frame, width=70)
        self.url_entry.pack(side="left", fill="x", expand=True)

        self.parse_button = ttk.Button(url_input_frame, text="Parse Video", command=self.parse_video)
        self.parse_button.pack(side="right", padx=(5, 0))

        # Video info section
        self.info_frame = tk.Frame(self.root)
        self.info_frame.pack(pady=5, fill="x", padx=10)

        # Create a frame for thumbnail and video info side by side
        info_content_frame = tk.Frame(self.info_frame)
        info_content_frame.pack(fill="x")

        # Thumbnail frame (left side)
        self.thumbnail_frame = tk.Frame(info_content_frame)
        self.thumbnail_frame.pack(side="left", padx=(0, 10))

        self.thumbnail_label = ttk.Label(self.thumbnail_frame, text="")
        self.thumbnail_label.pack()

        # Video details frame (right side)
        video_details_frame = tk.Frame(info_content_frame)
        video_details_frame.pack(side="left", fill="x", expand=True)

        self.video_title_label = ttk.Label(video_details_frame, text="", wraplength=500)
        self.video_title_label.pack(anchor="w")

        # Download format section
        self.download_type = tk.StringVar(value="mp4")  # Default to video
        format_frame = tk.Frame(self.root)
        format_frame.pack(pady=10)
        ttk.Label(format_frame, text="Download Format:").pack()
        ttk.Radiobutton(format_frame, text="MP3 (Audio)", variable=self.download_type, value="mp3", command=self.update_resolution_options).pack()
        ttk.Radiobutton(format_frame, text="MP4 (Video)", variable=self.download_type, value="mp4", command=self.update_resolution_options).pack()

        # Resolution selection section
        self.resolution_frame = tk.Frame(self.root)
        self.resolution_frame.pack(pady=10)
        self.resolution_label = ttk.Label(self.resolution_frame, text="Video Quality:")
        self.resolution_var = tk.StringVar(value="best")
        self.resolution_buttons = []

        # Folder and FFmpeg settings
        folder_frame = tk.Frame(self.root)
        folder_frame.pack(pady=5, fill="x", padx=10)
        ttk.Label(folder_frame, text="Save to:").pack(side="left")
        self.folder_label = ttk.Label(folder_frame, text=self.output_dir, width=50)
        self.folder_label.pack(side="left", padx=5)
        ttk.Button(folder_frame, text="Choose Folder", command=self.choose_folder).pack(side="left")

        ffmpeg_frame = tk.Frame(self.root)
        ffmpeg_frame.pack(pady=5, fill="x", padx=10)
        ttk.Label(ffmpeg_frame, text="FFmpeg path:").pack(side="left")
        self.ffmpeg_label = ttk.Label(ffmpeg_frame, text=self.ffmpeg_path, width=50)
        self.ffmpeg_label.pack(side="left", padx=5)
        ttk.Button(ffmpeg_frame, text="Choose FFmpeg", command=self.choose_ffmpeg).pack(side="left")

        # Download buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        self.start_button = ttk.Button(button_frame, text="Start Download", command=self.start_download, state="disabled")
        self.start_button.pack(side="left", padx=5)
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_download, state="disabled")
        self.stop_button.pack(side="left", padx=5)

        # Progress bar
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(pady=5, fill="x", padx=10)

        progress_header_frame = tk.Frame(progress_frame)
        progress_header_frame.pack(fill="x")

        ttk.Label(progress_header_frame, text="Progress:").pack(side="left")

        # Download phase indicator
        self.download_phase_label = ttk.Label(progress_header_frame, text="", foreground="blue")
        self.download_phase_label.pack(side="left", padx=(10, 0))

        # Center frame for elapsed time
        self.elapsed_time_label = ttk.Label(progress_header_frame, text="")
        self.elapsed_time_label.pack(side="left", padx=(20, 0))

        self.speed_label = ttk.Label(progress_header_frame, text="")
        self.speed_label.pack(side="right")

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=2)

        # Status label
        self.status_label = ttk.Label(self.root, text="Enter a YouTube URL and click 'Parse Video' to begin")
        self.status_label.pack(pady=5)

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = folder
            self.folder_label.config(text=self.output_dir)
            self.save_config()

    def choose_ffmpeg(self):
        folder = filedialog.askdirectory()
        if folder:
            self.ffmpeg_path = folder
            self.ffmpeg_label.config(text=self.ffmpeg_path)
            self.save_config()

    def parse_video(self):
        """Parse the video URL and extract available formats"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a YouTube video URL.")
            return

        self.parse_button.config(state="disabled")
        self.status_label.config(text="Parsing video information...")

        # Run parsing in a separate thread to avoid freezing the GUI
        threading.Thread(target=self._parse_video_thread, args=(url,)).start()

    def _parse_video_thread(self, url):
        """Thread function to parse video information"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with YoutubeDL(ydl_opts) as ydl:
                self.video_info = ydl.extract_info(url, download=False)
                self.available_formats = self.video_info.get('formats', [])

                # Update GUI in main thread
                self.root.after(0, self._update_video_info)

        except Exception as e:
            error_msg = f"Error parsing video: {str(e)}"
            self.root.after(0, lambda: self._show_parse_error(error_msg))

    def _show_parse_error(self, error_msg):
        """Show parsing error in main thread"""
        self.status_label.config(text=error_msg)
        self.parse_button.config(state="normal")
        messagebox.showerror("Parse Error", error_msg)

    def format_duration(self, seconds):
        """Format duration in hh:mm:ss format"""
        if not seconds:
            return "Unknown"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def format_elapsed_time(self, elapsed_seconds):
        """Format elapsed time for display"""
        if elapsed_seconds < 60:
            return f"Elapsed: {elapsed_seconds:.0f}s"
        elif elapsed_seconds < 3600:
            minutes = elapsed_seconds // 60
            seconds = elapsed_seconds % 60
            return f"Elapsed: {minutes:.0f}m {seconds:.0f}s"
        else:
            hours = elapsed_seconds // 3600
            minutes = (elapsed_seconds % 3600) // 60
            return f"Elapsed: {hours:.0f}h {minutes:.0f}m"

    def format_file_size(self, size_bytes):
        """Format file size in appropriate units"""
        if not size_bytes:
            return ""

        if size_bytes >= 1024 * 1024 * 1024:  # >= 1 GB
            size_gb = size_bytes / (1024 * 1024 * 1024)
            return f"{size_gb:.1f} GB"
        elif size_bytes >= 1024 * 1024:  # >= 1 MB
            size_mb = size_bytes / (1024 * 1024)
            return f"{size_mb:.0f} MB"
        else:  # < 1 MB
            size_kb = size_bytes / 1024
            return f"{size_kb:.0f} KB"

    def estimate_audio_size(self, duration, bitrate):
        """Estimate audio file size based on duration and bitrate"""
        if not duration or not bitrate:
            return None

        # Convert bitrate from kbps to bytes per second, then multiply by duration
        bitrate_bps = int(bitrate) * 1000 / 8  # Convert kbps to bytes per second
        estimated_size = duration * bitrate_bps
        return int(estimated_size)

    def estimate_video_size(self, height, duration):
        """Estimate video file size based on resolution and duration"""
        if not duration:
            return None

        # Rough bitrate estimates based on resolution (in kbps)
        bitrate_estimates = {
            144: 200,    # 144p
            240: 400,    # 240p
            360: 800,    # 360p
            480: 1200,   # 480p
            720: 2500,   # 720p
            1080: 4500,  # 1080p
            1440: 8000,  # 1440p (2K)
            2160: 15000, # 2160p (4K)
        }

        # Find closest resolution
        closest_height = min(bitrate_estimates.keys(), key=lambda x: abs(x - height))
        video_bitrate = bitrate_estimates.get(closest_height, 2500)

        # Add audio bitrate (assume 128 kbps for video downloads)
        audio_bitrate = 128
        total_bitrate = video_bitrate + audio_bitrate

        # Calculate size: (bitrate in kbps * duration in seconds) / 8 bits per byte / 1024 for KB
        estimated_size = (total_bitrate * duration * 1000) / 8
        return int(estimated_size)

    def get_combined_file_size(self, height):
        """Get combined file size for video + audio streams"""
        if not self.available_formats:
            return None

        video_size = 0
        audio_size = 0

        # Find best video format for this height
        video_formats = [f for f in self.available_formats
                        if f.get('vcodec') != 'none' and f.get('height') == height]
        if video_formats:
            # Get the best video format (usually first one after sorting)
            best_video = max(video_formats, key=lambda x: x.get('tbr', 0) or 0)
            video_size = best_video.get('filesize') or best_video.get('filesize_approx') or 0

        # Find best audio format
        audio_formats = [f for f in self.available_formats
                        if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        if audio_formats:
            # Get the best audio format
            best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
            audio_size = best_audio.get('filesize') or best_audio.get('filesize_approx') or 0

        # Return combined size if we have both
        if video_size and audio_size:
            return video_size + audio_size
        elif video_size:
            return video_size
        else:
            # Fallback to estimation if no file sizes available
            duration = self.video_info.get('duration', 0) if self.video_info else 0
            return self.estimate_video_size(height, duration)

    def load_thumbnail(self, thumbnail_url):
        """Load and display video thumbnail"""
        try:
            response = requests.get(thumbnail_url, timeout=10)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                # Resize thumbnail to a reasonable size
                image = image.resize((120, 90), Image.Resampling.LANCZOS)
                self.thumbnail_image = ImageTk.PhotoImage(image)
                self.thumbnail_label.config(image=self.thumbnail_image)
            else:
                self.thumbnail_label.config(text="No thumbnail", image="")
        except Exception as e:
            print(f"Error loading thumbnail: {e}")
            self.thumbnail_label.config(text="No thumbnail", image="")

    def _update_video_info(self):
        """Update GUI with video information"""
        if self.video_info:
            title = self.video_info.get('title', 'Unknown Title')
            duration = self.video_info.get('duration', 0)
            duration_str = self.format_duration(duration)

            info_text = f"Title: {title}\nDuration: {duration_str}"
            self.video_title_label.config(text=info_text)

            # Load thumbnail if available
            thumbnail_url = self.video_info.get('thumbnail')
            if thumbnail_url:
                threading.Thread(target=self.load_thumbnail, args=(thumbnail_url,)).start()
            else:
                self.thumbnail_label.config(text="No thumbnail", image="")

            self.update_resolution_options()
            self.start_button.config(state="normal")
            self.status_label.config(text="Video parsed successfully. Select format and quality, then start download.")

        self.parse_button.config(state="normal")

    def update_resolution_options(self):
        """Update resolution options based on download type and available formats"""
        # Clear existing resolution buttons and reset grid
        for button in self.resolution_buttons:
            button.destroy()
        self.resolution_buttons.clear()

        # Clear the label from any previous geometry manager
        self.resolution_label.grid_forget()
        self.resolution_label.pack_forget()

        if not self.available_formats:
            return

        is_mp3 = self.download_type.get() == "mp3"

        if is_mp3:
            # For MP3, show audio quality options
            self.resolution_label.config(text="Audio Quality:")
            self.resolution_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))

            audio_qualities = ["best", "192", "128", "96", "64"]
            self.resolution_var.set("192")

            # Create grid layout for audio quality options (3 per row)
            current_row = 1  # Start from row 1 since label is in row 0
            current_col = 0

            duration = self.video_info.get('duration', 0) if self.video_info else 0

            for quality in audio_qualities:
                if quality == "best":
                    text = "Best Available"
                else:
                    # Estimate file size for audio
                    estimated_size = self.estimate_audio_size(duration, quality)
                    size_text = f" (~{self.format_file_size(estimated_size)})" if estimated_size else ""
                    text = f"{quality} kbps{size_text}"

                rb = ttk.Radiobutton(self.resolution_frame, text=text,
                                   variable=self.resolution_var, value=quality, width=20)
                rb.grid(row=current_row, column=current_col, sticky="w", padx=5, pady=2)
                self.resolution_buttons.append(rb)

                current_col += 1
                if current_col >= 3:  # 3 columns per row
                    current_col = 0
                    current_row += 1
        else:
            # For MP4, show video resolution options
            self.resolution_label.config(text="Video Quality:")
            self.resolution_label.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))

            # Extract unique video resolutions from available formats with file sizes
            video_formats = []
            for fmt in self.available_formats:
                if fmt.get('vcodec') != 'none' and fmt.get('height'):
                    height = fmt.get('height')
                    # Check if this height is already in our list
                    existing_format = next((f for f in video_formats if f['height'] == height), None)
                    if not existing_format:
                        # Get file size information
                        filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                        video_formats.append({
                            'height': height,
                            'format_id': fmt.get('format_id'),
                            'ext': fmt.get('ext', 'mp4'),
                            'filesize': filesize
                        })

            # Sort by resolution (highest first)
            video_formats.sort(key=lambda x: x['height'], reverse=True)

            if video_formats:
                # Set default to highest quality
                self.resolution_var.set(str(video_formats[0]['height']))

                # Create a list of all resolution options
                all_resolutions = ["best"]  # Start with "Best Available"
                for fmt in video_formats:
                    all_resolutions.append(str(fmt['height']))

                # Create grid layout for video resolution options (3 per row)
                current_row = 1  # Start from row 1 since label is in row 0
                current_col = 0

                for i, resolution in enumerate(all_resolutions):
                    if resolution == "best":
                        text = "Best Available"
                    else:
                        height = int(resolution)

                        # Get combined file size (video + audio)
                        filesize = self.get_combined_file_size(height)

                        # Format the resolution text
                        if height >= 2160:
                            base_text = f"4K ({height}p)"
                        elif height >= 1440:
                            base_text = f"2K ({height}p)"
                        else:
                            base_text = f"{height}p"

                        # Add file size if available
                        if filesize:
                            size_text = f" (~{self.format_file_size(filesize)})"
                            text = f"{base_text}{size_text}"
                        else:
                            text = base_text

                    rb = ttk.Radiobutton(self.resolution_frame, text=text,
                                       variable=self.resolution_var, value=resolution, width=20)
                    rb.grid(row=current_row, column=current_col, sticky="w", padx=5, pady=2)
                    self.resolution_buttons.append(rb)

                    current_col += 1
                    if current_col >= 3:  # 3 columns per row
                        current_col = 0
                        current_row += 1
            else:
                # Fallback if no video formats found
                self.resolution_var.set("best")
                rb = ttk.Radiobutton(self.resolution_frame, text="Best Available",
                                   variable=self.resolution_var, value="best", width=20)
                rb.grid(row=1, column=0, sticky="w", padx=5, pady=2)  # Start from row 1
                self.resolution_buttons.append(rb)

    def stop_download(self):
        self.cancel_requested = True
        self.status_label.config(text="Stopping download...")
        # Reset progress bar, speed display, elapsed time, and download phase when stopping
        self.progress_var.set(0)
        self.speed_label.config(text="")
        self.elapsed_time_label.config(text="")
        self.download_phase_label.config(text="")
        self.current_download_phase = ""

    def start_download(self):
        self.cancel_requested = False
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a YouTube video URL.")
            return

        if not self.video_info:
            messagebox.showwarning("Parse Required", "Please parse the video first by clicking 'Parse Video'.")
            return

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        threading.Thread(target=self.download_video, args=(url,)).start()

    def format_speed(self, speed_bytes_per_sec):
        """Format download speed in appropriate units"""
        if not speed_bytes_per_sec:
            return ""

        # Convert bytes/sec to appropriate unit
        if speed_bytes_per_sec >= 1024 * 1024:  # >= 1 MB/s
            speed_mb = speed_bytes_per_sec / (1024 * 1024)
            return f"{speed_mb:.1f} MB/s"
        else:  # < 1 MB/s, show in KB/s
            speed_kb = speed_bytes_per_sec / 1024
            return f"{speed_kb:.0f} KB/s"

    def detect_download_phase(self, d):
        """Detect what type of stream is being downloaded"""
        filename = d.get('filename', '')
        info_dict = d.get('info_dict', {})

        # Check if it's an audio-only download
        if self.download_type.get() == "mp3":
            return "🎵 Audio"

        # For video downloads, try to detect the phase
        if 'vcodec' in info_dict and 'acodec' in info_dict:
            vcodec = info_dict.get('vcodec', 'none')
            acodec = info_dict.get('acodec', 'none')

            if vcodec != 'none' and acodec == 'none':
                return "🎬 Video Stream"
            elif vcodec == 'none' and acodec != 'none':
                return "🎵 Audio Stream"
            elif vcodec != 'none' and acodec != 'none':
                return "🎬 Video+Audio"

        # Fallback: try to detect from filename or format info
        if any(keyword in filename.lower() for keyword in ['audio', 'sound', 'm4a', 'mp3']):
            return "🎵 Audio Stream"
        elif any(keyword in filename.lower() for keyword in ['video', 'mp4', 'webm']):
            return "🎬 Video Stream"

        # Default fallback
        return "📥 Downloading"

    def progress_hook(self, d):
        """Progress hook for yt-dlp to update progress bar, speed, and elapsed time"""
        if d['status'] == 'downloading':
            # Detect and update download phase
            current_phase = self.detect_download_phase(d)
            if current_phase != self.current_download_phase:
                self.current_download_phase = current_phase
                self.root.after(0, lambda phase=current_phase: self.download_phase_label.config(text=phase))

            # Update elapsed time
            if self.download_start_time:
                elapsed = time.time() - self.download_start_time
                elapsed_text = self.format_elapsed_time(elapsed)
                self.root.after(0, lambda e=elapsed_text: self.elapsed_time_label.config(text=e))

            # Update progress bar
            if 'total_bytes' in d and d['total_bytes']:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                self.root.after(0, lambda p=percent: self.progress_var.set(p))
            elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                self.root.after(0, lambda p=percent: self.progress_var.set(p))

            # Update speed display
            if 'speed' in d and d['speed']:
                speed_text = self.format_speed(d['speed'])
                self.root.after(0, lambda s=speed_text: self.speed_label.config(text=s))

        elif d['status'] == 'finished':
            # Update phase to show completion
            self.root.after(0, lambda: self.download_phase_label.config(text="✅ Merging"))
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.speed_label.config(text=""))
        elif d['status'] == 'error':
            self.root.after(0, lambda: self.download_phase_label.config(text="❌ Error"))
            self.root.after(0, lambda: self.speed_label.config(text=""))

    def download_video(self, url):
        if self.cancel_requested:
            return

        # Reset progress bar, speed display, download phase, and start timer
        self.progress_var.set(0)
        self.speed_label.config(text="")
        self.elapsed_time_label.config(text="")
        self.download_phase_label.config(text="")
        self.current_download_phase = ""
        self.download_start_time = time.time()

        is_mp3 = self.download_type.get() == "mp3"
        selected_quality = self.resolution_var.get()

        # Build format selector based on user choice
        if is_mp3:
            format_selector = "bestaudio/best"
        else:
            if selected_quality == "best":
                format_selector = "bestvideo+bestaudio/best"
            else:
                # Try to get specific resolution
                height = selected_quality
                format_selector = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"

        ydl_opts = {
            "format": format_selector,
            "ffmpeg_location": self.ffmpeg_path,
            "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
            "postprocessors": [],
            "progress_hooks": [self.progress_hook]
        }

        if is_mp3:
            # Use selected audio quality
            audio_quality = selected_quality if selected_quality != "best" else "192"
            ydl_opts["postprocessors"].append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": audio_quality,
            })
        else:
            ydl_opts["postprocessors"].append({
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4"
            })

        try:
            title = self.video_info.get('title', 'Unknown') if self.video_info else 'Unknown'
            quality_text = f" ({selected_quality}{'p' if not is_mp3 and selected_quality != 'best' else ' kbps' if is_mp3 and selected_quality != 'best' else ''})"
            self.status_label.config(text=f"Downloading: {title}{quality_text}")

            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Ensure progress bar shows 100% when complete and show final elapsed time
            self.progress_var.set(100)
            self.speed_label.config(text="")
            self.download_phase_label.config(text="✅ Complete")

            # Show final elapsed time
            if self.download_start_time:
                total_elapsed = time.time() - self.download_start_time
                final_elapsed_text = f"Completed in {self.format_elapsed_time(total_elapsed).replace('Elapsed: ', '')}"
                self.elapsed_time_label.config(text=final_elapsed_text)

            self.status_label.config(text="Download complete.")
        except Exception as e:
            error_msg = f"Error downloading video: {e}"
            print(error_msg)
            self.status_label.config(text=error_msg)
            # Reset progress bar, speed display, elapsed time, and download phase on error
            self.progress_var.set(0)
            self.speed_label.config(text="")
            self.elapsed_time_label.config(text="")
            self.download_phase_label.config(text="")
        finally:
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()
