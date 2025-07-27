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
import threading
import json
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

from unified_epd_adapter import UnifiedEPD, EPDConfig

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variables for exit handling
exit_requested = False
clear_on_exit_requested = True

# Global lock to prevent concurrent display operations
display_lock = threading.Lock()

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
    def __init__(self, watched_folder="~/watched_files", clear_on_start=False, clear_on_exit=True, disable_startup_timer=False, disable_refresh_timer=False, refresh_interval_hours=24, startup_delay_minutes=1, enable_manufacturer_timing=False, enable_sleep_mode=True, display_type=None):
        logger.info("DEBUG: EinkDisplayHandler.__init__ called")
        self.watched_folder = Path(os.path.expanduser(watched_folder))
        self.watched_folder.mkdir(exist_ok=True)
        self.clear_on_start = clear_on_start
        self.clear_on_exit = clear_on_exit
        
        # Initialize e-paper display
        if display_type is None:
            display_type = EPDConfig.load_display_config().get('display_type', 'epd2in15g')
        logger.info(f"Initializing display type: {display_type}")
        self.epd = UnifiedEPD.create_display(display_type)
        
        # Clear screen on start if requested
        if self.clear_on_start:
            self.epd.Clear()
            time.sleep(1)
        
        # Configure display orientation 
        # Default orientation (will be overridden by settings or command line)
        self.orientation = 'landscape'
        
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
        
        # Timing control variables
        self.startup_time = time.time()
        self.last_file_update_time = time.time()
        self.last_refresh_time = time.time()
        self.current_displayed_file = None
        
        # Startup timer control
        self.startup_timer_active = True
        self.manual_selection_during_startup = False
        
        # E-ink display timing requirements (manufacturer specifications)
        self.enable_manufacturer_timing = enable_manufacturer_timing
        self.enable_sleep_mode = enable_sleep_mode
        self.min_refresh_interval = 180 if enable_manufacturer_timing else 0  # Minimum 180 seconds between refreshes (if enabled)
        
        # Set initial timing values from constructor parameters
        self.refresh_interval_hours = refresh_interval_hours
        self.startup_delay_minutes = startup_delay_minutes
        self.disable_startup_timer = disable_startup_timer
        self.disable_refresh_timer = disable_refresh_timer
        
        # Load settings (this will override timing values from settings file if available)
        self.load_settings()
        
        # Start background threads for timing features (unless disabled)
        self.startup_timer_thread = None
        self.refresh_timer_thread = None
        
        # Start startup timer if enabled
        if not self.disable_startup_timer:
            self.startup_timer_thread = threading.Thread(target=self.startup_timer_worker, daemon=True)
            self.startup_timer_thread.start()
            logger.info(f"Startup timer enabled: {self.startup_delay_minutes}-minute delay")
        else:
            logger.info("Startup timer disabled")
            
        # Start refresh timer if enabled
        if not self.disable_refresh_timer:
            self.refresh_timer_thread = threading.Thread(target=self.refresh_timer_worker, daemon=True)
            self.refresh_timer_thread.start()
            logger.info(f"Refresh timer enabled: {self.refresh_interval_hours}-hour interval")
        else:
            logger.info("Refresh timer disabled")
        
        logger.info(f"Monitoring folder: {self.watched_folder.absolute()}")
        logger.info(f"E-ink display initialized - Size: {self.epd.width}x{self.epd.height}")
        logger.info(f"Display orientation: {self.orientation}")
        logger.info(f"Auto-display uploads: {self.auto_display_uploads}")
        logger.info(f"Manufacturer timing requirements: {'ENABLED' if self.enable_manufacturer_timing else 'DISABLED'}")
        logger.info(f"Sleep mode: {'ENABLED' if self.enable_sleep_mode else 'DISABLED'}")
    

    
    def startup_timer_worker(self):
        """Worker thread for configurable startup display delay"""
        try:
            # Show welcome screen first
            logger.info("Showing welcome screen during startup delay...")
            self.display_welcome_screen()
            
            # Wait for the configured startup delay
            startup_delay_seconds = self.startup_delay_minutes * 60
            time.sleep(startup_delay_seconds)
            
            # Check if manual selection was made during startup
            if self.manual_selection_during_startup:
                logger.info("Manual selection made during startup - skipping automatic priority file display")
                self.startup_timer_active = False
                return
            
            # Check if we should display the priority file
            if not exit_requested and self.startup_timer_active:
                logger.info(f"{self.startup_delay_minutes}-minute startup timer triggered - checking for priority file")
                self.display_latest_file_if_no_updates()
                
        except Exception as e:
            logger.error(f"Startup timer worker error: {e}")
    
    def refresh_timer_worker(self):
        """Worker thread for configurable refresh interval"""
        try:
            while not exit_requested:
                # Wait for the configured refresh interval
                refresh_interval_seconds = self.refresh_interval_hours * 3600
                time.sleep(refresh_interval_seconds)
                
                if not exit_requested:
                    logger.info(f"{self.refresh_interval_hours}-hour refresh timer triggered - refreshing display")
                    self.perform_display_refresh()
                    
        except Exception as e:
            logger.error(f"Refresh timer worker error: {e}")
    
    def display_latest_file_if_no_updates(self):
        """Display the priority file if no updates have happened since startup"""
        try:
            # Get the priority file to display
            priority_file = self.get_priority_display_file()
            
            if priority_file:
                # Check if this file was updated since startup
                file_mtime = priority_file.stat().st_mtime
                if file_mtime < self.startup_time:
                    # No new files since startup, display the priority file
                    logger.info(f"No updates since startup - displaying priority file: {priority_file.name}")
                    self.display_file(priority_file)
                    self.current_displayed_file = priority_file
                else:
                    logger.info("Files have been updated since startup - skipping startup display")
            else:
                logger.info("No priority file found for startup display")
                
        except Exception as e:
            logger.error(f"Error in startup display: {e}")
    
    def perform_display_refresh(self):
        """Perform a configurable refresh by clearing and re-displaying current content"""
        try:
            logger.info(f"Performing {self.refresh_interval_hours}-hour display refresh...")
            
            # Clear the display
            self.epd.Clear()
            time.sleep(1)
            
            # Get the priority file to display
            priority_file = self.get_priority_display_file()
            if priority_file:
                logger.info(f"Displaying priority file after refresh: {priority_file.name}")
                self.display_file(priority_file)
                self.current_displayed_file = priority_file
            else:
                # No priority file available, show welcome screen
                logger.info("No priority file available after refresh - showing welcome screen")
                self.display_welcome_screen()
            
            self.last_refresh_time = time.time()
            logger.info(f"{self.refresh_interval_hours}-hour refresh completed successfully")
            
        except Exception as e:
            logger.error(f"Error during display refresh: {e}")
            # Try to reinitialize display if there was an error
            try:
                self.reinitialize_display()
                logger.info("Display reinitialized after refresh error")
            except Exception as reinit_error:
                logger.error(f"Display reinitialization failed after refresh error: {reinit_error}")
    
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
                    
                    # Load orientation setting
                    self.orientation = settings.get('orientation', 'landscape')
                    
                    # Load timing settings
                    self.startup_delay_minutes = settings.get('startup_delay_minutes', 1)
                    self.refresh_interval_hours = settings.get('refresh_interval_hours', 24)
                    self.disable_startup_timer = settings.get('disable_startup_timer', False)
                    self.disable_refresh_timer = settings.get('disable_refresh_timer', False)
                    self.enable_manufacturer_timing = settings.get('enable_manufacturer_timing', False)
                    self.enable_sleep_mode = settings.get('enable_sleep_mode', True)
                    self.selected_image = settings.get('selected_image', None)
                    
                    logger.info(f"Settings loaded from {settings_file} - Auto-display: {self.auto_display_uploads}, Crop mode: {self.image_crop_mode}, Orientation: {self.orientation}, Selected image: {self.selected_image}")
                    logger.info(f"Timing settings - Startup timer: {'DISABLED' if self.disable_startup_timer else 'ENABLED'}, Refresh timer: {'DISABLED' if self.disable_refresh_timer else 'ENABLED'}")
                    logger.info(f"Timing values - Startup delay: {self.startup_delay_minutes}min, Refresh: {self.refresh_interval_hours}h")
            else:
                # Default settings
                self.auto_display_uploads = True
                self.image_crop_mode = 'center_crop'
                self.orientation = 'landscape'
                self.startup_delay_minutes = 1
                self.refresh_interval_hours = 24
                self.disable_startup_timer = False
                self.disable_refresh_timer = False
                self.enable_manufacturer_timing = False
                self.enable_sleep_mode = True
                self.selected_image = None
                logger.info(f"Settings file not found at {settings_file}, using defaults")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            # Fallback to defaults
            self.auto_display_uploads = True
            self.image_crop_mode = 'center_crop'
            self.orientation = 'landscape'
            self.startup_delay_minutes = 1
            self.refresh_interval_hours = 24
            self.disable_startup_timer = False
            self.disable_refresh_timer = False
            self.enable_manufacturer_timing = False
            self.enable_sleep_mode = True
            self.selected_image = None
    
    def reload_settings(self):
        """Reload settings from file (useful when settings change)"""
        self.load_settings()
        logger.info(f"Settings reloaded - Auto-display: {self.auto_display_uploads}, Crop mode: {self.image_crop_mode}, Orientation: {self.orientation}")
    
    def save_selected_image_setting(self, filename):
        """Save the selected image setting to the settings file"""
        try:
            # Use the same path as the upload server
            settings_file = Path(os.path.expanduser('~/watched_files')) / '.settings.json'
            logger.info(f"DEBUG: Saving selected image setting to: {settings_file.absolute()}")
            
            # Load existing settings
            settings = {}
            if settings_file.exists():
                import json
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
            
            # Update selected image
            settings['selected_image'] = filename
            
            # Save settings back to file
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            logger.info(f"Saved selected image setting: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving selected image setting: {e}")
    
    def apply_orientation(self, image):
        """Apply orientation transformation to an image based on current orientation setting"""
        try:
            orientation = getattr(self, 'orientation', 'landscape')
            
            if orientation == 'landscape':
                # No rotation needed
                return image
            elif orientation == 'landscape_flipped':
                # Rotate 180 degrees
                return image.rotate(180)
            elif orientation == 'portrait':
                # Rotate 90 degrees clockwise
                return image.rotate(90, expand=True)
            elif orientation == 'portrait_flipped':
                # Rotate 270 degrees clockwise (or 90 degrees counter-clockwise)
                return image.rotate(270, expand=True)
            else:
                # Unknown orientation, return original
                logger.warning(f"Unknown orientation: {orientation}, using landscape")
                return image
                
        except Exception as e:
            logger.error(f"Error applying orientation {getattr(self, 'orientation', 'landscape')}: {e}")
            return image
    
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
    
    def get_priority_display_file(self):
        """Get the file that should be displayed based on priority logic"""
        try:
            logger.info(f"DEBUG: get_priority_display_file called, watched_folder: {self.watched_folder.absolute()}")
            logger.info(f"DEBUG: selected_image: {self.selected_image}")
            
            # Priority 1: Selected image (if set and exists) - takes precedence over uploads
            if self.selected_image:
                selected_file = self.watched_folder / self.selected_image
                logger.info(f"DEBUG: Looking for selected file at: {selected_file.absolute()}")
                if selected_file.exists():
                    logger.info(f"Priority: Selected image: {self.selected_image}")
                    return selected_file
                else:
                    logger.warning(f"Selected image not found: {self.selected_image} - clearing invalid selection")
                    logger.info(f"DEBUG: File does not exist at: {selected_file.absolute()}")
                    # Clear the invalid selected image setting
                    self.selected_image = None
                    self.save_selected_image_setting(None)
            
            # Priority 2: Latest file (fallback)
            latest_file = self.get_latest_file()
            if latest_file:
                logger.info(f"Priority: Latest file: {latest_file.name}")
                return latest_file
            
            # Priority 4: None (will show welcome screen)
            logger.info("Priority: No file to display (will show welcome screen)")
            return None
            
        except Exception as e:
            logger.error(f"Error getting priority display file: {e}")
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
        """Display image buffer with always-on sleep mode and optional timing restrictions"""
        try:
            # Check manufacturer timing requirements if enabled
            if self.enable_manufacturer_timing:
                current_time = time.time()
                if hasattr(self, 'last_refresh_time') and (current_time - self.last_refresh_time) < self.min_refresh_interval:
                    remaining_time = self.min_refresh_interval - (current_time - self.last_refresh_time)
                    logger.warning(f"Display refresh too soon. Must wait {remaining_time:.1f} more seconds (manufacturer requirement: 180s minimum)")
                    return False
            
            # Wake display from sleep mode if sleep mode is enabled
            if self.enable_sleep_mode:
                logger.info("Starting display operation - waking display from sleep...")
                self.epd.init()
                time.sleep(0.5)  # Brief delay after wake
            else:
                logger.info("Starting display operation (sleep mode disabled)...")
            
            # Apply orientation
            image = self.apply_orientation(image)

            logger.info("Calling epd.display()...")
            self.epd.display(self.epd.getbuffer(image))
            
            # Put display back to sleep mode if sleep mode is enabled
            if self.enable_sleep_mode:
                logger.info("Display completed - putting display to sleep...")
                self.epd.sleep()
            else:
                logger.info("Display completed (sleep mode disabled)")
            
            # Update last refresh time if manufacturer timing is enabled
            if self.enable_manufacturer_timing:
                self.last_refresh_time = time.time()
            
            logger.info("Display operation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Display buffer error: {e}")
            if "Bad file descriptor" in str(e):
                logger.info("Attempting to reinitialize display...")
                self.reinitialize_display()
                # Try again after reinitializing
                # Apply orientation again after reinitialization
                image = self.apply_orientation(image)
                self.epd.display(self.epd.getbuffer(image))
                if self.enable_sleep_mode:
                    self.epd.sleep()  # Put to sleep after successful retry
                return True
            return False
    
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
        
        # Check if this is a command file from the web interface
        if file_path.name == '.display_command':
            try:
                # Read and execute the command
                with open(file_path, 'r') as f:
                    command_data = json.load(f)
                
                action = command_data.get('action')
                filename = command_data.get('filename')
                
                logger.info(f"Received command: {action} for file: {filename}")
                
                if action == 'display_file' and filename:
                    # Display the requested file
                    target_file = self.watched_folder / filename
                    if target_file.exists():
                        logger.info(f"Executing display command for: {filename}")
                        self.display_file(target_file)
                        self.current_displayed_file = target_file
                        
                        # Mark that manual selection was made during startup
                        if self.startup_timer_active:
                            logger.info("Manual selection detected during startup - will cancel automatic priority display")
                            self.manual_selection_during_startup = True
                    else:
                        logger.error(f"Command file not found: {filename}")
                elif action == 'refresh_display':
                    # Refresh the display with current priority file
                    logger.info("Executing refresh display command")
                    
                    # During startup, just reload settings without forcing a display refresh
                    if self.startup_timer_active:
                        logger.info("Settings change detected during startup - reloading settings without display refresh")
                        self.reload_settings()  # Still reload settings for future use
                        return
                    
                    # Normal refresh behavior (outside startup)
                    self.reload_settings()  # Reload settings first
                    priority_file = self.get_priority_display_file()
                    if priority_file:
                        logger.info(f"Refreshing display with priority file: {priority_file.name}")
                        self.display_file(priority_file)
                        self.current_displayed_file = priority_file
                    else:
                        logger.info("No priority file found for refresh")
                
                # Clean up command file
                file_path.unlink()
                return
                
            except Exception as e:
                logger.error(f"Error processing command file: {e}")
                # Clean up command file even on error
                try:
                    file_path.unlink()
                except:
                    pass
                return
        
        # Update timing variables
        self.last_file_update_time = time.time()
        
        # Longer delay to ensure file is fully written
        time.sleep(2.0)
        
        # Validate file is complete and readable
        if not self.validate_file(file_path):
            logger.error(f"File validation failed: {file_path.name}")
            return
        
        # Check if auto-display is enabled (use current setting, don't reload)
        logger.info(f"Auto-display setting: {self.auto_display_uploads}")
        if self.auto_display_uploads:
            try:
                # Set this as the current displayed file first
                self.current_displayed_file = file_path
                
                # Mark that a new file was uploaded during startup
                if self.startup_timer_active:
                    logger.info("New file upload detected during startup - will cancel automatic priority display")
                    self.manual_selection_during_startup = True
                
                success = self.display_file(file_path)
                if success:
                    logger.info(f"Auto-displayed file: {file_path.name}")
                elif self.enable_manufacturer_timing:
                    logger.warning(f"Display operation failed for {file_path.name} - likely due to timing restrictions")
                    # Queue for retry after minimum interval
                    retry_time = self.min_refresh_interval - (time.time() - self.last_refresh_time)
                    if retry_time > 0:
                        logger.info(f"Will retry displaying {file_path.name} in {retry_time:.1f} seconds")
                        threading.Timer(retry_time, self.retry_display_file, args=[file_path]).start()
                else:
                    logger.warning(f"Display operation failed for {file_path.name}")
            except Exception as e:
                logger.error(f"Error auto-displaying file {file_path.name}: {e}")
                self.display_error(file_path.name, str(e))
        else:
            logger.info(f"Auto-display disabled - file {file_path.name} not displayed")
    
    def display_file(self, file_path):
        """Convert and display file on e-ink display"""
        # Use lock to prevent concurrent display operations
        if not display_lock.acquire(timeout=5):  # Wait up to 5 seconds
            logger.warning(f"Display lock timeout - skipping display of {file_path.name}")
            return False
            
        try:
            logger.info(f"DEBUG: Starting display of {file_path.name}")
            file_ext = file_path.suffix.lower()
            
            if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                result = self.display_image(file_path)
            elif file_ext in ['.txt', '.md', '.py', '.js', '.html', '.css']:
                result = self.display_text_file(file_path)
            elif file_ext == '.pdf':
                result = self.display_pdf(file_path)
            else:
                result = self.display_file_info(file_path)
                
            logger.info(f"DEBUG: Finished display of {file_path.name}, result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in display_file for {file_path.name}: {e}")
            return False
        finally:
            display_lock.release()
            logger.info(f"DEBUG: Released display lock for {file_path.name}")
    
    def retry_display_file(self, file_path):
        """Retry displaying a file after timing restrictions are met"""
        logger.info(f"Retrying display of {file_path.name}")
        try:
            success = self.display_file(file_path)
            if success:
                self.current_displayed_file = file_path
                logger.info(f"Successfully displayed file on retry: {file_path.name}")
            else:
                logger.warning(f"Retry failed for {file_path.name}")
        except Exception as e:
            logger.error(f"Error in retry_display_file for {file_path.name}: {e}")
    
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
            

            # Apply orientation
            image = self.apply_orientation(image)

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
            
            success = self.display_buffer(display_image)
            if success:
                logger.info(f"Displayed image: {file_path.name} (original: {original_size}, final: {display_image.size})")
            return success
            
        except Exception as e:
            logger.error(f"Error displaying image {file_path.name}: {e}")
            self.display_error(file_path.name, str(e))
            return False
    
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
            
            # Apply orientation to the display image
            display_image = self.apply_orientation(display_image)
            
            success = self.display_buffer(display_image)
            if success:
                logger.info(f"Displayed text file: {file_path.name}")
            return success
            
        except Exception as e:
            logger.error(f"Error displaying text file {file_path.name}: {e}")
            self.display_error(file_path.name, str(e))
            return False
    
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
                    
                    # Apply orientation to the display image
                    display_image = self.apply_orientation(display_image)
                    
                    success = self.display_buffer(display_image)
                    if success:
                        logger.info(f"Displayed PDF: {file_path.name}")
                    return success
            except ImportError:
                pass
            
            # Fallback: show PDF info
            return self.display_file_info(file_path)
            
        except Exception as e:
            logger.error(f"Error displaying PDF {file_path.name}: {e}")
            self.display_error(file_path.name, str(e))
            return False
    
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
            
            # Apply orientation to the display image
            display_image = self.apply_orientation(display_image)
            
            success = self.display_buffer(display_image)
            if success:
                logger.info(f"Displayed file info: {file_path.name}")
            return success
            
        except Exception as e:
            logger.error(f"Error displaying file info {file_path.name}: {e}")
            self.display_error(file_path.name, str(e))
            return False
    
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
            
            # Apply orientation to the display image
            display_image = self.apply_orientation(display_image)
            
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
            
            # Apply orientation to the display image
            display_image = self.apply_orientation(display_image)
            
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
            
            # Apply orientation to the display image
            display_image = self.apply_orientation(display_image)
            
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
  %(prog)s --orientation portrait             # Display in portrait orientation
  %(prog)s --orientation portrait_flipped     # Display in flipped portrait orientation
  %(prog)s --disable-timing                   # Disable automatic timing features
  %(prog)s --display-type epd7in3e            # Use 7.3" color display
  %(prog)s --display-type epd13in3E           # Use 13.3" color display

Orientation Options:
  - landscape: Normal horizontal orientation (default)
  - landscape_flipped: Upside-down horizontal orientation
  - portrait: Vertical orientation (rotated 90° clockwise)
  - portrait_flipped: Flipped vertical orientation (rotated 270° clockwise)

Timing Features:
  - Configurable startup display: Shows latest file if no updates occur within specified time of startup (default: 1 minute)
  - Configurable refresh: Automatically refreshes display at specified interval to prevent ghosting (default: 24 hours)
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--folder', '-f', default='~/watched_files', 
                       help='Folder to monitor for files (default: ~/watched_files)')
    parser.add_argument('--display-file', '-d', 
                       help='Display this file on startup and wait for new files')
    parser.add_argument('--display-type', choices=['epd2in15g', 'epd7in3e', 'epd13in3E'],
                       help='E-ink display type (default: from config file or epd2in15g)')
    parser.add_argument('--latest-file', '-l', action='store_true',
                       help='Display the latest file in watched folder on startup')
    parser.add_argument('--show-ip', action='store_true',
                       help='Display device IP address and exit')
    parser.add_argument('--no-clear-exit', action='store_true',
                       help='Do not clear screen on exit')
    parser.add_argument('--clear-start', action='store_true',
                       help='Clear screen on start')
    parser.add_argument('--orientation', choices=['landscape', 'landscape_flipped', 'portrait', 'portrait_flipped'],
                       default='landscape', help='Display orientation (default: landscape)')
    parser.add_argument('--disable-startup-timer', action='store_true',
                       help='Disable automatic startup display timer')
    parser.add_argument('--disable-refresh-timer', action='store_true',
                       help='Disable automatic refresh timer')
    parser.add_argument('--refresh-interval', type=int, default=24,
                       help='Refresh interval in hours (default: 24)')
    parser.add_argument('--startup-delay', type=int, default=1,
                       help='Startup delay in minutes before displaying latest file (default: 1)')
    parser.add_argument('--enable-manufacturer-timing', action='store_true',
                       help='Enable manufacturer timing requirements (180s minimum refresh interval)')
    parser.add_argument('--disable-sleep-mode', action='store_true',
                       help='Disable sleep mode between operations (faster but uses more power)')
    
    args = parser.parse_args()
    
    # Handle IP display option (show IP and exit)
    if args.show_ip:
        try:
            # Get display type for IP display
            display_type = args.display_type or EPDConfig.load_display_config().get('display_type', 'epd2in15g')
            logger.info(f"Using display type for IP display: {display_type}")
            
            # Create temporary handler just to display IP
            temp_handler = EinkDisplayHandler(clear_on_start=False, clear_on_exit=False, display_type=display_type)
            temp_handler.orientation = args.orientation
            temp_handler.display_ip_address()
            
            # Clean up
            temp_handler.epd.sleep()
            logger.info("IP address displayed. Exiting.")
            return
        except Exception as e:
            logger.error(f"Error displaying IP address: {e}")
            return
    
    # Configuration
    WATCHED_FOLDER = os.path.expanduser(args.folder)
    ORIENTATION = args.orientation
    CLEAR_ON_START = args.clear_start
    CLEAR_ON_EXIT = not args.no_clear_exit
    DISABLE_STARTUP_TIMER = args.disable_startup_timer
    DISABLE_REFRESH_TIMER = args.disable_refresh_timer
    REFRESH_INTERVAL_HOURS = args.refresh_interval
    STARTUP_DELAY_MINUTES = args.startup_delay
    ENABLE_MANUFACTURER_TIMING = args.enable_manufacturer_timing
    ENABLE_SLEEP_MODE = not args.disable_sleep_mode
    DISPLAY_TYPE = args.display_type
    
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
                               clear_on_exit=CLEAR_ON_EXIT,
                               disable_startup_timer=DISABLE_STARTUP_TIMER,
                               disable_refresh_timer=DISABLE_REFRESH_TIMER,
                               refresh_interval_hours=REFRESH_INTERVAL_HOURS,
                               startup_delay_minutes=STARTUP_DELAY_MINUTES,
                               enable_manufacturer_timing=ENABLE_MANUFACTURER_TIMING,
                               enable_sleep_mode=ENABLE_SLEEP_MODE,
                               display_type=DISPLAY_TYPE)
    handler.orientation = ORIENTATION
    
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
                handler.current_displayed_file = display_file_path  # Track current displayed file
                
                # Set this file as the selected image so it persists
                handler.selected_image = display_file_path.name
                handler.save_selected_image_setting(display_file_path.name)
                logger.info(f"Set {display_file_path.name} as selected image")
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
            # Display the priority file in the watched folder
            priority_file = handler.get_priority_display_file()
            if priority_file:
                logger.info(f"Displaying priority file: {priority_file}")
                handler.display_file(priority_file)
                handler.current_displayed_file = priority_file  # Track current displayed file
            else:
                logger.info("No priority file found, showing welcome screen")
                handler.display_welcome_screen()
        else:
            # Check if startup timer is enabled
            if not DISABLE_STARTUP_TIMER:
                # Startup timer is enabled - show welcome screen, timer will handle priority file later
                logger.info("Startup timer enabled - showing welcome screen, priority file will be displayed after delay")
                handler.display_welcome_screen()
            else:
                # Startup timer is disabled - display priority file immediately
                priority_file = handler.get_priority_display_file()
                if priority_file:
                    logger.info(f"Displaying priority file: {priority_file}")
                    handler.display_file(priority_file)
                    handler.current_displayed_file = priority_file  # Track current displayed file
                else:
                    logger.info("No priority file found, showing welcome screen")
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
