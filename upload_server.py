#!/usr/bin/env python3
"""
Web management server for e-ink display system.
Provides both API endpoints and web interface for file management.
"""
import os
import time
import json
import base64
import hashlib
import random
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory, url_for, session, redirect, flash
from werkzeug.utils import secure_filename
from PIL import Image
import logging
from functools import wraps

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system environment variables

# Configure logging
import os
# Use the user's home directory for log files
log_dir = os.path.expanduser('~/logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'eink_upload.log')),  # Log to file
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Security configuration
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-change-this-in-production')
# Only require secure cookies in production (HTTPS)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# Admin password configuration
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH',
    hashlib.sha256('admin123'.encode()).hexdigest())  # Default password: admin123

# API key for TouchDesigner (generate a secure random key)
API_KEY = os.environ.get('API_KEY', 'td-api-key-change-this-in-production')



# Configuration
UPLOAD_FOLDER = os.path.expanduser('~/watched_files')
THUMBNAILS_FOLDER = os.path.join(UPLOAD_FOLDER, '.thumbnails')
APP_CONFIG_DIR = os.path.expanduser('~/.config/rpi-einky')
SETTINGS_FILE = os.path.join(APP_CONFIG_DIR, 'settings.json')
COMMANDS_DIR = os.path.join(APP_CONFIG_DIR, 'commands')

ALLOWED_EXTENSIONS = {
    'txt', 'md', 'py', 'js', 'html', 'css',  # Text files
    'jpg', 'jpeg', 'png', 'bmp', 'gif',      # Images
    'pdf',                                    # PDFs
    'json', 'xml', 'csv'                     # Data files
}

# Default settings
DEFAULT_SETTINGS = {
    'image_crop_mode': 'center_crop',  # 'center_crop' or 'fit_with_letterbox'
    'auto_display_upload': True,       # Automatically display uploaded files
    'thumbnail_quality': 85,           # JPEG quality for thumbnails
    'max_file_size_mb': 16,           # Maximum file size in MB
    'startup_delay_minutes': 1,        # Startup delay before displaying latest file
    'refresh_interval_hours': 24,      # Refresh interval to prevent ghosting
    'enable_startup_timer': True,      # Enable automatic startup display timer
    'enable_refresh_timer': True,      # Enable automatic refresh timer
    'enable_manufacturer_timing': False,  # Enable manufacturer timing requirements (180s minimum)
    'enable_sleep_mode': True,  # Enable sleep mode between operations (power efficiency)
    'orientation': 'landscape',  # Display orientation: 'landscape', 'portrait', 'landscape_flipped', 'portrait_flipped'
    # Playlist settings
    'playlist_enabled': True,          # Enable playlist mode
    'playlist_interval_minutes': 5,    # Minutes between playlist image changes
    'playlist_current_name': 'default', # Name of currently active playlist
    'playlists': {                     # Dictionary of named playlists
        'default': {
            'name': 'Default Playlist',
            'files': [],
            'current_index': 0,
            'last_change': 0,
            'randomize': False
        }
    },
    'display_mode': 'playlist',        # 'manual', 'playlist', or 'live' (TouchDesigner upload)
    'live_mode_timeout_minutes': 30,   # Minutes to wait before returning to playlist from live mode (0 = no timeout)
    'live_mode_start_time': 0          # Timestamp when live mode started
}

# Image extensions for thumbnail generation
IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp', 'gif'}

# Authentication functions
def login_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key authentication (TouchDesigner)
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')
        if api_key:
            # Remove "Bearer " prefix if present
            if api_key.startswith('Bearer '):
                api_key = api_key[7:]
            if api_key == API_KEY:
                return f(*args, **kwargs)
            else:
                return jsonify({'error': 'Invalid API key'}), 401

        # Check for session authentication (web interface)
        if not session.get('logged_in'):
            if request.is_json:
                return jsonify({'error': 'Authentication required. Use X-API-Key header or login via web interface.'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def check_password(password):
    """Check if provided password matches admin password"""
    return hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_upload_folder():
    """Create upload folder and thumbnails folder if they don't exist"""
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(THUMBNAILS_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(APP_CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    Path(COMMANDS_DIR).mkdir(parents=True, exist_ok=True)

def load_settings():
    """Load settings from file or return defaults"""
    try:
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    content = f.read().strip()
                    if content:  # File is not empty
                        saved_settings = json.loads(content)
                        logger.info(f"Settings loaded from {SETTINGS_FILE}")
                    else:
                        # File is empty
                        logger.warning(f"Settings file {SETTINGS_FILE} is empty, using defaults")
                        saved_settings = {}
            except (json.JSONDecodeError, FileNotFoundError) as e:
                # File is corrupted or can't be read
                logger.warning(f"Settings file {SETTINGS_FILE} is corrupted or unreadable: {e}, using defaults")
                saved_settings = {}
        else:
            logger.info(f"Settings file not found at {SETTINGS_FILE}, using defaults")
            saved_settings = {}

        # Check if all required settings are present
        settings_need_update = False
        for key, default_value in DEFAULT_SETTINGS.items():
            if key not in saved_settings:
                logger.warning(f"Missing setting '{key}' in settings file, using default: {default_value}")
                settings_need_update = True
                break

        # Merge with defaults to ensure all settings exist
        settings = DEFAULT_SETTINGS.copy()
        settings.update(saved_settings)

        # Update settings file if it was missing, empty, corrupted, or had missing fields
        if settings_need_update:
            try:
                os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
                with open(SETTINGS_FILE, 'w') as f:
                    json.dump(settings, f, indent=2)
                logger.info(f"Updated settings file with complete values: {list(settings.keys())}")
            except Exception as e:
                logger.error(f"Error updating settings file: {e}")

        return settings
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to file atomically with rolling backups.

    Strategy:
    - Write to SETTINGS_FILE.tmp then os.replace() -> atomic on POSIX/Win10+
    - Keep up to 5 timestamped backups in the same directory
    """
    try:
        settings_dir = os.path.dirname(SETTINGS_FILE)
        os.makedirs(settings_dir, exist_ok=True)

        # Create a timestamped backup if the file exists and is non-empty
        if os.path.exists(SETTINGS_FILE):
            try:
                if os.path.getsize(SETTINGS_FILE) > 0:
                    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
                    backup_file = os.path.join(settings_dir, f"settings.{ts}.bak.json")
                    try:
                        # Best-effort copy existing file
                        with open(SETTINGS_FILE, 'r') as src, open(backup_file, 'w') as dst:
                            dst.write(src.read())
                        logger.info(f"Created settings backup: {backup_file}")
                    except Exception as e:
                        logger.warning(f"Failed to create settings backup: {e}")

                    # Prune old backups, keep last 5
                    try:
                        backups = sorted([
                            p for p in Path(settings_dir).glob('settings.*.bak.json')
                        ], key=lambda p: p.stat().st_mtime, reverse=True)
                        for old in backups[5:]:
                            old.unlink(missing_ok=True)
                    except Exception as e:
                        logger.warning(f"Failed to prune old backups: {e}")
            except Exception:
                pass

        # Atomic write via temp + replace
        tmp_path = SETTINGS_FILE + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(settings, f, indent=2)
            f.flush()
            os.fsync(f.fileno()) if hasattr(os, 'fsync') else None

        os.replace(tmp_path, SETTINGS_FILE)
        logger.info("Settings saved successfully (atomic)")
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass
        return False

def get_setting(key, default=None):
    """Get a specific setting value"""
    settings = load_settings()
    return settings.get(key, default)

def get_file_type(filename):
    """Determine file type category"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    elif ext in {'txt', 'md', 'py', 'js', 'html', 'css', 'json', 'xml', 'csv'}:
        return 'text'
    elif ext == 'pdf':
        return 'pdf'
    else:
        return 'other'

def generate_thumbnail(filepath, filename):
    """Generate thumbnail for image files"""
    try:
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if file_ext not in IMAGE_EXTENSIONS:
            return None

        # Create thumbnail filename
        name_without_ext = filename.rsplit('.', 1)[0]
        thumb_filename = f"{name_without_ext}_thumb.jpg"
        thumb_path = os.path.join(THUMBNAILS_FOLDER, thumb_filename)

        # Skip if thumbnail already exists and is newer than original
        if os.path.exists(thumb_path):
            if os.path.getmtime(thumb_path) >= os.path.getmtime(filepath):
                return thumb_filename

        # Generate thumbnail
        with Image.open(filepath) as img:
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Create thumbnail (max 200x200)
            img.thumbnail((200, 200), Image.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=85)

        logger.info(f"Generated thumbnail: {thumb_filename}")
        return thumb_filename

    except Exception as e:
        logger.error(f"Thumbnail generation failed for {filename}: {e}")
        return None

def trigger_settings_reload_and_redisplay():
    """Trigger a settings reload and re-display of current content when settings change"""
    try:
        logger.info("Starting settings reload and redisplay process")

        # Brief delay to ensure settings file is written
        import time
        time.sleep(0.5)

        # Send a refresh command to the main handler
        command_file = Path(COMMANDS_DIR) / 'refresh_display.json'
        command_data = {
            'action': 'refresh_display',
            'timestamp': time.time()
        }

        with open(command_file, 'w') as f:
            json.dump(command_data, f)

        logger.info(f"Sent refresh display command to {command_file}")
        return True

    except Exception as e:
        logger.error(f"Error in trigger_settings_reload_and_redisplay: {e}")
        return False

def display_file_on_eink(filename, mode='manual'):
    """Display a specific file on the e-ink display"""
    try:
        # Save the selected image setting and display mode
        settings = load_settings()
        old_selected = settings.get('selected_image')
        settings['selected_image'] = filename
        settings['display_mode'] = mode

        # Set live mode start time if entering live mode
        if mode == 'live':
            settings['live_mode_start_time'] = time.time()

        save_success = save_settings(settings)
        logger.info(f"display_file_on_eink: Updated selected_image from '{old_selected}' to '{filename}' (mode: {mode}): save_success={save_success}")

        # Verify the save worked
        if save_success:
            verification_settings = load_settings()
            verification_selected = verification_settings.get('selected_image')
            if verification_selected != filename:
                logger.error(f"display_file_on_eink VERIFICATION FAILED: Expected '{filename}', got '{verification_selected}'")
            else:
                logger.info(f"display_file_on_eink: Verified selected_image correctly saved as '{filename}'")

        # Small delay to ensure settings file is written
        time.sleep(0.1)

        # Write a display command for the main handler to execute
        command_file = Path(COMMANDS_DIR) / 'display_file.json'
        command_data = {
            'action': 'display_file',
            'filename': filename,
            'mode': mode,
            'timestamp': time.time()
        }

        with open(command_file, 'w') as f:
            json.dump(command_data, f)

        logger.info(f"Sent display command for: {filename} (mode: {mode})")
        return True

    except Exception as e:
        logger.error(f"Failed to send display command for {filename}: {e}")
        return False

def get_playlist_files():
    """Get list of image files suitable for playlist"""
    try:
        folder = Path(UPLOAD_FOLDER)
        files = [f for f in folder.glob('*') if f.is_file() and not f.name.startswith('.')]

        # Filter to only image files
        image_files = []
        for file in files:
            if file.suffix.lower().lstrip('.') in IMAGE_EXTENSIONS:
                image_files.append({
                    'filename': file.name,
                    'size': file.stat().st_size,
                    'modified': file.stat().st_mtime
                })

        # Sort by modification time (latest first)
        image_files.sort(key=lambda f: f['modified'], reverse=True)
        return image_files

    except Exception as e:
        logger.error(f"Error getting playlist files: {e}")
        return []

def advance_playlist():
    """Advance to next item in playlist and display it"""
    try:
        settings = load_settings()

        if not settings.get('playlist_enabled', False):
            return False

        # Get current playlist
        current_playlist_name = settings.get('playlist_current_name', 'default')
        playlists = settings.get('playlists', {})

        if current_playlist_name not in playlists:
            logger.warning(f"Current playlist '{current_playlist_name}' not found")
            return False

        current_playlist = playlists[current_playlist_name]
        playlist_files = current_playlist.get('files', [])

        if not playlist_files:
            logger.warning(f"Playlist '{current_playlist_name}' is enabled but has no files")
            return False

        # Verify files still exist
        existing_files = []
        folder = Path(UPLOAD_FOLDER)
        for filename in playlist_files:
            if (folder / filename).exists():
                existing_files.append(filename)

        if not existing_files:
            logger.warning(f"No files in playlist '{current_playlist_name}' exist anymore")
            return False

        # Update playlist if files were removed
        if len(existing_files) != len(playlist_files):
            current_playlist['files'] = existing_files
            settings['playlists'][current_playlist_name] = current_playlist
            logger.info(f"Updated playlist '{current_playlist_name}', removed {len(playlist_files) - len(existing_files)} missing files")

        # Get current index and advance
        current_index = current_playlist.get('current_index', 0)
        randomize = current_playlist.get('randomize', False)

        if randomize:
            # Random selection - pick any file except the current one (if there are multiple files)
            if len(existing_files) > 1:
                available_indices = [i for i in range(len(existing_files)) if i != current_index]
                current_index = random.choice(available_indices)
            else:
                current_index = 0
        else:
            # Sequential selection - advance to next file
            current_index = (current_index + 1) % len(existing_files)

        filename = existing_files[current_index]

        # Display the file
        success = display_file_on_eink(filename, mode='playlist')

        if success:
            # Reload settings to get the updated display_mode from display_file_on_eink
            settings = load_settings()
            playlists = settings.get('playlists', {})
            current_playlist = playlists.get(current_playlist_name, {})

            # Update playlist with current index and timestamp
            # current_index should always point to the currently displayed file
            current_playlist['current_index'] = current_index
            current_playlist['last_change'] = time.time()
            settings['playlists'][current_playlist_name] = current_playlist
            playlist_save_success = save_settings(settings)

            mode_text = "random" if randomize else "sequential"
            logger.info(f"Playlist '{current_playlist_name}' advanced to: {filename} (index {current_index}, {mode_text} mode)")
            logger.info(f"Playlist settings save result: {playlist_save_success}")

            # Verify that selected_image was updated correctly
            verification_settings = load_settings()
            verification_selected = verification_settings.get('selected_image')
            if verification_selected != filename:
                logger.error(f"SYNC ERROR: Expected selected_image='{filename}', but got '{verification_selected}' after save!")
            else:
                logger.info(f"Verified: selected_image correctly set to '{filename}'")

            return True
        else:
            logger.error(f"Failed to display playlist file: {filename}")
            return False

    except Exception as e:
        logger.error(f"Error advancing playlist: {e}")
        return False

def check_playlist_timer():
    """Check if it's time to advance the playlist or timeout from live mode"""
    try:
        settings = load_settings()

        if not settings.get('playlist_enabled', False):
            return False

        # Check if we should timeout from live mode back to playlist
        if settings.get('display_mode') == 'live':
            live_timeout_minutes = settings.get('live_mode_timeout_minutes', 30)
            live_start_time = settings.get('live_mode_start_time', 0)

            # If timeout is disabled (0), stay in live mode
            if live_timeout_minutes == 0:
                return False

            # Check if live mode has timed out
            if time.time() - live_start_time >= (live_timeout_minutes * 60):
                logger.info(f"Live mode timed out after {live_timeout_minutes} minutes, returning to playlist")
                # Force advance playlist to resume playlist mode
                return advance_playlist()
            else:
                return False

        # Get current playlist for timing check
        current_playlist_name = settings.get('playlist_current_name', 'default')
        playlists = settings.get('playlists', {})

        if current_playlist_name not in playlists:
            return False

        current_playlist = playlists[current_playlist_name]
        interval_minutes = settings.get('playlist_interval_minutes', 5)
        last_change = current_playlist.get('last_change', 0)

        # Check if enough time has passed for playlist advance
        if time.time() - last_change >= (interval_minutes * 60):
            return advance_playlist()

        return False

    except Exception as e:
        logger.error(f"Error checking playlist timer: {e}")
        return False

@app.route('/upload', methods=['POST', 'PUT'])
@login_required
def upload_file():
    """Handle file upload from TouchDesigner"""
    try:
        if request.method == 'POST':
            # Handle both multipart form data and raw binary data

            # Check if this is raw binary data (TouchDesigner tunnel upload)
            if request.headers.get('Content-Type') == 'application/octet-stream' and request.headers.get('X-Filename'):
                # Handle raw binary data from TouchDesigner
                filename = request.headers.get('X-Filename', 'uploaded_file')
                file_data = request.get_data()

                logger.info(f"POST raw binary upload: {filename}, size: {len(file_data)} bytes")

                if not file_data or len(file_data) == 0:
                    logger.error("No file data received in POST request")
                    return jsonify({'error': 'No file data received'}), 400

                if not allowed_file(filename):
                    return jsonify({'error': 'File type not allowed'}), 400

                # Secure the filename
                filename = secure_filename(filename)

                # Add timestamp to avoid conflicts
                timestamp = int(time.time())
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{timestamp}{ext}"

                # Save file data using atomic operation
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                temp_filepath = filepath + '.tmp'

                # Write to temporary file first
                logger.info(f"Starting raw data write to temp: {temp_filepath}, data size: {len(file_data)} bytes")
                with open(temp_filepath, 'wb') as f:
                    f.write(file_data)
                logger.info(f"Raw data write completed, file size: {os.path.getsize(temp_filepath)} bytes")

                # Atomically move to final location
                logger.info(f"Performing atomic rename from {temp_filepath} to {filepath}")
                os.rename(temp_filepath, filepath)
                logger.info(f"Atomic rename completed")

                # Generate thumbnail
                try:
                    generate_thumbnail(filepath)
                    logger.info(f"Thumbnail generated for {filename}")
                except Exception as e:
                    logger.error(f"Thumbnail generation failed for {filename}: {e}")

                # Auto-display if enabled
                settings = load_settings()
                if settings.get('auto_display_upload', True):
                    logger.info(f"Auto-display enabled, displaying uploaded file: {filename}")
                    result = display_file_on_eink(filename, mode='live')
                    logger.info(f"Auto-display result for {filename}: {result}")
                else:
                    logger.info(f"Auto-display disabled, not displaying uploaded file: {filename}")

                logger.info(f"File uploaded (POST binary): {filename}")
                return jsonify({
                    'message': 'File uploaded successfully',
                    'filename': filename,
                    'size': os.path.getsize(filepath)
                }), 200

            # Handle multipart form data (traditional upload)
            elif 'file' in request.files:
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': 'No file selected'}), 400

                if file and allowed_file(file.filename):
                    # Secure the filename
                    filename = secure_filename(file.filename)

                    # Add timestamp to avoid conflicts
                    timestamp = int(time.time())
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{timestamp}{ext}"

                    # Save file to watched folder using atomic operation
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    temp_filepath = filepath + '.tmp'

                    # Write to temporary file first
                    logger.info(f"Starting file save to temp: {temp_filepath}")
                    file.save(temp_filepath)
                    logger.info(f"File save completed, size: {os.path.getsize(temp_filepath)} bytes")

                    # Atomically move to final location (only then will watcher see it)
                    logger.info(f"Performing atomic rename from {temp_filepath} to {filepath}")
                    os.rename(temp_filepath, filepath)
                    logger.info(f"Atomic rename completed")

                    # Generate thumbnail if it's an image
                    generate_thumbnail(filepath, filename)

                    # Check if auto-display is enabled and display the file
                    settings = load_settings()
                    if settings.get('auto_display_upload', True):
                        logger.info(f"Auto-display enabled, displaying uploaded file: {filename}")
                        success = display_file_on_eink(filename, mode='live')
                        logger.info(f"Auto-display result for {filename}: {success}")
                    else:
                        logger.info(f"Auto-display disabled, not displaying uploaded file: {filename}")

                    logger.info(f"File uploaded (POST): {filename}")
                    return jsonify({
                        'message': 'File uploaded successfully',
                        'filename': filename,
                        'size': os.path.getsize(filepath)
                    }), 200
                else:
                    return jsonify({'error': 'File type not allowed'}), 400
            else:
                return jsonify({'error': 'No file provided'}), 400

        elif request.method == 'PUT':
            # Handle raw file data (TouchDesigner WebclientDAT uploadFile)
            # TouchDesigner sends data differently, try multiple approaches

            # Debug: Log all request details
            logger.info(f"PUT request debug:")
            logger.info(f"  Headers: {dict(request.headers)}")
            logger.info(f"  Content-Type: {request.content_type}")
            logger.info(f"  Content-Length: {request.content_length}")
            logger.info(f"  Has files: {bool(request.files)}")
            logger.info(f"  Files keys: {list(request.files.keys()) if request.files else 'None'}")
            logger.info(f"  Form data: {dict(request.form) if request.form else 'None'}")
            logger.info(f"  Raw data length: {len(request.data) if request.data else 0}")
            logger.info(f"  Via Cloudflare: {'CF-Ray' in request.headers}")
            logger.info(f"  Remote addr: {request.remote_addr}")
            logger.info(f"  X-Forwarded-For: {request.headers.get('X-Forwarded-For', 'None')}")

            # Get filename from headers or use a default
            filename = request.headers.get('X-Filename', 'uploaded_file')

            # Try to get file data from different sources
            file_data = None
            data_source = "unknown"

            # Method 1: Check if there's form data with file
            if request.files:
                logger.info("Trying method 1: form files")
                file_obj = list(request.files.values())[0]  # Get first file
                file_data = file_obj.read()
                data_source = "form_files"
                if not filename or filename == 'uploaded_file':
                    filename = file_obj.filename or 'uploaded_file'
                logger.info(f"Form files method: got {len(file_data)} bytes")

            # Method 2: Check raw request data
            elif request.data and len(request.data) > 0:
                logger.info("Trying method 2: request.data")
                file_data = request.data
                data_source = "request_data"
                logger.info(f"Request data method: got {len(file_data)} bytes")

            # Method 3: Check if it's in the request stream
            elif hasattr(request, 'stream'):
                logger.info("Trying method 3: request.stream")
                try:
                    file_data = request.stream.read()
                    data_source = "request_stream"
                    logger.info(f"Request stream method: got {len(file_data) if file_data else 0} bytes")
                except Exception as e:
                    logger.info(f"Request stream method failed: {e}")
                    pass

            # Method 4: Try to read from request directly
            if not file_data:
                logger.info("Trying method 4: request.get_data()")
                try:
                    file_data = request.get_data()
                    data_source = "get_data"
                    logger.info(f"Get data method: got {len(file_data) if file_data else 0} bytes")
                except Exception as e:
                    logger.info(f"Get data method failed: {e}")
                    pass

            if not file_data or len(file_data) == 0:
                logger.error("No file data received in PUT request - all methods failed")
                return jsonify({'error': 'No file data received'}), 400

            # If no extension, try to guess from content-type
            if '.' not in filename:
                content_type = request.headers.get('Content-Type', '')
                if 'image/jpeg' in content_type:
                    filename += '.jpg'
                elif 'image/png' in content_type:
                    filename += '.png'
                elif 'text/plain' in content_type:
                    filename += '.txt'
                elif 'application/pdf' in content_type:
                    filename += '.pdf'
                else:
                    filename += '.bin'

            # Secure the filename
            filename = secure_filename(filename)

            # Add timestamp to avoid conflicts
            timestamp = int(time.time())
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{timestamp}{ext}"

            # Save file data using atomic operation
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            temp_filepath = filepath + '.tmp'

            # Write to temporary file first
            logger.info(f"Starting raw data write to temp: {temp_filepath}, data size: {len(file_data)} bytes (source: {data_source})")
            with open(temp_filepath, 'wb') as f:
                f.write(file_data)
            logger.info(f"Raw data write completed, file size: {os.path.getsize(temp_filepath)} bytes")

            # Atomically move to final location (only then will watcher see it)
            logger.info(f"Performing atomic rename from {temp_filepath} to {filepath}")
            os.rename(temp_filepath, filepath)
            logger.info(f"Atomic rename completed")

            # Generate thumbnail if it's an image
            generate_thumbnail(filepath, filename)

            # Check if auto-display is enabled and display the file
            settings = load_settings()
            if settings.get('auto_display_upload', True):
                logger.info(f"Auto-display enabled, displaying uploaded file: {filename}")
                success = display_file_on_eink(filename, mode='live')
                logger.info(f"Auto-display result for {filename}: {success}")
            else:
                logger.info(f"Auto-display disabled, not displaying uploaded file: {filename}")

            logger.info(f"File uploaded (PUT): {filename}")
            return jsonify({
                'message': 'File uploaded successfully',
                'filename': filename,
                'size': os.path.getsize(filepath)
            }), 200

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/upload_text', methods=['POST'])
@login_required
def upload_text():
    """Handle text content upload from TouchDesigner"""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'No content provided'}), 400

        content = data['content']
        filename = data.get('filename', f'touchdesigner_{int(time.time())}.txt')

        # Ensure .txt extension
        if not filename.endswith('.txt'):
            filename += '.txt'

        filename = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Write text content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        # Generate thumbnail if applicable (text files don't get thumbnails)
        generate_thumbnail(filepath, filename)

        # Check if auto-display is enabled and display the file
        settings = load_settings()
        if settings.get('auto_display_upload', True):
            logger.info(f"Auto-display enabled, displaying uploaded text file: {filename}")
            success = display_file_on_eink(filename, mode='live')
            logger.info(f"Auto-display result for {filename}: {success}")
        else:
            logger.info(f"Auto-display disabled, not displaying uploaded text file: {filename}")

        logger.info(f"Text uploaded: {filename}")
        return jsonify({
            'message': 'Text uploaded successfully',
            'filename': filename,
            'size': len(content)
        }), 200

    except Exception as e:
        logger.error(f"Text upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    """Get server status - no auth required for health checks"""
    return jsonify({
        'status': 'running',
        'upload_folder': UPLOAD_FOLDER,
        'allowed_extensions': list(ALLOWED_EXTENSIONS)
    })

@app.route('/settings', methods=['GET'])
def get_settings():
    """Get current settings"""
    try:
        settings = load_settings()
        return jsonify(settings), 200
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/settings', methods=['POST'])
@login_required
def update_settings():
    """Update settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No settings data provided'}), 400

        current_settings = load_settings()

        # Track which settings actually changed
        changed_settings = []

        # Validate and update settings
        for key, value in data.items():
            if key in DEFAULT_SETTINGS:
                if key not in current_settings or current_settings[key] != value:
                    current_settings[key] = value
                    changed_settings.append(key)
            else:
                logger.warning(f"Unknown setting key: {key}")

        # Save updated settings
        if save_settings(current_settings):
            logger.info(f"Settings updated: {changed_settings}")

            # Check if any settings that require immediate action were changed
            immediate_action_settings = [
                'orientation',           # Display refresh needed
                'image_crop_mode',      # Display refresh needed
                'enable_sleep_mode',    # Display refresh needed
                'enable_refresh_timer', # Timer restart needed
                'refresh_interval_hours', # Timer restart needed
                'enable_manufacturer_timing' # Timer restart needed
            ]
            immediate_action_changed = any(setting in immediate_action_settings for setting in changed_settings)

            if immediate_action_changed:
                relevant_changes = [setting for setting in changed_settings if setting in immediate_action_settings]
                logger.info(f"Settings requiring immediate action changed: {relevant_changes} - triggering refresh display")
                try:
                    import threading
                    # Run re-display in background thread so web interface doesn't block
                    thread = threading.Thread(target=trigger_settings_reload_and_redisplay, daemon=True)
                    thread.start()
                    logger.info("Started background re-display due to settings change")

                    # If orientation changed, also update display info
                    if 'orientation' in changed_settings:
                        logger.info("Orientation changed - updating display info")
                        try:
                            command_file = Path(COMMANDS_DIR) / 'update_display_info.json'
                            command_data = {
                                'action': 'update_display_info',
                                'timestamp': time.time()
                            }
                            with open(command_file, 'w') as f:
                                json.dump(command_data, f)
                            logger.info(f"Sent update display info command to {command_file}")
                        except Exception as e:
                            logger.error(f"Error sending update display info command: {e}")

                except Exception as e:
                    logger.warning(f"Failed to start background re-display after settings change: {e}")
            else:
                logger.info("No settings requiring immediate action changed - skipping refresh display")

            return jsonify({
                'message': 'Settings updated successfully',
                'settings': current_settings
            }), 200
        else:
            return jsonify({'error': 'Failed to save settings'}), 500

    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/list_files', methods=['GET'])
def list_files():
    """List all files in the watched folder"""
    try:
        folder = Path(UPLOAD_FOLDER)
        files = [f for f in folder.glob('*') if f.is_file()]

        if not files:
            return jsonify({'files': []}), 200

        # Sort by modification time (latest first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        file_list = []
        for file in files:
            file_list.append({
                'filename': file.name,
                'size': file.stat().st_size,
                'modified': file.stat().st_mtime
            })

        logger.info(f"Listed {len(file_list)} files")
        return jsonify({
            'files': file_list,
            'total_files': len(file_list)
        }), 200

    except Exception as e:
        logger.error(f"List files error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/latest_file', methods=['GET'])
def get_latest_file():
    """Get information about the latest file in the watched folder"""
    try:
        folder = Path(UPLOAD_FOLDER)
        files = [f for f in folder.glob('*') if f.is_file()]

        if not files:
            return jsonify({'message': 'No files found'}), 404

        # Sort by modification time (latest first)
        latest_file = max(files, key=lambda f: f.stat().st_mtime)

        logger.info(f"Latest file: {latest_file.name}")
        return jsonify({
            'filename': latest_file.name,
            'size': latest_file.stat().st_size,
            'modified': latest_file.stat().st_mtime
        }), 200

    except Exception as e:
        logger.error(f"Latest file error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/cleanup_old_files', methods=['POST'])
def cleanup_old_files():
    """Remove old files, keeping only the most recent N files"""
    try:
        # Get number of files to keep (default: 10)
        data = request.get_json() or {}
        keep_count = data.get('keep_count', 10)

        folder = Path(UPLOAD_FOLDER)
        files = [f for f in folder.glob('*') if f.is_file()]

        if len(files) <= keep_count:
            return jsonify({
                'message': f'No cleanup needed. Only {len(files)} files found.',
                'files_removed': []
            }), 200

        # Sort by modification time (latest first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # Keep the most recent files, remove the rest
        files_to_keep = files[:keep_count]
        files_to_remove = files[keep_count:]

        removed_files = []
        for file in files_to_remove:
            file.unlink()
            removed_files.append(file.name)

        logger.info(f"Cleaned up {len(removed_files)} old files, kept {len(files_to_keep)} recent files")
        return jsonify({
            'message': f'Cleaned up {len(removed_files)} old files',
            'files_removed': removed_files,
            'files_kept': len(files_to_keep)
        }), 200

    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/debug/playlist_state', methods=['GET'])
def debug_playlist_state():
    """Debug endpoint to check playlist state"""
    try:
        settings = load_settings()
        return jsonify({
            'selected_image': settings.get('selected_image'),
            'display_mode': settings.get('display_mode'),
            'playlist_enabled': settings.get('playlist_enabled'),
            'current_playlist_name': settings.get('playlist_current_name'),
            'playlists': settings.get('playlists', {}),
            'timestamp': time.time()
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug/force_sync', methods=['POST'])
@login_required
def force_playlist_sync():
    """Force sync the displayed file with current playlist"""
    try:
        settings = load_settings()
        display_mode = settings.get('display_mode', 'manual')
        playlist_enabled = settings.get('playlist_enabled', False)

        # If playlist is enabled but display_mode is wrong, fix it
        if playlist_enabled and display_mode != 'playlist':
            logger.warning(f"Force sync: Fixing display_mode from '{display_mode}' to 'playlist'")
            settings['display_mode'] = 'playlist'
            display_mode = 'playlist'

        if display_mode == 'playlist' and playlist_enabled:
            current_playlist_name = settings.get('playlist_current_name', 'default')
            playlists = settings.get('playlists', {})

            if current_playlist_name in playlists:
                current_playlist = playlists[current_playlist_name]
                playlist_files = current_playlist.get('files', [])
                current_index = current_playlist.get('current_index', 0)

                if playlist_files and current_index < len(playlist_files):
                    expected_file = playlist_files[current_index]

                    # Force update selected_image
                    old_selected = settings.get('selected_image')
                    settings['selected_image'] = expected_file
                    save_success = save_settings(settings)

                    return jsonify({
                        'message': 'Force sync completed',
                        'old_selected_image': old_selected,
                        'new_selected_image': expected_file,
                        'save_success': save_success,
                        'current_index': current_index,
                        'playlist_files': playlist_files
                    }), 200
                else:
                    return jsonify({'error': 'No valid playlist files'}), 400
            else:
                return jsonify({'error': f'Playlist {current_playlist_name} not found'}), 404
        else:
            return jsonify({'error': 'Not in playlist mode'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/displayed_file', methods=['GET'])
def get_displayed_file():
    """Get information about the currently displayed file"""
    try:
        # Read settings to get the selected image (priority system)
        settings = load_settings()
        selected_image = settings.get('selected_image')
        display_mode = settings.get('display_mode', 'manual')

        logger.info(f"Displayed file check - selected_image: {selected_image}, display_mode: {display_mode}")

        # If playlist is enabled and we're in manual mode, prefer playlist.
        # Do NOT override 'live' here; live mode should persist until timeout.
        playlist_enabled = settings.get('playlist_enabled', False)
        if playlist_enabled and display_mode == 'manual':
            logger.warning(f"Playlist enabled and display_mode is 'manual'. Switching to 'playlist'.")
            settings['display_mode'] = 'playlist'
            display_mode = 'playlist'
            save_settings(settings)

        # In playlist mode, ALWAYS use the current playlist file as the source of truth
        if display_mode == 'playlist' and playlist_enabled:
            current_playlist_name = settings.get('playlist_current_name', 'default')
            playlists = settings.get('playlists', {})

            if current_playlist_name in playlists:
                current_playlist = playlists[current_playlist_name]
                playlist_files = current_playlist.get('files', [])
                current_index = current_playlist.get('current_index', 0)

                if playlist_files and current_index < len(playlist_files):
                    expected_file = playlist_files[current_index]

                    # In playlist mode, always return the playlist file as the currently displayed file
                    if selected_image != expected_file:
                        logger.warning(f"Playlist mode override: selected_image was '{selected_image}', but playlist shows '{expected_file}' at index {current_index}. Using playlist file.")

                        # Update the selected_image setting to keep it in sync for future calls
                        settings['selected_image'] = expected_file
                        save_settings(settings)
                    else:
                        logger.info(f"Playlist mode: selected_image matches playlist file: {expected_file}")

                    # Always use the playlist file in playlist mode
                    selected_image = expected_file
                    logger.info(f"Playlist mode: returning current playlist file: {expected_file} (index {current_index})")
                else:
                    logger.warning(f"Playlist mode: No valid files in playlist or invalid index. current_index={current_index}, files_length={len(playlist_files)}")

        # If we're in override (live) with no selected image (cleared), report none
        if display_mode == 'live' and not selected_image:
            logger.info("Override active with no selected image (cleared). Returning none.")
            return jsonify({
                'filename': None,
                'type': 'none',
                'exists': False,
                'display_mode': display_mode
            })

        if selected_image:
            file_path = Path(UPLOAD_FOLDER) / selected_image
            if file_path.exists():
                logger.info(f"Returning selected image as currently displayed: {selected_image}")
                return jsonify({
                    'filename': selected_image,
                    'type': 'selected_image',
                    'exists': True,
                    'display_mode': display_mode
                })
            else:
                logger.warning(f"Selected image file does not exist: {selected_image}")

        # Fallback to latest file
        files = [f for f in os.listdir(UPLOAD_FOLDER) if os.path.isfile(os.path.join(UPLOAD_FOLDER, f)) and not f.startswith('.')]
        if files:
            files_with_time = [(f, os.path.getmtime(os.path.join(UPLOAD_FOLDER, f))) for f in files]
            latest_file = max(files_with_time, key=lambda x: x[1])[0]
            logger.info(f"Fallback to latest file as currently displayed: {latest_file}")
            return jsonify({
                'filename': latest_file,
                'type': 'latest_file',
                'exists': True,
                'display_mode': display_mode
            })

        logger.info("No files found, returning null")
        return jsonify({
            'filename': None,
            'type': 'none',
            'exists': False,
            'display_mode': display_mode
        })

    except Exception as e:
        logger.error(f"Error getting displayed file info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear_screen', methods=['POST'])
@login_required
def clear_screen():
    """Clear the e-ink display and enter override with timeout."""
    try:
        # Enter override-blank: set live mode and clear selected image
        settings = load_settings()
        settings['display_mode'] = 'live'
        settings['live_mode_start_time'] = time.time()
        settings['selected_image'] = None
        save_settings(settings)

        # Send clear command to the main display handler instead of direct EPD access
        command_file = Path(COMMANDS_DIR) / 'clear_display.json'
        command_data = {
            'action': 'clear_display',
            'timestamp': time.time()
        }

        with open(command_file, 'w') as f:
            json.dump(command_data, f)

        logger.info("Display cleared and override-blank engaged")
        return jsonify({'message': 'Display cleared; override active'}), 200

    except Exception as e:
        logger.error(f"Clear screen error: {e}")
        return jsonify({'error': str(e)}), 500

# ============ NEW API ROUTES ============

@app.route('/display_file', methods=['POST'])
@login_required
def display_file():
    """Display a specific file on the e-ink display"""
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'error': 'Filename not provided'}), 400

        filename = data['filename']
        # Treat manual display as LIVE to pause playlist until timeout
        # Tag the live source as 'manual' so UI can show correct text
        success = display_file_on_eink(filename, mode='live')

        if success:
            return jsonify({
                'message': f'File displayed successfully: {filename}'
            }), 200
        else:
            return jsonify({'error': 'Failed to display file'}), 500

    except Exception as e:
        logger.error(f"Display file error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_file', methods=['POST'])
@login_required
def delete_file():
    """Delete a specific file"""
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'error': 'Filename not provided'}), 400

        filename = secure_filename(data['filename'])
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404

        # Delete main file
        os.remove(filepath)

        # Delete thumbnail if it exists
        name_without_ext = filename.rsplit('.', 1)[0]
        thumb_filename = f"{name_without_ext}_thumb.jpg"
        thumb_path = os.path.join(THUMBNAILS_FOLDER, thumb_filename)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)

        logger.info(f"Deleted file: {filename}")
        return jsonify({
            'message': f'File deleted successfully: {filename}'
        }), 200

    except Exception as e:
        logger.error(f"Delete file error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_multiple', methods=['POST'])
@login_required
def delete_multiple_files():
    """Delete multiple files"""
    try:
        data = request.get_json()
        if not data or 'filenames' not in data:
            return jsonify({'error': 'Filenames not provided'}), 400

        filenames = data['filenames']
        deleted_files = []
        errors = []

        for filename in filenames:
            try:
                filename = secure_filename(filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)

                if os.path.exists(filepath):
                    os.remove(filepath)
                    deleted_files.append(filename)

                    # Delete thumbnail if it exists
                    name_without_ext = filename.rsplit('.', 1)[0]
                    thumb_filename = f"{name_without_ext}_thumb.jpg"
                    thumb_path = os.path.join(THUMBNAILS_FOLDER, thumb_filename)
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)
                else:
                    errors.append(f"File not found: {filename}")

            except Exception as e:
                errors.append(f"Error deleting {filename}: {str(e)}")

        logger.info(f"Deleted {len(deleted_files)} files")
        return jsonify({
            'message': f'Deleted {len(deleted_files)} files',
            'deleted_files': deleted_files,
            'errors': errors if errors else None
        }), 200

    except Exception as e:
        logger.error(f"Delete multiple files error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/thumbnails/<filename>')
def serve_thumbnail(filename):
    """Serve thumbnail images"""
    try:
        return send_from_directory(THUMBNAILS_FOLDER, filename)
    except Exception:
        # Return a default image or 404
        return '', 404

@app.route('/files/<filename>')
def serve_file(filename):
    """Serve uploaded files"""
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception:
        return '', 404

@app.route('/display_info', methods=['GET'])
def get_display_info():
    """Get display information including resolution"""
    try:
        settings = load_settings()
        display_type = settings.get('display_type', 'epd2in15g')

        display_info_file = Path(os.path.expanduser('~/.config/rpi-einky/display_info.json'))

        if display_info_file.exists():
            try:
                with open(display_info_file, 'r') as f:
                    display_data = json.load(f)
                    logger.info(f"Loaded display info from file: {display_data}")
                    return jsonify(display_data), 200
            except Exception as e:
                logger.warning(f"Could not read display info file: {e}")

        command_file = Path(COMMANDS_DIR) / 'get_display_info.json'
        command_data = {
            'action': 'get_display_info',
            'timestamp': time.time()
        }

        try:
            with open(command_file, 'w') as f:
                json.dump(command_data, f)

            time.sleep(0.2)

            response_file = Path(COMMANDS_DIR) / 'display_info_response.json'
            if response_file.exists():
                try:
                    with open(response_file, 'r') as f:
                        display_data = json.load(f)

                    response_file.unlink(missing_ok=True)

                    logger.info(f"Got display info from handler: {display_data}")
                    return jsonify(display_data), 200
                except Exception as e:
                    logger.warning(f"Could not read display info response: {e}")
                    response_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Could not send display info command: {e}")

        logger.info(f"Using settings-based display info for {display_type}")

        orientation = settings.get('orientation', 'landscape')

        # TODO: remove hardcoded resolutions
        display_resolutions = {
            'epd2in15g': {'width': 250, 'height': 122},
            'epd7in3e': {'width': 800, 'height': 480},
            'epd13in3E': {'width': 1872, 'height': 1404}
        }

        resolution = display_resolutions.get(display_type, {'width': 250, 'height': 122})

        return jsonify({
            'display_type': display_type,
            'resolution': resolution,
            'native_resolution': resolution,
            'orientation': orientation,
            'native_orientation': 'landscape',
            'source': 'settings_fallback'
        }), 200

    except Exception as e:
        logger.error(f"Error getting display info: {e}")
        return jsonify({'error': str(e)}), 500

# ============ PLAYLIST API ROUTES ============

@app.route('/api/playlist', methods=['GET'])
@login_required
def get_playlist():
    """Get current playlist configuration and status"""
    try:
        settings = load_settings()
        available_files = get_playlist_files()

        # Get current playlist info
        current_playlist_name = settings.get('playlist_current_name', 'default')
        playlists = settings.get('playlists', {})
        current_playlist = playlists.get(current_playlist_name, {})

        # Calculate timing information
        timing_info = {}
        if settings.get('playlist_enabled', False) and current_playlist.get('files'):
            last_change = current_playlist.get('last_change', 0)
            interval_minutes = settings.get('playlist_interval_minutes', 5)

            if last_change > 0:
                elapsed_seconds = time.time() - last_change
                remaining_seconds = max(0, (interval_minutes * 60) - elapsed_seconds)
                timing_info = {
                    'last_change_timestamp': last_change,
                    'elapsed_seconds': elapsed_seconds,
                    'remaining_seconds': remaining_seconds,
                    'next_change_in_minutes': max(0, remaining_seconds / 60)
                }

        return jsonify({
            'enabled': settings.get('playlist_enabled', False),
            'interval_minutes': settings.get('playlist_interval_minutes', 5),
            'current_playlist_name': current_playlist_name,
            'playlists': playlists,
            'files': current_playlist.get('files', []),
            'current_index': current_playlist.get('current_index', 0),
            'last_change': current_playlist.get('last_change', 0),
            'display_mode': settings.get('display_mode', 'manual'),
            'live_mode_timeout_minutes': settings.get('live_mode_timeout_minutes', 30),
            'live_mode_start_time': settings.get('live_mode_start_time', 0),
            'available_files': available_files,
            'timing_info': timing_info
        }), 200

    except Exception as e:
        logger.error(f"Error getting playlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist', methods=['POST'])
@login_required
def update_playlist():
    """Update playlist configuration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        settings = load_settings()

        # Update global playlist settings
        if 'enabled' in data:
            settings['playlist_enabled'] = bool(data['enabled'])

        if 'interval_minutes' in data:
            interval = int(data['interval_minutes'])
            if interval < 1:
                return jsonify({'error': 'Interval must be at least 1 minute'}), 400
            settings['playlist_interval_minutes'] = interval

        if 'live_mode_timeout_minutes' in data:
            timeout = int(data['live_mode_timeout_minutes'])
            if timeout < 0:
                return jsonify({'error': 'Live mode timeout must be 0 or greater (0 = no timeout)'}), 400
            settings['live_mode_timeout_minutes'] = timeout

        if 'current_playlist_name' in data:
            playlist_name = data['current_playlist_name']
            playlists = settings.get('playlists', {})
            if playlist_name in playlists:
                settings['playlist_current_name'] = playlist_name
            else:
                return jsonify({'error': f'Playlist "{playlist_name}" does not exist'}), 400

        # Update specific playlist files and settings
        if 'files' in data or 'randomize' in data:
            current_playlist_name = data.get('playlist_name', settings.get('playlist_current_name', 'default'))
            playlists = settings.get('playlists', {})

            # Update the specific playlist
            if current_playlist_name not in playlists:
                playlists[current_playlist_name] = {
                    'name': current_playlist_name.title() + ' Playlist',
                    'files': [],
                    'current_index': 0,
                    'last_change': 0,
                    'randomize': False
                }

            # Update files if provided
            if 'files' in data:
                # Validate that all files exist
                folder = Path(UPLOAD_FOLDER)
                valid_files = []
                for filename in data['files']:
                    if (folder / filename).exists():
                        valid_files.append(filename)
                    else:
                        logger.warning(f"Playlist file does not exist: {filename}")

                playlists[current_playlist_name]['files'] = valid_files
                playlists[current_playlist_name]['current_index'] = 0  # Reset to start

            # Update randomize setting if provided
            if 'randomize' in data:
                playlists[current_playlist_name]['randomize'] = bool(data['randomize'])
                # Reset index when changing randomize mode
                playlists[current_playlist_name]['current_index'] = 0

            settings['playlists'] = playlists

        # Save settings
        if save_settings(settings):
            current_playlist_name = settings.get('playlist_current_name', 'default')
            current_playlist = settings.get('playlists', {}).get(current_playlist_name, {})

            logger.info(f"Playlist settings updated: enabled={settings.get('playlist_enabled')}, current='{current_playlist_name}', files={len(current_playlist.get('files', []))}")

            # If playlist was enabled and has files, start it
            if settings.get('playlist_enabled') and current_playlist.get('files'):
                advance_playlist()

            return jsonify({
                'message': 'Playlist updated successfully',
                'playlist': {
                    'enabled': settings.get('playlist_enabled', False),
                    'interval_minutes': settings.get('playlist_interval_minutes', 5),
                    'current_playlist_name': current_playlist_name,
                    'files': current_playlist.get('files', []),
                    'current_index': current_playlist.get('current_index', 0),
                    'live_mode_timeout_minutes': settings.get('live_mode_timeout_minutes', 30)
                }
            }), 200
        else:
            return jsonify({'error': 'Failed to save playlist settings'}), 500

    except Exception as e:
        logger.error(f"Error updating playlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist/advance', methods=['POST'])
@login_required
def advance_playlist_manual():
    """Manually advance to next playlist item"""
    try:
        success = advance_playlist()
        if success:
            return jsonify({'message': 'Playlist advanced successfully'}), 200
        else:
            return jsonify({'error': 'Failed to advance playlist'}), 500

    except Exception as e:
        logger.error(f"Error manually advancing playlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist/resume', methods=['POST'])
@login_required
def resume_playlist():
    """Resume playlist immediately from live/manual override.
    Sets display_mode to 'playlist' and displays the current playlist item.
    """
    try:
        settings = load_settings()
        settings['display_mode'] = 'playlist'

        current_playlist_name = settings.get('playlist_current_name', 'default')
        playlists = settings.get('playlists', {})

        if current_playlist_name not in playlists:
            return jsonify({'error': f"Playlist '{current_playlist_name}' not found"}), 404

        current_playlist = playlists[current_playlist_name]
        files = current_playlist.get('files', [])
        if not files:
            return jsonify({'error': 'Current playlist has no files'}), 400

        index = current_playlist.get('current_index', 0)
        if index >= len(files):
            index = 0
        filename = files[index]

        # Display current item and reset live start/timeout context
        success = display_file_on_eink(filename, mode='playlist')
        if not success:
            return jsonify({'error': 'Failed to display playlist item'}), 500

        # Mark last_change now to restart interval timer
        settings = load_settings()
        settings['display_mode'] = 'playlist'
        playlists = settings.get('playlists', {})
        current_playlist = playlists.get(current_playlist_name, {})
        current_playlist['last_change'] = time.time()
        settings['playlists'][current_playlist_name] = current_playlist
        # Clear live source when resuming playlist
        # remove any legacy live_source
        settings.pop('live_source', None)
        save_settings(settings)

        return jsonify({'message': 'Playlist resumed', 'filename': filename}), 200

    except Exception as e:
        logger.error(f"Error resuming playlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist/check', methods=['POST'])
def check_playlist():
    """Check and advance playlist if needed (internal endpoint)"""
    try:
        advanced = check_playlist_timer()
        return jsonify({'advanced': advanced}), 200

    except Exception as e:
        logger.error(f"Error checking playlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist/create', methods=['POST'])
@login_required
def create_playlist():
    """Create a new playlist"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Playlist name is required'}), 400

        playlist_name = data['name'].strip()
        if not playlist_name:
            return jsonify({'error': 'Playlist name cannot be empty'}), 400

        settings = load_settings()
        playlists = settings.get('playlists', {})

        if playlist_name in playlists:
            return jsonify({'error': f'Playlist "{playlist_name}" already exists'}), 400

        # Create new playlist
        playlists[playlist_name] = {
            'name': data.get('display_name', playlist_name.title() + ' Playlist'),
            'files': data.get('files', []),
            'current_index': 0,
            'last_change': 0,
            'randomize': data.get('randomize', False)
        }

        settings['playlists'] = playlists

        if save_settings(settings):
            logger.info(f"Created new playlist: {playlist_name}")
            return jsonify({
                'message': f'Playlist "{playlist_name}" created successfully',
                'playlist': playlists[playlist_name]
            }), 200
        else:
            return jsonify({'error': 'Failed to save playlist'}), 500

    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist/delete', methods=['POST'])
@login_required
def delete_playlist():
    """Delete a playlist"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Playlist name is required'}), 400

        playlist_name = data['name']
        settings = load_settings()
        playlists = settings.get('playlists', {})

        if playlist_name not in playlists:
            return jsonify({'error': f'Playlist "{playlist_name}" does not exist'}), 404

        if playlist_name == 'default':
            return jsonify({'error': 'Cannot delete the default playlist'}), 400

        # Remove the playlist
        del playlists[playlist_name]
        settings['playlists'] = playlists

        # If this was the current playlist, switch to default
        if settings.get('playlist_current_name') == playlist_name:
            settings['playlist_current_name'] = 'default'

        if save_settings(settings):
            logger.info(f"Deleted playlist: {playlist_name}")
            return jsonify({
                'message': f'Playlist "{playlist_name}" deleted successfully'
            }), 200
        else:
            return jsonify({'error': 'Failed to save changes'}), 500

    except Exception as e:
        logger.error(f"Error deleting playlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist/switch', methods=['POST'])
@login_required
def switch_playlist():
    """Switch to a different playlist"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Playlist name is required'}), 400

        playlist_name = data['name']
        settings = load_settings()
        playlists = settings.get('playlists', {})

        if playlist_name not in playlists:
            return jsonify({'error': f'Playlist "{playlist_name}" does not exist'}), 404

        settings['playlist_current_name'] = playlist_name

        if save_settings(settings):
            logger.info(f"Switched to playlist: {playlist_name}")

            # If playlist is enabled and has files, start displaying it
            if settings.get('playlist_enabled') and playlists[playlist_name].get('files'):
                advance_playlist()

            return jsonify({
                'message': f'Switched to playlist "{playlist_name}"',
                'current_playlist': playlists[playlist_name]
            }), 200
        else:
            return jsonify({'error': 'Failed to switch playlist'}), 500

    except Exception as e:
        logger.error(f"Error switching playlist: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/playlist/rename', methods=['POST'])
@login_required
def rename_playlist():
    """Rename a playlist"""
    try:
        data = request.get_json()
        if not data or 'old_name' not in data or 'new_name' not in data:
            return jsonify({'error': 'Both old_name and new_name are required'}), 400

        old_name = data['old_name']
        new_name = data['new_name'].strip()
        display_name = data.get('display_name', new_name.title() + ' Playlist')

        if not new_name:
            return jsonify({'error': 'New name cannot be empty'}), 400

        if old_name == 'default':
            return jsonify({'error': 'Cannot rename the default playlist'}), 400

        settings = load_settings()
        playlists = settings.get('playlists', {})

        if old_name not in playlists:
            return jsonify({'error': f'Playlist "{old_name}" does not exist'}), 404

        if new_name in playlists and new_name != old_name:
            return jsonify({'error': f'Playlist "{new_name}" already exists'}), 400

        # Rename the playlist
        playlist_data = playlists[old_name].copy()
        playlist_data['name'] = display_name

        playlists[new_name] = playlist_data
        del playlists[old_name]
        settings['playlists'] = playlists

        # Update current playlist name if this was the current one
        if settings.get('playlist_current_name') == old_name:
            settings['playlist_current_name'] = new_name

        if save_settings(settings):
            logger.info(f"Renamed playlist from '{old_name}' to '{new_name}'")
            return jsonify({
                'message': f'Playlist renamed from "{old_name}" to "{new_name}" successfully',
                'playlist': playlists[new_name]
            }), 200
        else:
            return jsonify({'error': 'Failed to save changes'}), 500

    except Exception as e:
        logger.error(f"Error renaming playlist: {e}")
        return jsonify({'error': str(e)}), 500

# ============ AUTHENTICATION ROUTES ============

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if check_password(password):
            session['logged_in'] = True
            session.permanent = True
            flash('Successfully logged in!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid password. Please try again.', 'error')
            logger.warning(f"Failed login attempt from {request.remote_addr}")

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.pop('logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ============ WEB INTERFACE ROUTES ============

@app.route('/')
@login_required
def index():
    """Main web interface"""
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Serve the favicon"""
    return send_from_directory('static', 'favicon.ico')

@app.route('/api/files')
@login_required
def api_list_files():
    """Enhanced file listing with thumbnails and metadata"""
    try:
        folder = Path(UPLOAD_FOLDER)
        files = [f for f in folder.glob('*') if f.is_file() and not f.name.startswith('.')]

        if not files:
            return jsonify({'files': []}), 200

        # Sort by modification time (latest first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        file_list = []
        for file in files:
            file_info = {
                'filename': file.name,
                'size': file.stat().st_size,
                'modified': file.stat().st_mtime,
                'type': get_file_type(file.name),
                'thumbnail': None
            }

            # Generate thumbnail for images
            if file_info['type'] == 'image':
                thumb_filename = generate_thumbnail(str(file), file.name)
                if thumb_filename:
                    file_info['thumbnail'] = url_for('serve_thumbnail', filename=thumb_filename)

            file_list.append(file_info)

        logger.info(f"Listed {len(file_list)} files with metadata")
        return jsonify({
            'files': file_list,
            'total_files': len(file_list)
        }), 200

    except Exception as e:
        logger.error(f"Enhanced list files error: {e}")
        return jsonify({'error': str(e)}), 500

# Background task for playlist management
import threading

def playlist_background_task():
    """Background task to check playlist timer periodically"""
    consecutive_errors = 0
    while True:
        try:
            check_playlist_timer()
            consecutive_errors = 0  # Reset error count on success
            time.sleep(15)  # Check every 15 seconds for good balance
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Playlist background task error #{consecutive_errors}: {e}")

            # If too many consecutive errors, wait longer to prevent spam
            if consecutive_errors > 5:
                logger.warning(f"Too many playlist errors ({consecutive_errors}), sleeping for 2 minutes")
                time.sleep(120)  # Sleep 2 minutes after many errors
            else:
                time.sleep(60)  # Wait longer on error

if __name__ == '__main__':
    ensure_upload_folder()
    logger.info(f"Starting upload server...")
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"Allowed extensions: {ALLOWED_EXTENSIONS}")

    # Start background playlist task
    playlist_thread = threading.Thread(target=playlist_background_task, daemon=True)
    playlist_thread.start()
    logger.info("Started playlist background task")

    # Get host and port from environment or use defaults
    # In production with Cloudflare tunnel, bind to localhost only for security
    default_host = '127.0.0.1' if os.environ.get('FLASK_ENV') == 'production' else '0.0.0.0'
    host = os.environ.get('FLASK_HOST', default_host)
    port = int(os.environ.get('FLASK_PORT', 5000))

    logger.info(f"Server will run on {host}:{port}")

    # Run server (accessible from network)
    app.run(host=host, port=port, debug=False)
