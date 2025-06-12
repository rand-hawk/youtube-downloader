import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from yt_dlp import YoutubeDL
import time
import requests
from io import BytesIO
import re
import signal
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# Optional imports
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL not available - thumbnail display disabled")

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    print("pyperclip not available - clipboard monitoring disabled")

CONFIG_FILE = "config.json"
ICON_FILE = "youtube-downloader-icon.png"

class InterruptibleYoutubeDL(YoutubeDL):
    """Custom YoutubeDL class that can be interrupted using threading events"""
    def __init__(self, stop_event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_event = stop_event

    def process_info(self, info_dict):
        """Override to check for interruption"""
        if self.stop_event.is_set():
            raise KeyboardInterrupt("Download interrupted by user")
        return super().process_info(info_dict)


class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader v2.0")
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

        # Playlist processing
        self.playlist_info = None
        self.playlist_entries = []
        self.playlist_selections = {}  # Track selected items and their qualities

        # Clipboard monitoring
        self.clipboard_monitoring = True
        self.last_clipboard_content = ""
        self.last_parsed_url = ""  # Track the last URL that was parsed
        self.clipboard_check_interval = 1000  # milliseconds

        # Concurrent downloads
        self.max_concurrent_downloads = 2
        self.download_executor = ThreadPoolExecutor(max_workers=self.max_concurrent_downloads)
        self.active_downloads = {}
        self.download_speed_limit = None  # KB/s, None for unlimited

        # Download process control
        self.active_download_processes = []  # Track active yt-dlp processes
        self.download_threads = []  # Track download threads
        self.stop_events = []  # Track stop events for each download
        self.download_stop_event = threading.Event()  # Global stop event

        # Progress tracking for concurrent downloads
        self.concurrent_progress = {}  # Track progress of each concurrent download
        self.total_concurrent_downloads = 0
        self.completed_concurrent_downloads = 0

        # Dynamic queue management
        self.initial_queue_size = 0  # Size when download started
        self.queue_extended = False  # Flag to track if queue was extended
        self.active_futures = {}  # Track active download futures

        # Resume functionality (will be initialized after config loading)
        self.partial_downloads_dir = None
        self.resume_data_file = None
        self.resume_data = {}  # Track partial downloads

        self.load_config()

        # Initialize resume system after config is loaded
        self.setup_resume_system()

        self.setup_widgets()

    def load_config(self):
        default_output = os.path.abspath("downloaded_media")

        # Detect if running as PyInstaller executable and find bundled FFmpeg
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller executable
            application_path = os.path.dirname(sys.executable)
            bundled_ffmpeg = os.path.join(application_path, "ffmpeg")
            if os.path.exists(os.path.join(bundled_ffmpeg, "ffmpeg.exe")):
                default_ffmpeg = bundled_ffmpeg
            else:
                default_ffmpeg = "c:/ffmpeg/bin"
        else:
            # Running as script
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

        # FFmpeg path is always auto-detected, not user-configurable
        self.output_dir = output_dir
        self.ffmpeg_path = default_ffmpeg

        # Load performance settings
        self.clipboard_monitoring = config.get("clipboard_monitoring", True)
        self.max_concurrent_downloads = config.get("max_concurrent_downloads", 2)
        self.download_speed_limit = config.get("download_speed_limit", None)

        # Update thread pool with loaded settings
        self.download_executor = ThreadPoolExecutor(max_workers=self.max_concurrent_downloads)

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

    def setup_resume_system(self):
        """Initialize the resume download system"""
        # Initialize resume paths now that output_dir is available
        self.partial_downloads_dir = os.path.join(self.output_dir, ".partial_downloads")
        self.resume_data_file = os.path.join(self.partial_downloads_dir, "resume_data.json")

        # Create partial downloads directory
        os.makedirs(self.partial_downloads_dir, exist_ok=True)

        # Load existing resume data
        self.load_resume_data()

        # Check for resumable downloads on startup
        self.check_resumable_downloads()

    def load_resume_data(self):
        """Load resume data from file"""
        if os.path.exists(self.resume_data_file):
            try:
                with open(self.resume_data_file, 'r') as f:
                    self.resume_data = json.load(f)
            except Exception as e:
                print(f"Error loading resume data: {e}")
                self.resume_data = {}
        else:
            self.resume_data = {}

    def save_resume_data(self):
        """Save resume data to file"""
        try:
            with open(self.resume_data_file, 'w') as f:
                json.dump(self.resume_data, f, indent=2)
        except Exception as e:
            print(f"Error saving resume data: {e}")

    def check_resumable_downloads(self):
        """Check for resumable downloads on startup"""
        if not self.resume_data:
            return

        resumable_count = 0
        for url, data in self.resume_data.items():
            partial_file = data.get('partial_file')
            if partial_file and os.path.exists(partial_file):
                resumable_count += 1

        if resumable_count > 0:
            # Show resume dialog after UI is ready
            self.root.after(1000, lambda: self.show_resume_dialog(resumable_count))

    def show_resume_dialog(self, count):
        """Show dialog asking user about resuming downloads"""
        result = messagebox.askyesno(
            "Resume Downloads",
            f"Found {count} interrupted download(s) that can be resumed.\n\n"
            "Would you like to resume these downloads now?\n\n"
            "Click 'Yes' to add them to the queue for resuming,\n"
            "or 'No' to clear the resume data and start fresh."
        )

        if result:
            self.add_resumable_to_queue()
        else:
            self.clear_resume_data()

    def add_resumable_to_queue(self):
        """Add resumable downloads to the queue"""
        added_count = 0
        for url, data in self.resume_data.items():
            partial_file = data.get('partial_file')
            if partial_file and os.path.exists(partial_file):
                # Create queue item for resume
                queue_item = {
                    'url': url,
                    'title': data.get('title', 'Resuming Download'),
                    'download_type': data.get('download_type', 'mp4'),
                    'quality': data.get('quality', 'best'),
                    'video_info': data.get('video_info', {}),
                    'available_formats': data.get('available_formats', []),
                    'status': 'Queued',
                    'resume_data': data  # Include resume data
                }
                self.download_queue.append(queue_item)
                added_count += 1

        if added_count > 0:
            self.update_queue_display()
            self.status_label.config(text=f"Added {added_count} resumable download(s) to queue.")

    def clear_resume_data(self):
        """Clear all resume data"""
        self.resume_data = {}
        self.save_resume_data()

        # Clean up partial files
        try:
            for file in os.listdir(self.partial_downloads_dir):
                if file != "resume_data.json":
                    file_path = os.path.join(self.partial_downloads_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
        except Exception as e:
            print(f"Error cleaning partial files: {e}")

        self.status_label.config(text="Resume data cleared.")

    def manual_resume_check(self):
        """Manually check for resumable downloads"""
        if not self.resume_data:
            messagebox.showinfo("No Resumes", "No interrupted downloads found.")
            return

        resumable_count = 0
        for url, data in self.resume_data.items():
            partial_file = data.get('partial_file')
            if partial_file and os.path.exists(partial_file):
                resumable_count += 1

        if resumable_count > 0:
            self.show_resume_dialog(resumable_count)
        else:
            messagebox.showinfo("No Resumes", "No resumable downloads found.")

    def save_config(self):
        config = {
            "output_dir": self.output_dir,
            "clipboard_monitoring": self.clipboard_monitoring,
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "download_speed_limit": self.download_speed_limit,
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
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Single Video Tab
        self.single_video_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.single_video_frame, text="Single Video")

        # Playlist Tab
        self.playlist_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.playlist_frame, text="Playlist")

        # Setup single video tab
        self.setup_single_video_tab()

        # Setup playlist tab
        self.setup_playlist_tab()

        # Setup common elements (queue, settings, etc.)
        self.setup_common_widgets()

    def setup_single_video_tab(self):
        # URL input section
        url_frame = tk.Frame(self.single_video_frame)
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
        self.info_frame = tk.Frame(self.single_video_frame)
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
        format_frame = tk.Frame(self.single_video_frame)
        format_frame.pack(pady=10)
        ttk.Label(format_frame, text="Download Format:").pack()
        ttk.Radiobutton(format_frame, text="MP3 (Audio)", variable=self.download_type, value="mp3", command=self.update_resolution_options).pack()
        ttk.Radiobutton(format_frame, text="MP4 (Video)", variable=self.download_type, value="mp4", command=self.update_resolution_options).pack()

        # Resolution selection section
        self.resolution_frame = tk.Frame(self.single_video_frame)
        self.resolution_frame.pack(pady=10)
        self.resolution_label = ttk.Label(self.resolution_frame, text="Video Quality:")
        self.resolution_var = tk.StringVar(value="best")
        self.resolution_buttons = []

        # Single video action buttons
        single_button_frame = tk.Frame(self.single_video_frame)
        single_button_frame.pack(pady=10)
        self.add_to_queue_button = ttk.Button(single_button_frame, text="Add to Queue", command=self.add_to_queue, state="disabled")
        self.add_to_queue_button.pack(side="left", padx=5)
        self.start_single_button = ttk.Button(single_button_frame, text="Download Current", command=self.start_download, state="disabled")
        self.start_single_button.pack(side="left", padx=5)

    def setup_playlist_tab(self):
        # Playlist URL input section
        playlist_url_frame = tk.Frame(self.playlist_frame)
        playlist_url_frame.pack(pady=(10, 5), fill="x", padx=10)

        ttk.Label(playlist_url_frame, text="YouTube Playlist URL:").pack(anchor="w")

        playlist_input_frame = tk.Frame(playlist_url_frame)
        playlist_input_frame.pack(fill="x", pady=5)

        self.playlist_url_entry = tk.Entry(playlist_input_frame, width=70)
        self.playlist_url_entry.pack(side="left", fill="x", expand=True)

        self.parse_playlist_button = ttk.Button(playlist_input_frame, text="Parse Playlist", command=self.parse_playlist)
        self.parse_playlist_button.pack(side="right", padx=(5, 0))

        # Playlist info section
        self.playlist_info_frame = tk.Frame(self.playlist_frame)
        self.playlist_info_frame.pack(pady=5, fill="x", padx=10)

        self.playlist_title_label = ttk.Label(self.playlist_info_frame, text="", wraplength=600)
        self.playlist_title_label.pack(anchor="w")

        # Playlist items section
        playlist_items_frame = tk.Frame(self.playlist_frame)
        playlist_items_frame.pack(pady=5, fill="both", expand=True, padx=10)

        ttk.Label(playlist_items_frame, text="Playlist Items:").pack(anchor="w")

        # Create playlist listbox with scrollbar
        playlist_list_frame = tk.Frame(playlist_items_frame)
        playlist_list_frame.pack(fill="both", expand=True)

        self.playlist_listbox = tk.Listbox(playlist_list_frame, height=8, selectmode=tk.EXTENDED)
        playlist_scrollbar = ttk.Scrollbar(playlist_list_frame, orient="vertical", command=self.playlist_listbox.yview)
        self.playlist_listbox.configure(yscrollcommand=playlist_scrollbar.set)

        self.playlist_listbox.pack(side="left", fill="both", expand=True)
        playlist_scrollbar.pack(side="right", fill="y")

        # Playlist controls
        playlist_controls_frame = tk.Frame(playlist_items_frame)
        playlist_controls_frame.pack(pady=5, fill="x")

        # Selection controls
        selection_frame = tk.Frame(playlist_controls_frame)
        selection_frame.pack(side="left", fill="x", expand=True)

        ttk.Button(selection_frame, text="Select All", command=self.select_all_playlist_items).pack(side="left", padx=2)
        ttk.Button(selection_frame, text="Select None", command=self.select_none_playlist_items).pack(side="left", padx=2)

        # Format and quality selection for playlist
        format_quality_frame = tk.Frame(playlist_controls_frame)
        format_quality_frame.pack(side="right")

        ttk.Label(format_quality_frame, text="Format:").pack(side="left")
        self.playlist_download_type = tk.StringVar(value="mp4")
        ttk.Radiobutton(format_quality_frame, text="MP3", variable=self.playlist_download_type, value="mp3").pack(side="left", padx=2)
        ttk.Radiobutton(format_quality_frame, text="MP4", variable=self.playlist_download_type, value="mp4").pack(side="left", padx=2)

        ttk.Label(format_quality_frame, text="Quality:").pack(side="left", padx=(10, 0))
        self.playlist_quality_var = tk.StringVar(value="720")
        quality_combo = ttk.Combobox(format_quality_frame, textvariable=self.playlist_quality_var, width=8, state="readonly")
        quality_combo['values'] = ('144', '240', '360', '480', '720', '1080', 'best')
        quality_combo.pack(side="left", padx=2)

        # Playlist action buttons
        playlist_button_frame = tk.Frame(playlist_items_frame)
        playlist_button_frame.pack(pady=5)

        self.add_selected_to_queue_button = ttk.Button(playlist_button_frame, text="Add Selected to Queue",
                                                      command=self.add_selected_playlist_items_to_queue, state="disabled")
        self.add_selected_to_queue_button.pack(side="left", padx=5)

    def setup_common_widgets(self):
        # Create a frame at the bottom for common widgets
        common_frame = tk.Frame(self.root)
        common_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Folder settings
        folder_frame = tk.Frame(common_frame)
        folder_frame.pack(pady=5, fill="x")
        ttk.Label(folder_frame, text="Save to:").pack(side="left")
        self.folder_label = ttk.Label(folder_frame, text=self.output_dir, width=45)
        self.folder_label.pack(side="left", padx=5)
        ttk.Button(folder_frame, text="Choose Folder", command=self.choose_folder).pack(side="left", padx=2)
        ttk.Button(folder_frame, text="Open Folder", command=self.open_download_folder).pack(side="left")

        # Performance and clipboard settings
        settings_frame = tk.Frame(common_frame)
        settings_frame.pack(pady=5, fill="x")

        # Clipboard monitoring
        clipboard_frame = tk.Frame(settings_frame)
        clipboard_frame.pack(side="left", fill="x", expand=True)

        self.clipboard_var = tk.BooleanVar(value=self.clipboard_monitoring)
        self.clipboard_checkbox = ttk.Checkbutton(clipboard_frame, text="Monitor Clipboard for YouTube URLs",
                                                 variable=self.clipboard_var, command=self.toggle_clipboard_monitoring)
        self.clipboard_checkbox.pack(anchor="w")

        # Performance settings
        perf_frame = tk.Frame(settings_frame)
        perf_frame.pack(side="right")

        ttk.Label(perf_frame, text="Max Downloads:").pack(side="left")
        self.concurrent_var = tk.StringVar(value=str(self.max_concurrent_downloads))
        concurrent_spinbox = ttk.Spinbox(perf_frame, from_=1, to=5, width=5, textvariable=self.concurrent_var,
                                       command=self.update_concurrent_downloads)
        concurrent_spinbox.pack(side="left", padx=5)

        ttk.Label(perf_frame, text="Speed Limit (KB/s):").pack(side="left", padx=(10, 0))
        self.speed_limit_var = tk.StringVar(value="" if self.download_speed_limit is None else str(self.download_speed_limit))
        speed_limit_entry = ttk.Entry(perf_frame, width=8, textvariable=self.speed_limit_var)
        speed_limit_entry.pack(side="left", padx=5)
        speed_limit_entry.bind('<Return>', self.update_speed_limit)
        speed_limit_entry.bind('<FocusOut>', self.update_speed_limit)

        # Queue management buttons
        queue_button_frame = tk.Frame(common_frame)
        queue_button_frame.pack(pady=5)
        self.clear_queue_button = ttk.Button(queue_button_frame, text="Clear Queue", command=self.clear_queue)
        self.clear_queue_button.pack(side="left", padx=5)

        self.resume_button = ttk.Button(queue_button_frame, text="Check for Resumes", command=self.manual_resume_check)
        self.resume_button.pack(side="left", padx=5)

        # Download queue display
        queue_frame = tk.Frame(common_frame)
        queue_frame.pack(pady=5, fill="both", expand=True)

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
        button_frame = tk.Frame(common_frame)
        button_frame.pack(pady=10)
        self.start_queue_button = ttk.Button(button_frame, text="Start Queue", command=self.start_queue_download)
        self.start_queue_button.pack(side="left", padx=5)
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_download, state="disabled")
        self.stop_button.pack(side="left", padx=5)

        # Progress bar
        progress_frame = tk.Frame(common_frame)
        progress_frame.pack(pady=5, fill="x")

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
        self.status_label = ttk.Label(common_frame, text="Enter a YouTube URL and click 'Parse Video' to begin")
        self.status_label.pack(pady=5)

        # Update queue display if there are saved items
        if self.download_queue:
            self.update_queue_display()
            self.status_label.config(text=f"Restored {len(self.download_queue)} items from previous session.")

        # Start clipboard monitoring
        if self.clipboard_monitoring:
            self.start_clipboard_monitoring()

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = folder
            self.folder_label.config(text=self.output_dir)
            self.save_config()

    def open_download_folder(self):
        """Open the download folder in Windows Explorer"""
        try:
            if os.path.exists(self.output_dir):
                # Use Windows Explorer to open the folder
                os.startfile(self.output_dir)
            else:
                # Create the folder if it doesn't exist and then open it
                os.makedirs(self.output_dir, exist_ok=True)
                os.startfile(self.output_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {str(e)}")

    def toggle_clipboard_monitoring(self):
        """Toggle clipboard monitoring on/off"""
        self.clipboard_monitoring = self.clipboard_var.get()
        if self.clipboard_monitoring:
            self.start_clipboard_monitoring()
            self.status_label.config(text="Clipboard monitoring enabled")
        else:
            self.status_label.config(text="Clipboard monitoring disabled")
        self.save_config()

    def start_clipboard_monitoring(self):
        """Start monitoring clipboard for YouTube URLs"""
        self.check_clipboard()

    def check_clipboard(self):
        """Check clipboard for YouTube URLs"""
        if not self.clipboard_monitoring or not PYPERCLIP_AVAILABLE:
            # Schedule next check even if disabled
            self.root.after(self.clipboard_check_interval, self.check_clipboard)
            return

        try:
            current_clipboard = pyperclip.paste()
            if current_clipboard != self.last_clipboard_content:
                self.last_clipboard_content = current_clipboard
                # Only handle single video URLs, not playlists
                if self.is_youtube_video_url(current_clipboard):
                    self.handle_clipboard_url(current_clipboard)
        except Exception as e:
            print(f"Clipboard monitoring error: {e}")

        # Schedule next check
        self.root.after(self.clipboard_check_interval, self.check_clipboard)

    def is_youtube_url(self, url):
        """Check if URL is a valid YouTube URL"""
        if not url or not isinstance(url, str):
            return False

        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/channel/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/@[\w-]+',
        ]

        for pattern in youtube_patterns:
            if re.match(pattern, url.strip()):
                return True
        return False

    def is_playlist_url(self, url):
        """Check if URL is a YouTube playlist URL"""
        if not url or not isinstance(url, str):
            return False

        playlist_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?.*list=[\w-]+',
        ]

        for pattern in playlist_patterns:
            if re.search(pattern, url.strip()):
                return True
        return False

    def is_youtube_video_url(self, url):
        """Check if URL is a valid YouTube single video URL (not playlist)"""
        if not url or not isinstance(url, str):
            return False

        # First check if it's a playlist URL
        if self.is_playlist_url(url):
            return False

        # Check for valid single video patterns
        video_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&(?!list=)[\w=&-]*)*$',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+(?:\?(?!list=)[\w=&-]*)*$',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+(?:\?(?!list=)[\w=&-]*)*$',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/[\w-]+(?:\?(?!list=)[\w=&-]*)*$',
        ]

        for pattern in video_patterns:
            if re.match(pattern, url.strip()):
                return True
        return False

    def handle_clipboard_url(self, url):
        """Handle detected YouTube URL from clipboard"""
        # Only auto-fill if URL field is empty or contains the same URL
        current_url = self.url_entry.get().strip()
        url_stripped = url.strip()

        if not current_url or current_url == url_stripped:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url_stripped)

            # Show notification
            self.status_label.config(text="📋 YouTube URL detected and pasted from clipboard!")

            # Optional: Auto-parse if no video is currently loaded AND this URL hasn't been parsed yet
            if not self.video_info and url_stripped != self.last_parsed_url:
                # Ask user if they want to auto-parse
                self.root.after(100, lambda: self.ask_auto_parse(url_stripped))

    def ask_auto_parse(self, url):
        """Ask user if they want to auto-parse the detected URL"""
        result = messagebox.askyesno("Auto-Parse URL",
                                   "YouTube URL detected in clipboard!\n\n"
                                   f"URL: {url[:50]}{'...' if len(url) > 50 else ''}\n\n"
                                   "Would you like to parse this video automatically?")
        if result:
            self.parse_video()

    def update_concurrent_downloads(self):
        """Update maximum concurrent downloads"""
        try:
            new_value = int(self.concurrent_var.get())
            if 1 <= new_value <= 5:
                self.max_concurrent_downloads = new_value
                # Update thread pool
                self.download_executor.shutdown(wait=False)
                self.download_executor = ThreadPoolExecutor(max_workers=self.max_concurrent_downloads)
                self.save_config()
                self.status_label.config(text=f"Max concurrent downloads set to {new_value}")
        except ValueError:
            self.concurrent_var.set(str(self.max_concurrent_downloads))

    def update_speed_limit(self, event=None):
        """Update download speed limit"""
        try:
            speed_text = self.speed_limit_var.get().strip()
            if speed_text == "":
                self.download_speed_limit = None
                self.status_label.config(text="Speed limit removed (unlimited)")
            else:
                speed_value = int(speed_text)
                if speed_value > 0:
                    self.download_speed_limit = speed_value
                    self.status_label.config(text=f"Speed limit set to {speed_value} KB/s")
                else:
                    raise ValueError("Speed must be positive")
            self.save_config()
        except ValueError:
            self.speed_limit_var.set("" if self.download_speed_limit is None else str(self.download_speed_limit))
            messagebox.showwarning("Invalid Speed", "Please enter a valid positive number for speed limit (KB/s)")

    def parse_playlist(self):
        """Parse the playlist URL and extract video information"""
        url = self.playlist_url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a YouTube playlist URL.")
            return

        if not self.is_playlist_url(url):
            messagebox.showwarning("Invalid URL", "Please enter a valid YouTube playlist URL.")
            return

        # Convert watch URL with list parameter to proper playlist URL
        playlist_url = self.convert_to_playlist_url(url)

        self.parse_playlist_button.config(state="disabled")
        self.playlist_title_label.config(text="Parsing playlist information...")
        self.playlist_listbox.delete(0, tk.END)
        self.add_selected_to_queue_button.config(state="disabled")

        # Run parsing in a separate thread to avoid freezing the GUI
        threading.Thread(target=self._parse_playlist_thread, args=(playlist_url,)).start()

    def convert_to_playlist_url(self, url):
        """Convert various YouTube playlist URL formats to the standard playlist URL"""
        import re

        # Extract playlist ID from various URL formats
        playlist_id = None

        # Pattern 1: https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID
        match = re.search(r'[&?]list=([a-zA-Z0-9_-]+)', url)
        if match:
            playlist_id = match.group(1)

        # Pattern 2: https://www.youtube.com/playlist?list=PLAYLIST_ID
        elif 'playlist?list=' in url:
            match = re.search(r'playlist\?list=([a-zA-Z0-9_-]+)', url)
            if match:
                playlist_id = match.group(1)

        if playlist_id:
            return f"https://www.youtube.com/playlist?list={playlist_id}"
        else:
            return url  # Return original if no playlist ID found

    def _parse_playlist_thread(self, url):
        """Thread function to parse playlist information with progressive loading"""
        try:
            # Reset playlist data
            self.playlist_entries = []
            self.playlist_info = None

            # Clear the listbox first
            self.root.after(0, lambda: self.playlist_listbox.delete(0, tk.END))

            # Update status to show parsing started
            self.root.after(0, lambda: self.playlist_title_label.config(text="Connecting to playlist..."))

            ydl_opts = {
                'quiet': True,  # Disable output for production
                'no_warnings': True,  # Hide warnings for production
                'extract_flat': True,  # Only get basic info, don't download
                'playlistend': 1000,   # Allow up to 1000 videos
                'ignoreerrors': True,  # Continue on errors
                'yes_playlist': True,  # Force playlist extraction
            }

            with YoutubeDL(ydl_opts) as ydl:
                # Get playlist info first
                playlist_info = ydl.extract_info(url, download=False)
                self.playlist_info = playlist_info

                # Update playlist title immediately
                title = playlist_info.get('title', 'Unknown Playlist')
                total_count = playlist_info.get('playlist_count', len(playlist_info.get('entries', [])))

                self.root.after(0, lambda: self.playlist_title_label.config(
                    text=f"Playlist: {title} (Loading... 0/{total_count})"
                ))

                # Process entries progressively
                entries = playlist_info.get('entries', [])

                valid_entries = 0
                for i, entry in enumerate(entries):
                    if entry and entry.get('id'):  # Skip None entries and entries without ID
                        self.playlist_entries.append(entry)
                        valid_entries += 1

                        # Add to GUI immediately
                        video_title = entry.get('title', entry.get('id', f'Video {valid_entries}'))
                        duration = entry.get('duration', 0)
                        duration_str = self.format_duration(duration) if duration else "Unknown"

                        display_text = f"{valid_entries:3d}. {video_title} ({duration_str})"

                        # Update GUI in main thread
                        self.root.after(0, lambda text=display_text: self.playlist_listbox.insert(tk.END, text))

                        # Update progress every 5 items for small playlists, every 25 for large ones, or at the end
                        update_interval = 5 if len(entries) <= 100 else 25
                        if valid_entries % update_interval == 0 or i == len(entries) - 1:
                            progress_text = f"Playlist: {title} (Loading... {valid_entries}/{total_count})"
                            self.root.after(0, lambda text=progress_text: self.playlist_title_label.config(text=text))

                # Final update
                final_count = len(self.playlist_entries)
                final_text = f"Playlist: {title} ({final_count} videos)"

                self.root.after(0, lambda text=final_text: self.playlist_title_label.config(text=text))

                if final_count > 0:
                    self.root.after(0, lambda: self.add_selected_to_queue_button.config(state="normal"))
                else:
                    self.root.after(0, lambda: self.playlist_title_label.config(text=f"Playlist: {title} (No videos found)"))

                self.root.after(0, lambda: self.parse_playlist_button.config(state="normal"))

        except Exception as e:
            error_msg = f"Error parsing playlist: {str(e)}"
            self.root.after(0, lambda: self._show_playlist_parse_error(error_msg))
            self.root.after(0, lambda: self.parse_playlist_button.config(state="normal"))

    def _show_playlist_parse_error(self, error_msg):
        """Show playlist parsing error in main thread"""
        self.playlist_title_label.config(text=error_msg)
        self.parse_playlist_button.config(state="normal")
        messagebox.showerror("Parse Error", error_msg)

    def _update_playlist_info(self):
        """Update GUI with playlist information - now handled progressively in thread"""
        # This method is now mostly handled in the thread itself
        # Just re-enable the parse button
        self.parse_playlist_button.config(state="normal")

    def select_all_playlist_items(self):
        """Select all items in the playlist"""
        self.playlist_listbox.selection_set(0, tk.END)

    def select_none_playlist_items(self):
        """Deselect all items in the playlist"""
        self.playlist_listbox.selection_clear(0, tk.END)

    def add_selected_playlist_items_to_queue(self):
        """Add selected playlist items to download queue"""
        selection = self.playlist_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select videos from the playlist to add to queue.")
            return

        if not self.playlist_entries:
            messagebox.showwarning("No Playlist", "Please parse a playlist first.")
            return

        download_type = self.playlist_download_type.get()
        quality = self.playlist_quality_var.get()

        added_count = 0
        for index in selection:
            if index < len(self.playlist_entries):
                entry = self.playlist_entries[index]

                # Create queue item for playlist video
                queue_item = {
                    'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}",
                    'title': entry.get('title', f'Video {index+1}'),
                    'download_type': download_type,
                    'quality': quality,
                    'video_info': entry.copy(),
                    'available_formats': [],  # Will be populated when downloading
                    'status': 'Queued',
                    'from_playlist': True,
                    'playlist_title': self.playlist_info.get('title', 'Unknown Playlist')
                }

                # Add to queue
                self.download_queue.append(queue_item)
                added_count += 1

        if added_count > 0:
            self.update_queue_display()

            # Check if downloads are currently active and extend the session
            if self.is_queue_processing:
                for i in range(added_count):
                    queue_item = self.download_queue[-(added_count-i)]
                    self.extend_download_session(queue_item)

            queue_status = f"Added {added_count} videos from playlist to queue. Total items: {len(self.download_queue)}"
            if self.is_queue_processing:
                queue_status += " (Download session extended)"
            self.status_label.config(text=queue_status)

    def parse_video(self):
        """Parse the video URL and extract available formats"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a YouTube video URL.")
            return

        # Check if this is a playlist URL
        if self.is_playlist_url(url):
            messagebox.showwarning("Playlist URL Detected",
                                 "This appears to be a playlist URL!\n\n"
                                 "Please use the 'Playlist' tab to process playlists.\n"
                                 "The 'Single Video' tab is only for individual video URLs.\n\n"
                                 "To download just this specific video, remove the '&list=...' "
                                 "part from the URL.")
            return

        # Check if it's a valid YouTube video URL
        if not self.is_youtube_video_url(url):
            messagebox.showwarning("Invalid URL",
                                 "Please enter a valid YouTube video URL.\n\n"
                                 "Supported formats:\n"
                                 "• https://www.youtube.com/watch?v=VIDEO_ID\n"
                                 "• https://youtu.be/VIDEO_ID\n"
                                 "• https://www.youtube.com/embed/VIDEO_ID")
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
                'no_playlist': True,  # Force single video extraction only
            }

            with YoutubeDL(ydl_opts) as ydl:
                self.video_info = ydl.extract_info(url, download=False)
                self.available_formats = self.video_info.get('formats', [])

                # Update GUI in main thread
                self.root.after(0, self._update_video_info)

        except Exception as e:
            error_msg = f"Error parsing video: {str(e)}"
            self.root.after(0, lambda: self._show_parse_error(error_msg))
        finally:
            # Always re-enable the parse button
            self.root.after(0, lambda: self.parse_button.config(state="normal"))

    def _show_parse_error(self, error_msg):
        """Show parsing error in main thread"""
        self.status_label.config(text=error_msg)
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
        if not PIL_AVAILABLE:
            self.thumbnail_label.config(text="Thumbnail\n(PIL not available)", image="")
            return

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
            # Track the URL that was successfully parsed
            self.last_parsed_url = self.url_entry.get().strip()

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

        # Check if downloads are currently active and extend the session
        if self.is_queue_processing:
            self.extend_download_session(queue_item)

        # Clear current video info to allow adding more
        self.clear_current_video()

        queue_status = f"Added '{title}' to queue. Total items: {len(self.download_queue)}"
        if self.is_queue_processing:
            queue_status += " (Download session extended)"
        self.status_label.config(text=queue_status)

    def clear_current_video(self):
        """Clear current video information to allow parsing new video"""
        self.url_entry.delete(0, tk.END)
        self.video_info = None
        self.available_formats = []
        self.last_parsed_url = ""  # Reset the last parsed URL
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
            # Determine status icon
            if item['status'] == 'Queued':
                status_icon = "🔄" if 'resume_data' in item else "⏳"
            elif item['status'] == 'Downloading':
                status_icon = "📥"
            elif item['status'] == 'Completed':
                status_icon = "✅"
            else:
                status_icon = "❌"

            format_text = f"{item['download_type'].upper()}"
            if item['quality'] != 'best':
                if item['download_type'] == 'mp3':
                    format_text += f" {item['quality']} kbps"
                else:
                    format_text += f" {item['quality']}p"
            else:
                format_text += " Best"

            # Add resume indicator
            resume_text = " (Resume)" if 'resume_data' in item else ""

            display_text = f"{status_icon} {item['title']} ({format_text}){resume_text}"
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

    def extend_download_session(self, new_queue_item):
        """Extend current download session with newly added queue item"""
        if not self.is_queue_processing:
            return

        # Mark that queue has been extended
        self.queue_extended = True

        # If we're doing concurrent downloads, submit the new item immediately
        if self.max_concurrent_downloads > 1:
            # Add to concurrent tracking
            download_id = f"download_{len(self.concurrent_progress)}"
            self.concurrent_progress[download_id] = 0

            # Submit new download
            new_queue_item['status'] = 'Downloading'
            future = self.download_executor.submit(self.download_video_from_queue_concurrent, new_queue_item, download_id)
            self.active_futures[future] = (new_queue_item, download_id)

            # Update totals
            self.total_concurrent_downloads += 1

            # Update display
            self.update_queue_display()
            self.update_extended_session_status()

        # For sequential downloads, the item will be picked up naturally when the current download finishes

    def update_extended_session_status(self):
        """Update status message for extended download session"""
        if self.max_concurrent_downloads == 1:
            remaining = len([item for item in self.download_queue if item['status'] == 'Queued'])
            current_pos = self.current_download_index + 1
            total = len(self.download_queue)
            self.status_label.config(text=f"Downloading {current_pos}/{total} (Queue extended - {remaining} items added)")
        else:
            active_count = len([item for item in self.download_queue if item['status'] == 'Downloading'])
            completed_count = len([item for item in self.download_queue if item['status'] == 'Completed'])
            total = len(self.download_queue)
            self.status_label.config(text=f"Concurrent downloads: {active_count} active, {completed_count}/{total} completed (Queue extended)")

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

            # Order from lowest to highest quality (bandwidth-friendly first)
            audio_qualities = ["64", "96", "128", "192", "best"]
            # Set default to lowest quality for bandwidth-friendly downloads
            self.resolution_var.set("64")

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

            # Sort by resolution (lowest first for bandwidth-friendly display)
            video_formats.sort(key=lambda x: x['height'], reverse=False)

            if video_formats:
                # Set default to lowest quality for bandwidth-friendly downloads
                self.resolution_var.set(str(video_formats[0]['height']))

                # Create a list of all resolution options (lowest first, then "best")
                all_resolutions = []
                for fmt in video_formats:
                    all_resolutions.append(str(fmt['height']))
                all_resolutions.append("best")  # Add "Best Available" at the end

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
        """Stop current download or queue processing and interrupt all active processes"""
        self.cancel_requested = True

        # Set the global stop event to interrupt all downloads
        self.download_stop_event.set()

        # Set all individual stop events
        for stop_event in self.stop_events:
            stop_event.set()

        # Cancel any running futures
        for future in list(self.active_futures.keys()):
            try:
                future.cancel()
            except Exception as e:
                print(f"Error cancelling future: {e}")

        # Shutdown and recreate the thread pool executor to force stop
        if hasattr(self, 'download_executor'):
            try:
                self.download_executor.shutdown(wait=False)
            except Exception as e:
                print(f"Error shutting down executor: {e}")

            # Recreate the executor
            self.download_executor = ThreadPoolExecutor(max_workers=self.max_concurrent_downloads)

        if self.is_queue_processing:
            self.status_label.config(text="Stopping queue...")
            self.is_queue_processing = False
            # Clear concurrent progress tracking
            self.concurrent_progress = {}
            self.completed_concurrent_downloads = 0
            self.total_concurrent_downloads = 0
            # Clear dynamic queue tracking
            self.queue_extended = False
            self.active_futures = {}
            self.initial_queue_size = 0
        else:
            self.status_label.config(text="Stopping download...")

        # Clear tracking lists
        self.active_download_processes.clear()
        self.stop_events.clear()

        # Reset progress indicators
        self.progress_var.set(0)
        self.speed_label.config(text="")
        self.elapsed_time_label.config(text="")
        self.download_phase_label.config(text="")
        self.current_download_phase = ""

        # Reset button states
        self.reset_download_buttons()

        # Clear the global stop event for next download
        self.download_stop_event.clear()

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

        # Initialize dynamic queue tracking
        self.initial_queue_size = len(self.download_queue)
        self.queue_extended = False
        self.active_futures = {}

        # Reset progress tracking
        self.progress_var.set(0)
        self.speed_label.config(text="")
        self.download_phase_label.config(text="")
        self.elapsed_time_label.config(text="")

        # Update button states
        self.start_queue_button.config(state="disabled")
        self.start_single_button.config(state="disabled")
        self.stop_button.config(state="normal")

        # Start queue processing
        threading.Thread(target=self.process_download_queue).start()

    def process_download_queue(self):
        """Process all items in the download queue with concurrent downloads"""
        total_items = len(self.download_queue)

        if self.max_concurrent_downloads == 1:
            # Sequential processing for single download
            self.process_queue_sequential(total_items)
        else:
            # Concurrent processing for multiple downloads
            self.process_queue_concurrent(total_items)

    def process_queue_sequential(self, _):
        """Process queue sequentially with dynamic queue extension support"""
        i = 0
        while i < len(self.download_queue) and not self.cancel_requested:
            queue_item = self.download_queue[i]

            # Skip already completed items
            if queue_item['status'] == 'Completed':
                i += 1
                continue

            self.current_download_index = i
            queue_item['status'] = 'Downloading'

            # Update display in main thread
            current_total = len(self.download_queue)
            self.root.after(0, self.update_queue_display)

            if self.queue_extended:
                self.root.after(0, lambda pos=i+1, total=current_total, item=queue_item:
                              self.status_label.config(text=f"Downloading {pos}/{total}: {item['title']} (Queue extended)"))
            else:
                self.root.after(0, lambda pos=i+1, total=current_total, item=queue_item:
                              self.status_label.config(text=f"Downloading {pos}/{total}: {item['title']}"))

            # Set up video info for this download
            self.video_info = queue_item['video_info']
            self.available_formats = queue_item['available_formats']

            # Download the video
            success = self.download_video_from_queue(queue_item)

            # Update status
            current_total = len(self.download_queue)  # Refresh total in case queue was extended
            if success and not self.cancel_requested:
                queue_item['status'] = 'Completed'
                self.root.after(0, lambda pos=i+1, total=current_total, item=queue_item:
                              self.status_label.config(text=f"Completed {pos}/{total}: {item['title']}"))
            else:
                queue_item['status'] = 'Failed'
                self.root.after(0, lambda pos=i+1, total=current_total, item=queue_item:
                              self.status_label.config(text=f"Failed {pos}/{total}: {item['title']}"))

            # Update display
            self.root.after(0, self.update_queue_display)

            # Small delay between downloads
            if not self.cancel_requested and i < len(self.download_queue) - 1:
                time.sleep(1)

            i += 1

        # Queue processing complete
        self.finish_queue_processing(len(self.download_queue))

    def process_queue_concurrent(self, total_items):
        """Process queue with concurrent downloads"""
        # Initialize concurrent progress tracking
        self.concurrent_progress = {}
        self.completed_concurrent_downloads = 0

        # Submit initial downloads to thread pool
        self.active_futures = {}
        download_count = 0

        for queue_item in self.download_queue:
            if self.cancel_requested:
                break

            if queue_item['status'] != 'Completed':
                queue_item['status'] = 'Downloading'
                download_id = f"download_{download_count}"
                self.concurrent_progress[download_id] = 0
                future = self.download_executor.submit(self.download_video_from_queue_concurrent, queue_item, download_id)
                self.active_futures[future] = (queue_item, download_id)
                download_count += 1

        self.total_concurrent_downloads = download_count

        # Update display to show all items as downloading
        self.root.after(0, self.update_queue_display)
        if self.total_concurrent_downloads == 1:
            self.root.after(0, lambda: self.status_label.config(text="Starting download..."))
        else:
            self.root.after(0, lambda: self.status_label.config(text=f"Starting {self.total_concurrent_downloads} concurrent downloads..."))

        # Start progress monitoring
        self.monitor_concurrent_progress()

        # Process completed downloads with dynamic queue support
        self.process_concurrent_downloads_with_extension()

        # Queue processing complete
        self.finish_queue_processing(total_items)

    def process_concurrent_downloads_with_extension(self):
        """Process concurrent downloads with support for dynamic queue extension"""
        completed = 0

        while self.active_futures and not self.cancel_requested:
            # Wait for any download to complete
            for future in as_completed(self.active_futures.copy()):
                if self.cancel_requested:
                    break

                queue_item, _ = self.active_futures.pop(future)

                try:
                    success = future.result()
                    if success:
                        queue_item['status'] = 'Completed'
                        completed += 1
                    else:
                        queue_item['status'] = 'Failed'
                        completed += 1  # Count failed as completed for progress tracking
                except Exception as e:
                    print(f"Download error for {queue_item['title']}: {e}")
                    queue_item['status'] = 'Failed'
                    completed += 1  # Count failed as completed for progress tracking

                # Update completed count
                self.completed_concurrent_downloads = completed

                # Update display
                self.root.after(0, self.update_queue_display)

                # Update status with current progress
                if self.queue_extended:
                    self.root.after(0, self.update_extended_session_status)
                else:
                    self.root.after(0, lambda c=completed, t=self.total_concurrent_downloads:
                                  self.status_label.config(text=f"Completed {c}/{t} concurrent downloads"))

                # Break from inner loop to check for new futures
                break

    def monitor_concurrent_progress(self):
        """Monitor and update progress for concurrent downloads with dynamic queue support"""
        if not self.is_queue_processing:
            return

        # Calculate average progress across all active downloads
        if self.concurrent_progress:
            total_progress = sum(self.concurrent_progress.values())
            avg_progress = total_progress / len(self.concurrent_progress)

            # Factor in completed downloads - use current queue size for dynamic calculation
            current_total = len(self.download_queue)
            completed_count = len([item for item in self.download_queue if item['status'] == 'Completed'])

            if current_total > 0:
                completion_factor = completed_count / current_total
                overall_progress = (completion_factor * 100) + ((1 - completion_factor) * avg_progress)
                self.progress_var.set(overall_progress)

        # Schedule next update
        self.root.after(500, self.monitor_concurrent_progress)

    def finish_queue_processing(self, _):
        """Finish queue processing and update UI"""
        self.is_queue_processing = False
        completed_count = sum(1 for item in self.download_queue if item['status'] == 'Completed')
        failed_count = sum(1 for item in self.download_queue if item['status'] == 'Failed')
        actual_total = len(self.download_queue)

        # Create completion message
        if self.queue_extended:
            message = f"Extended queue complete! {completed_count}/{actual_total} downloads successful"
            if failed_count > 0:
                message += f" ({failed_count} failed)"
            message += f". Started with {self.initial_queue_size}, processed {actual_total} total."
        else:
            message = f"Queue complete! {completed_count}/{actual_total} downloads successful"
            if failed_count > 0:
                message += f" ({failed_count} failed)"
            message += "."

        # Reset dynamic queue tracking
        self.queue_extended = False
        self.active_futures = {}
        self.initial_queue_size = 0

        try:
            self.root.after(0, lambda: self.status_label.config(text=message))
            self.root.after(0, self.reset_download_buttons)
        except RuntimeError:
            # Handle case where main thread is not in main loop (app closing)
            pass

    def download_video_from_queue_concurrent(self, queue_item, download_id):
        """Download a single video from queue item for concurrent processing with resume support"""
        try:
            url = queue_item['url']
            download_type = queue_item['download_type']
            quality = queue_item['quality']

            # Check if this is a resume operation
            is_resume = 'resume_data' in queue_item
            resume_data = queue_item.get('resume_data', {})

            # Parse video info if not available
            if not queue_item.get('video_info'):
                success = self.parse_queue_item_info(queue_item)
                if not success:
                    return False

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

            # Create progress hook for this specific download
            def concurrent_progress_hook(d):
                # Check for cancellation first
                if self.cancel_requested or self.download_stop_event.is_set() or stop_event.is_set():
                    raise KeyboardInterrupt("Download cancelled by user")

                if d['status'] == 'downloading':
                    if 'total_bytes' in d and d['total_bytes']:
                        progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                        self.concurrent_progress[download_id] = progress
                    elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                        progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                        self.concurrent_progress[download_id] = progress
                elif d['status'] == 'finished':
                    self.concurrent_progress[download_id] = 100

            # Create unique filename for concurrent download
            safe_title = "".join(c for c in queue_item['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:50]  # Limit length

            # Setup resume-capable download options for concurrent downloads
            if is_resume:
                # Use existing partial file for resume
                partial_file = resume_data.get('partial_file')
                output_template = partial_file.replace('.part', '.%(ext)s') if partial_file else os.path.join(self.output_dir, f"{safe_title}.%(ext)s")
            else:
                output_template = os.path.join(self.output_dir, f"{safe_title}.%(ext)s")
                # Create resume data entry
                self.create_resume_entry(url, queue_item, output_template)

            ydl_opts = {
                "format": format_selector,
                "ffmpeg_location": self.ffmpeg_path,
                "outtmpl": output_template,
                "postprocessors": [],
                "progress_hooks": [concurrent_progress_hook],
                "continuedl": True,  # Enable resume functionality
                "part": True,  # Create .part files for resuming
                "mtime": True,  # Preserve modification time
                "quiet": True,  # Reduce output for concurrent downloads
                "no_warnings": True
            }

            # Add speed limit if configured
            if self.download_speed_limit:
                ydl_opts["ratelimit"] = self.download_speed_limit * 1024  # Convert KB/s to bytes/s

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

            # Create stop event for this download
            stop_event = threading.Event()
            self.stop_events.append(stop_event)

            # Download the video with interruptible downloader
            ydl = InterruptibleYoutubeDL(stop_event, ydl_opts)
            self.active_download_processes.append(ydl)

            try:
                # Check if already cancelled before starting
                if self.cancel_requested or self.download_stop_event.is_set():
                    return False

                ydl.download([url])

                # Remove from resume data on successful completion
                if url in self.resume_data:
                    del self.resume_data[url]
                    self.save_resume_data()

                # Mark as completed
                self.concurrent_progress[download_id] = 100
                return True
            finally:
                # Remove from active processes
                if ydl in self.active_download_processes:
                    self.active_download_processes.remove(ydl)
                if stop_event in self.stop_events:
                    self.stop_events.remove(stop_event)

        except KeyboardInterrupt:
            print(f"Download interrupted by user: {queue_item['title']}")
            # Save resume data on interruption (partial download may be available)
            if url in self.resume_data:
                self.save_resume_data()
            # Mark as completed even if interrupted
            self.concurrent_progress[download_id] = 100
            return False
        except Exception as e:
            print(f"Error downloading {queue_item['title']}: {e}")

            # Save resume data on error (partial download may be available)
            if url in self.resume_data:
                self.save_resume_data()

            # Mark as completed even if failed
            self.concurrent_progress[download_id] = 100
            return False

    def download_video_from_queue(self, queue_item):
        """Download a single video from queue item with resume support"""
        try:
            url = queue_item['url']
            download_type = queue_item['download_type']
            quality = queue_item['quality']

            # Check if this is a resume operation
            is_resume = 'resume_data' in queue_item
            resume_data = queue_item.get('resume_data', {})

            # Reset progress bar and indicators
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, lambda: self.speed_label.config(text=""))
            self.root.after(0, lambda: self.download_phase_label.config(text=""))
            self.root.after(0, lambda: self.elapsed_time_label.config(text=""))

            if is_resume:
                self.root.after(0, lambda: self.status_label.config(text=f"Resuming download: {queue_item['title']}"))

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

            # Create unique filename for this download
            safe_title = "".join(c for c in queue_item['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:50]  # Limit length

            # Setup resume-capable download options
            if is_resume:
                # Use existing partial file for resume
                partial_file = resume_data.get('partial_file')
                output_template = partial_file.replace('.part', '.%(ext)s') if partial_file else os.path.join(self.output_dir, f"{safe_title}.%(ext)s")
            else:
                output_template = os.path.join(self.output_dir, f"{safe_title}.%(ext)s")
                # Create resume data entry
                self.create_resume_entry(url, queue_item, output_template)

            ydl_opts = {
                "format": format_selector,
                "ffmpeg_location": self.ffmpeg_path,
                "outtmpl": output_template,
                "postprocessors": [],
                "progress_hooks": [self.progress_hook_with_resume],
                "continuedl": True,  # Enable resume functionality
                "part": True,  # Create .part files for resuming
                "mtime": True,  # Preserve modification time
            }

            # Add speed limit if configured
            if self.download_speed_limit:
                ydl_opts["ratelimit"] = self.download_speed_limit * 1024  # Convert KB/s to bytes/s

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

            # Create stop event for this download
            stop_event = threading.Event()
            self.stop_events.append(stop_event)

            # Download the video with interruptible downloader
            ydl = InterruptibleYoutubeDL(stop_event, ydl_opts)
            self.active_download_processes.append(ydl)

            try:
                # Check if already cancelled before starting
                if self.cancel_requested or self.download_stop_event.is_set():
                    return False

                ydl.download([url])

                # Remove from resume data on successful completion
                if url in self.resume_data:
                    del self.resume_data[url]
                    self.save_resume_data()

                return True
            finally:
                # Remove from active processes
                if ydl in self.active_download_processes:
                    self.active_download_processes.remove(ydl)
                if stop_event in self.stop_events:
                    self.stop_events.remove(stop_event)

        except KeyboardInterrupt:
            print(f"Download interrupted by user: {queue_item['title']}")
            # Save resume data on interruption (partial download may be available)
            if url in self.resume_data:
                self.save_resume_data()
            return False
        except Exception as e:
            error_msg = f"Error downloading {queue_item['title']}: {e}"
            print(error_msg)

            # Save resume data on error (partial download may be available)
            if url in self.resume_data:
                self.save_resume_data()

            return False

    def create_resume_entry(self, url, queue_item, output_template):
        """Create resume data entry for a new download"""
        # Generate partial file path
        base_path = output_template.replace('.%(ext)s', '')
        partial_file = f"{base_path}.part"

        self.resume_data[url] = {
            'title': queue_item['title'],
            'download_type': queue_item['download_type'],
            'quality': queue_item['quality'],
            'video_info': queue_item.get('video_info', {}),
            'available_formats': queue_item.get('available_formats', []),
            'partial_file': partial_file,
            'output_template': output_template,
            'created_time': time.time(),
            'last_progress': 0
        }
        self.save_resume_data()

    def progress_hook_with_resume(self, d):
        """Progress hook that also handles resume data updates and checks for cancellation"""
        # Check for cancellation first
        if self.cancel_requested or self.download_stop_event.is_set():
            raise KeyboardInterrupt("Download cancelled by user")

        # Call the original progress hook
        self.progress_hook(d)

        # Update resume data
        if d['status'] == 'downloading':
            url = d.get('info_dict', {}).get('webpage_url', '')
            if url in self.resume_data:
                if 'total_bytes' in d and d['total_bytes']:
                    progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                    self.resume_data[url]['last_progress'] = progress
                elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                    progress = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                    self.resume_data[url]['last_progress'] = progress

                # Update partial file path if it changed
                if 'filename' in d:
                    filename = d['filename']
                    if filename.endswith('.part'):
                        self.resume_data[url]['partial_file'] = filename

                # Save resume data periodically (every 5% progress)
                current_progress = self.resume_data[url]['last_progress']
                if current_progress % 5 < 1:  # Roughly every 5%
                    self.save_resume_data()

        elif d['status'] == 'finished':
            # Download completed, remove from resume data
            url = d.get('info_dict', {}).get('webpage_url', '')
            if url in self.resume_data:
                del self.resume_data[url]
                self.save_resume_data()

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
        # Check for cancellation first
        if self.cancel_requested or self.download_stop_event.is_set():
            raise KeyboardInterrupt("Download cancelled by user")

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

        # Add speed limit if configured
        if self.download_speed_limit:
            ydl_opts["ratelimit"] = self.download_speed_limit * 1024  # Convert KB/s to bytes/s

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

            # Create stop event for this download
            stop_event = threading.Event()
            self.stop_events.append(stop_event)

            ydl = InterruptibleYoutubeDL(stop_event, ydl_opts)
            self.active_download_processes.append(ydl)

            try:
                # Check if already cancelled before starting
                if self.cancel_requested or self.download_stop_event.is_set():
                    return

                ydl.download([url])

                # Ensure progress bar shows 100% when complete and show final elapsed time
                if not self.cancel_requested and not self.download_stop_event.is_set():
                    self.progress_var.set(100)
                    self.speed_label.config(text="")
                    self.download_phase_label.config(text="✅ Complete")

                    # Show final elapsed time
                    if self.download_start_time:
                        total_elapsed = time.time() - self.download_start_time
                        final_elapsed_text = f"Completed in {self.format_elapsed_time(total_elapsed).replace('Elapsed: ', '')}"
                        self.elapsed_time_label.config(text=final_elapsed_text)

                    self.status_label.config(text="Download complete.")
            finally:
                # Remove from active processes
                if ydl in self.active_download_processes:
                    self.active_download_processes.remove(ydl)
                if stop_event in self.stop_events:
                    self.stop_events.remove(stop_event)

        except KeyboardInterrupt:
            self.status_label.config(text="Download cancelled by user.")
            # Reset progress bar, speed display, elapsed time, and download phase on cancellation
            self.progress_var.set(0)
            self.speed_label.config(text="")
            self.elapsed_time_label.config(text="")
            self.download_phase_label.config(text="")
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
