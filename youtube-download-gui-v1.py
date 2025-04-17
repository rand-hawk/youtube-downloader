import os
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from yt_dlp import YoutubeDL

CONFIG_FILE = "config.json"


class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.video_entries = []
        self.cancel_requested = False
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
        self.source_type = tk.StringVar(value="playlist")
        source_frame = ttk.Frame(self.root)
        source_frame.pack(pady=(10, 0))
        ttk.Radiobutton(source_frame, text="Playlist", variable=self.source_type, value="playlist", command=self.update_input_mode).pack(side="left", padx=5)
        ttk.Radiobutton(source_frame, text="Individual Video(s)", variable=self.source_type, value="individual", command=self.update_input_mode).pack(side="left", padx=5)

        self.url_label = ttk.Label(self.root, text="YouTube Playlist URL:")
        self.url_label.pack()
        self.url_entry = tk.Text(self.root, height=3, width=80)
        self.url_entry.pack(pady=5)

        self.fetch_button = ttk.Button(self.root, text="Fetch Playlist / Add Videos", command=self.fetch_sources)
        self.fetch_button.pack(pady=5)

        self.list_frame = tk.Frame(self.root)
        self.canvas = tk.Canvas(self.list_frame, height=200)
        self.scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.canvas.yview)
        self.checklist_frame = tk.Frame(self.canvas)
        self.checklist_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.checklist_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.list_frame.pack(pady=5, fill="x", padx=10)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=(0, 10))
        ttk.Button(btn_frame, text="Select All", command=self.select_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Deselect All", command=self.deselect_all).pack(side="left", padx=5)

        self.download_type = tk.StringVar(value="mp3")
        ttk.Label(self.root, text="Download Format:").pack()
        ttk.Radiobutton(self.root, text="MP3 (Audio)", variable=self.download_type, value="mp3").pack()
        ttk.Radiobutton(self.root, text="MP4 (Video)", variable=self.download_type, value="mp4").pack()

        folder_frame = tk.Frame(self.root)
        folder_frame.pack(pady=5)
        ttk.Label(folder_frame, text="Save to:").pack(side="left")
        self.folder_label = ttk.Label(folder_frame, text=self.output_dir, width=50)
        self.folder_label.pack(side="left", padx=5)
        ttk.Button(folder_frame, text="Choose Folder", command=self.choose_folder).pack(side="left")

        ffmpeg_frame = tk.Frame(self.root)
        ffmpeg_frame.pack(pady=5)
        ttk.Label(ffmpeg_frame, text="FFmpeg path:").pack(side="left")
        self.ffmpeg_label = ttk.Label(ffmpeg_frame, text=self.ffmpeg_path, width=50)
        self.ffmpeg_label.pack(side="left", padx=5)
        ttk.Button(ffmpeg_frame, text="Choose FFmpeg", command=self.choose_ffmpeg).pack(side="left")

        self.start_button = ttk.Button(self.root, text="Start Download", command=self.start_download)
        self.start_button.pack(pady=(10, 0))
        self.stop_button = ttk.Button(self.root, text="Stop", command=self.stop_download, state="disabled")
        self.stop_button.pack(pady=(5, 10))

        self.status_label = ttk.Label(self.root, text="")
        self.status_label.pack()

    def update_input_mode(self):
        if self.source_type.get() == "playlist":
            self.url_label.config(text="YouTube Playlist URL:")
        else:
            self.url_label.config(text="YouTube Video URL(s) (one per line):")

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

    def select_all(self):
        for _, var in self.video_entries:
            var.set(True)

    def deselect_all(self):
        for _, var in self.video_entries:
            var.set(False)

    def fetch_sources(self):
        self.video_entries.clear()
        for widget in self.checklist_frame.winfo_children():
            widget.destroy()

        urls = self.url_entry.get("1.0", "end").strip().splitlines()
        if not urls:
            messagebox.showwarning("Input Error", "Please enter a URL.")
            return

        for url in urls:
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(self.checklist_frame, text=url, variable=var)
            cb.pack(anchor="w")
            self.video_entries.append((url, var))

    def stop_download(self):
        self.cancel_requested = True
        self.status_label.config(text="Stopping download...")

    def start_download(self):
        self.cancel_requested = False
        selected_urls = [url for url, var in self.video_entries if var.get()]
        if not selected_urls:
            messagebox.showinfo("No Selection", "Please select at least one video to download.")
            return

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        threading.Thread(target=self.download_videos, args=(selected_urls,)).start()

    def download_videos(self, urls):
        for idx, url in enumerate(urls, 1):
            if self.cancel_requested:
                break

            is_mp3 = self.download_type.get() == "mp3"

            ydl_opts = {
                "format": "bestaudio/best" if is_mp3 else "bestvideo+bestaudio/best",
                "ffmpeg_location": self.ffmpeg_path,
                "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
                "postprocessors": []
            }

            if is_mp3:
                ydl_opts["postprocessors"].append({
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                })
            else:
                ydl_opts["postprocessors"].append({
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4"
                })

            try:
                self.status_label.config(text=f"Downloading {idx}/{len(urls)}: {url}")
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                print(f"Error downloading {url}: {e}")

        self.status_label.config(text="Download complete.")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()
