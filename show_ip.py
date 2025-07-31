#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Simple script to display device IP address on e-ink display and exit.
Useful for quickly checking the IP address of your Raspberry Pi.
"""
import sys
import os
import time
import socket
import subprocess
import argparse
from PIL import Image, ImageDraw, ImageFont

# Setup paths like in the main script
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

# EPD import moved to inside function to use unified system

def get_ip_address():
    """Get the device's IP address"""
    try:
        # Method 1: Try to get IP by connecting to a remote address (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            # Connect to a remote address (8.8.8.8 is Google's DNS)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            s.close()
    except Exception:
        pass
    
    try:
        # Method 2: Use hostname command
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            ips = result.stdout.strip().split()
            if ips:
                return ips[0]  # Return first IP address
    except Exception:
        pass
    
    try:
        # Method 3: Parse ip route command
        result = subprocess.run(['ip', 'route', 'get', '1'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'src' in line:
                    parts = line.split()
                    try:
                        src_idx = parts.index('src')
                        if src_idx + 1 < len(parts):
                            return parts[src_idx + 1]
                    except (ValueError, IndexError):
                        continue
    except Exception:
        pass
    
    try:
        # Method 4: Get hostname and resolve it
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if ip != '127.0.0.1':
            return ip
    except Exception:
        pass
    
    # Fallback
    return "IP not found"

def main():
    parser = argparse.ArgumentParser(
        description='Display device IP address on e-ink display',
        epilog='This script shows the IP address and exits. Useful for quick IP checks.'
    )
    parser.add_argument('--orientation', choices=['landscape', 'landscape_flipped', 'portrait', 'portrait_flipped'],
                       help='Display orientation (default: landscape)')
    parser.add_argument('--no-clear', action='store_true',
                       help='Do not clear display before showing IP')
    
    args = parser.parse_args()
    
    try:
        print("🔍 Getting IP address...")
        ip_address = get_ip_address()
        hostname = socket.gethostname()
        
        print(f"📡 IP Address: {ip_address}")
        print(f"🏠 Hostname: {hostname}")
        print("📺 Displaying on e-ink...")
        
        # Initialize e-paper display using unified system
        from unified_epd_adapter import UnifiedEPD, EPDConfig
        display_type = EPDConfig.load_display_config()
        epd = UnifiedEPD.create_display(display_type)
        epd.init()
        
        # Clear screen if requested
        if not args.no_clear:
            epd.clear()
            time.sleep(1)
        
        # Load fonts (fallback to default if Font.ttc not available)
        try:
            font_small = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 12)
            font_medium = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 16)
            font_large = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)
            font_xl = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 24)
        except:
            font_small = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_xl = ImageFont.load_default()
        
        # Create display image
        display_image = Image.new('RGB', (epd.landscape_width, epd.landscape_height), epd.WHITE)
        draw = ImageDraw.Draw(display_image)
        
        # Title
        draw.rectangle([(0, 0), (epd.landscape_width, 40)], fill=epd.BLACK)
        draw.text((5, 12), "Raspberry Pi Network Info", font=font_large, fill=epd.WHITE)
        
        # Hostname
        y_pos = 55
        draw.text((5, y_pos), "Hostname:", font=font_medium, fill=epd.BLACK)
        y_pos += 25
        draw.text((5, y_pos), hostname, font=font_medium, fill=epd.RED)
        
        # IP Address (main focus)
        y_pos += 40
        draw.text((5, y_pos), "IP Address:", font=font_medium, fill=epd.BLACK)
        y_pos += 30
        draw.text((5, y_pos), ip_address, font=font_xl, fill=epd.RED)
        
        # Timestamp
        y_pos += 45
        draw.text((5, y_pos), f"Updated: {time.strftime('%H:%M:%S')}", 
                 font=font_small, fill=epd.BLACK)
        
        # Instructions
        y_pos += 25
        draw.text((5, y_pos), "Use this IP to connect from", font=font_small, fill=epd.BLACK)
        y_pos += 15
        draw.text((5, y_pos), "other devices on your network", font=font_small, fill=epd.BLACK)
        
        # Apply orientation
        if args.orientation:
            # Use the new orientation system
            if args.orientation == 'landscape':
                # No rotation needed
                pass
            elif args.orientation == 'landscape_flipped':
                # Rotate 180 degrees
                display_image = display_image.rotate(180)
            elif args.orientation == 'portrait':
                # Rotate 90 degrees clockwise
                display_image = display_image.rotate(90, expand=True)
            elif args.orientation == 'portrait_flipped':
                # Rotate 270 degrees clockwise (or 90 degrees counter-clockwise)
                display_image = display_image.rotate(270, expand=True)
        else:
            # Default is landscape (no rotation)
            pass
        
        # Display the image
        epd.display(epd.getbuffer(display_image))
        
        # Clean up
        epd.sleep()
        
        print("✅ IP address displayed successfully!")
        print(f"📱 Connect to: {ip_address}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 