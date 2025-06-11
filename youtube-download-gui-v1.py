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

        # Download queue system
        self.download_queue = []
        self.current_download_index = 0
        self.is_queue_processing = False

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

        # Load saved queue
        saved_queue = config.get("download_queue", [])
        for item in saved_queue:
            if item['status'] != 'Completed':  # Only restore non-completed items
                queue_item = {
                    'url': item['url'],
                    'title': item['title'],
                    'download_type': item['download_type'],
                    'quality': item['quality'],
                    'video_info': {},  # Will be populated when needed
                    'available_formats': [],  # Will be populated when needed
                    'status': 'Queued'
                }
                self.download_queue.append(queue_item)

        os.makedirs(self.output_dir, exist_ok=True)

    def save_config(self):
        config = {
            "output_dir": self.output_dir,
            "ffmpeg_path": self.ffmpeg_path,
            "download_queue": [
                {
                    'url': item['url'],
                    'title': item['title'],
                    'download_type': item['download_type'],
                    'quality': item['quality'],
                    'status': 'Queued' if item['status'] in ['Downloading', 'Failed'] else item['status']
                }
                for item in self.download_queue
            ]
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

        # Queue management buttons
        queue_button_frame = tk.Frame(self.root)
        queue_button_frame.pack(pady=5)
        self.add_to_queue_button = ttk.Button(queue_button_frame, text="Add to Queue", command=self.add_to_queue, state="disabled")
        self.add_to_queue_button.pack(side="left", padx=5)
        self.clear_queue_button = ttk.Button(queue_button_frame, text="Clear Queue", command=self.clear_queue)
        self.clear_queue_button.pack(side="left", padx=5)

        # Download queue display
        queue_frame = tk.Frame(self.root)
        queue_frame.pack(pady=5, fill="both", expand=True, padx=10)

        ttk.Label(queue_frame, text="Download Queue:").pack(anchor="w")

        # Create queue listbox with scrollbar
        queue_list_frame = tk.Frame(queue_frame)
        queue_list_frame.pack(fill="both", expand=True)

        self.queue_listbox = tk.Listbox(queue_list_frame, height=6)
        queue_scrollbar = ttk.Scrollbar(queue_list_frame, orient="vertical", command=self.queue_listbox.yview)
        self.queue_listbox.configure(yscrollcommand=queue_scrollbar.set)

        # Add context menu for queue listbox
        self.queue_context_menu = tk.Menu(self.root, tearoff=0)
        self.queue_context_menu.add_command(label="Download This Item", command=self.download_selected_from_queue)
        self.queue_context_menu.add_separator()
        self.queue_context_menu.add_command(label="Move Up", command=self.move_up_in_queue)
        self.queue_context_menu.add_command(label="Move Down", command=self.move_down_in_queue)
        self.queue_context_menu.add_separator()
        self.queue_context_menu.add_command(label="Remove from Queue", command=self.remove_selected_from_queue)

        # Bind right-click to show context menu
        self.queue_listbox.bind("<Button-3>", self.show_queue_context_menu)

        self.queue_listbox.pack(side="left", fill="both", expand=True)
        queue_scrollbar.pack(side="right", fill="y")

        # Queue control buttons
        queue_control_frame = tk.Frame(queue_frame)
        queue_control_frame.pack(pady=5)

        self.download_selected_button = ttk.Button(queue_control_frame, text="Download Selected", command=self.download_selected_from_queue)
        self.download_selected_button.pack(side="left", padx=5)

        self.remove_selected_button = ttk.Button(queue_control_frame, text="Remove Selected", command=self.remove_selected_from_queue)
        self.remove_selected_button.pack(side="left", padx=5)

        self.move_up_button = ttk.Button(queue_control_frame, text="Move Up", command=self.move_up_in_queue)
        self.move_up_button.pack(side="left", padx=5)

        self.move_down_button = ttk.Button(queue_control_frame, text="Move Down", command=self.move_down_in_queue)
        self.move_down_button.pack(side="left", padx=5)

        # Download buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        self.start_queue_button = ttk.Button(button_frame, text="Start Queue", command=self.start_queue_download)
        self.start_queue_button.pack(side="left", padx=5)
        self.start_single_button = ttk.Button(button_frame, text="Download Current", command=self.start_download, state="disabled")
        self.start_single_button.pack(side="left", padx=5)
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

        # Update queue display if there are saved items
        if self.download_queue:
            self.update_queue_display()
            self.status_label.config(text=f"Restored {len(self.download_queue)} items from previous session.")

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
            self.start_single_button.config(state="normal")
            self.add_to_queue_button.config(state="normal")
            self.status_label.config(text="Video parsed successfully. Select format and quality, then add to queue or download.")

        self.parse_button.config(state="normal")

    def add_to_queue(self):
        """Add current video to download queue"""
        if not self.video_info:
            messagebox.showwarning("No Video", "Please parse a video first.")
            return

        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a video URL.")
            return

        # Get current settings
        download_type = self.download_type.get()
        quality = self.resolution_var.get()
        title = self.video_info.get('title', 'Unknown Title')

        # Create queue item
        queue_item = {
            'url': url,
            'title': title,
            'download_type': download_type,
            'quality': quality,
            'video_info': self.video_info.copy(),
            'available_formats': self.available_formats.copy(),
            'status': 'Queued'
        }

        # Add to queue
        self.download_queue.append(queue_item)
        self.update_queue_display()

        # Clear current video info to allow adding more
        self.clear_current_video()

        self.status_label.config(text=f"Added '{title}' to queue. Total items: {len(self.download_queue)}")

    def clear_current_video(self):
        """Clear current video information to allow parsing new video"""
        self.url_entry.delete(0, tk.END)
        self.video_info = None
        self.available_formats = []
        self.video_title_label.config(text="")
        self.thumbnail_label.config(text="", image="")
        self.thumbnail_image = None

        # Clear resolution options
        for button in self.resolution_buttons:
            button.destroy()
        self.resolution_buttons.clear()
        self.resolution_label.grid_forget()

        # Reset button states
        self.start_single_button.config(state="disabled")
        self.add_to_queue_button.config(state="disabled")

    def update_queue_display(self):
        """Update the queue listbox display"""
        self.queue_listbox.delete(0, tk.END)

        for i, item in enumerate(self.download_queue):
            status_icon = "⏳" if item['status'] == 'Queued' else "📥" if item['status'] == 'Downloading' else "✅" if item['status'] == 'Completed' else "❌"
            format_text = f"{item['download_type'].upper()}"
            if item['quality'] != 'best':
                if item['download_type'] == 'mp3':
                    format_text += f" {item['quality']} kbps"
                else:
                    format_text += f" {item['quality']}p"
            else:
                format_text += " Best"

            display_text = f"{status_icon} {item['title']} ({format_text})"
            self.queue_listbox.insert(tk.END, display_text)

            # Highlight current download
            if self.is_queue_processing and i == self.current_download_index:
                self.queue_listbox.selection_set(i)

    def clear_queue(self):
        """Clear all items from the download queue"""
        if self.is_queue_processing:
            messagebox.showwarning("Queue Active", "Cannot clear queue while downloads are in progress.")
            return

        if self.download_queue:
            result = messagebox.askyesno("Clear Queue", f"Are you sure you want to clear all {len(self.download_queue)} items from the queue?")
            if result:
                self.download_queue.clear()
                self.update_queue_display()
                self.status_label.config(text="Queue cleared.")

    def remove_selected_from_queue(self):
        """Remove selected item from queue"""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item to remove.")
            return

        if self.is_queue_processing or self.stop_button['state'] == 'normal':
            messagebox.showwarning("Download Active", "Cannot modify queue while downloads are in progress.")
            return

        index = selection[0]
        removed_item = self.download_queue.pop(index)
        self.update_queue_display()
        self.status_label.config(text=f"Removed '{removed_item['title']}' from queue.")

    def move_up_in_queue(self):
        """Move selected item up in queue"""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item to move.")
            return

        if self.is_queue_processing or self.stop_button['state'] == 'normal':
            messagebox.showwarning("Download Active", "Cannot modify queue while downloads are in progress.")
            return

        index = selection[0]
        if index > 0:
            # Swap items
            self.download_queue[index], self.download_queue[index-1] = self.download_queue[index-1], self.download_queue[index]
            self.update_queue_display()
            self.queue_listbox.selection_set(index-1)

    def move_down_in_queue(self):
        """Move selected item down in queue"""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item to move.")
            return

        if self.is_queue_processing or self.stop_button['state'] == 'normal':
            messagebox.showwarning("Download Active", "Cannot modify queue while downloads are in progress.")
            return

        index = selection[0]
        if index < len(self.download_queue) - 1:
            # Swap items
            self.download_queue[index], self.download_queue[index+1] = self.download_queue[index+1], self.download_queue[index]
            self.update_queue_display()
            self.queue_listbox.selection_set(index+1)

    def show_queue_context_menu(self, event):
        """Show context menu for queue listbox"""
        # Select the item under cursor
        index = self.queue_listbox.nearest(event.y)
        self.queue_listbox.selection_clear(0, tk.END)
        self.queue_listbox.selection_set(index)

        # Show context menu
        try:
            self.queue_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.queue_context_menu.grab_release()

    def download_selected_from_queue(self):
        """Download selected item from queue immediately"""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an item to download.")
            return

        if self.is_queue_processing:
            messagebox.showwarning("Queue Active", "Cannot download individual items while queue is processing. Stop the queue first.")
            return

        # Check if any download is currently in progress
        if self.stop_button['state'] == 'normal':
            messagebox.showwarning("Download Active", "Another download is currently in progress. Please wait for it to complete or stop it first.")
            return

        index = selection[0]
        queue_item = self.download_queue[index]

        # Check if item is already completed
        if queue_item['status'] == 'Completed':
            messagebox.showinfo("Already Downloaded", f"'{queue_item['title']}' has already been downloaded.")
            return

        # Confirm download
        result = messagebox.askyesno("Download Selected",
                                   f"Download '{queue_item['title']}' ({queue_item['download_type'].upper()} {queue_item['quality']}) now?")
        if not result:
            return

        # Update item status
        queue_item['status'] = 'Downloading'
        self.update_queue_display()

        # Disable relevant buttons
        self.start_queue_button.config(state="disabled")
        self.start_single_button.config(state="disabled")
        self.download_selected_button.config(state="disabled")
        self.stop_button.config(state="normal")

        # Start download in separate thread
        threading.Thread(target=self.download_selected_item, args=(queue_item,)).start()

    def download_selected_item(self, queue_item):
        """Download a selected queue item"""
        try:
            self.cancel_requested = False

            # Set up video info for this download
            self.video_info = queue_item['video_info'] if queue_item['video_info'] else {}
            self.available_formats = queue_item['available_formats'] if queue_item['available_formats'] else []

            # If video info is empty, we need to parse it first
            if not self.video_info:
                self.root.after(0, lambda: self.status_label.config(text=f"Parsing video info for: {queue_item['title']}"))
                success = self.parse_queue_item_info(queue_item)
                if not success:
                    queue_item['status'] = 'Failed'
                    self.root.after(0, self.update_queue_display)
                    self.root.after(0, lambda: self.status_label.config(text=f"Failed to parse: {queue_item['title']}"))
                    return

            # Download the video
            self.root.after(0, lambda: self.status_label.config(text=f"Downloading selected: {queue_item['title']}"))
            success = self.download_video_from_queue(queue_item)

            # Update status
            if success and not self.cancel_requested:
                queue_item['status'] = 'Completed'
                self.root.after(0, lambda: self.status_label.config(text=f"Successfully downloaded: {queue_item['title']}"))
            else:
                queue_item['status'] = 'Failed' if not self.cancel_requested else 'Queued'
                status_text = f"Failed to download: {queue_item['title']}" if not self.cancel_requested else f"Download cancelled: {queue_item['title']}"
                self.root.after(0, lambda: self.status_label.config(text=status_text))

            # Update display
            self.root.after(0, self.update_queue_display)

        except Exception as e:
            error_msg = f"Error downloading {queue_item['title']}: {e}"
            print(error_msg)
            queue_item['status'] = 'Failed'
            self.root.after(0, self.update_queue_display)
            self.root.after(0, lambda: self.status_label.config(text=error_msg))
        finally:
            # Reset button states
            self.root.after(0, self.reset_download_buttons)

    def parse_queue_item_info(self, queue_item):
        """Parse video information for a queue item that doesn't have it"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(queue_item['url'], download=False)
                available_formats = video_info.get('formats', [])

                # Update queue item with parsed info
                queue_item['video_info'] = video_info
                queue_item['available_formats'] = available_formats

                # Update the global variables for download
                self.video_info = video_info
                self.available_formats = available_formats

                return True

        except Exception as e:
            print(f"Error parsing queue item {queue_item['title']}: {e}")
            return False

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
        """Stop current download or queue processing"""
        self.cancel_requested = True

        if self.is_queue_processing:
            self.status_label.config(text="Stopping queue...")
            self.is_queue_processing = False
        else:
            self.status_label.config(text="Stopping download...")

        # Reset progress indicators
        self.progress_var.set(0)
        self.speed_label.config(text="")
        self.elapsed_time_label.config(text="")
        self.download_phase_label.config(text="")
        self.current_download_phase = ""

        # Reset button states
        self.reset_download_buttons()

    def reset_download_buttons(self):
        """Reset download button states"""
        self.start_queue_button.config(state="normal")
        self.download_selected_button.config(state="normal")
        if self.video_info:
            self.start_single_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def start_queue_download(self):
        """Start downloading all items in the queue"""
        if not self.download_queue:
            messagebox.showinfo("Empty Queue", "No items in download queue. Add some videos first.")
            return

        if self.is_queue_processing:
            messagebox.showinfo("Queue Active", "Queue download is already in progress.")
            return

        self.is_queue_processing = True
        self.current_download_index = 0
        self.cancel_requested = False

        # Update button states
        self.start_queue_button.config(state="disabled")
        self.start_single_button.config(state="disabled")
        self.stop_button.config(state="normal")

        # Start queue processing
        threading.Thread(target=self.process_download_queue).start()

    def process_download_queue(self):
        """Process all items in the download queue"""
        total_items = len(self.download_queue)

        for i, queue_item in enumerate(self.download_queue):
            if self.cancel_requested:
                break

            self.current_download_index = i
            queue_item['status'] = 'Downloading'

            # Update display in main thread
            self.root.after(0, self.update_queue_display)
            self.root.after(0, lambda: self.status_label.config(text=f"Downloading {i+1}/{total_items}: {queue_item['title']}"))

            # Set up video info for this download
            self.video_info = queue_item['video_info']
            self.available_formats = queue_item['available_formats']

            # Download the video
            success = self.download_video_from_queue(queue_item)

            # Update status
            if success and not self.cancel_requested:
                queue_item['status'] = 'Completed'
                self.root.after(0, lambda: self.status_label.config(text=f"Completed {i+1}/{total_items}: {queue_item['title']}"))
            else:
                queue_item['status'] = 'Failed'
                self.root.after(0, lambda: self.status_label.config(text=f"Failed {i+1}/{total_items}: {queue_item['title']}"))

            # Update display
            self.root.after(0, self.update_queue_display)

            # Small delay between downloads
            if not self.cancel_requested and i < total_items - 1:
                time.sleep(1)

        # Queue processing complete
        self.is_queue_processing = False
        completed_count = sum(1 for item in self.download_queue if item['status'] == 'Completed')

        self.root.after(0, lambda: self.status_label.config(text=f"Queue complete! {completed_count}/{total_items} downloads successful."))
        self.root.after(0, self.reset_download_buttons)

    def download_video_from_queue(self, queue_item):
        """Download a single video from queue item"""
        try:
            url = queue_item['url']
            download_type = queue_item['download_type']
            quality = queue_item['quality']

            # Reset progress bar and indicators
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, lambda: self.speed_label.config(text=""))
            self.root.after(0, lambda: self.download_phase_label.config(text=""))
            self.root.after(0, lambda: self.elapsed_time_label.config(text=""))

            self.download_start_time = time.time()
            self.current_download_phase = ""

            # Build format selector
            is_mp3 = download_type == "mp3"
            if is_mp3:
                format_selector = "bestaudio/best"
            else:
                if quality == "best":
                    format_selector = "bestvideo+bestaudio/best"
                else:
                    height = quality
                    format_selector = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"

            ydl_opts = {
                "format": format_selector,
                "ffmpeg_location": self.ffmpeg_path,
                "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
                "postprocessors": [],
                "progress_hooks": [self.progress_hook]
            }

            if is_mp3:
                audio_quality = quality if quality != "best" else "192"
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

            # Download the video
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            return True

        except Exception as e:
            error_msg = f"Error downloading {queue_item['title']}: {e}"
            print(error_msg)
            return False

    def start_download(self):
        """Start downloading current single video"""
        self.cancel_requested = False
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a YouTube video URL.")
            return

        if not self.video_info:
            messagebox.showwarning("Parse Required", "Please parse the video first by clicking 'Parse Video'.")
            return

        self.start_single_button.config(state="disabled")
        self.start_queue_button.config(state="disabled")
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
            self.reset_download_buttons()


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()
