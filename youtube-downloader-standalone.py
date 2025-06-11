#!/usr/bin/env python3
"""
YouTube Downloader - Standalone Version
Uses yt-dlp as subprocess to avoid packaging issues
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
import requests
from PIL import Image, ImageTk
from io import BytesIO
import pyperclip
from concurrent.futures import ThreadPoolExecutor, as_completed

class YouTubeDownloaderStandalone:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube Downloader v1.0")
        self.root.geometry("800x600")
        
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
        """Download yt-dlp executable"""
        try:
            print("📥 Downloading yt-dlp...")
            
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(__file__)
            
            ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
            ytdlp_path = os.path.join(base_path, "yt-dlp.exe")
            
            response = requests.get(ytdlp_url, stream=True)
            response.raise_for_status()
            
            with open(ytdlp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
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
        """Create the main GUI"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # URL input
        ttk.Label(main_frame, text="YouTube URL:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=60)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(buttons_frame, text="Add to Queue", command=self.add_to_queue).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="Start Downloads", command=self.start_downloads).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="Stop Downloads", command=self.stop_downloads).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="Clear Queue", command=self.clear_queue).pack(side=tk.LEFT, padx=(0, 5))
        
        # Queue frame
        queue_frame = ttk.LabelFrame(main_frame, text="Download Queue", padding="5")
        queue_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)
        
        # Queue listbox with scrollbar
        queue_scroll_frame = ttk.Frame(queue_frame)
        queue_scroll_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        queue_scroll_frame.columnconfigure(0, weight=1)
        queue_scroll_frame.rowconfigure(0, weight=1)
        
        self.queue_listbox = tk.Listbox(queue_scroll_frame, height=8)
        self.queue_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        queue_scrollbar = ttk.Scrollbar(queue_scroll_frame, orient=tk.VERTICAL, command=self.queue_listbox.yview)
        queue_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.queue_listbox.configure(yscrollcommand=queue_scrollbar.set)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Download Progress", padding="5")
        progress_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.progress_var).grid(row=0, column=0, sticky=tk.W)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E))
    
    def add_to_queue(self):
        """Add URL to download queue"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a YouTube URL")
            return
        
        if not self.is_valid_url(url):
            messagebox.showwarning("Warning", "Please enter a valid YouTube URL")
            return
        
        # Add to queue
        self.download_queue.append({
            'url': url,
            'status': 'Queued',
            'progress': 0
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
            url_short = item['url'][:50] + "..." if len(item['url']) > 50 else item['url']
            display_text = f"{i+1}. {url_short} - {status} ({progress}%)"
            self.queue_listbox.insert(tk.END, display_text)
    
    def start_downloads(self):
        """Start downloading items from queue"""
        if not self.download_queue:
            messagebox.showwarning("Warning", "No items in queue")
            return
        
        if self.is_downloading:
            messagebox.showinfo("Info", "Downloads already in progress")
            return
        
        if not self.ytdlp_path:
            messagebox.showerror("Error", "yt-dlp not available")
            return
        
        self.is_downloading = True
        self.stop_event.clear()
        
        # Start download thread
        self.download_thread = threading.Thread(target=self.download_worker, daemon=True)
        self.download_thread.start()
        
        self.status_var.set("Downloads started")
    
    def download_worker(self):
        """Worker thread for downloads"""
        try:
            for i, item in enumerate(self.download_queue):
                if self.stop_event.is_set():
                    break
                
                if item['status'] != 'Queued':
                    continue
                
                # Update status
                item['status'] = 'Downloading'
                self.root.after(0, self.update_queue_display)
                self.root.after(0, lambda: self.progress_var.set(f"Downloading item {i+1} of {len(self.download_queue)}"))
                
                # Download using yt-dlp subprocess
                success = self.download_with_ytdlp(item)
                
                if success:
                    item['status'] = 'Completed'
                    item['progress'] = 100
                else:
                    item['status'] = 'Failed'
                
                self.root.after(0, self.update_queue_display)
            
            self.is_downloading = False
            self.root.after(0, lambda: self.progress_var.set("Downloads completed"))
            self.root.after(0, lambda: self.status_var.set("All downloads completed"))
            
        except Exception as e:
            self.is_downloading = False
            self.root.after(0, lambda: self.status_var.set(f"Download error: {e}"))
    
    def download_with_ytdlp(self, item):
        """Download using yt-dlp subprocess"""
        try:
            # Prepare command
            cmd = [
                self.ytdlp_path,
                "--format", "best[height<=720]",
                "--output", os.path.join(self.config['download_path'], "%(title)s.%(ext)s"),
                item['url']
            ]
            
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
                    # Parse progress from yt-dlp output
                    progress_match = re.search(r'(\d+(?:\.\d+)?)%', output)
                    if progress_match:
                        progress = float(progress_match.group(1))
                        item['progress'] = int(progress)
                        self.root.after(0, self.update_queue_display)
            
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
        """Start monitoring clipboard for YouTube URLs"""
        def monitor():
            last_clipboard = ""
            while True:
                try:
                    current_clipboard = pyperclip.paste()
                    if current_clipboard != last_clipboard and self.is_valid_url(current_clipboard):
                        self.root.after(0, lambda: self.url_var.set(current_clipboard))
                        last_clipboard = current_clipboard
                except:
                    pass
                time.sleep(1)
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = YouTubeDownloaderStandalone()
    app.run()
