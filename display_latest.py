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
    def __init__(self, watched_folder="~/watched_files", clear_on_start=False, clear_on_exit=True, disable_startup_timer=None, disable_refresh_timer=None, refresh_interval_hours=None, startup_delay_minutes=None, enable_manufacturer_timing=None, enable_sleep_mode=None, display_type=None):
        logger.info("DEBUG: EinkDisplayHandler.__init__ called")
        self.watched_folder = Path(os.path.expanduser(watched_folder))
        self.watched_folder.mkdir(exist_ok=True)
        self.clear_on_start = clear_on_start
        self.clear_on_exit = clear_on_exit
        
        # Initialize e-paper display
        if display_type is None:
            display_type = EPDConfig.load_display_config()
        logger.info(f"Initializing display type: {display_type}")
        self.epd = UnifiedEPD.create_display(display_type)
        self.epd.init()
        
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
        
        # Override settings with command line arguments (command line takes precedence)
        # Command line arguments always take precedence when provided
        logger.info(f"COMMAND LINE OVERRIDE - disable_startup_timer parameter: {disable_startup_timer}")
        logger.info(f"COMMAND LINE OVERRIDE - disable_startup_timer parameter type: {type(disable_startup_timer)}")
        
        # Store original settings file values for comparison
        original_disable_startup_timer = self.disable_startup_timer
        original_disable_refresh_timer = self.disable_refresh_timer
        original_startup_delay_minutes = self.startup_delay_minutes
        original_refresh_interval_hours = self.refresh_interval_hours
        original_enable_manufacturer_timing = self.enable_manufacturer_timing
        original_enable_sleep_mode = self.enable_sleep_mode
        
        # Track if any command line arguments were used
        command_line_args_used = False
        
        # Convert string arguments to appropriate types
        if disable_startup_timer is not None:
            disable_startup_timer_bool = disable_startup_timer.lower() == 'true'
            if disable_startup_timer_bool != original_disable_startup_timer:
                self.disable_startup_timer = disable_startup_timer_bool
                logger.info(f"Command line override: disable_startup_timer = {disable_startup_timer_bool} (was {original_disable_startup_timer})")
                command_line_args_used = True
                
        if disable_refresh_timer is not None:
            disable_refresh_timer_bool = disable_refresh_timer.lower() == 'true'
            if disable_refresh_timer_bool != original_disable_refresh_timer:
                self.disable_refresh_timer = disable_refresh_timer_bool
                logger.info(f"Command line override: disable_refresh_timer = {disable_refresh_timer_bool} (was {original_disable_refresh_timer})")
                command_line_args_used = True
                
        if startup_delay_minutes is not None and startup_delay_minutes != 1:  # Only override if not default
            self.startup_delay_minutes = startup_delay_minutes
            logger.info(f"Command line override: startup_delay_minutes = {startup_delay_minutes} (was {original_startup_delay_minutes})")
            command_line_args_used = True
            
        if refresh_interval_hours is not None and refresh_interval_hours != 24:  # Only override if not default
            self.refresh_interval_hours = refresh_interval_hours
            logger.info(f"Command line override: refresh_interval_hours = {refresh_interval_hours} (was {original_refresh_interval_hours})")
            command_line_args_used = True
            
        if enable_manufacturer_timing is not None:
            enable_manufacturer_timing_bool = enable_manufacturer_timing.lower() == 'true'
            if enable_manufacturer_timing_bool != original_enable_manufacturer_timing:
                self.enable_manufacturer_timing = enable_manufacturer_timing_bool
                logger.info(f"Command line override: enable_manufacturer_timing = {enable_manufacturer_timing_bool} (was {original_enable_manufacturer_timing})")
                command_line_args_used = True
                
        if enable_sleep_mode is not None:
            enable_sleep_mode_bool = enable_sleep_mode.lower() == 'true'
            if enable_sleep_mode_bool != original_enable_sleep_mode:
                self.enable_sleep_mode = enable_sleep_mode_bool
                logger.info(f"Command line override: enable_sleep_mode = {enable_sleep_mode_bool} (was {original_enable_sleep_mode})")
                command_line_args_used = True
            
        # Save settings to file if command line arguments were used
        if command_line_args_used:
            logger.info("Command line arguments used - saving updated settings to file")
            self.save_settings_to_file()
        
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
        self.last_welcome_screen_time = 0  # Track when welcome screen was last shown
        
        # Startup timer control
        self.startup_timer_active = True
        self.manual_selection_during_startup = False
        
        # E-ink display timing requirements (manufacturer specifications)
        self.enable_manufacturer_timing = enable_manufacturer_timing
        self.enable_sleep_mode = enable_sleep_mode
        self.min_refresh_interval = 180 if enable_manufacturer_timing else 0  # Minimum 180 seconds between refreshes (if enabled)
        
        # Set initial timing values from constructor parameters
        # Only set these if they were explicitly provided (not None)
        if refresh_interval_hours is not None:
            self.refresh_interval_hours = refresh_interval_hours
        if startup_delay_minutes is not None:
            self.startup_delay_minutes = startup_delay_minutes
        if disable_startup_timer is not None:
            self.disable_startup_timer = disable_startup_timer
        if disable_refresh_timer is not None:
            self.disable_refresh_timer = disable_refresh_timer
        
        # Start background threads for timing features (unless disabled)
        self.startup_timer_thread = None
        self.refresh_timer_thread = None
        
        # Start startup timer if enabled
        logger.info(f"About to start startup timer - disable_startup_timer: {self.disable_startup_timer}")
        logger.info(f"About to start startup timer - disable_startup_timer type: {type(self.disable_startup_timer)}")
        logger.info(f"About to start startup timer - disable_startup_timer == True: {self.disable_startup_timer == True}")
        logger.info(f"About to start startup timer - disable_startup_timer == False: {self.disable_startup_timer == False}")
        logger.info(f"About to start startup timer - not self.disable_startup_timer: {not self.disable_startup_timer}")
        
        if not self.disable_startup_timer:
            self.startup_timer_thread = threading.Thread(target=self.startup_timer_worker, daemon=True)
            self.startup_timer_thread.start()
            logger.info(f"Startup timer enabled: {self.startup_delay_minutes}-minute delay")
        else:
            logger.info("Startup timer disabled - NOT starting startup timer thread")
            
        # Start refresh timer if enabled
        if not self.disable_refresh_timer:
            self.refresh_timer_thread = threading.Thread(target=self.refresh_timer_worker, daemon=True)
            self.refresh_timer_thread.start()
            logger.info(f"Refresh timer enabled: {self.refresh_interval_hours}-hour interval")
        else:
            logger.info("Refresh timer disabled")
        
        logger.info(f"Monitoring folder: {self.watched_folder.absolute()}")
        logger.info(f"E-ink display initialized - Size: {self.epd.width}x{self.epd.height} (native: {self.epd.native_orientation}, landscape: {self.epd.landscape_width}x{self.epd.landscape_height})")
        logger.info(f"Display orientation: {self.orientation}")
        logger.info(f"Auto-display uploads: {self.auto_display_uploads}")
        logger.info(f"Manufacturer timing requirements: {'ENABLED' if self.enable_manufacturer_timing else 'DISABLED'}")
        logger.info(f"Sleep mode: {'ENABLED' if self.enable_sleep_mode else 'DISABLED'}")
        logger.info(f"Display dimensions - Width: {self.epd.landscape_width}, Height: {self.epd.landscape_height}")
        logger.info(f"FINAL TIMING SETTINGS - Startup timer: {'DISABLED' if self.disable_startup_timer else 'ENABLED'}, Refresh timer: {'DISABLED' if self.disable_refresh_timer else 'ENABLED'}")
        
        # Save display info for web server access
        self._save_display_info()
    

    
    def startup_timer_worker(self):
        """Worker thread for configurable startup display delay"""
        try:
            logger.info("Startup timer worker started")
            logger.info(f"Startup timer worker - disable_startup_timer value: {self.disable_startup_timer}")
            logger.info(f"Startup timer worker - startup_timer_active value: {self.startup_timer_active}")
            
            # Check if startup timer is still enabled (in case it was disabled after thread started)
            if self.disable_startup_timer:
                logger.info("Startup timer was disabled after thread started - exiting worker")
                return
                
            # Ensure we have valid timing values
            if self.startup_delay_minutes is None:
                logger.warning("startup_delay_minutes is None, using default value of 1")
                self.startup_delay_minutes = 1
                
            # Show welcome screen first
            logger.info("Showing welcome screen during startup delay...")
            self.display_welcome_screen()
            
            # Wait for the configured startup delay
            startup_delay_seconds = self.startup_delay_minutes * 60
            logger.info(f"Waiting {startup_delay_seconds} seconds for startup delay...")
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
            else:
                logger.info(f"Startup timer conditions not met - exit_requested: {exit_requested}, startup_timer_active: {self.startup_timer_active}")
                
        except Exception as e:
            logger.error(f"Startup timer worker error: {e}")
    
    def refresh_timer_worker(self):
        """Worker thread for configurable refresh interval"""
        try:
            # Ensure we have valid timing values
            if self.refresh_interval_hours is None:
                logger.warning("refresh_interval_hours is None, using default value of 24")
                self.refresh_interval_hours = 24
                
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
            # Ensure we have valid timing values
            if self.refresh_interval_hours is None:
                logger.warning("refresh_interval_hours is None, using default value of 24")
                self.refresh_interval_hours = 24
                
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
            settings_file = Path(os.path.expanduser('~/.config/rpi-einky')) / 'settings.json'
            
            # Default settings that should always be present
            default_settings = {
                'auto_display_upload': True,
                'image_crop_mode': 'center_crop',
                'orientation': 'landscape',
                'startup_delay_minutes': 1,
                'refresh_interval_hours': 24,
                'enable_startup_timer': True,
                'enable_refresh_timer': True,
                'enable_manufacturer_timing': False,
                'enable_sleep_mode': True,
                'selected_image': None
            }
            
            # Try to load existing settings
            loaded_settings = {}
            settings_need_update = False
            
            if settings_file.exists():
                try:
                    import json
                    with open(settings_file, 'r') as f:
                        content = f.read().strip()
                        if content:  # File is not empty
                            loaded_settings = json.loads(content)
                            logger.info(f"Settings loaded from {settings_file}")
                        else:
                            # File is empty
                            logger.warning(f"Settings file {settings_file} is empty, using defaults")
                            settings_need_update = True
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    # File is corrupted or can't be read
                    logger.warning(f"Settings file {settings_file} is corrupted or unreadable: {e}, using defaults")
                    settings_need_update = True
            else:
                # File doesn't exist
                logger.info(f"Settings file not found at {settings_file}, using defaults")
                settings_need_update = True
            
            # Check if all required settings are present
            if not settings_need_update:
                for key, default_value in default_settings.items():
                    if key not in loaded_settings:
                        logger.warning(f"Missing setting '{key}' in settings file, using default: {default_value}")
                        settings_need_update = True
                        break
            
            # Merge loaded settings with defaults (loaded settings take precedence)
            final_settings = default_settings.copy()
            if loaded_settings:
                final_settings.update(loaded_settings)
            
            # Apply settings to instance variables
            self.auto_display_uploads = final_settings['auto_display_upload']
            self.image_crop_mode = final_settings['image_crop_mode']
            self.orientation = final_settings['orientation']
            self.startup_delay_minutes = final_settings['startup_delay_minutes']
            self.refresh_interval_hours = final_settings['refresh_interval_hours']
            self.disable_startup_timer = not final_settings['enable_startup_timer']
            self.disable_refresh_timer = not final_settings['enable_refresh_timer']
            self.enable_manufacturer_timing = final_settings['enable_manufacturer_timing']
            self.enable_sleep_mode = final_settings['enable_sleep_mode']
            self.selected_image = final_settings['selected_image']
            
            logger.info(f"Final settings - Auto-display: {self.auto_display_uploads}, Crop mode: {self.image_crop_mode}, Orientation: {self.orientation}, Selected image: {self.selected_image}")
            logger.info(f"Timing settings - Startup timer: {'DISABLED' if self.disable_startup_timer else 'ENABLED'}, Refresh timer: {'DISABLED' if self.disable_refresh_timer else 'ENABLED'}")
            logger.info(f"Timing values - Startup delay: {self.startup_delay_minutes}min, Refresh: {self.refresh_interval_hours}h")
            logger.info(f"LOAD_SETTINGS - disable_startup_timer value: {self.disable_startup_timer}")
            logger.info(f"LOAD_SETTINGS - disable_startup_timer type: {type(self.disable_startup_timer)}")
            
            # Update settings file if it was missing, empty, corrupted, or had missing fields
            if settings_need_update:
                try:
                    settings_file.parent.mkdir(parents=True, exist_ok=True)
                    import json
                    with open(settings_file, 'w') as f:
                        json.dump(final_settings, f, indent=2)
                    logger.info(f"Updated settings file with complete values: {list(final_settings.keys())}")
                except Exception as e:
                    logger.error(f"Error updating settings file: {e}")
                    
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
        
        # Update display info with new settings
        self.update_display_info()
    
    def restart_refresh_timer(self):
        """Restart the refresh timer with current settings"""
        try:
            logger.info(f"Restarting refresh timer - Current settings:")
            logger.info(f"  disable_refresh_timer: {self.disable_refresh_timer}")
            logger.info(f"  refresh_interval_hours: {self.refresh_interval_hours}")
            logger.info(f"  enable_manufacturer_timing: {self.enable_manufacturer_timing}")
            
            # Stop existing timer thread if running
            if hasattr(self, 'refresh_timer_thread') and self.refresh_timer_thread.is_alive():
                logger.info("Stopping existing refresh timer thread")
                # Note: We can't directly stop the thread, but we can set a flag
                # The thread will exit on its own when it checks the condition
            
            # Start new timer thread if enabled
            if not self.disable_refresh_timer:
                self.refresh_timer_thread = threading.Thread(target=self.refresh_timer_worker, daemon=True)
                self.refresh_timer_thread.start()
                logger.info(f"Refresh timer restarted: {self.refresh_interval_hours}-hour interval")
            else:
                logger.info("Refresh timer disabled - not starting new thread")
                
        except Exception as e:
            logger.error(f"Error restarting refresh timer: {e}")
    
    def save_settings_to_file(self):
        """Save current settings to the settings file"""
        try:
            # Use the same path as the upload server
            settings_file = Path(os.path.expanduser('~/.config/rpi-einky')) / 'settings.json'
            logger.info(f"DEBUG: Saving settings to: {settings_file.absolute()}")
            
            # Ensure the directory exists
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing settings if file exists
            settings = {}
            if settings_file.exists():
                import json
                try:
                    with open(settings_file, 'r') as f:
                        settings = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    # If file is corrupted or empty, start with empty dict
                    settings = {}
            
            # Update settings with current values
            settings['auto_display_upload'] = self.auto_display_uploads
            settings['image_crop_mode'] = self.image_crop_mode
            settings['orientation'] = self.orientation
            settings['startup_delay_minutes'] = self.startup_delay_minutes
            settings['refresh_interval_hours'] = self.refresh_interval_hours
            settings['enable_startup_timer'] = not self.disable_startup_timer
            settings['enable_refresh_timer'] = not self.disable_refresh_timer
            settings['enable_manufacturer_timing'] = self.enable_manufacturer_timing
            settings['enable_sleep_mode'] = self.enable_sleep_mode
            if hasattr(self, 'selected_image'):
                settings['selected_image'] = self.selected_image
            
            # Save settings back to file
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            logger.info(f"Settings saved to file: {list(settings.keys())}")
            
        except Exception as e:
            logger.error(f"Error saving settings to file: {e}")
    
    def save_selected_image_setting(self, filename):
        """Save the selected image setting to the settings file"""
        try:
            # Use the same path as the upload server
            settings_file = Path(os.path.expanduser('~/.config/rpi-einky')) / 'settings.json'
            logger.info(f"DEBUG: Saving selected image setting to: {settings_file.absolute()}")
            
            # Ensure the directory exists
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing settings if file exists
            settings = {}
            if settings_file.exists():
                import json
                try:
                    with open(settings_file, 'r') as f:
                        settings = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    # If file is corrupted or empty, start with empty dict
                    settings = {}
            
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
            logger.info(f"Applying orientation: {orientation} to image size {image.size}")
            
            if orientation == 'landscape':
                # No rotation needed
                logger.info(f"No rotation needed for landscape orientation")
                return image
            elif orientation == 'landscape_flipped':
                # Rotate 180 degrees
                logger.info(f"Rotating image 180 degrees for landscape_flipped")
                return image.rotate(180)
            elif orientation == 'portrait':
                # Rotate 90 degrees clockwise
                logger.info(f"Rotating image 90 degrees clockwise for portrait")
                rotated = image.rotate(90, expand=True)
                logger.info(f"Image rotated from {image.size} to {rotated.size}")
                return rotated
            elif orientation == 'portrait_flipped':
                # Rotate 270 degrees clockwise (or 90 degrees counter-clockwise)
                logger.info(f"Rotating image 270 degrees clockwise for portrait_flipped")
                rotated = image.rotate(270, expand=True)
                logger.info(f"Image rotated from {image.size} to {rotated.size}")
                return rotated
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
            logger.info(f"DEBUG: Latest file result: {latest_file}")
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
        """Display an image buffer on the e-ink display"""
        try:
            # Check manufacturer timing requirements if enabled
            if self.enable_manufacturer_timing:
                current_time = time.time()
                if hasattr(self, 'last_refresh_time') and (current_time - self.last_refresh_time) < self.min_refresh_interval:
                    remaining_time = self.min_refresh_interval - (current_time - self.last_refresh_time)
                    logger.warning(f"Display refresh too soon. Must wait {remaining_time:.1f} more seconds (manufacturer requirement: 180s minimum)")
                    return False
            
            # Wake up display if sleep mode is enabled
            if self.enable_sleep_mode:
                logger.info("Starting display operation (sleep mode enabled)...")
                try:
                    self.epd.init()
                    time.sleep(0.5)  # Brief delay after wake
                except Exception as e:
                    logger.warning(f"Display init failed, attempting reinitialization: {e}")
                    self.reinitialize_display()
            else:
                logger.info("Starting display operation (sleep mode disabled)...")
            
            # Display the image (orientation already applied)
            logger.info("Calling epd.display()...")
            self.epd.display(self.epd.getbuffer(image))
            
            # Put display back to sleep mode if sleep mode is enabled
            if self.enable_sleep_mode:
                logger.info("Display completed - putting display to sleep...")
                try:
                    self.epd.sleep()
                except Exception as e:
                    logger.warning(f"Display sleep failed: {e}")
            else:
                logger.info("Display completed (sleep mode disabled)")
            
            # Update last refresh time if manufacturer timing is enabled
            if self.enable_manufacturer_timing:
                self.last_refresh_time = time.time()
            
            logger.info("Display operation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Display buffer error: {e}")
            if "Bad file descriptor" in str(e) or "I/O error" in str(e):
                logger.info("File descriptor error detected - attempting to reinitialize display...")
                try:
                    self.reinitialize_display()
                    # Try again after reinitializing
                    # Don't apply orientation again - image is already oriented
                    self.epd.display(self.epd.getbuffer(image))
                    if self.enable_sleep_mode:
                        try:
                            self.epd.sleep()  # Put to sleep after successful retry
                        except Exception as sleep_error:
                            logger.warning(f"Sleep after retry failed: {sleep_error}")
                    logger.info("Display operation completed successfully after reinitialization")
                    return True
                except Exception as retry_error:
                    logger.error(f"Reinitialization and retry failed: {retry_error}")
                    return False
            return False
    
    def reinitialize_display(self):
        """Reinitialize the e-ink display"""
        try:
            logger.info("Reinitializing e-ink display...")
            
            # Try to sleep first (if it fails, that's okay)
            try:
                self.epd.sleep()
            except Exception as e:
                logger.warning(f"Sleep during reinitialization failed: {e}")
            
            # Wait a bit longer to ensure clean state
            time.sleep(2)
            
            # Reinitialize the display
            try:
                self.epd.init()
                logger.info("Display reinitialized successfully")
            except Exception as e:
                logger.error(f"Display init failed during reinitialization: {e}")
                # Try one more time after a longer delay
                time.sleep(3)
                self.epd.init()
                logger.info("Display reinitialized successfully on second attempt")
                
        except Exception as e:
            logger.error(f"Display reinitialization failed: {e}")
            raise
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        logger.info(f"New file detected: {file_path.name}")
        
        # Check if this is a command file from the commands directory
        if 'commands' in str(file_path) and file_path.suffix == '.json':
            self._process_command_file(file_path)
            return
        
        # Skip hidden files and thumbnails
        if file_path.name.startswith('.') or '_thumb.' in file_path.name:
            return
        
        self._process_regular_file(file_path)
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Check if this is a command file from the commands directory
        if 'commands' in str(file_path) and file_path.suffix == '.json':
            logger.info(f"Command file modified: {file_path.name}")
            self._process_command_file(file_path)
            return
    
    def _process_command_file(self, file_path):
        """Process command file from commands directory"""
        try:
            # Add a small delay to ensure file is fully written
            time.sleep(0.1)
            
            # Check if file exists and is readable
            if not file_path.exists():
                logger.warning(f"Command file does not exist: {file_path}")
                return
                
            # Read and execute the command
            logger.info(f"Reading command file: {file_path}")
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
                
                # Always reload settings first
                self.reload_settings()
                
                # Restart refresh timer with new settings
                self.restart_refresh_timer()
                
                # During startup, still refresh display if this is an orientation change
                # (orientation changes should always trigger immediate refresh)
                if self.startup_timer_active:
                    logger.info("Settings change detected during startup - reloading settings and refreshing display")
                
                # Get and display the priority file
                priority_file = self.get_priority_display_file()
                if priority_file:
                    logger.info(f"Refreshing display with priority file: {priority_file.name}")
                    self.display_file(priority_file)
                    self.current_displayed_file = priority_file
                else:
                    logger.info("No priority file found for refresh - showing welcome screen")
                    self.display_welcome_screen()
            elif action == 'clear_display':
                # Clear the display
                logger.info("Executing clear display command")
                try:
                    if self.enable_sleep_mode:
                        self.epd.init()
                    self.epd.clear()
                    if self.enable_sleep_mode:
                        self.epd.sleep()
                    logger.info("Display cleared successfully")
                    self.current_displayed_file = None
                except Exception as e:
                    logger.error(f"Error clearing display: {e}")
            elif action == 'get_display_info':
                # Send display info response
                logger.info("Executing get display info command")
                self._send_display_info_response()
            elif action == 'update_display_info':
                # Update display info with current settings
                logger.info("Executing update display info command")
                self.update_display_info()
            else:
                logger.warning(f"Unknown command action: {action}")
            
            # Clean up command file
            file_path.unlink()
            
        except Exception as e:
            logger.error(f"Error processing command file: {e}")
            # Clean up command file even on error
            try:
                file_path.unlink()
            except:
                pass
    
    def _process_regular_file(self, file_path):
        """Process regular file uploads"""
        
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
            logger.info(f"Displaying image: {file_path.name}, original size: {original_size}")

                
            # Convert to RGB if necessary, using white background for transparency
            if image.mode != 'RGB':
                if image.mode == 'RGBA':
                    # Create white background for transparent pixels
                    white_bg = Image.new('RGB', image.size, (255, 255, 255))
                    white_bg.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                    image = white_bg
                else:
                    image = image.convert('RGB')
            

            # Apply orientation first, then resize to fit
            image = self.apply_orientation(image)
            logger.info(f"After orientation: {image.size}")

            # Resize and crop to fit display
            processed_image = self.resize_image_to_fit(image)
            logger.info(f"After resize: {processed_image.size}")
            
            # Get the correct display dimensions based on orientation

            display_width = self.epd.landscape_width
            display_height = self.epd.landscape_height
            
            # # Create display image and center the processed image
            # display_image = Image.new('RGB', (display_width, display_height), self.epd.WHITE)
            # x_offset = (display_width - processed_image.width) // 2
            # y_offset = (display_height - processed_image.height) // 2
            # display_image.paste(processed_image, (x_offset, y_offset))
            # logger.info(f"Created display image: {display_image.size}, offset: ({x_offset}, {y_offset})")
            
            display_image = processed_image
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
            display_image = Image.new('RGB', (self.epd.landscape_width, self.epd.landscape_height), self.epd.WHITE)
            draw = ImageDraw.Draw(display_image)
            
            # Title
            draw.rectangle([(0, 0), (self.epd.landscape_width, 25)], fill=self.epd.BLACK)
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
                if y_pos > self.epd.landscape_height - 20:
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
                                if y_pos > self.epd.landscape_height - 20:
                                    break
                            current_line = word + " "
                    
                    if current_line and y_pos <= self.epd.landscape_height - 20:
                        draw.text((5, y_pos), current_line.strip(), 
                                font=self.font_small, fill=self.epd.BLACK)
                        y_pos += line_height
                else:
                    draw.text((5, y_pos), line, font=self.font_small, fill=self.epd.BLACK)
                    y_pos += line_height
            
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
                    
                    display_image = Image.new('RGB', (self.epd.landscape_width, self.epd.landscape_height), self.epd.WHITE)
                    x_offset = (self.epd.landscape_width - pdf_image.width) // 2
                    y_offset = (self.epd.landscape_height - pdf_image.height) // 2
                    display_image.paste(pdf_image, (x_offset, y_offset))
                    
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
            display_image = Image.new('RGB', (self.epd.landscape_width, self.epd.landscape_height), self.epd.WHITE)
            draw = ImageDraw.Draw(display_image)
            
            # Title
            draw.rectangle([(0, 0), (self.epd.landscape_width, 30)], fill=self.epd.BLACK)
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
                if y_pos > self.epd.landscape_height - 30:
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
            display_image = Image.new('RGB', (self.epd.landscape_width, self.epd.landscape_height), self.epd.WHITE)
            draw = ImageDraw.Draw(display_image)
            
            # Error title
            draw.rectangle([(0, 0), (self.epd.landscape_width, 30)], fill=self.epd.RED)
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
                        if y_pos > self.epd.landscape_height - 30:
                            break
                    current_line = word + " "
            
            if current_line and y_pos <= self.epd.landscape_height - 30:
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
            
            display_image = Image.new('RGB', (self.epd.landscape_width, self.epd.landscape_height), self.epd.WHITE)
            draw = ImageDraw.Draw(display_image)
            
            # Title
            draw.rectangle([(0, 0), (self.epd.landscape_width, 35)], fill=self.epd.BLACK)
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
            # Check if we've shown the welcome screen recently (cooldown of 30 seconds)
            current_time = time.time()
            if current_time - self.last_welcome_screen_time < 30:
                logger.info("Welcome screen shown recently, skipping to avoid file descriptor issues")
                return
            
            self.last_welcome_screen_time = current_time
            
            ip_address = get_ip_address()
            hostname = socket.gethostname()
            
            display_image = Image.new('RGB', (self.epd.landscape_width, self.epd.landscape_height), self.epd.WHITE)
            draw = ImageDraw.Draw(display_image)
            
            # Title
            draw.rectangle([(0, 0), (self.epd.landscape_width, 35)], fill=self.epd.BLACK)
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
        # Get the correct display dimensions based on orientation
        # orientation = getattr(self, 'orientation', 'landscape')
        # if orientation in ['portrait', 'portrait_flipped']:
        #     display_width = self.epd.landscape_height  # Swap dimensions for portrait
        #     display_height = self.epd.landscape_width
        # else:
        display_width = self.epd.landscape_width
        display_height = self.epd.landscape_height
        
        # Use the loaded crop mode setting
        crop_mode = getattr(self, 'image_crop_mode', 'center_crop')
        logger.info(f"Resizing image {image.size} to display {display_width}x{display_height} with crop mode: {crop_mode}")
        
        if crop_mode == 'center_crop':
            # Center-crop mode: scale to cover display, then crop (works for both smaller and larger images)
            scale_x = display_width / image.width
            scale_y = display_height / image.height
            scale = max(scale_x, scale_y)  # Use max to ensure image covers display
            
            # Resize image to cover display
            new_width = int(image.width * scale)
            new_height = int(image.height * scale)
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Center-crop to exact display size
            left = (new_width - display_width) // 2
            top = (new_height - display_height) // 2
            right = left + display_width
            bottom = top + display_height
            
            cropped_image = resized_image.crop((left, top, right, bottom))
            
            logger.info(f"Center-cropped image from {image.size} to {cropped_image.size} (scale: {scale:.2f})")
            return cropped_image
            
        else:  # fit_with_letterbox
            # Letterbox mode: scale to fit within display, add letterboxing
            scale_x = display_width / image.width
            scale_y = display_height / image.height
            scale = min(scale_x, scale_y)  # Use min to fit within display
            
            new_width = int(image.width * scale)
            new_height = int(image.height * scale)
            
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            logger.info(f"Letterboxed image from {image.size} to {resized_image.size} (scale: {scale:.2f})")
            return resized_image
    
    def update_display_info(self):
        """Update display info file with current settings"""
        try:
            self._save_display_info()
            logger.info("Display info updated with current settings")
        except Exception as e:
            logger.error(f"Error updating display info: {e}")
    
    def _send_display_info_response(self):
        """Send display info response to the web server"""
        try:
            # Get actual display information from the unified EPD library
            display_info = {
                'display_type': getattr(self.epd, 'display_type', 'epd2in15g'),
                'resolution': {
                    'width': getattr(self.epd, 'landscape_width', 250),
                    'height': getattr(self.epd, 'landscape_height', 122)
                },
                'native_resolution': {
                    'width': getattr(self.epd, 'width', 250),
                    'height': getattr(self.epd, 'height', 122)
                },
                'orientation': getattr(self, 'orientation', 'landscape'),
                'native_orientation': getattr(self.epd, 'native_orientation', 'landscape'),
                'source': 'display_handler'
            }
            
            # Write response file for web server to read
            response_file = Path(os.path.expanduser('~/.config/rpi-einky/commands/display_info_response.json'))
            with open(response_file, 'w') as f:
                json.dump(display_info, f, indent=2)
            
            logger.info(f"Sent display info response: {display_info}")
            
        except Exception as e:
            logger.error(f"Error sending display info response: {e}")
    
    def _save_display_info(self):
        """Save display info to persistent file for web server access"""
        try:
            # Get actual display information from the unified EPD library
            display_info = {
                'display_type': getattr(self.epd, 'display_type', 'epd2in15g'),
                'resolution': {
                    'width': getattr(self.epd, 'landscape_width', 250),
                    'height': getattr(self.epd, 'landscape_height', 122)
                },
                'native_resolution': {
                    'width': getattr(self.epd, 'width', 250),
                    'height': getattr(self.epd, 'height', 122)
                },
                'orientation': getattr(self, 'orientation', 'landscape'),
                'native_orientation': getattr(self.epd, 'native_orientation', 'landscape'),
                'source': 'display_handler',
                'last_updated': time.time()
            }
            
            # Save to persistent file
            display_info_file = Path(os.path.expanduser('~/.config/rpi-einky/display_info.json'))
            with open(display_info_file, 'w') as f:
                json.dump(display_info, f, indent=2)
            
            logger.info(f"Saved display info: {display_info}")
            
        except Exception as e:
            logger.error(f"Error saving display info: {e}")
    
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
    parser.add_argument('--test-orientation', choices=['landscape', 'landscape_flipped', 'portrait', 'portrait_flipped'],
                        help='Test orientation by displaying a test image immediately and exiting')
    parser.add_argument('--orientation', choices=['landscape', 'landscape_flipped', 'portrait', 'portrait_flipped'],
                        help='Display orientation (default: from settings file)')
    parser.add_argument('--disable-startup-timer', type=str, choices=['true', 'false'], default=None,
                       help='Set disable_startup_timer (true/false)')
    parser.add_argument('--disable-refresh-timer', type=str, choices=['true', 'false'], default=None,
                       help='Set disable_refresh_timer (true/false)')
    parser.add_argument('--refresh-interval', type=int, default=24,
                       help='Refresh interval in hours (default: 24)')
    parser.add_argument('--startup-delay', type=int, default=1,
                       help='Startup delay in minutes before displaying latest file (default: 1)')
    parser.add_argument('--enable-manufacturer-timing', type=str, choices=['true', 'false'], default=None,
                       help='Set enable_manufacturer_timing (true/false)')
    parser.add_argument('--enable-sleep-mode', type=str, choices=['true', 'false'], default=None,
                       help='Set enable_sleep_mode (true/false)')
    
    args = parser.parse_args()
    
    # Handle IP display option (show IP and exit)
    if args.show_ip:
        try:
            # Get display type for IP display
            display_type = args.display_type or EPDConfig.load_display_config()
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
    
    # Test orientation if requested
    if args.test_orientation:
        logger.info(f"Testing orientation: {args.test_orientation}")
        try:
            # Create temporary handler just to test orientation
            temp_handler = EinkDisplayHandler(clear_on_start=False, clear_on_exit=False, display_type=args.display_type)
            temp_handler.orientation = args.test_orientation
            
            # Create a test image with orientation indicators
            test_image = Image.new('RGB', (temp_handler.epd.landscape_width, temp_handler.epd.landscape_height), (255, 255, 255))
            draw = ImageDraw.Draw(test_image)
            
            # Draw orientation test pattern
            draw.rectangle([0, 0, test_image.width-1, test_image.height-1], outline=(0, 0, 0), width=5)
            draw.text((10, 10), f"Orientation: {args.test_orientation}", font=temp_handler.font_large, fill=(0, 0, 0))
            draw.text((10, 40), f"Display: {test_image.width}x{test_image.height}", font=temp_handler.font_medium, fill=(0, 0, 0))
            
            # Draw corner markers
            draw.rectangle([10, 10, 50, 50], fill=(255, 0, 0))  # Top-left: Red
            draw.rectangle([test_image.width-50, 10, test_image.width-10, 50], fill=(0, 255, 0))  # Top-right: Green
            draw.rectangle([10, test_image.height-50, 50, test_image.height-10], fill=(0, 0, 255))  # Bottom-left: Blue
            draw.rectangle([test_image.width-50, test_image.height-50, test_image.width-10, test_image.height-10], fill=(255, 255, 0))  # Bottom-right: Yellow
            
            # Apply orientation
            oriented_image = temp_handler.apply_orientation(test_image)
            
            # Display the test image
            temp_handler.display_buffer(oriented_image)
            
            # Clean up
            temp_handler.epd.sleep()
            logger.info(f"Orientation test completed for: {args.test_orientation}. Exiting.")
            return
        except Exception as e:
            logger.error(f"Error testing orientation: {e}")
            return
    
    # Configuration
    WATCHED_FOLDER = os.path.expanduser(args.folder)
    ORIENTATION = args.orientation if args.orientation is not None else 'landscape'  # Fallback for None
    CLEAR_ON_START = args.clear_start
    CLEAR_ON_EXIT = not args.no_clear_exit
    DISABLE_STARTUP_TIMER = args.disable_startup_timer
    DISABLE_REFRESH_TIMER = args.disable_refresh_timer
    REFRESH_INTERVAL_HOURS = args.refresh_interval
    STARTUP_DELAY_MINUTES = args.startup_delay
    ENABLE_MANUFACTURER_TIMING = args.enable_manufacturer_timing
    ENABLE_SLEEP_MODE = args.enable_sleep_mode
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
    
    # Only override orientation if explicitly provided via command line
    if args.orientation is not None:  # Only override if explicitly provided
        handler.orientation = ORIENTATION
        logger.info(f"Orientation overridden by command line argument: {ORIENTATION}")
    else:
        logger.info(f"Using orientation from settings file: {handler.orientation}")
    
    # Set up file system observer for both watched folder and commands directory
    observer = Observer()
    observer.schedule(handler, handler.watched_folder, recursive=False)
    
    # Also watch the commands directory for command files
    commands_dir = Path(os.path.expanduser('~/.config/rpi-einky/commands'))
    commands_dir.mkdir(parents=True, exist_ok=True)
    observer.schedule(handler, str(commands_dir), recursive=False)
    
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
            logger.info(f"MAIN FUNCTION - DISABLE_STARTUP_TIMER value: {DISABLE_STARTUP_TIMER}")
            logger.info(f"MAIN FUNCTION - handler.disable_startup_timer value: {handler.disable_startup_timer}")
            if not handler.disable_startup_timer:
                # Startup timer is enabled - show welcome screen, timer will handle priority file later
                logger.info("Startup timer enabled - showing welcome screen, priority file will be displayed after delay")
                handler.display_welcome_screen()
            else:
                # Startup timer is disabled - display priority file immediately
                logger.info("Startup timer disabled - attempting to display priority file immediately")
                priority_file = handler.get_priority_display_file()
                logger.info(f"Priority file result: {priority_file}")
                if priority_file:
                    logger.info(f"Displaying priority file: {priority_file}")
                    success = handler.display_file(priority_file)
                    logger.info(f"Priority file display result: {success}")
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
