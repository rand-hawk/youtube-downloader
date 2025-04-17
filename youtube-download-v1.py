import subprocess
import os

# === CONFIG ===
PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLNPfH5fig6GIQpQY48OwRqT-7tb_OV28i"
OUTPUT_DIR = "downloaded_mp3s"
RETRIES = 3

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_with_yt_dlp(url):
    command = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--output", os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s"),
        "--retry-sleep", "5",
        "--retries", str(RETRIES),
        url
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Download failed: {e}")

if __name__ == "__main__":
    print(f"📚 Downloading playlist: {PLAYLIST_URL}")
    download_with_yt_dlp(PLAYLIST_URL)
