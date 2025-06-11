# PyInstaller hook for yt-dlp
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# Collect all yt-dlp modules and data
datas, binaries, hiddenimports = collect_all('yt_dlp')

# Ensure all submodules are included
hiddenimports += collect_submodules('yt_dlp')

# Add specific modules that might be missed
additional_imports = [
    'yt_dlp.extractor',
    'yt_dlp.extractor.youtube',
    'yt_dlp.extractor.common',
    'yt_dlp.extractor.generic',
    'yt_dlp.downloader',
    'yt_dlp.downloader.http',
    'yt_dlp.downloader.fragment',
    'yt_dlp.postprocessor',
    'yt_dlp.postprocessor.ffmpeg',
    'yt_dlp.utils',
    'yt_dlp.version',
    'yt_dlp.YoutubeDL',
]

hiddenimports += additional_imports
