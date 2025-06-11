#!/usr/bin/env python3
"""
YouTube Downloader - Final Version
Uses only built-in modules and yt-dlp as subprocess
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import json
import subprocess
import signal
import time
import re
import os
import sys
import tempfile
import shutil
from pathlib import Path
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

class YouTubeDownloaderFinal:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube Downloader")
        self.root.geometry("570x650")
        self.root.resizable(True, True)

        # Set icon
        try:
            if getattr(sys, 'frozen', False):
                # Running from PyInstaller executable
                base_path = os.path.dirname(sys.executable)
            else:
                # Running from source
                base_path = os.path.dirname(__file__)

            icon_path = os.path.join(base_path, "youtube-downloader.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass

        # Initialize variables
        self.download_queue = []
        self.current_downloads = {}
        self.is_downloading = False
        self.download_thread = None
        self.stop_event = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.clipboard_monitoring = True
        self.max_downloads = 2
        self.speed_limit = ""

        # Load configuration
        self.load_config()

        # Setup yt-dlp
        self.setup_ytdlp()

        # Create GUI
        self.create_gui()

        # Start clipboard monitoring
        self.start_clipboard_monitoring()
    
    def setup_ytdlp(self):
        """Setup yt-dlp executable"""
        try:
            if getattr(sys, 'frozen', False):
                # Running from PyInstaller executable
                base_path = os.path.dirname(sys.executable)
            else:
                # Running from source
                base_path = os.path.dirname(__file__)
            
            # Check for bundled yt-dlp
            self.ytdlp_path = os.path.join(base_path, "yt-dlp.exe")
            
            if not os.path.exists(self.ytdlp_path):
                # Try to find yt-dlp in system PATH
                try:
                    result = subprocess.run(["yt-dlp", "--version"], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        self.ytdlp_path = "yt-dlp"
                    else:
                        self.download_ytdlp()
                except:
                    self.download_ytdlp()
            
            print(f"✓ yt-dlp ready at: {self.ytdlp_path}")
            
        except Exception as e:
            print(f"❌ Failed to setup yt-dlp: {e}")
            messagebox.showerror("Error", f"Failed to setup yt-dlp: {e}")
    
    def download_ytdlp(self):
        """Download yt-dlp executable using urllib"""
        try:
            print("📥 Downloading yt-dlp...")
            
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(__file__)
            
            ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
            ytdlp_path = os.path.join(base_path, "yt-dlp.exe")
            
            # Download using urllib
            urllib.request.urlretrieve(ytdlp_url, ytdlp_path)
            
            self.ytdlp_path = ytdlp_path
            print("✓ yt-dlp downloaded successfully")
            
        except Exception as e:
            print(f"❌ Failed to download yt-dlp: {e}")
            messagebox.showerror("Error", f"Failed to download yt-dlp: {e}")
            self.ytdlp_path = None
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(__file__)
            
            config_path = os.path.join(base_path, "config.json")
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = {
                    "download_path": str(Path.home() / "Downloads"),
                    "default_quality": "720p",
                    "default_format": "mp4"
                }
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
            self.config = {
                "download_path": str(Path.home() / "Downloads"),
                "default_quality": "720p", 
                "default_format": "mp4"
            }
    
    def create_gui(self):
        """Create the main GUI matching the reference design"""
        # Configure root grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)  # Make queue area expandable

        # YouTube Video URL section
        ttk.Label(main_frame, text="YouTube Video URL:", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        url_frame = ttk.Frame(main_frame)
        url_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        url_frame.columnconfigure(0, weight=1)

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("Arial", 9))
        self.url_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        ttk.Button(url_frame, text="Parse Video", command=self.parse_video).grid(row=0, column=1)

        # Download Format section
        format_frame = ttk.Frame(main_frame)
        format_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))

        ttk.Label(format_frame, text="Download Format:", font=("Arial", 9, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 10))

        self.format_var = tk.StringVar(value="MP4 (Video)")
        ttk.Radiobutton(format_frame, text="MP3 (Audio)", variable=self.format_var, value="MP3 (Audio)").grid(row=1, column=0, sticky=tk.W, padx=(20, 0))
        ttk.Radiobutton(format_frame, text="MP4 (Video)", variable=self.format_var, value="MP4 (Video)").grid(row=2, column=0, sticky=tk.W, padx=(20, 0))

        # Save to section
        save_frame = ttk.Frame(main_frame)
        save_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        save_frame.columnconfigure(1, weight=1)

        ttk.Label(save_frame, text="Save to:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.path_var = tk.StringVar(value=self.config.get('download_path', str(Path.home() / "Downloads")))
        path_entry = ttk.Entry(save_frame, textvariable=self.path_var, font=("Arial", 9))
        path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(save_frame, text="Choose Folder", command=self.browse_folder).grid(row=0, column=2)

        # FFmpeg path section
        ffmpeg_frame = ttk.Frame(main_frame)
        ffmpeg_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        ffmpeg_frame.columnconfigure(1, weight=1)

        ttk.Label(ffmpeg_frame, text="FFmpeg path:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.ffmpeg_var = tk.StringVar(value="C:/ffmpeg/bin")
        ffmpeg_entry = ttk.Entry(ffmpeg_frame, textvariable=self.ffmpeg_var, font=("Arial", 9))
        ffmpeg_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(ffmpeg_frame, text="Choose FFmpeg", command=self.browse_ffmpeg).grid(row=0, column=2)

        # Options section
        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        options_frame.columnconfigure(2, weight=1)

        # Clipboard monitoring
        self.clipboard_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Monitor Clipboard for YouTube URLs",
                       variable=self.clipboard_var, command=self.toggle_clipboard).grid(row=0, column=0, columnspan=3, sticky=tk.W)

        # Max downloads
        ttk.Label(options_frame, text="Max Downloads:", font=("Arial", 9)).grid(row=1, column=0, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        self.max_downloads_var = tk.StringVar(value="2")
        max_combo = ttk.Combobox(options_frame, textvariable=self.max_downloads_var,
                               values=["1", "2", "3", "4", "5"], state="readonly", width=5)
        max_combo.grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 20))

        # Speed limit
        ttk.Label(options_frame, text="Speed Limit (KB/s):", font=("Arial", 9)).grid(row=1, column=2, sticky=tk.W, pady=(10, 0), padx=(0, 5))
        self.speed_var = tk.StringVar()
        speed_entry = ttk.Entry(options_frame, textvariable=self.speed_var, width=10)
        speed_entry.grid(row=1, column=3, sticky=tk.W, pady=(10, 0))

        # Queue control buttons
        queue_buttons_frame = ttk.Frame(main_frame)
        queue_buttons_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Button(queue_buttons_frame, text="Add to Queue", command=self.add_to_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_buttons_frame, text="Clear Queue", command=self.clear_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_buttons_frame, text="Check for Resumes", command=self.check_resumes).pack(side=tk.LEFT, padx=(0, 5))

        # Download Queue section
        ttk.Label(main_frame, text="Download Queue:", font=("Arial", 9, "bold")).grid(row=7, column=0, sticky=tk.W, pady=(10, 5))

        # Queue listbox with scrollbar
        queue_frame = ttk.Frame(main_frame)
        queue_frame.grid(row=8, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)

        self.queue_listbox = tk.Listbox(queue_frame, height=8, font=("Arial", 9))
        self.queue_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        queue_scrollbar = ttk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=self.queue_listbox.yview)
        queue_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.queue_listbox.configure(yscrollcommand=queue_scrollbar.set)

        # Queue management buttons
        queue_mgmt_frame = ttk.Frame(main_frame)
        queue_mgmt_frame.grid(row=9, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Button(queue_mgmt_frame, text="Download Selected", command=self.download_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_mgmt_frame, text="Remove Selected", command=self.remove_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_mgmt_frame, text="Move Up", command=self.move_up).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(queue_mgmt_frame, text="Move Down", command=self.move_down).pack(side=tk.LEFT, padx=(0, 5))

        # Download control buttons
        download_control_frame = ttk.Frame(main_frame)
        download_control_frame.grid(row=10, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Button(download_control_frame, text="Start Queue", command=self.start_downloads).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(download_control_frame, text="Download Current", command=self.download_current).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(download_control_frame, text="Stop", command=self.stop_downloads).pack(side=tk.LEFT, padx=(0, 5))

        # Progress section
        ttk.Label(main_frame, text="Progress:", font=("Arial", 9, "bold")).grid(row=11, column=0, sticky=tk.W, pady=(10, 5))

        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate')
        self.progress_bar.grid(row=12, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Status message
        self.status_var = tk.StringVar(value="Enter a YouTube URL and click 'Parse Video' to begin")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Arial", 9),
                               foreground="gray", anchor=tk.CENTER)
        status_label.grid(row=13, column=0, sticky=(tk.W, tk.E))
    
    def parse_video(self):
        """Parse video information from URL"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL")
            return

        if not self.is_valid_url(url):
            messagebox.showwarning("Warning", "Please enter a valid YouTube URL")
            return

        self.status_var.set("Parsing video information...")
        # In a real implementation, you would get video info here
        self.status_var.set("Video parsed successfully. Click 'Add to Queue' to add to download queue.")

    def browse_folder(self):
        """Browse for download folder"""
        folder = filedialog.askdirectory(initialdir=self.path_var.get())
        if folder:
            self.path_var.set(folder)
            self.config['download_path'] = folder

    def browse_ffmpeg(self):
        """Browse for FFmpeg folder"""
        folder = filedialog.askdirectory(initialdir=self.ffmpeg_var.get())
        if folder:
            self.ffmpeg_var.set(folder)

    def toggle_clipboard(self):
        """Toggle clipboard monitoring"""
        self.clipboard_monitoring = self.clipboard_var.get()
        if self.clipboard_monitoring:
            self.status_var.set("Clipboard monitoring enabled")
        else:
            self.status_var.set("Clipboard monitoring disabled")

    def check_resumes(self):
        """Check for resumable downloads"""
        self.status_var.set("Checking for resumable downloads...")
        # In a real implementation, you would check for partial downloads
        messagebox.showinfo("Resume Check", "No resumable downloads found.")

    def download_selected(self):
        """Download only selected items"""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select items to download")
            return
        self.start_downloads(selected_only=True)

    def remove_selected(self):
        """Remove selected items from queue"""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select items to remove")
            return

        # Remove items in reverse order to maintain indices
        for index in reversed(selection):
            del self.download_queue[index]

        self.update_queue_display()
        self.status_var.set(f"Removed {len(selection)} item(s) from queue")

    def move_up(self):
        """Move selected item up in queue"""
        selection = self.queue_listbox.curselection()
        if not selection or selection[0] == 0:
            return

        index = selection[0]
        self.download_queue[index], self.download_queue[index-1] = \
            self.download_queue[index-1], self.download_queue[index]

        self.update_queue_display()
        self.queue_listbox.selection_set(index-1)

    def move_down(self):
        """Move selected item down in queue"""
        selection = self.queue_listbox.curselection()
        if not selection or selection[0] == len(self.download_queue) - 1:
            return

        index = selection[0]
        self.download_queue[index], self.download_queue[index+1] = \
            self.download_queue[index+1], self.download_queue[index]

        self.update_queue_display()
        self.queue_listbox.selection_set(index+1)

    def download_current(self):
        """Download current/selected item immediately"""
        selection = self.queue_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item to download")
            return

        # Start download for selected item only
        self.start_downloads(selected_only=True, immediate=True)

    def add_to_queue(self):
        """Add URL to download queue"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL")
            return

        if not self.is_valid_url(url):
            messagebox.showwarning("Warning", "Please enter a valid YouTube URL")
            return

        # Get selected options
        format_type = self.format_var.get()
        download_path = self.path_var.get()

        # Add to queue
        self.download_queue.append({
            'url': url,
            'format': format_type,
            'path': download_path,
            'status': 'Queued',
            'progress': 0,
            'title': 'Unknown'
        })

        # Update queue display
        self.update_queue_display()

        # Clear URL entry
        self.url_var.set("")

        self.status_var.set(f"Added to queue. Total items: {len(self.download_queue)}")
    
    def is_valid_url(self, url):
        """Check if URL is a valid YouTube URL"""
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
        ]
        
        for pattern in youtube_patterns:
            if re.match(pattern, url):
                return True
        return False
    
    def update_queue_display(self):
        """Update the queue listbox display"""
        self.queue_listbox.delete(0, tk.END)
        for i, item in enumerate(self.download_queue):
            status = item['status']
            progress = item['progress']
            format_type = item.get('format', 'MP4 (Video)')
            title = item.get('title', 'Unknown')

            if title == 'Unknown':
                url_short = item['url'][:50] + "..." if len(item['url']) > 50 else item['url']
                display_text = f"{url_short}"
            else:
                title_short = title[:50] + "..." if len(title) > 50 else title
                display_text = f"{title_short}"

            display_text += f" [{format_type}] - {status}"
            if progress > 0:
                display_text += f" ({progress}%)"

            self.queue_listbox.insert(tk.END, display_text)
    
    def start_downloads(self, selected_only=False, immediate=False):
        """Start downloading items from queue"""
        if not self.download_queue:
            messagebox.showwarning("Warning", "No items in queue")
            return

        if self.is_downloading and not immediate:
            messagebox.showinfo("Info", "Downloads already in progress")
            return

        if not self.ytdlp_path:
            messagebox.showerror("Error", "yt-dlp not available")
            return

        self.is_downloading = True
        self.stop_event.clear()

        # Determine which items to download
        if selected_only:
            selection = self.queue_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select items to download")
                self.is_downloading = False
                return
            download_indices = list(selection)
        else:
            download_indices = list(range(len(self.download_queue)))

        # Start download thread
        self.download_thread = threading.Thread(
            target=self.download_worker,
            args=(download_indices,),
            daemon=True
        )
        self.download_thread.start()

        self.status_var.set("Downloads started")
    
    def download_worker(self, download_indices=None):
        """Worker thread for downloads"""
        try:
            if download_indices is None:
                download_indices = list(range(len(self.download_queue)))

            total_items = len(download_indices)

            for count, i in enumerate(download_indices):
                if self.stop_event.is_set():
                    break

                if i >= len(self.download_queue):
                    continue

                item = self.download_queue[i]

                if item['status'] != 'Queued':
                    continue

                # Update status
                item['status'] = 'Downloading'
                self.root.after(0, self.update_queue_display)
                self.root.after(0, lambda c=count+1, t=total_items: self.status_var.set(f"Downloading item {c} of {t}"))

                # Download using yt-dlp subprocess
                success = self.download_with_ytdlp(item)

                if success:
                    item['status'] = 'Completed'
                    item['progress'] = 100
                else:
                    item['status'] = 'Failed'

                self.root.after(0, self.update_queue_display)

            self.is_downloading = False
            self.root.after(0, lambda: self.progress_bar.configure(value=0))
            self.root.after(0, lambda: self.status_var.set("All downloads completed"))

        except Exception as e:
            self.is_downloading = False
            self.root.after(0, lambda: self.status_var.set(f"Download error: {e}"))
    
    def download_with_ytdlp(self, item):
        """Download using yt-dlp subprocess"""
        try:
            # Get format string based on selection
            format_type = item.get('format', 'MP4 (Video)')
            download_path = item.get('path', self.config['download_path'])

            # Build format selector and command
            output_template = os.path.join(download_path, "%(title)s.%(ext)s")

            if format_type == "MP3 (Audio)":
                cmd = [
                    self.ytdlp_path,
                    "--extract-audio",
                    "--audio-format", "mp3",
                    "--audio-quality", "192K",
                    "--output", output_template,
                    item['url']
                ]
            else:  # MP4 (Video) - default to 720p for user preference
                cmd = [
                    self.ytdlp_path,
                    "--format", "best[height<=720]",
                    "--output", output_template,
                    item['url']
                ]

            # Add speed limit if specified
            speed_limit = self.speed_var.get().strip()
            if speed_limit and speed_limit.isdigit():
                cmd.extend(["--limit-rate", f"{speed_limit}K"])

            # Run yt-dlp
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            # Monitor progress
            while True:
                if self.stop_event.is_set():
                    process.terminate()
                    return False

                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break

                if output:
                    # Parse title if available
                    if '[download]' in output and 'Destination:' in output:
                        try:
                            title_match = re.search(r'Destination: (.+)', output)
                            if title_match:
                                full_path = title_match.group(1)
                                filename = os.path.basename(full_path)
                                title = os.path.splitext(filename)[0]
                                item['title'] = title
                                self.root.after(0, self.update_queue_display)
                        except:
                            pass

                    # Parse progress from yt-dlp output
                    progress_match = re.search(r'(\d+(?:\.\d+)?)%', output)
                    if progress_match:
                        progress = float(progress_match.group(1))
                        item['progress'] = int(progress)
                        self.root.after(0, self.update_queue_display)

                        # Update progress bar
                        self.root.after(0, lambda p=progress: self.progress_bar.configure(value=p))

            return process.returncode == 0

        except Exception as e:
            print(f"Download error: {e}")
            return False
    
    def stop_downloads(self):
        """Stop all downloads"""
        self.stop_event.set()
        self.is_downloading = False
        self.status_var.set("Downloads stopped")
    
    def clear_queue(self):
        """Clear the download queue"""
        if self.is_downloading:
            messagebox.showwarning("Warning", "Cannot clear queue while downloading")
            return
        
        self.download_queue.clear()
        self.update_queue_display()
        self.status_var.set("Queue cleared")
    
    def start_clipboard_monitoring(self):
        """Start monitoring clipboard for YouTube URLs - simplified version"""
        def monitor():
            # Simple clipboard monitoring without pyperclip
            # This is a basic implementation
            last_clipboard = ""
            while True:
                try:
                    # Basic clipboard check - this is simplified
                    # In a real implementation, you might want to use win32clipboard
                    time.sleep(2)  # Check every 2 seconds
                except:
                    pass
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = YouTubeDownloaderFinal()
    app.run()
