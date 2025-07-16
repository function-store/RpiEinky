#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Test script to demonstrate the e-ink display system
Run this after starting display_latest.py to see how it works
"""

import time
import os
from pathlib import Path
from PIL import Image, ImageDraw

def create_test_files():
    """Create sample files to test the display system"""
    
    # Create watched_files directory if it doesn't exist
    watched_dir = Path(os.path.expanduser("~/watched_files"))
    watched_dir.mkdir(exist_ok=True)
    
    print("Creating test files...")
    
    # Test 1: Simple text file
    print("1. Creating text file...")
    with open(watched_dir / "hello.txt", "w") as f:
        f.write("Hello World!\n\nThis is a test text file.\n\nIt should be displayed on your e-ink screen with word wrapping and proper formatting.")
    
    time.sleep(3)  # Wait for display to update
    
    # Test 2: Python code file
    print("2. Creating Python file...")
    with open(watched_dir / "test_code.py", "w") as f:
        f.write("""#!/usr/bin/python
def hello_world():
    print("Hello from e-ink!")
    return True

if __name__ == "__main__":
    hello_world()
""")
    
    time.sleep(3)
    
    # Test 3: Create a simple image
    print("3. Creating test image...")
    img = Image.new('RGB', (200, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw some shapes
    draw.rectangle([10, 10, 190, 140], outline=(0, 0, 0), width=2)
    draw.ellipse([50, 50, 150, 100], fill=(200, 200, 200))
    draw.text((60, 70), "Test Image", fill=(0, 0, 0))
    
    img.save(watched_dir / "test_image.png")
    
    time.sleep(3)
    
    # Test 4: File info test (unknown format)
    print("4. Creating unknown file type...")
    with open(watched_dir / "data.xyz", "w") as f:
        f.write("This is an unknown file type that should show file info.")
    
    time.sleep(3)
    
    print("\nTest files created! Check your e-ink display.")
    print("You can add more files to the watched_files folder to test the system.")

if __name__ == "__main__":
    create_test_files() 