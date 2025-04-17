import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from yt_dlp import YoutubeDL


class YouTubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.video_entries = []
        self.cancel_requested = False
        self.output_dir = os.path.abspath("downloaded_media")
        self.ffmpeg_path = "c:/ffmpeg/bin"
        os.makedirs(self.output_dir, exist_ok=True)

        self.setup_widgets()

    def setup_widgets(self):
        # Source type (playlist or individual)
        self.source_type = tk.StringVar(value="playlist")
        source_frame = ttk.Frame(self.root)
        source_frame.pack(pady=(10, 0))
        ttk.Radiobutton(source_frame, text="Playlist", variable=self.source_type, value="playlist", command=self.update_input_mode).pack(side="left", padx=5)
        ttk.Radiobutton(source_frame, text="Individual Video(s)", variable=self.source_type, value="individual", command=self.update_input_mode).pack(side="left", padx=5)

        # URL input area
        self.url_label = ttk.Label(self.root, text="YouTube Playlist URL:")
        self.url_label.pack()
        self.url_entry = tk.Text(self.root, height=3, width=80)
        self.url_entry.pack(pady=5)

        # Fetch Button
        self.fetch_button = ttk.Button(self.root, text="Fetch Playlist / Add Videos", command=self.fetch_sources)
        self.fetch_button.pack(pady=5)

        # Playlist Checkboxes
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

        # Select / Deselect buttons
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=(0, 10))
        ttk.Button(btn_frame, text="Select All", command=self.select_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Deselect All", command=self.deselect_all).pack(side="left", padx=5)

        # Format Options
        self.download_type = tk.StringVar(value="mp3")
        ttk.Label(self.root, text="Download Format:").pack()
        ttk.Radiobutton(self.root, text="MP3 (Audio)", variable=self.download_type, value="mp3").pack()
        ttk.Radiobutton(self.root, text="MP4 (Video)", variable=self.download_type, value="mp4").pack()

        # Output folder selection
        folder_frame = tk.Frame(self.root)
        folder_frame.pack(pady=5)
        ttk.Label(folder_frame, text="Save to:").pack(side="left")
        self.folder_label = ttk.Label(folder_frame, text=self.output_dir, width=50)
        self.folder_label.pack(side="left", padx=5)
        ttk.Button(folder_frame, text="Choose Folder", command=self.choose_folder).pack(side="left")

        # FFmpeg path selection
        ffmpeg_frame = tk.Frame(self.root)
        ffmpeg_frame.pack(pady=5)
        ttk.Label(ffmpeg_frame, text="FFmpeg path:").pack(side="left")
        self.ffmpeg_label = ttk.Label(ffmpeg_frame, text=self.ffmpeg_path, width=50)
        self.ffmpeg_label.pack(side="left", padx=5)
        ttk.Button(ffmpeg_frame, text="Choose FFmpeg", command=self.choose_ffmpeg).pack(side="left")

        # Start / Stop Buttons
        self.start_button = ttk.Button(self.root, text="Start Download", command=self.start_download)
        self.start_button.pack(pady=(10, 0))
        self.stop_button = ttk.Button(self.root, text="Stop", command=self.stop_download, state="disabled")
        self.stop_button.pack(pady=(5, 10))

        # Status
        self.status_label = ttk.Label(self.root, text="")
        self.status_label.pack()

    def update_input_mode(self):
        if self.source_type.get() == "playlist":
            self.url_label.config(text="YouTube Playlist URL:")
        else:
            self.url_label.config(text="One or More Video URLs (one per line):")

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = folder
            self.folder_label.config(text=self.output_dir)

    def choose_ffmpeg(self):
        folder = filedialog.askdirectory()
        if folder:
            self.ffmpeg_path = folder
            self.ffmpeg_label.config(text=self.ffmpeg_path)

    def fetch_sources(self):
        self.clear_checklist()
        self.status_label.config(text="Fetching...")

        def fetch():
            mode = self.source_type.get()
            urls = self.url_entry.get("1.0", tk.END).strip().splitlines()

            if not urls:
                messagebox.showerror("Error", "Please enter URL(s).")
                return

            if mode == "playlist":
                url = urls[0]  # Only first one used for playlist
                ydl_opts = {
                    "quiet": True,
                    "extract_flat": True,
                    "dump_single_json": True,
                    "encoding": "utf-8"
                }
                try:
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        entries = info.get("entries", [])
                        for entry in entries:
                            var = tk.BooleanVar(value=False)
                            title = entry.get("title", "Untitled")
                            video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                            cb = ttk.Checkbutton(self.checklist_frame, text=title, variable=var)
                            cb.pack(anchor="w")
                            self.video_entries.append((var, title, video_url))
                        self.status_label.config(text=f"{len(entries)} videos found.")
                except Exception as e:
                    self.status_label.config(text=f"Error: {e}")
                    messagebox.showerror("Error", str(e))
            else:
                # Individual videos
                for url in urls:
                    var = tk.BooleanVar(value=True)
                    title = url
                    cb = ttk.Checkbutton(self.checklist_frame, text=title, variable=var)
                    cb.pack(anchor="w")
                    self.video_entries.append((var, title, url))
                self.status_label.config(text=f"{len(urls)} individual video(s) added.")

        threading.Thread(target=fetch).start()

    def clear_checklist(self):
        for widget in self.checklist_frame.winfo_children():
            widget.destroy()
        self.video_entries.clear()

    def select_all(self):
        for var, _, _ in self.video_entries:
            var.set(True)

    def deselect_all(self):
        for var, _, _ in self.video_entries:
            var.set(False)

    def start_download(self):
        selected = [(title, url) for var, title, url in self.video_entries if var.get()]
        if not selected:
            messagebox.showwarning("Nothing Selected", "Please select at least one video.")
            return

        self.cancel_requested = False
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_label.config(text="Starting download...")

        threading.Thread(target=self.download_videos, args=(selected,)).start()

    def stop_download(self):
        self.cancel_requested = True
        self.status_label.config(text="Stopping...")
        self.stop_button.config(state="disabled")

    def download_videos(self, selected_videos):
        ydl_opts_mp3 = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
            "ignoreerrors": True,
            "ffmpeg_location": self.ffmpeg_path,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        }

        ydl_opts_mp4 = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
            "merge_output_format": "mp4",
            "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
            "ignoreerrors": True,
            "ffmpeg_location": self.ffmpeg_path,
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4"
                }
            ]
        }

        ydl_opts = ydl_opts_mp3 if self.download_type.get() == "mp3" else ydl_opts_mp4

        with YoutubeDL(ydl_opts) as ydl:
            for title, url in selected_videos:
                if self.cancel_requested:
                    break
                self.status_label.config(text=f"Downloading: {title}")
                try:
                    ydl.download([url])
                except Exception as e:
                    self.status_label.config(text=f"Failed: {title} | {e}")

        self.status_label.config(
            text="✅ Done!" if not self.cancel_requested else "⛔ Cancelled"
        )
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloaderApp(root)
    root.mainloop()
