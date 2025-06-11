#!/usr/bin/env python3
"""Test script to verify all required modules can be imported"""

import sys
import traceback

def test_import(module_name):
    """Test importing a module and return success status"""
    try:
        __import__(module_name)
        print(f"✓ {module_name} - OK")
        return True
    except ImportError as e:
        print(f"✗ {module_name} - FAILED: {e}")
        return False
    except Exception as e:
        print(f"✗ {module_name} - ERROR: {e}")
        return False

def main():
    """Test all required imports"""
    print("Testing module imports...")
    print("=" * 50)
    
    modules_to_test = [
        'yt_dlp',
        'yt_dlp.YoutubeDL',
        'yt_dlp.extractor',
        'yt_dlp.extractor.youtube',
        'yt_dlp.downloader',
        'yt_dlp.postprocessor',
        'yt_dlp.utils',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'requests',
        'pyperclip',
        'tkinter',
        'json',
        'threading',
        'subprocess',
        'concurrent.futures',
    ]
    
    failed_modules = []
    
    for module in modules_to_test:
        if not test_import(module):
            failed_modules.append(module)
    
    print("=" * 50)
    if failed_modules:
        print(f"❌ {len(failed_modules)} modules failed to import:")
        for module in failed_modules:
            print(f"  - {module}")
        return 1
    else:
        print("✅ All modules imported successfully!")
        
        # Test yt-dlp functionality
        try:
            from yt_dlp import YoutubeDL
            ydl = YoutubeDL({'quiet': True})
            print("✅ yt-dlp YoutubeDL class instantiated successfully!")
        except Exception as e:
            print(f"❌ yt-dlp functionality test failed: {e}")
            return 1
        
        return 0

if __name__ == "__main__":
    sys.exit(main())
