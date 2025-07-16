#!/usr/bin/env python3
"""
Test script for the e-ink display upload server.
Run this to verify the upload server is working correctly.
"""

import requests
import json
import time
import sys
import os

# Configuration - UPDATE THIS TO YOUR RASPBERRY PI'S IP ADDRESS
PI_IP = "192.168.1.141"
PI_PORT = 5000
SERVER_URL = f"http://{PI_IP}:{PI_PORT}"

def test_server_status():
    """Test if the server is running and responsive"""
    print("Testing server status...")
    try:
        response = requests.get(f"{SERVER_URL}/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is running")
            print(f"   Upload folder: {data.get('upload_folder')}")
            print(f"   Allowed extensions: {data.get('allowed_extensions')}")
            return True
        else:
            print(f"❌ Server returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        return False

def test_text_upload():
    """Test uploading text content"""
    print("\nTesting text upload...")
    try:
        data = {
            'content': f"Test message from upload test\nTimestamp: {time.ctime()}\n\nThis is a test of the e-ink display system!",
            'filename': 'test_upload.txt'
        }
        
        response = requests.post(
            f"{SERVER_URL}/upload_text",
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Text upload successful: {result['filename']}")
            return True
        else:
            print(f"❌ Text upload failed: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Text upload error: {e}")
        return False

def test_file_upload():
    """Test uploading a file"""
    print("\nTesting file upload...")
    
    # Create a test image file
    test_file = "test_image.txt"
    test_content = f"""Test File Upload
=================

This is a test file created at {time.ctime()}

If you can see this on your e-ink display, 
the file upload system is working correctly!

Features tested:
- File upload via HTTP POST
- Text content display
- Server communication
- TouchDesigner integration

🎉 Success! 🎉
"""
    
    try:
        # Write test file
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Upload test file
        with open(test_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{SERVER_URL}/upload", files=files, timeout=10)
        
        # Clean up test file
        os.remove(test_file)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ File upload successful: {result['filename']}")
            return True
        else:
            print(f"❌ File upload failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ File upload error: {e}")
        if os.path.exists(test_file):
            os.remove(test_file)
        return False

def test_clear_display():
    """Test clearing the display"""
    print("\nTesting display clear...")
    try:
        response = requests.post(f"{SERVER_URL}/clear_display", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Display cleared successfully")
            print(f"   Files removed: {result.get('removed_files', [])}")
            return True
        else:
            print(f"❌ Clear display failed: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Clear display error: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("E-INK DISPLAY UPLOAD SERVER TEST")
    print("=" * 60)
    print(f"Server URL: {SERVER_URL}")
    print()
    
    tests = [
        ("Server Status", test_server_status),
        ("Text Upload", test_text_upload),
        ("File Upload", test_file_upload),
        ("Clear Display", test_clear_display)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n[{passed + 1}/{total}] {test_name}")
        print("-" * 40)
        if test_func():
            passed += 1
            time.sleep(1)  # Small delay between tests
        else:
            print("Test failed - stopping here")
            break
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Server is working correctly.")
        print("\nNext steps:")
        print("1. Open TouchDesigner")
        print("2. Use the touchdesigner_eink_script.py to build the interface")
        print("3. Update the PI_IP in the script to match your Pi's IP")
        print("4. Start uploading files to your e-ink display!")
    else:
        print("❌ Some tests failed. Check the server and try again.")
        print("\nTroubleshooting:")
        print("1. Make sure the upload server is running: python upload_server.py")
        print("2. Check the IP address is correct")
        print("3. Ensure the Pi and computer are on the same network")
        print("4. Check firewall settings on the Pi")
    
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        PI_IP = sys.argv[1]
        SERVER_URL = f"http://{PI_IP}:{PI_PORT}"
        print(f"Using custom IP: {PI_IP}")
    
    run_all_tests() 