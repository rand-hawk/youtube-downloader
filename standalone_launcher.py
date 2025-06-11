#!/usr/bin/env python3
"""
Standalone YouTube Downloader Launcher
This launcher completely bypasses pkg_resources and other problematic modules
"""

import sys
import os

# Completely disable pkg_resources and related modules
def disable_problematic_modules():
    """Completely disable problematic modules before they can cause issues"""
    
    # Create a null module class
    class NullModule:
        def __getattr__(self, name):
            return NullModule()
        def __call__(self, *args, **kwargs):
            return NullModule()
        def __bool__(self):
            return False
        def __str__(self):
            return ""
        def __repr__(self):
            return ""
        def __iter__(self):
            return iter([])
        def __getitem__(self, key):
            return NullModule()
        def __setitem__(self, key, value):
            pass
        def __contains__(self, item):
            return False
        def __len__(self):
            return 0
    
    # List of modules to completely disable
    disabled_modules = [
        'pkg_resources',
        'pkg_resources.extern',
        'pkg_resources._vendor',
        'setuptools._vendor',
        'jaraco',
        'importlib_metadata',
        'zipp'
    ]
    
    # Add disabled modules to sys.modules
    for module_name in disabled_modules:
        sys.modules[module_name] = NullModule()
    
    # Also add any submodules that might be imported
    for module_name in list(disabled_modules):
        for i in range(5):  # Handle up to 5 levels deep
            for suffix in ['.text', '.functools', '.context', '.classes', '.version', '.specifiers', '.requirements', '.packaging', '.jaraco']:
                submodule = module_name + suffix
                if submodule not in sys.modules:
                    sys.modules[submodule] = NullModule()

# Apply the fix immediately
disable_problematic_modules()

# Now try to import the required modules
def safe_import():
    """Safely import all required modules"""
    try:
        # Core yt-dlp imports
        import yt_dlp
        from yt_dlp import YoutubeDL
        
        # GUI and system imports
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog
        import threading
        import json
        import subprocess
        import signal
        import time
        import re
        
        # Network and image processing
        import requests
        from PIL import Image, ImageTk
        from io import BytesIO
        import pyperclip
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        print("✓ All required modules imported successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import required module: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test imports
if not safe_import():
    print("❌ Module import failed. Press Enter to exit...")
    input()
    sys.exit(1)

# Now run the main application
if __name__ == "__main__":
    try:
        # Get the path to the main script
        if getattr(sys, 'frozen', False):
            # Running from PyInstaller executable
            app_dir = os.path.dirname(sys.executable)
            main_script_path = os.path.join(app_dir, 'youtube-download-gui-v1.py')
        else:
            # Running from source
            app_dir = os.path.dirname(__file__)
            main_script_path = os.path.join(app_dir, 'youtube-download-gui-v1.py')
        
        if os.path.exists(main_script_path):
            # Execute the main script
            with open(main_script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            
            # Execute in the current namespace
            exec(script_content, {'__name__': '__main__', '__file__': main_script_path})
        else:
            print(f"❌ Main script not found at: {main_script_path}")
            print("Available files:")
            if os.path.exists(app_dir):
                for file in os.listdir(app_dir):
                    print(f"  - {file}")
            input("Press Enter to exit...")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Failed to launch application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
