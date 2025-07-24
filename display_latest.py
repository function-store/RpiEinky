#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import time
import logging
import argparse
import signal
import socket
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageDraw, ImageFont
import traceback

# Setup paths like in the test file
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from waveshare_epd import epd2in15g

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variables for exit handling
exit_requested = False
clear_on_exit_requested = True

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

def signal_handler_clear_exit(signum, frame):
    """Handle Ctrl+C - exit with display clearing"""
    global exit_requested, clear_on_exit_requested
    logger.info("\n🛑 Ctrl+C pressed - exiting with display clearing...")
    exit_requested = True
    clear_on_exit_requested = True



class EinkDisplayHandler(FileSystemEventHandler):
    def __init__(self, watched_folder="./watched_files", clear_on_start=False, clear_on_exit=True):
        self.watched_folder = Path(watched_folder)
        self.watched_folder.mkdir(exist_ok=True)
        self.clear_on_start = clear_on_start
        self.clear_on_exit = clear_on_exit
        
        # Initialize e-paper display
        self.epd = epd2in15g.EPD()
        self.epd.init()
        
        # Clear screen on start if requested
        if self.clear_on_start:
            self.epd.Clear()
            time.sleep(1)
        
        # Configure display orientation 
        # Set to True to rotate display 180 degrees (upside-down)
        self.display_upside_down = True
        
        # Configure image processing mode
        self.image_crop_mode = 'center_crop'  # 'center_crop' or 'fit_with_letterbox'
        
        # Load settings
        self.load_settings()
        
        # Load fonts (fallback to default if Font.ttc not available)
        try:
            self.font_small = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 12)
            self.font_medium = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 16)
            self.font_large = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)
        except:
            self.font_small = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
        
        logger.info(f"Monitoring folder: {self.watched_folder.absolute()}")
        logger.info(f"E-ink display initialized - Size: {self.epd.width}x{self.epd.height}")
        logger.info(f"Auto-display uploads: {self.auto_display_uploads}")
    
    def load_settings(self):
        """Load settings from the settings file"""
        try:
            # Use the same path as the upload server
            settings_file = Path(os.path.expanduser('~/watched_files')) / '.settings.json'
            if settings_file.exists():
                import json
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    self.auto_display_uploads = settings.get('auto_display_upload', True)
                    self.image_crop_mode = settings.get('image_crop_mode', 'center_crop')
                    logger.info(f"Settings loaded from {settings_file} - Auto-display: {self.auto_display_uploads}, Crop mode: {self.image_crop_mode}")
            else:
                # Default settings
                self.auto_display_uploads = True
                self.image_crop_mode = 'center_crop'
                logger.info(f"Settings file not found at {settings_file}, using defaults - Auto-display: True, Crop mode: center_crop")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            # Fallback to defaults
            self.auto_display_uploads = True
            self.image_crop_mode = 'center_crop'
    
    def reload_settings(self):
        """Reload settings from file (useful when settings change)"""
        self.load_settings()
        logger.info(f"Settings reloaded - Auto-display: {self.auto_display_uploads}, Crop mode: {self.image_crop_mode}")
    
    def get_latest_file(self):
        """Get the most recent file in the watched folder"""
        try:
            files = [f for f in self.watched_folder.glob('*') if f.is_file() and not f.name.startswith('.')]
            if not files:
                return None
            
            # Sort by modification time (latest first)
            latest_file = max(files, key=lambda f: f.stat().st_mtime)
            return latest_file
        except Exception as e:
            logger.error(f"Error finding latest file: {e}")
            return None
    
    def validate_file(self, file_path):
        """Validate that file is complete and readable"""
        try:
            # Check file exists and has content
            if not file_path.exists() or file_path.stat().st_size == 0:
                logger.error(f"File is empty or doesn't exist: {file_path}")
                return False
            
            # For image files, try to open with PIL
            if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                try:
                    with Image.open(file_path) as img:
                        # Force loading to ensure file is complete
                        img.load()
                        logger.info(f"File validation passed: {file_path.name} ({img.size[0]}x{img.size[1]})")
                        return True
                except Exception as e:
                    logger.error(f"Image validation failed: {file_path.name} - {e}")
                    return False
            
            # For other files, just check readability
            try:
                with open(file_path, 'rb') as f:
                    f.read(1024)  # Read first 1KB to check if readable
                return True
            except Exception as e:
                logger.error(f"File read validation failed: {file_path.name} - {e}")
                return False
                
        except Exception as e:
            logger.error(f"File validation error: {file_path.name} - {e}")
            return False
    
    def display_buffer(self, image):
        """Display image buffer with orientation support"""
        try:
            if self.display_upside_down:
                # Simple 180-degree rotation using PIL
                image = image.rotate(180)
            
            self.epd.display(self.epd.getbuffer(image))
            
        except Exception as e:
            logger.error(f"Display buffer error: {e}")
            if "Bad file descriptor" in str(e):
                logger.info("Attempting to reinitialize display...")
                self.reinitialize_display()
                # Try again after reinitializing
                if self.display_upside_down:
                    image = image.rotate(180)
                self.epd.display(self.epd.getbuffer(image))
    
    def reinitialize_display(self):
        """Reinitialize the e-ink display"""
        try:
            logger.info("Reinitializing e-ink display...")
            self.epd.sleep()
            time.sleep(1)
            self.epd.init()
            logger.info("Display reinitialized successfully")
        except Exception as e:
            logger.error(f"Display reinitialization failed: {e}")
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        logger.info(f"New file detected: {file_path.name}")
        
        # Longer delay to ensure file is fully written
        time.sleep(2.0)
        
        # Validate file is complete and readable
        if not self.validate_file(file_path):
            logger.error(f"File validation failed: {file_path.name}")
            return
        
        # Reload settings to get the latest auto-display setting
        self.reload_settings()
        
        # Check if auto-display is enabled
        logger.info(f"Auto-display setting: {self.auto_display_uploads}")
        if self.auto_display_uploads:
            try:
                self.display_file(file_path)
                logger.info(f"Auto-displayed file: {file_path.name}")
            except Exception as e:
                logger.error(f"Error auto-displaying file {file_path.name}: {e}")
                self.display_error(file_path.name, str(e))
        else:
            logger.info(f"Auto-display disabled - file {file_path.name} not displayed")
    
    def display_file(self, file_path):
        """Convert and display file on e-ink display"""
        file_ext = file_path.suffix.lower()
        
        if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            self.display_image(file_path)
        elif file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css']:
            self.display_text_file(file_path)
        elif file_ext == '.pdf':
            self.display_pdf(file_path)
        else:
            self.display_file_info(file_path)
    
    def display_image(self, file_path):
        """Display image file on e-ink"""
        try:
            # Open and process image
            image = Image.open(file_path)
            original_size = image.size
            
            # Convert to RGB if necessary, using white background for transparency
            if image.mode != 'RGB':
                if image.mode == 'RGBA':
                    # Create white background for transparent pixels
                    white_bg = Image.new('RGB', image.size, (255, 255, 255))
                    white_bg.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                    image = white_bg
                else:
                    image = image.convert('RGB')
            
            # Resize and crop to fit display
            processed_image = self.resize_image_to_fit(image)
            
            # If the processed image is exactly display size, use it directly
            if processed_image.size == (self.epd.height, self.epd.width):
                display_image = processed_image
            else:
                # Create display image and center the processed image
                display_image = Image.new('RGB', (self.epd.height, self.epd.width), self.epd.WHITE)
                x_offset = (self.epd.height - processed_image.width) // 2
                y_offset = (self.epd.width - processed_image.height) // 2
                display_image.paste(processed_image, (x_offset, y_offset))
            
            self.display_buffer(display_image)
            logger.info(f"Displayed image: {file_path.name} (original: {original_size}, final: {display_image.size})")
            
        except Exception as e:
            logger.error(f"Error displaying image {file_path.name}: {e}")
            self.display_error(file_path.name, str(e))
    
    def display_text_file(self, file_path):
        """Display text file content on e-ink"""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Create display image
            display_image = Image.new('RGB', (self.epd.height, self.epd.width), self.epd.WHITE)
            draw = ImageDraw.Draw(display_image)
            
            # Title
            draw.rectangle([(0, 0), (self.epd.height, 25)], fill=self.epd.BLACK)
            title = file_path.name
            if len(title) > 25:
                title = title[:22] + "..."
            draw.text((5, 5), title, font=self.font_medium, fill=self.epd.WHITE)
            
            # Content
            y_pos = 30
            line_height = 15
            max_chars_per_line = 35
            
            lines = content.split('\n')
            for line in lines:
                if y_pos > self.epd.width - 20:
                    break
                
                # Wrap long lines
                if len(line) > max_chars_per_line:
                    words = line.split(' ')
                    current_line = ""
                    for word in words:
                        if len(current_line + word) <= max_chars_per_line:
                            current_line += word + " "
                        else:
                            if current_line:
                                draw.text((5, y_pos), current_line.strip(), 
                                        font=self.font_small, fill=self.epd.BLACK)
                                y_pos += line_height
                                if y_pos > self.epd.width - 20:
                                    break
                            current_line = word + " "
                    
                    if current_line and y_pos <= self.epd.width - 20:
                        draw.text((5, y_pos), current_line.strip(), 
                                font=self.font_small, fill=self.epd.BLACK)
                        y_pos += line_height
                else:
                    draw.text((5, y_pos), line, font=self.font_small, fill=self.epd.BLACK)
                    y_pos += line_height
            
            self.display_buffer(display_image)
            logger.info(f"Displayed text file: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error displaying text file {file_path.name}: {e}")
            self.display_error(file_path.name, str(e))
    
    def display_pdf(self, file_path):
        """Display PDF file (first page) on e-ink"""
        try:
            # Try to use pdf2image if available
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(file_path, first_page=1, last_page=1)
                if images:
                    # Convert PDF page to image and display
                    pdf_image = images[0]
                    
                    # Handle transparency for PDF images
                    if pdf_image.mode == 'RGBA':
                        # Create white background for transparent pixels
                        white_bg = Image.new('RGB', pdf_image.size, (255, 255, 255))
                        white_bg.paste(pdf_image, mask=pdf_image.split()[-1])  # Use alpha channel as mask
                        pdf_image = white_bg
                    elif pdf_image.mode != 'RGB':
                        pdf_image = pdf_image.convert('RGB')
                    
                    pdf_image = self.resize_image_to_fit(pdf_image)
                    
                    display_image = Image.new('RGB', (self.epd.height, self.epd.width), self.epd.WHITE)
                    x_offset = (self.epd.height - pdf_image.width) // 2
                    y_offset = (self.epd.width - pdf_image.height) // 2
                    display_image.paste(pdf_image, (x_offset, y_offset))
                    
                    self.display_buffer(display_image)
                    logger.info(f"Displayed PDF: {file_path.name}")
                    return
            except ImportError:
                pass
            
            # Fallback: show PDF info
            self.display_file_info(file_path)
            
        except Exception as e:
            logger.error(f"Error displaying PDF {file_path.name}: {e}")
            self.display_error(file_path.name, str(e))
    
    def display_file_info(self, file_path):
        """Display file information for unsupported formats"""
        try:
            display_image = Image.new('RGB', (self.epd.height, self.epd.width), self.epd.WHITE)
            draw = ImageDraw.Draw(display_image)
            
            # Title
            draw.rectangle([(0, 0), (self.epd.height, 30)], fill=self.epd.BLACK)
            draw.text((5, 8), "New File Added", font=self.font_large, fill=self.epd.WHITE)
            
            # File info
            y_pos = 40
            info_items = [
                f"Name: {file_path.name}",
                f"Size: {file_path.stat().st_size} bytes",
                f"Type: {file_path.suffix.upper() if file_path.suffix else 'No extension'}",
                f"Modified: {time.ctime(file_path.stat().st_mtime)}"
            ]
            
            for item in info_items:
                if y_pos > self.epd.width - 30:
                    break
                
                # Wrap long lines
                if len(item) > 35:
                    words = item.split(' ')
                    current_line = ""
                    for word in words:
                        if len(current_line + word) <= 35:
                            current_line += word + " "
                        else:
                            if current_line:
                                draw.text((5, y_pos), current_line.strip(), 
                                        font=self.font_small, fill=self.epd.BLACK)
                                y_pos += 15
                            current_line = word + " "
                    
                    if current_line:
                        draw.text((5, y_pos), current_line.strip(), 
                                font=self.font_small, fill=self.epd.BLACK)
                        y_pos += 15
                else:
                    draw.text((5, y_pos), item, font=self.font_small, fill=self.epd.BLACK)
                    y_pos += 15
                
                y_pos += 5  # Extra spacing
            
            self.display_buffer(display_image)
            logger.info(f"Displayed file info: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error displaying file info {file_path.name}: {e}")
            self.display_error(file_path.name, str(e))
    
    def display_error(self, filename, error_msg):
        """Display error message on e-ink"""
        try:
            display_image = Image.new('RGB', (self.epd.height, self.epd.width), self.epd.WHITE)
            draw = ImageDraw.Draw(display_image)
            
            # Error title
            draw.rectangle([(0, 0), (self.epd.height, 30)], fill=self.epd.RED)
            draw.text((5, 8), "ERROR", font=self.font_large, fill=self.epd.WHITE)
            
            # Error details
            y_pos = 40
            draw.text((5, y_pos), f"File: {filename}", font=self.font_small, fill=self.epd.BLACK)
            y_pos += 20
            
            # Wrap error message
            words = error_msg.split(' ')
            current_line = ""
            for word in words:
                if len(current_line + word) <= 35:
                    current_line += word + " "
                else:
                    if current_line:
                        draw.text((5, y_pos), current_line.strip(), 
                                font=self.font_small, fill=self.epd.BLACK)
                        y_pos += 15
                        if y_pos > self.epd.width - 30:
                            break
                    current_line = word + " "
            
            if current_line and y_pos <= self.epd.width - 30:
                draw.text((5, y_pos), current_line.strip(), 
                        font=self.font_small, fill=self.epd.BLACK)
            
            self.display_buffer(display_image)
            logger.error(f"Displayed error for: {filename}")
            
        except Exception as e:
            logger.error(f"Error displaying error message: {e}")
            if "Bad file descriptor" in str(e):
                logger.info("Display error failed due to bad file descriptor - attempting reinitialize...")
                self.reinitialize_display()
                # Don't retry error display to avoid infinite loop
                logger.info("Display reinitialized after error display failure")
    
    def display_ip_address(self):
        """Display device IP address on e-ink"""
        try:
            ip_address = get_ip_address()
            hostname = socket.gethostname()
            
            display_image = Image.new('RGB', (self.epd.height, self.epd.width), self.epd.WHITE)
            draw = ImageDraw.Draw(display_image)
            
            # Title
            draw.rectangle([(0, 0), (self.epd.height, 35)], fill=self.epd.BLACK)
            draw.text((5, 10), "Device Information", font=self.font_large, fill=self.epd.WHITE)
            
            # Hostname
            y_pos = 50
            draw.text((5, y_pos), "Hostname:", font=self.font_medium, fill=self.epd.BLACK)
            y_pos += 25
            draw.text((5, y_pos), hostname, font=self.font_medium, fill=self.epd.RED)
            
            # IP Address
            y_pos += 35
            draw.text((5, y_pos), "IP Address:", font=self.font_medium, fill=self.epd.BLACK)
            y_pos += 25
            draw.text((5, y_pos), ip_address, font=self.font_large, fill=self.epd.RED)
            
            # Additional info
            y_pos += 40
            draw.text((5, y_pos), f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}", 
                     font=self.font_small, fill=self.epd.BLACK)
            
            # Instructions
            y_pos += 25
            draw.text((5, y_pos), "Connect to this IP address", font=self.font_small, fill=self.epd.BLACK)
            y_pos += 15
            draw.text((5, y_pos), "for file uploads", font=self.font_small, fill=self.epd.BLACK)
            
            self.display_buffer(display_image)
            logger.info(f"Displayed IP address: {ip_address} (hostname: {hostname})")
            
        except Exception as e:
            logger.error(f"Error displaying IP address: {e}")
            self.display_error("IP Display", str(e))
    
    def display_welcome_screen(self):
        """Display welcome screen with IP address and web interface information"""
        try:
            ip_address = get_ip_address()
            hostname = socket.gethostname()
            
            display_image = Image.new('RGB', (self.epd.height, self.epd.width), self.epd.WHITE)
            draw = ImageDraw.Draw(display_image)
            
            # Title
            draw.rectangle([(0, 0), (self.epd.height, 35)], fill=self.epd.BLACK)
            draw.text((5, 10), "E-ink File Monitor", font=self.font_large, fill=self.epd.WHITE)
            
            # IP Address and Web Interface (consolidated)
            y_pos = 45
            draw.text((5, y_pos), "Web Interface:", font=self.font_medium, fill=self.epd.BLACK)
            y_pos += 20
            web_url = f"http://{ip_address}:5000"
            draw.text((5, y_pos), web_url, font=self.font_medium, fill=self.epd.RED)
            
            # Hostname and folder (consolidated)
            y_pos += 25
            draw.text((5, y_pos), f"Host: {hostname}", font=self.font_small, fill=self.epd.BLACK)
            
            # Folder path (shortened)
            y_pos += 15
            folder_path = str(self.watched_folder)
            if len(folder_path) > 25:
                folder_path = "..." + folder_path[-22:]
            draw.text((5, y_pos), f"Folder: {folder_path}", font=self.font_small, fill=self.epd.BLACK)
            
            # Status message
            y_pos += 20
            draw.text((5, y_pos), "Ready for uploads!", font=self.font_medium, fill=self.epd.RED)
            
            self.display_buffer(display_image)
            logger.info(f"Displayed welcome screen - IP: {ip_address}, Web: {web_url}")
            
        except Exception as e:
            logger.error(f"Error displaying welcome screen: {e}")
            self.display_error("Welcome Screen", str(e))
    
    def resize_image_to_fit(self, image):
        """Resize image to fit display while maintaining aspect ratio, with configurable crop mode"""
        display_width = self.epd.width
        display_height = self.epd.height
        
        # If image is smaller than display in both dimensions, scale up to fit
        if image.width <= display_height and image.height <= display_width:
            # Calculate scaling factor to fit within display
            scale_x = display_height / image.width
            scale_y = display_width / image.height
            scale = min(scale_x, scale_y)
            
            new_width = int(image.width * scale)
            new_height = int(image.height * scale)
            
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # If image is larger than display in any dimension, handle based on crop mode
        else:
            # Use the loaded crop mode setting
            crop_mode = getattr(self, 'image_crop_mode', 'center_crop')
            if crop_mode == 'center_crop':
                # Center-crop mode: scale to cover display, then crop
                scale_x = display_height / image.width
                scale_y = display_width / image.height
                scale = max(scale_x, scale_y)  # Use max to ensure image covers display
                
                # Resize image to cover display
                new_width = int(image.width * scale)
                new_height = int(image.height * scale)
                resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Center-crop to exact display size
                left = (new_width - display_height) // 2
                top = (new_height - display_width) // 2
                right = left + display_height
                bottom = top + display_width
                
                cropped_image = resized_image.crop((left, top, right, bottom))
                
                logger.info(f"Center-cropped image from {image.size} to {cropped_image.size}")
                return cropped_image
                
            else:  # fit_with_letterbox
                # Letterbox mode: scale to fit within display, add letterboxing
                scale_x = display_height / image.width
                scale_y = display_width / image.height
                scale = min(scale_x, scale_y)  # Use min to fit within display
                
                new_width = int(image.width * scale)
                new_height = int(image.height * scale)
                
                resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                logger.info(f"Letterboxed image from {image.size} to {resized_image.size}")
                return resized_image
    
    def cleanup(self, force_clear=None):
        """Clean up resources"""
        try:
            # Use force_clear if provided, otherwise use instance setting
            should_clear = force_clear if force_clear is not None else self.clear_on_exit
            
            if should_clear:
                self.epd.Clear()
                logger.info("E-ink display cleared")
            else:
                logger.info("E-ink display NOT cleared (keeping content)")
            self.epd.sleep()
            logger.info("E-ink display cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    parser = argparse.ArgumentParser(
        description='E-ink File Display Monitor for Raspberry Pi with Waveshare 2.15" display',
        epilog='''
Examples:
  %(prog)s                                    # Monitor ~/watched_files, show welcome screen
  %(prog)s --latest-file                      # Display latest file in folder on startup
  %(prog)s --show-ip                          # Display device IP address and exit
  %(prog)s -d image.jpg                       # Display image.jpg on startup, then monitor
  %(prog)s -f ~/my_files --clear-start        # Monitor ~/my_files, clear screen on start
  %(prog)s --no-clear-exit                    # Don't clear screen when exiting
  %(prog)s --normal-orientation               # Display in normal orientation (not upside-down)
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--folder', '-f', default='~/watched_files', 
                       help='Folder to monitor for files (default: ~/watched_files)')
    parser.add_argument('--display-file', '-d', 
                       help='Display this file on startup and wait for new files')
    parser.add_argument('--latest-file', '-l', action='store_true',
                       help='Display the latest file in watched folder on startup')
    parser.add_argument('--show-ip', action='store_true',
                       help='Display device IP address and exit')
    parser.add_argument('--no-clear-exit', action='store_true',
                       help='Do not clear screen on exit')
    parser.add_argument('--clear-start', action='store_true',
                       help='Clear screen on start')
    parser.add_argument('--normal-orientation', action='store_true',
                       help='Display in normal orientation (not upside-down)')
    
    args = parser.parse_args()
    
    # Handle IP display option (show IP and exit)
    if args.show_ip:
        try:
            # Initialize display just for IP display
            epd = epd2in15g.EPD()
            epd.init()
            
            # Create temporary handler just to display IP
            temp_handler = EinkDisplayHandler(clear_on_start=False, clear_on_exit=False)
            temp_handler.display_upside_down = not args.normal_orientation
            temp_handler.display_ip_address()
            
            # Clean up
            epd.sleep()
            logger.info("IP address displayed. Exiting.")
            return
        except Exception as e:
            logger.error(f"Error displaying IP address: {e}")
            return
    
    # Configuration
    WATCHED_FOLDER = os.path.expanduser(args.folder)
    DISPLAY_UPSIDE_DOWN = not args.normal_orientation
    CLEAR_ON_START = args.clear_start
    CLEAR_ON_EXIT = not args.no_clear_exit
    
    # Set up signal handlers only if we're in the main thread
    signal_handlers_registered = False
    try:
        signal.signal(signal.SIGINT, signal_handler_clear_exit)      # Ctrl+C - clear and exit
        logger.info("Signal handlers registered for exit control")
        signal_handlers_registered = True
    except ValueError as e:
        # This happens when not in main thread (e.g., when called from run_eink_system.py)
        logger.info("Signal handlers not registered (not in main thread)")
        logger.info("Exit control will be handled by parent process")
    
    # Create the handler
    handler = EinkDisplayHandler(WATCHED_FOLDER, 
                               clear_on_start=CLEAR_ON_START, 
                               clear_on_exit=CLEAR_ON_EXIT)
    handler.display_upside_down = DISPLAY_UPSIDE_DOWN
    
    # Set up file system observer
    observer = Observer()
    observer.schedule(handler, handler.watched_folder, recursive=False)
    
    try:
        observer.start()
        logger.info("File monitoring started.")
        if signal_handlers_registered:
            logger.info("Press Ctrl+C to stop and clear display")
        else:
            logger.info("Exit control handled by parent process")
        
        # Display initial file if provided
        if args.display_file:
            display_file_path = Path(args.display_file)
            if display_file_path.exists():
                logger.info(f"Displaying initial file: {display_file_path}")
                handler.display_file(display_file_path)
            else:
                logger.error(f"Initial display file not found: {display_file_path}")
                # Show error message on display
                display_image = Image.new('RGB', (handler.epd.height, handler.epd.width), handler.epd.WHITE)
                draw = ImageDraw.Draw(display_image)
                draw.rectangle([(0, 0), (handler.epd.height, 35)], fill=handler.epd.RED)
                draw.text((5, 10), "File Not Found", font=handler.font_large, fill=handler.epd.WHITE)
                draw.text((5, 50), f"File: {display_file_path.name}", font=handler.font_small, fill=handler.epd.BLACK)
                handler.display_buffer(display_image)
        elif args.latest_file:
            # Display the latest file in the watched folder
            latest_file = handler.get_latest_file()
            if latest_file:
                logger.info(f"Displaying latest file: {latest_file}")
                handler.display_file(latest_file)
            else:
                logger.info("No files found in watched folder, showing welcome screen")
                handler.display_welcome_screen()
        else:
            # Display welcome screen with IP address and web interface info
            handler.display_welcome_screen()
        
        # Keep the script running until exit is requested
        if signal_handlers_registered:
            # Use signal-based exit control
            while not exit_requested:
                time.sleep(1)
        else:
            # Fallback to KeyboardInterrupt when running in thread
            while True:
                time.sleep(1)
            
    except KeyboardInterrupt:
        # This shouldn't happen anymore since we handle signals, but keep as fallback
        logger.info("Stopping file monitor...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        observer.stop()
        observer.join()
        # Use the global flag to determine if we should clear
        global clear_on_exit_requested
        handler.cleanup(force_clear=clear_on_exit_requested)

if __name__ == "__main__":
    main()
