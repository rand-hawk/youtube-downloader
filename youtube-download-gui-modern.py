#!/usr/bin/env python3
"""
Modern YouTube Downloader GUI with CustomTkinter
Enhanced UI/UX with modern design elements
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import json
import os
import re
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Import yt-dlp
try:
    from yt_dlp import YoutubeDL
except ImportError:
    print("yt-dlp not found. Please install it with: pip install yt-dlp")
    exit(1)

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

# Import PIL for thumbnails
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("PIL not available. Thumbnails will not be displayed.")

# Import pyperclip for clipboard monitoring
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False
    print("pyperclip not available. Clipboard monitoring disabled.")

# Load theme preference from config
def load_theme_preference():
    try:
        import json
        import os
        config_file = "config.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get('theme', 'dark')
    except:
        pass
    return 'dark'

# Set CustomTkinter appearance
saved_theme = load_theme_preference()
ctk.set_appearance_mode(saved_theme)  # Load saved theme or default to "dark"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

class ModernYouTubeDownloader:
    def __init__(self):
        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("🎬 YouTube Downloader v2.1")
        self.root.geometry("950x720")
        self.root.minsize(900, 650)
        
        # Set window icon
        try:
            icon_path = get_resource_path("youtube-downloader.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass

        # Initialize variables
        self.setup_variables()
        
        # Setup modern UI
        self.setup_modern_ui()
        
        # Load configuration
        self.load_config()
        
        # Start clipboard monitoring
        if PYPERCLIP_AVAILABLE:
            self.check_clipboard()

    def setup_variables(self):
        """Initialize all application variables"""
        # Configuration - use proper paths for PyInstaller builds
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller executable - use executable directory
            app_dir = os.path.dirname(sys.executable)
        else:
            # Running as Python script - use script directory
            app_dir = os.path.dirname(os.path.abspath(__file__))

        self.config_file = os.path.join(app_dir, "config.json")
        self.output_dir = os.path.join(app_dir, "downloaded_media")
        self.max_concurrent_downloads = 3
        self.download_speed_limit = None
        
        # Video information
        self.video_info = None
        self.available_formats = []
        self.current_thumbnail = None
        
        # Download queue system
        self.download_queue = []
        self.current_download_index = 0
        self.is_queue_processing = False
        
        # Playlist processing
        self.playlist_info = None
        self.playlist_entries = []
        
        # Clipboard monitoring
        self.clipboard_monitoring = True
        self.last_clipboard_content = ""
        self.last_parsed_url = ""
        self.clipboard_check_interval = 1000
        
        # Download management
        self.download_executor = ThreadPoolExecutor(max_workers=self.max_concurrent_downloads)
        self.active_downloads = {}
        self.download_start_time = None

        # Stop control for downloads
        self.cancel_requested = False
        self.download_stop_event = threading.Event()
        self.stop_events = []
        self.active_download_processes = []

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

    def setup_modern_ui(self):
        """Setup the modern CustomTkinter UI"""
        # Configure grid weights for responsive design
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # Header frame
        self.setup_header()
        
        # Main content frame
        self.setup_main_content()
        
        # Footer frame
        self.setup_footer()

    def setup_header(self):
        """Setup the header with title and controls"""
        header_frame = ctk.CTkFrame(self.root, height=45, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(1, weight=1)

        # App title with icon
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w", padx=15, pady=8)
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="🎬 YouTube Downloader v2.1",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(side="left")

        # Header controls
        controls_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=2, sticky="e", padx=15, pady=8)
        
        # Theme toggle button
        # Set initial icon based on current theme
        current_mode = ctk.get_appearance_mode()
        initial_icon = "☀️" if current_mode == "dark" else "🌙"

        self.theme_button = ctk.CTkButton(
            controls_frame,
            text=initial_icon,
            width=35,
            height=25,
            command=self.toggle_theme
        )
        self.theme_button.pack(side="right", padx=3)

        # Settings button
        settings_button = ctk.CTkButton(
            controls_frame,
            text="⚙️",
            width=35,
            height=25,
            command=self.open_settings
        )
        settings_button.pack(side="right", padx=3)

    def setup_main_content(self):
        """Setup the main content area with tabs"""
        # Main container
        main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # Tab view
        self.tabview = ctk.CTkTabview(main_frame, height=350)
        self.tabview.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        
        # Add tabs
        self.tabview.add("📹 Single Video")
        self.tabview.add("📋 Playlist")
        self.tabview.add("📊 Analytics")
        
        # Setup tab contents
        self.setup_single_video_tab()
        self.setup_playlist_tab()
        self.setup_analytics_tab()
        
        # Download queue section
        self.setup_download_queue(main_frame)

    def setup_single_video_tab(self):
        """Setup the single video download tab"""
        tab = self.tabview.tab("📹 Single Video")
        tab.grid_columnconfigure(0, weight=1)
        
        # URL input section
        url_frame = ctk.CTkFrame(tab, fg_color="transparent")
        url_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=8)
        url_frame.grid_columnconfigure(0, weight=1)

        url_label = ctk.CTkLabel(url_frame, text="YouTube Video URL:", font=ctk.CTkFont(size=13, weight="bold"))
        url_label.grid(row=0, column=0, sticky="w", pady=(0, 3))

        # URL input with parse button
        url_input_frame = ctk.CTkFrame(url_frame, fg_color="transparent")
        url_input_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        url_input_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            url_input_frame,
            placeholder_text="Paste YouTube video URL here...",
            height=35,
            font=ctk.CTkFont(size=11)
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.parse_button = ctk.CTkButton(
            url_input_frame,
            text="🔍 Parse",
            width=90,
            height=35,
            command=self.parse_video,
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.parse_button.grid(row=0, column=1)
        
        # Video info section
        self.setup_video_info_section(tab)

    def setup_video_info_section(self, parent):
        """Setup the video information display section"""
        info_frame = ctk.CTkFrame(parent)
        info_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=8)
        info_frame.grid_columnconfigure(1, weight=1)

        # Thumbnail frame
        self.thumbnail_frame = ctk.CTkFrame(info_frame, width=140, height=100)
        self.thumbnail_frame.grid(row=0, column=0, sticky="nw", padx=15, pady=15)
        self.thumbnail_frame.grid_propagate(False)

        self.thumbnail_label = ctk.CTkLabel(
            self.thumbnail_frame,
            text="📹\nThumbnail",
            font=ctk.CTkFont(size=11)
        )
        self.thumbnail_label.pack(expand=True)

        # Video details frame
        details_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        details_frame.grid(row=0, column=1, sticky="ew", padx=15, pady=15)
        details_frame.grid_columnconfigure(0, weight=1)
        
        self.video_title_label = ctk.CTkLabel(
            details_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=350,
            justify="left"
        )
        self.video_title_label.grid(row=0, column=0, sticky="w", pady=(0, 8))

        # Format and quality selection
        format_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        format_frame.grid(row=1, column=0, sticky="ew", pady=8)
        
        # Download format selection
        format_label = ctk.CTkLabel(format_frame, text="Format:", font=ctk.CTkFont(size=11, weight="bold"))
        format_label.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.download_type = ctk.StringVar(value="mp4")
        format_mp4 = ctk.CTkRadioButton(format_frame, text="MP4 Video", variable=self.download_type, value="mp4")
        format_mp4.grid(row=0, column=1, padx=8)

        format_mp3 = ctk.CTkRadioButton(format_frame, text="MP3 Audio", variable=self.download_type, value="mp3")
        format_mp3.grid(row=0, column=2, padx=8)

        # Quality selection
        quality_label = ctk.CTkLabel(format_frame, text="Quality:", font=ctk.CTkFont(size=11, weight="bold"))
        quality_label.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(8, 0))

        self.quality_var = ctk.StringVar(value="144")
        self.quality_menu = ctk.CTkOptionMenu(
            format_frame,
            variable=self.quality_var,
            values=["144", "240", "360", "480", "720", "1080", "best"],
            width=110
        )
        self.quality_menu.grid(row=1, column=1, sticky="w", pady=(8, 0))

        # Action buttons
        button_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, sticky="ew", pady=15)
        
        self.add_to_queue_button = ctk.CTkButton(
            button_frame,
            text="➕ Add to Queue",
            command=self.add_to_queue,
            state="disabled",
            width=130,
            height=30
        )
        self.add_to_queue_button.grid(row=0, column=0, padx=(0, 8))

        self.download_now_button = ctk.CTkButton(
            button_frame,
            text="⬇️ Download Now",
            command=self.start_download,
            state="disabled",
            width=130,
            height=30
        )
        self.download_now_button.grid(row=0, column=1)

    def setup_playlist_tab(self):
        """Setup the playlist processing tab"""
        tab = self.tabview.tab("📋 Playlist")
        tab.grid_columnconfigure(0, weight=1)

        # Playlist URL input section
        playlist_url_frame = ctk.CTkFrame(tab, fg_color="transparent")
        playlist_url_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        playlist_url_frame.grid_columnconfigure(0, weight=1)

        playlist_label = ctk.CTkLabel(playlist_url_frame, text="YouTube Playlist URL:", font=ctk.CTkFont(size=14, weight="bold"))
        playlist_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Playlist URL input with parse button
        playlist_input_frame = ctk.CTkFrame(playlist_url_frame, fg_color="transparent")
        playlist_input_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        playlist_input_frame.grid_columnconfigure(0, weight=1)

        self.playlist_url_entry = ctk.CTkEntry(
            playlist_input_frame,
            placeholder_text="Paste YouTube playlist URL here...",
            height=40,
            font=ctk.CTkFont(size=12)
        )
        self.playlist_url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.parse_playlist_button = ctk.CTkButton(
            playlist_input_frame,
            text="🔍 Parse Playlist",
            width=140,
            height=40,
            command=self.parse_playlist,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.parse_playlist_button.grid(row=0, column=1)

        # Playlist info section
        self.playlist_info_frame = ctk.CTkFrame(tab)
        self.playlist_info_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        self.playlist_info_frame.grid_columnconfigure(0, weight=1)

        self.playlist_title_label = ctk.CTkLabel(
            self.playlist_info_frame,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=600
        )
        self.playlist_title_label.grid(row=0, column=0, sticky="w", padx=20, pady=10)

        # Playlist items section
        playlist_items_frame = ctk.CTkFrame(tab)
        playlist_items_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        playlist_items_frame.grid_columnconfigure(0, weight=1)

        # Playlist items header
        items_header = ctk.CTkFrame(playlist_items_frame, fg_color="transparent")
        items_header.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        items_header.grid_columnconfigure(0, weight=1)

        items_title = ctk.CTkLabel(items_header, text="📋 Playlist Items:", font=ctk.CTkFont(size=14, weight="bold"))
        items_title.grid(row=0, column=0, sticky="w")

        # Selection controls
        selection_controls = ctk.CTkFrame(items_header, fg_color="transparent")
        selection_controls.grid(row=0, column=1, sticky="e")

        select_all_btn = ctk.CTkButton(
            selection_controls,
            text="Select All",
            width=80,
            height=30,
            command=self.select_all_playlist_items
        )
        select_all_btn.pack(side="left", padx=2)

        select_none_btn = ctk.CTkButton(
            selection_controls,
            text="Select None",
            width=80,
            height=30,
            command=self.select_none_playlist_items
        )
        select_none_btn.pack(side="left", padx=2)

        # Playlist listbox
        self.playlist_listbox = tk.Listbox(
            playlist_items_frame,
            height=8,
            selectmode=tk.EXTENDED,
            font=("Consolas", 10),
            bg="#212121",
            fg="#ffffff",
            selectbackground="#1f538d",
            relief="flat",
            borderwidth=0
        )
        self.playlist_listbox.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))

        # Playlist controls
        playlist_controls_frame = ctk.CTkFrame(playlist_items_frame, fg_color="transparent")
        playlist_controls_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        playlist_controls_frame.grid_columnconfigure(0, weight=1)

        # Format and quality selection for playlist
        format_quality_frame = ctk.CTkFrame(playlist_controls_frame, fg_color="transparent")
        format_quality_frame.grid(row=0, column=0, sticky="w")

        format_label = ctk.CTkLabel(format_quality_frame, text="Format:", font=ctk.CTkFont(size=12, weight="bold"))
        format_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.playlist_download_type = ctk.StringVar(value="mp4")
        playlist_mp4 = ctk.CTkRadioButton(format_quality_frame, text="MP4", variable=self.playlist_download_type, value="mp4")
        playlist_mp4.grid(row=0, column=1, padx=5)

        playlist_mp3 = ctk.CTkRadioButton(format_quality_frame, text="MP3", variable=self.playlist_download_type, value="mp3")
        playlist_mp3.grid(row=0, column=2, padx=5)

        quality_label = ctk.CTkLabel(format_quality_frame, text="Quality:", font=ctk.CTkFont(size=12, weight="bold"))
        quality_label.grid(row=0, column=3, sticky="w", padx=(20, 10))

        self.playlist_quality_var = ctk.StringVar(value="144")
        playlist_quality_menu = ctk.CTkOptionMenu(
            format_quality_frame,
            variable=self.playlist_quality_var,
            values=["144", "240", "360", "480", "720", "1080", "best"],
            width=100
        )
        playlist_quality_menu.grid(row=0, column=4, padx=5)

        # Add selected to queue button
        self.add_selected_to_queue_button = ctk.CTkButton(
            playlist_controls_frame,
            text="➕ Add Selected to Queue",
            command=self.add_selected_playlist_items_to_queue,
            state="disabled",
            width=180,
            height=35
        )
        self.add_selected_to_queue_button.grid(row=0, column=1, sticky="e", padx=20)

    def setup_analytics_tab(self):
        """Setup the analytics tab"""
        tab = self.tabview.tab("📊 Analytics")
        # Placeholder for now - will implement in next chunk
        placeholder = ctk.CTkLabel(tab, text="Analytics coming soon...", font=ctk.CTkFont(size=16))
        placeholder.pack(expand=True)

    def setup_download_queue(self, parent):
        """Setup the download queue section"""
        # Queue frame
        queue_frame = ctk.CTkFrame(parent)
        queue_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        queue_frame.grid_columnconfigure(0, weight=1)
        queue_frame.grid_rowconfigure(1, weight=1)

        # Queue header
        queue_header = ctk.CTkFrame(queue_frame, fg_color="transparent")
        queue_header.grid(row=0, column=0, sticky="ew", padx=15, pady=8)
        queue_header.grid_columnconfigure(0, weight=1)
        
        queue_title = ctk.CTkLabel(
            queue_header,
            text="📥 Download Queue",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        queue_title.grid(row=0, column=0, sticky="w")

        clear_button = ctk.CTkButton(
            queue_header,
            text="🗑️ Clear",
            width=70,
            height=25,
            command=self.clear_queue
        )
        clear_button.grid(row=0, column=1, sticky="e")

        # Queue listbox (using tkinter Listbox for now, will enhance later)
        self.queue_listbox = tk.Listbox(
            queue_frame,
            height=8,
            font=("Consolas", 9),
            bg="#212121",
            fg="#ffffff",
            selectbackground="#1f538d",
            relief="flat",
            borderwidth=0
        )
        self.queue_listbox.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 8))

    def setup_footer(self):
        """Setup the footer with progress and controls"""
        footer_frame = ctk.CTkFrame(self.root, height=100, corner_radius=0)
        footer_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        footer_frame.grid_columnconfigure(0, weight=1)

        # Progress section
        progress_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
        progress_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=8)
        progress_frame.grid_columnconfigure(0, weight=1)
        
        # Progress info
        progress_info = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_info.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        progress_info.grid_columnconfigure(1, weight=1)

        progress_label = ctk.CTkLabel(progress_info, text="Progress:", font=ctk.CTkFont(size=11, weight="bold"))
        progress_label.grid(row=0, column=0, sticky="w")

        self.speed_label = ctk.CTkLabel(progress_info, text="", font=ctk.CTkFont(size=11))
        self.speed_label.grid(row=0, column=2, sticky="e")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=16)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.progress_bar.set(0)

        # Control buttons
        controls_frame = ctk.CTkFrame(progress_frame, fg_color="transparent")
        controls_frame.grid(row=2, column=0, pady=3)
        
        self.start_queue_button = ctk.CTkButton(
            controls_frame,
            text="▶️ Start Queue",
            command=self.start_queue_download,
            width=110,
            height=30
        )
        self.start_queue_button.pack(side="left", padx=4)

        self.stop_button = ctk.CTkButton(
            controls_frame,
            text="⏹️ Stop",
            command=self.stop_download,
            state="disabled",
            width=70,
            height=30
        )
        self.stop_button.pack(side="left", padx=4)

        # Open folder button
        self.open_folder_button = ctk.CTkButton(
            controls_frame,
            text="📁 Open Downloads",
            command=self.open_download_folder,
            width=120,
            height=30
        )
        self.open_folder_button.pack(side="left", padx=4)

        # Status label
        self.status_label = ctk.CTkLabel(
            footer_frame,
            text="Enter a YouTube URL and click 'Parse' to begin",
            font=ctk.CTkFont(size=11)
        )
        self.status_label.grid(row=1, column=0, pady=(0, 8))

    def toggle_theme(self):
        """Toggle between dark and light themes"""
        # Get current mode and determine new mode
        current_mode = ctk.get_appearance_mode()
        if current_mode.lower() == "dark":
            new_mode = "light"
        else:
            new_mode = "dark"

        print(f"Switching theme from {current_mode} to {new_mode}")

        # Save the theme preference to config
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)

            config['theme'] = new_mode

            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)

        except Exception as e:
            print(f"Error saving theme preference: {e}")

        # Set the new appearance mode
        ctk.set_appearance_mode(new_mode)

        # Update the button text and icon
        if new_mode == "dark":
            self.theme_button.configure(text="☀️")  # Sun icon for dark mode (to switch to light)
        else:
            self.theme_button.configure(text="🌙")  # Moon icon for light mode (to switch to dark)

        # Show a message about restarting for full effect
        try:
            import tkinter.messagebox as msgbox
            msgbox.showinfo("Theme Changed",
                          f"Theme changed to {new_mode} mode.\n\n"
                          "Some elements may require an application restart to fully update.")
        except:
            pass

        print(f"Theme switched to: {new_mode}")

    def open_settings(self):
        """Open settings dialog"""
        self.open_settings_dialog()

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
                                 "The 'Single Video' tab is only for individual video URLs.")
            return

        # Check if it's a valid YouTube video URL
        if not self.is_youtube_video_url(url):
            messagebox.showwarning("Invalid URL",
                                 "Please enter a valid YouTube video URL.")
            return

        self.parse_button.configure(state="disabled", text="🔄 Parsing...")
        self.status_label.configure(text="Parsing video information...")

        # Run parsing in a separate thread
        threading.Thread(target=self._parse_video_thread, args=(url,), daemon=True).start()

    def _parse_video_thread(self, url):
        """Thread function to parse video information"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'no_playlist': True,
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
            self.root.after(0, lambda: self.parse_button.configure(state="normal", text="🔍 Parse"))

    def _update_video_info(self):
        """Update GUI with video information"""
        if self.video_info:
            title = self.video_info.get('title', 'Unknown Title')
            duration = self.video_info.get('duration', 0)
            duration_str = self.format_duration(duration) if duration else "Unknown"

            # Update video title
            self.video_title_label.configure(text=f"{title}\nDuration: {duration_str}")

            # Load thumbnail if available
            self.load_thumbnail()

            # Enable action buttons
            self.add_to_queue_button.configure(state="normal")
            self.download_now_button.configure(state="normal")

            self.status_label.configure(text="Video parsed successfully. Select format and quality, then add to queue or download.")

    def _show_parse_error(self, error_msg):
        """Show parsing error in main thread"""
        self.status_label.configure(text=error_msg)
        messagebox.showerror("Parse Error", error_msg)

    def load_thumbnail(self):
        """Load and display video thumbnail"""
        if not PIL_AVAILABLE or not self.video_info:
            return

        thumbnail_url = self.video_info.get('thumbnail')
        if thumbnail_url:
            threading.Thread(target=self._load_thumbnail_thread, args=(thumbnail_url,), daemon=True).start()

    def _load_thumbnail_thread(self, thumbnail_url):
        """Load thumbnail in background thread"""
        try:
            import urllib.request

            # Download thumbnail
            urllib.request.urlretrieve(thumbnail_url, "temp_thumbnail.jpg")

            # Load and resize image
            image = Image.open("temp_thumbnail.jpg")
            image = image.resize((140, 100), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)

            # Update GUI in main thread
            self.root.after(0, lambda: self._update_thumbnail(photo))

            # Clean up
            os.remove("temp_thumbnail.jpg")

        except Exception as e:
            print(f"Error loading thumbnail: {e}")

    def _update_thumbnail(self, photo):
        """Update thumbnail in main thread"""
        self.current_thumbnail = photo
        self.thumbnail_label.configure(image=photo, text="")

    def add_to_queue(self):
        """Add video to download queue"""
        if not self.video_info:
            messagebox.showwarning("No Video", "Please parse a video first.")
            return

        download_type = self.download_type.get()
        quality = self.quality_var.get()

        queue_item = {
            'url': self.video_info.get('webpage_url', ''),
            'title': self.video_info.get('title', 'Unknown Title'),
            'download_type': download_type,
            'quality': quality,
            'video_info': self.video_info.copy(),
            'available_formats': self.available_formats.copy(),
            'status': 'Queued',
            'from_playlist': False
        }

        self.download_queue.append(queue_item)
        self.update_queue_display()

        self.status_label.configure(text=f"Added to queue. Total items: {len(self.download_queue)}")

    def update_queue_display(self):
        """Update the queue listbox display"""
        self.queue_listbox.delete(0, tk.END)

        for i, item in enumerate(self.download_queue):
            status_icon = self.get_status_icon(item['status'])
            format_info = f"{item['download_type'].upper()}-{item['quality']}"
            display_text = f"{status_icon} {item['title'][:50]}... ({format_info})"
            self.queue_listbox.insert(tk.END, display_text)

    def get_status_icon(self, status):
        """Get icon for download status"""
        icons = {
            'Queued': '⏳',
            'Downloading': '📥',
            'Completed': '✅',
            'Error': '❌',
            'Paused': '⏸️'
        }
        return icons.get(status, '❓')

    def start_download(self):
        """Start single video download"""
        if not self.video_info:
            messagebox.showwarning("No Video", "Please parse a video first.")
            return

        # Add to queue and start immediately
        self.add_to_queue()
        if self.download_queue:
            self.download_single_item(len(self.download_queue) - 1)

    def clear_queue(self):
        """Clear download queue"""
        self.download_queue.clear()
        self.queue_listbox.delete(0, tk.END)
        self.status_label.configure(text="Queue cleared.")

    def start_queue_download(self):
        """Start queue processing"""
        if not self.download_queue:
            messagebox.showinfo("Empty Queue", "No items in download queue.")
            return

        # Reset stop control
        self.cancel_requested = False
        self.download_stop_event.clear()

        # Reset any stopped items back to queued for resume functionality
        for item in self.download_queue:
            if item['status'] == 'Stopped':
                item['status'] = 'Queued'
                print(f"Resuming download: {item['title']}")

        self.is_queue_processing = True
        self.start_queue_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        # Update display to show resumed items
        self.update_queue_display()

        # Start downloading items
        threading.Thread(target=self._process_queue, daemon=True).start()

    def _process_queue(self):
        """Process download queue"""
        try:
            for i, item in enumerate(self.download_queue):
                if not self.is_queue_processing or self.cancel_requested:  # Check if stopped
                    break

                # Process items that are queued or stopped (for resume functionality)
                if item['status'] in ['Queued', 'Stopped']:
                    self.download_single_item(i)

                    # Wait for this item to complete before starting next
                    while item['status'] == 'Downloading' and self.is_queue_processing and not self.cancel_requested:
                        threading.Event().wait(0.5)  # Small delay

        except Exception as e:
            print(f"Queue processing error: {e}")
        finally:
            self.is_queue_processing = False
            self.root.after(0, lambda: self.start_queue_button.configure(state="normal"))
            self.root.after(0, lambda: self.stop_button.configure(state="disabled"))
            self.root.after(0, lambda: self.status_label.configure(text="Queue processing completed."))

    def download_single_item(self, index):
        """Download a single item from the queue"""
        if index >= len(self.download_queue):
            return

        item = self.download_queue[index]
        item['status'] = 'Downloading'
        self.root.after(0, self.update_queue_display)

        # Run download in separate thread
        threading.Thread(target=self._download_item_thread, args=(item, index), daemon=True).start()

    def _download_item_thread(self, item, index):
        """Thread function to download a single item"""
        try:
            url = item['url']
            download_type = item['download_type']
            quality = item['quality']

            # Determine if this is an MP3 download first
            is_mp3 = download_type == 'mp3'

            # Use the GUI-defined output directory with user-friendly filename approach
            import re

            # Extract video ID from YouTube URL
            video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', url)
            video_id = video_id_match.group(1) if video_id_match else "unknown"

            # Create a user-friendly filename with title + quality + video ID
            # Sanitize the title for Windows filename compatibility
            safe_title = "".join(c for c in item['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = re.sub(r'\s+', ' ', safe_title)  # Replace multiple spaces with single space
            safe_title = safe_title.strip()  # Remove leading/trailing spaces

            # Format quality for filename
            if quality == 'best':
                quality_tag = 'Best'
            elif is_mp3:
                quality_tag = f'{quality}kbps'
            else:
                quality_tag = f'{quality}p'

            # Limit title length and combine with quality and video ID
            if safe_title:
                # Use first 25 characters of title + quality + video ID for identification
                title_part = safe_title[:25].rstrip()
                simple_filename = f"{title_part} [{quality_tag}] [{video_id}]"
            else:
                # Fallback to quality + video ID if title sanitization fails
                simple_filename = f"{quality_tag} [{video_id}]"

            # Use the GUI-defined output directory
            os.makedirs(self.output_dir, exist_ok=True)

            # Create output template with the GUI directory
            output_template = os.path.join(self.output_dir, f"{simple_filename}.%(ext)s")

            # Use the exact working format selector from the original version
            # Build format selector based on download type and quality
            if is_mp3:
                format_selector = "bestaudio/best"
            else:
                if quality == 'best':
                    format_selector = "bestvideo+bestaudio/best"
                else:
                    height = quality
                    format_selector = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"

            # Configure yt-dlp options with a different approach - avoid merging issues
            ffmpeg_path = self.get_ffmpeg_path()

            # Test if we can write to the GUI-defined directory first
            test_file = os.path.join(self.output_dir, "test_write.txt")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                print(f"Directory write test: PASSED ({self.output_dir})")
            except Exception as e:
                print(f"Directory write test: FAILED ({self.output_dir}) - {e}")

            # Use EXACT ydl_opts from working version
            ydl_opts = {
                "format": format_selector,
                "ffmpeg_location": ffmpeg_path,
                "outtmpl": output_template,
                "postprocessors": [],
                "progress_hooks": [self.progress_hook],
                "continuedl": True,  # Enable resume functionality
                "part": True,  # Create .part files for resuming
                "mtime": True,  # Preserve modification time
                "quiet": True,  # Reduce output for stability
                "no_warnings": True
            }

            print(f"FFmpeg found at: {ffmpeg_path}")
            print(f"Using format selector: {format_selector}")
            print(f"Output template: {output_template}")
            print(f"Output directory exists: {os.path.exists(self.output_dir)}")
            print(f"Output directory writable: {os.access(self.output_dir, os.W_OK)}")

            # Add postprocessors EXACTLY like the working version
            if is_mp3:
                audio_quality = quality if quality != "best" else "192"
                ydl_opts["postprocessors"].append({
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": audio_quality,
                })
            else:
                # Simple video postprocessor - just like the working version
                ydl_opts["postprocessors"].append({
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4"
                })



            print(f"Downloading: {item['title']}")
            print(f"URL: {url}")
            print(f"Quality requested: {quality}")
            print(f"Download type: {download_type}")
            print(f"Format: {ydl_opts.get('format', 'default')}")
            print(f"Output: {output_template}")

            # Create stop event for this download
            stop_event = threading.Event()
            self.stop_events.append(stop_event)

            # Download the video/audio with interruptible downloader
            ydl = InterruptibleYoutubeDL(stop_event, ydl_opts)
            self.active_download_processes.append(ydl)

            try:
                # Check if already cancelled before starting
                if self.cancel_requested or self.download_stop_event.is_set():
                    return

                ydl.download([url])

                # Update status to completed
                item['status'] = 'Completed'
                self.root.after(0, lambda: self.update_queue_display())
                self.root.after(0, lambda: self.status_label.configure(text=f"Downloaded: {item['title']}"))

            finally:
                # Remove from active processes
                if ydl in self.active_download_processes:
                    self.active_download_processes.remove(ydl)
                if stop_event in self.stop_events:
                    self.stop_events.remove(stop_event)

        except KeyboardInterrupt:
            print(f"Download interrupted by user: {item['title']}")
            item['status'] = 'Stopped'
            self.root.after(0, lambda: self.update_queue_display())
            self.root.after(0, lambda: self.status_label.configure(text=f"Download stopped: {item['title']}"))

        except Exception as e:
            item['status'] = 'Error'
            error_msg = f"Download failed: {str(e)}"
            self.root.after(0, lambda: self.update_queue_display())
            self.root.after(0, lambda: self.status_label.configure(text=error_msg))

            # Comprehensive error logging
            print(f"=" * 60)
            print(f"DOWNLOAD ERROR DETAILS:")
            print(f"=" * 60)
            print(f"Video: {item['title']}")
            print(f"URL: {item['url']}")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")

            # Import traceback for detailed error info
            import traceback
            print(f"Full traceback:")
            traceback.print_exc()
            print(f"=" * 60)

    def sanitize_filename(self, filename):
        """Sanitize filename for safe file system usage"""
        import unicodedata
        import re

        # Normalize Unicode characters
        filename = unicodedata.normalize('NFKD', filename)

        # Replace non-ASCII characters with ASCII equivalents or remove them
        filename = filename.encode('ascii', 'ignore').decode('ascii')

        # Remove or replace ALL problematic characters for Windows
        # This includes: < > : " / \ | ? * ( ) [ ] { } ' ` ~ ! @ # $ % ^ & + = , ;
        invalid_chars = '<>:"/\\|?*()[]{}\'`~!@#$%^&+=,;'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Replace dots with underscores (except for file extension)
        filename = filename.replace('.', '_')

        # Replace multiple spaces, underscores, and dashes with single underscore
        filename = re.sub(r'[_\s\-]+', '_', filename)

        # Remove leading/trailing underscores and spaces
        filename = filename.strip('_').strip()

        # Limit length to be safe
        if len(filename) > 80:
            filename = filename[:80]

        # Ensure filename is not empty and doesn't start with numbers only
        if not filename or filename.isdigit():
            filename = "video_" + filename if filename else "video"

        return filename

    def get_format_selector(self, download_type, quality):
        """Get format selector string for yt-dlp"""
        if download_type == 'mp3':
            return 'bestaudio/best'

        if quality == 'best':
            return 'best'
        else:
            # Very flexible format selection with multiple fallbacks
            return f'best[height<={quality}]/worst[height>={quality}]/best/worst'

    def get_ffmpeg_path(self):
        """Get FFmpeg path - works for both development and PyInstaller builds"""
        # For PyInstaller builds, check the bundled ffmpeg directory
        bundled_ffmpeg_dir = get_resource_path('ffmpeg')
        bundled_ffmpeg_exe = os.path.join(bundled_ffmpeg_dir, 'ffmpeg.exe')
        if os.path.exists(bundled_ffmpeg_exe):
            print(f"Found bundled FFmpeg at: {bundled_ffmpeg_dir}")
            return bundled_ffmpeg_dir

        # Check if FFmpeg is in the same directory as the executable (for portable version)
        try:
            if getattr(sys, 'frozen', False):
                # Running as PyInstaller executable
                exe_dir = os.path.dirname(sys.executable)
            else:
                # Running as Python script
                exe_dir = os.path.dirname(os.path.abspath(__file__))

            local_ffmpeg_dir = os.path.join(exe_dir, 'ffmpeg')
            local_ffmpeg_exe = os.path.join(local_ffmpeg_dir, 'ffmpeg.exe')
            if os.path.exists(local_ffmpeg_exe):
                print(f"Found local FFmpeg at: {local_ffmpeg_dir}")
                return local_ffmpeg_dir
        except Exception as e:
            print(f"Error checking local FFmpeg: {e}")

        # Check if FFmpeg is in ffmpeg subdirectory of current working directory
        ffmpeg_dir = os.path.join(os.getcwd(), 'ffmpeg')
        ffmpeg_exe = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
        if os.path.exists(ffmpeg_exe):
            print(f"Found FFmpeg in working directory: {ffmpeg_dir}")
            return ffmpeg_dir

        print("FFmpeg not found in any expected location")
        return None

    def progress_hook(self, d):
        """Progress hook for yt-dlp downloads"""
        try:
            # Check for cancellation first
            if self.cancel_requested or self.download_stop_event.is_set():
                raise KeyboardInterrupt("Download cancelled by user")

            if d['status'] == 'downloading':
                # Calculate progress percentage
                if 'total_bytes' in d and d['total_bytes']:
                    progress = d['downloaded_bytes'] / d['total_bytes']
                elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                    progress = d['downloaded_bytes'] / d['total_bytes_estimate']
                else:
                    progress = 0

                # Update progress bar in main thread
                self.root.after(0, lambda: self.progress_bar.set(progress))

                # Update speed info
                speed = d.get('speed', 0)
                if speed:
                    speed_mb = speed / (1024 * 1024)
                    speed_text = f"Speed: {speed_mb:.1f} MB/s"
                else:
                    speed_text = "Speed: Calculating..."

                self.root.after(0, lambda: self.speed_label.configure(text=speed_text))

            elif d['status'] == 'finished':
                # Download completed
                self.root.after(0, lambda: self.progress_bar.set(1.0))
                self.root.after(0, lambda: self.speed_label.configure(text="Download completed"))

        except Exception as e:
            print(f"Progress hook error: {e}")

    def convert_video_quality(self, safe_title, target_quality):
        """Convert video to target quality using FFmpeg"""
        try:
            ffmpeg_path = self.get_ffmpeg_path()
            if not ffmpeg_path:
                print("FFmpeg not found, skipping quality conversion")
                return

            # Find the downloaded file
            input_file = None
            for ext in ['.mp4', '.webm', '.mkv']:
                potential_file = os.path.join(self.output_dir, f"{safe_title}{ext}")
                if os.path.exists(potential_file):
                    input_file = potential_file
                    break

            if not input_file:
                print(f"Could not find downloaded file for {safe_title}")
                return

            # Create output filename with quality suffix
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}_{target_quality}p.mp4"

            # FFmpeg command for quality conversion
            ffmpeg_exe = os.path.join(ffmpeg_path, 'ffmpeg.exe')
            cmd = [
                ffmpeg_exe,
                '-i', input_file,
                '-vf', f'scale=-2:{target_quality}',
                '-c:a', 'copy',
                '-y',  # Overwrite output file
                output_file
            ]

            print(f"Converting {safe_title} to {target_quality}p...")
            self.root.after(0, lambda: self.status_label.configure(text=f"Converting to {target_quality}p..."))

            # Run FFmpeg conversion
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                # Conversion successful, remove original file
                os.remove(input_file)
                print(f"Successfully converted to {target_quality}p: {output_file}")
                self.root.after(0, lambda: self.status_label.configure(text=f"Converted to {target_quality}p: {safe_title}"))
            else:
                print(f"FFmpeg conversion failed: {result.stderr}")
                self.root.after(0, lambda: self.status_label.configure(text=f"Conversion failed for {safe_title}"))

        except Exception as e:
            print(f"Error converting video quality: {e}")
            self.root.after(0, lambda: self.status_label.configure(text=f"Conversion error: {str(e)}"))

    def stop_download(self):
        """Stop current download or queue processing and interrupt all active processes"""
        self.cancel_requested = True

        # Set the global stop event to interrupt all downloads
        self.download_stop_event.set()

        # Set all individual stop events
        for stop_event in self.stop_events:
            stop_event.set()

        # Stop queue processing
        if self.is_queue_processing:
            self.is_queue_processing = False
            self.status_label.configure(text="Stopping queue...")
        else:
            self.status_label.configure(text="Stopping download...")

        # Update button states
        self.start_queue_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

        print("Stop requested - interrupting all active downloads")

    def check_clipboard(self):
        """Check clipboard for YouTube URLs"""
        if not self.clipboard_monitoring or not PYPERCLIP_AVAILABLE:
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

    def handle_clipboard_url(self, url):
        """Handle URL detected from clipboard"""
        if url != self.last_parsed_url:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)
            self.last_parsed_url = url

    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.output_dir = config.get('output_dir', self.output_dir)
                    self.max_concurrent_downloads = config.get('max_concurrent_downloads', self.max_concurrent_downloads)
                    self.download_speed_limit = config.get('download_speed_limit', self.download_speed_limit)
                    self.clipboard_monitoring = config.get('clipboard_monitoring', self.clipboard_monitoring)
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        """Save configuration to file"""
        try:
            config = {
                'output_dir': self.output_dir,
                'max_concurrent_downloads': self.max_concurrent_downloads,
                'download_speed_limit': self.download_speed_limit,
                'clipboard_monitoring': self.clipboard_monitoring
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    # Utility methods
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
        """Check if URL is a valid YouTube single video URL"""
        if not url or not isinstance(url, str):
            return False

        if self.is_playlist_url(url):
            return False

        video_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&(?!list=)[\w=&-]*)*$',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+(?:\?(?!list=)[\w=&-]*)*$',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+(?:\?(?!list=)[\w=&-]*)*$',
        ]

        for pattern in video_patterns:
            if re.match(pattern, url.strip()):
                return True
        return False

    def format_duration(self, seconds):
        """Format duration in seconds to readable format"""
        if not seconds:
            return "Unknown"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def open_settings_dialog(self):
        """Open settings dialog window"""
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("⚙️ YouTube Downloader v2.1 - Settings")
        settings_window.geometry("450x350")
        settings_window.transient(self.root)
        settings_window.grab_set()

        # Settings content
        settings_label = ctk.CTkLabel(
            settings_window,
            text="Settings",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        settings_label.pack(pady=20)

        # Output directory setting
        dir_frame = ctk.CTkFrame(settings_window, fg_color="transparent")
        dir_frame.pack(fill="x", padx=20, pady=10)

        dir_label = ctk.CTkLabel(dir_frame, text="Download Directory:", font=ctk.CTkFont(size=14, weight="bold"))
        dir_label.pack(anchor="w")

        dir_display = ctk.CTkLabel(dir_frame, text=self.output_dir, font=ctk.CTkFont(size=12))
        dir_display.pack(anchor="w", pady=(5, 10))

        dir_button = ctk.CTkButton(dir_frame, text="📁 Choose Directory", command=self.choose_output_directory)
        dir_button.pack(anchor="w")

        # Close button
        close_button = ctk.CTkButton(
            settings_window,
            text="Close",
            command=settings_window.destroy,
            width=100
        )
        close_button.pack(pady=20)

    def choose_output_directory(self):
        """Choose output directory"""
        directory = filedialog.askdirectory(initialdir=self.output_dir)
        if directory:
            self.output_dir = directory
            self.save_config()

    def open_download_folder(self):
        """Open the download folder in file explorer"""
        try:
            # Create the directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)

            # Open the folder in file explorer
            if os.name == 'nt':  # Windows
                os.startfile(self.output_dir)
            elif os.name == 'posix':  # macOS and Linux
                if sys.platform == 'darwin':  # macOS
                    subprocess.run(['open', self.output_dir])
                else:  # Linux
                    subprocess.run(['xdg-open', self.output_dir])

            self.status_label.configure(text=f"Opened download folder: {self.output_dir}")

        except Exception as e:
            error_msg = f"Error opening download folder: {str(e)}"
            self.status_label.configure(text=error_msg)
            messagebox.showerror("Error", error_msg)

    # Playlist processing methods
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

        self.parse_playlist_button.configure(state="disabled", text="🔄 Parsing...")
        self.playlist_title_label.configure(text="Parsing playlist information...")
        self.playlist_listbox.delete(0, tk.END)
        self.add_selected_to_queue_button.configure(state="disabled")

        # Run parsing in a separate thread
        threading.Thread(target=self._parse_playlist_thread, args=(playlist_url,), daemon=True).start()

    def convert_to_playlist_url(self, url):
        """Convert various YouTube playlist URL formats to the standard playlist URL"""
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
            return url

    def _parse_playlist_thread(self, url):
        """Thread function to parse playlist information with progressive loading"""
        try:
            # Reset playlist data
            self.playlist_entries = []
            self.playlist_info = None

            # Clear the listbox first
            self.root.after(0, lambda: self.playlist_listbox.delete(0, tk.END))

            # Update status to show parsing started
            self.root.after(0, lambda: self.playlist_title_label.configure(text="Connecting to playlist..."))

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'playlistend': 1000,
                'ignoreerrors': True,
                'yes_playlist': True,
            }

            with YoutubeDL(ydl_opts) as ydl:
                # Get playlist info first
                playlist_info = ydl.extract_info(url, download=False)
                self.playlist_info = playlist_info

                # Update playlist title immediately
                title = playlist_info.get('title', 'Unknown Playlist')
                total_count = playlist_info.get('playlist_count', len(playlist_info.get('entries', [])))

                self.root.after(0, lambda: self.playlist_title_label.configure(
                    text=f"Playlist: {title} (Loading... 0/{total_count})"
                ))

                # Process entries progressively
                entries = playlist_info.get('entries', [])

                valid_entries = 0
                for i, entry in enumerate(entries):
                    if entry and entry.get('id'):
                        self.playlist_entries.append(entry)
                        valid_entries += 1

                        # Add to GUI immediately
                        video_title = entry.get('title', entry.get('id', f'Video {valid_entries}'))
                        duration = entry.get('duration', 0)
                        duration_str = self.format_duration(duration) if duration else "Unknown"

                        display_text = f"{valid_entries:3d}. {video_title} ({duration_str})"

                        # Update GUI in main thread
                        self.root.after(0, lambda text=display_text: self.playlist_listbox.insert(tk.END, text))

                        # Update progress every 5 items for small playlists, every 25 for large ones
                        update_interval = 5 if len(entries) <= 100 else 25
                        if valid_entries % update_interval == 0 or i == len(entries) - 1:
                            progress_text = f"Playlist: {title} (Loading... {valid_entries}/{total_count})"
                            self.root.after(0, lambda text=progress_text: self.playlist_title_label.configure(text=text))

                # Final update
                final_count = len(self.playlist_entries)
                final_text = f"Playlist: {title} ({final_count} videos)"

                self.root.after(0, lambda text=final_text: self.playlist_title_label.configure(text=text))

                if final_count > 0:
                    self.root.after(0, lambda: self.add_selected_to_queue_button.configure(state="normal"))
                else:
                    self.root.after(0, lambda: self.playlist_title_label.configure(text=f"Playlist: {title} (No videos found)"))

                self.root.after(0, lambda: self.parse_playlist_button.configure(state="normal", text="🔍 Parse Playlist"))

        except Exception as e:
            error_msg = f"Error parsing playlist: {str(e)}"
            self.root.after(0, lambda: self._show_playlist_parse_error(error_msg))
            self.root.after(0, lambda: self.parse_playlist_button.configure(state="normal", text="🔍 Parse Playlist"))

    def _show_playlist_parse_error(self, error_msg):
        """Show playlist parsing error in main thread"""
        self.playlist_title_label.configure(text=error_msg)
        messagebox.showerror("Parse Error", error_msg)

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
                    'available_formats': [],
                    'status': 'Queued',
                    'from_playlist': True,
                    'playlist_title': self.playlist_info.get('title', 'Unknown Playlist')
                }

                # Add to queue
                self.download_queue.append(queue_item)
                added_count += 1

        if added_count > 0:
            self.update_queue_display()

            queue_status = f"Added {added_count} videos from playlist to queue. Total items: {len(self.download_queue)}"
            self.status_label.configure(text=queue_status)

    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = ModernYouTubeDownloader()
    app.run()
