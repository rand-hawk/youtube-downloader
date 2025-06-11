#!/usr/bin/env python3
"""
Ultimate YouTube Downloader Launcher
This launcher patches the import system to prevent any pkg_resources issues
"""

import sys
import os
import builtins

# Patch the import system BEFORE any other imports
original_import = builtins.__import__

def patched_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Patched import function that blocks problematic modules"""
    
    # List of modules to completely block
    blocked_modules = [
        'pkg_resources.extern',
        'pkg_resources._vendor',
        'setuptools._vendor.jaraco',
        'setuptools._vendor.packaging',
        'jaraco.text',
        'jaraco.functools',
        'jaraco.context',
        'jaraco.classes',
        'jaraco.collections',
        'importlib_metadata',
        'zipp'
    ]
    
    # Check if this is a blocked module
    for blocked in blocked_modules:
        if name == blocked or name.startswith(blocked + '.'):
            # Return a mock module instead
            return MockModule(name)
    
    # For pkg_resources, return a patched version
    if name == 'pkg_resources':
        try:
            module = original_import(name, globals, locals, fromlist, level)
            # Patch the problematic attributes
            if not hasattr(module, 'extern'):
                module.extern = MockModule('pkg_resources.extern')
            if not hasattr(module, '_vendor'):
                module._vendor = MockModule('pkg_resources._vendor')
            return module
        except ImportError:
            return MockModule(name)
    
    # For setuptools, return a patched version
    if name == 'setuptools':
        try:
            module = original_import(name, globals, locals, fromlist, level)
            # Patch the problematic attributes
            if not hasattr(module, '_vendor'):
                module._vendor = MockModule('setuptools._vendor')
            return module
        except ImportError:
            return MockModule(name)
    
    # For jaraco, always return mock
    if name == 'jaraco' or name.startswith('jaraco.'):
        return MockModule(name)
    
    # For all other imports, use the original function
    try:
        return original_import(name, globals, locals, fromlist, level)
    except ImportError as e:
        # If it's a known problematic module, return a mock
        if any(blocked in str(e) for blocked in blocked_modules):
            return MockModule(name)
        # Otherwise, re-raise the error
        raise

class MockModule:
    """Mock module that can handle any attribute or call"""
    def __init__(self, name="MockModule"):
        self._name = name
        self.__name__ = name
        self.__file__ = f"<mock {name}>"
        self.__package__ = name.split('.')[0] if '.' in name else name
        
    def __getattr__(self, name):
        return MockModule(f"{self._name}.{name}")
        
    def __call__(self, *args, **kwargs):
        return MockModule(f"{self._name}()")
        
    def __str__(self):
        return f"<Mock: {self._name}>"
        
    def __repr__(self):
        return self.__str__()
        
    def __bool__(self):
        return True
        
    def __iter__(self):
        return iter([])
        
    def __getitem__(self, key):
        return MockModule(f"{self._name}[{key}]")
        
    def __setitem__(self, key, value):
        pass
        
    def __contains__(self, item):
        return False
        
    def __len__(self):
        return 0
        
    def __dir__(self):
        return []

# Apply the import patch immediately
builtins.__import__ = patched_import

# Also pre-populate sys.modules with mocks for known problematic modules
problematic_modules = [
    'pkg_resources.extern',
    'pkg_resources.extern.jaraco',
    'pkg_resources.extern.jaraco.text',
    'pkg_resources.extern.jaraco.functools',
    'pkg_resources.extern.jaraco.context',
    'pkg_resources.extern.packaging',
    'pkg_resources.extern.packaging.version',
    'pkg_resources.extern.packaging.specifiers',
    'pkg_resources._vendor',
    'pkg_resources._vendor.jaraco',
    'pkg_resources._vendor.jaraco.text',
    'pkg_resources._vendor.jaraco.functools',
    'pkg_resources._vendor.jaraco.context',
    'pkg_resources._vendor.packaging',
    'pkg_resources._vendor.packaging.version',
    'setuptools._vendor',
    'setuptools._vendor.jaraco',
    'setuptools._vendor.jaraco.text',
    'setuptools._vendor.jaraco.functools',
    'setuptools._vendor.jaraco.context',
    'setuptools._vendor.packaging',
    'setuptools._vendor.packaging.version',
    'jaraco',
    'jaraco.text',
    'jaraco.functools',
    'jaraco.context',
    'jaraco.classes',
    'jaraco.collections',
    'importlib_metadata',
    'zipp'
]

for module_name in problematic_modules:
    if module_name not in sys.modules:
        sys.modules[module_name] = MockModule(module_name)

# Suppress all warnings
import warnings
warnings.filterwarnings("ignore")

# Now try to import the required modules
def safe_import():
    """Safely import all required modules"""
    try:
        print("🔧 Patched import system activated")
        
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
            print(f"🚀 Launching main application from: {main_script_path}")
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
