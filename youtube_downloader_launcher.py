#!/usr/bin/env python3
"""
YouTube Downloader Launcher
This script ensures all required modules are properly imported before launching the main application.
"""

import sys
import os

# Comprehensive fix for PyInstaller packaging issues
def fix_all_import_issues():
    """Fix all known import issues in PyInstaller builds"""
    try:
        # Suppress all warnings that might cause issues
        import warnings
        warnings.filterwarnings("ignore")

        # Create a comprehensive mock class
        class UniversalMock:
            """Universal mock class that can handle any attribute or call"""
            def __init__(self, name="UniversalMock"):
                self._name = name

            def __getattr__(self, name):
                return UniversalMock(f"{self._name}.{name}")

            def __call__(self, *args, **kwargs):
                return UniversalMock(f"{self._name}()")

            def __str__(self):
                return f"<Mock: {self._name}>"

            def __repr__(self):
                return self.__str__()

            def __bool__(self):
                return True

            def __iter__(self):
                return iter([])

            def __getitem__(self, key):
                return UniversalMock(f"{self._name}[{key}]")

            def __setitem__(self, key, value):
                pass

            def __contains__(self, item):
                return False

        # Comprehensive list of problematic modules to mock
        problematic_modules = [
            # jaraco modules
            'jaraco',
            'jaraco.text',
            'jaraco.functools',
            'jaraco.context',
            'jaraco.collections',
            'jaraco.classes',
            'jaraco.itertools',

            # pkg_resources extern modules
            'pkg_resources.extern',
            'pkg_resources.extern.jaraco',
            'pkg_resources.extern.jaraco.text',
            'pkg_resources.extern.jaraco.functools',
            'pkg_resources.extern.jaraco.context',
            'pkg_resources.extern.jaraco.classes',
            'pkg_resources.extern.packaging',
            'pkg_resources.extern.packaging.version',
            'pkg_resources.extern.packaging.specifiers',
            'pkg_resources.extern.packaging.requirements',
            'pkg_resources.extern.packaging.markers',
            'pkg_resources.extern.packaging.utils',

            # pkg_resources vendor modules
            'pkg_resources._vendor',
            'pkg_resources._vendor.jaraco',
            'pkg_resources._vendor.jaraco.text',
            'pkg_resources._vendor.jaraco.functools',
            'pkg_resources._vendor.jaraco.context',
            'pkg_resources._vendor.packaging',
            'pkg_resources._vendor.packaging.version',
            'pkg_resources._vendor.packaging.specifiers',

            # setuptools vendor modules
            'setuptools._vendor',
            'setuptools._vendor.jaraco',
            'setuptools._vendor.jaraco.text',
            'setuptools._vendor.jaraco.functools',
            'setuptools._vendor.jaraco.context',
            'setuptools._vendor.packaging',
            'setuptools._vendor.packaging.version',
            'setuptools._vendor.packaging.specifiers',

            # Other potentially problematic modules
            'importlib_metadata',
            'importlib_metadata._compat',
            'zipp',
        ]

        # Add all problematic modules to sys.modules as mocks
        for module_name in problematic_modules:
            if module_name not in sys.modules:
                sys.modules[module_name] = UniversalMock(module_name)

        # Special handling for pkg_resources
        try:
            import pkg_resources
            # If pkg_resources is available, try to patch its problematic parts
            if not hasattr(pkg_resources, 'extern'):
                pkg_resources.extern = UniversalMock('pkg_resources.extern')
            if not hasattr(pkg_resources, '_vendor'):
                pkg_resources._vendor = UniversalMock('pkg_resources._vendor')
        except ImportError:
            # If pkg_resources is not available, create a mock
            sys.modules['pkg_resources'] = UniversalMock('pkg_resources')

        # Try to import and patch setuptools
        try:
            import setuptools
            if not hasattr(setuptools, '_vendor'):
                setuptools._vendor = UniversalMock('setuptools._vendor')
        except ImportError:
            pass

    except Exception as e:
        # If anything fails, just continue - the mocks should handle it
        pass

# Apply comprehensive fixes before any other imports
fix_all_import_issues()

# Ensure we can import all required modules
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

except ImportError as e:
    print(f"❌ Failed to import required module: {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)

# Now import and run the main application
if __name__ == "__main__":
    try:
        # Import the main application module
        import importlib.util
        
        # Get the path to the main script
        main_script_path = os.path.join(os.path.dirname(__file__), 'youtube-download-gui-v1.py')
        
        if os.path.exists(main_script_path):
            # Load and execute the main script
            spec = importlib.util.spec_from_file_location("main_app", main_script_path)
            main_app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_app)
        else:
            # Fallback - try to import directly
            exec(open('youtube-download-gui-v1.py').read())
            
    except Exception as e:
        print(f"❌ Failed to launch application: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)
