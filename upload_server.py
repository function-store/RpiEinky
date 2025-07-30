#!/usr/bin/env python3
"""
Web management server for e-ink display system.
Provides both API endpoints and web interface for file management.
"""
import os
import time
import json
import base64
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import logging

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
    'orientation': 'landscape'  # Display orientation: 'landscape', 'portrait', 'landscape_flipped', 'portrait_flipped'
}

# Image extensions for thumbnail generation
IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp', 'gif'}

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
    """Save settings to file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        logger.info("Settings saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
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

def display_file_on_eink(filename):
    """Display a specific file on the e-ink display"""
    try:
        # Save the selected image setting
        settings = load_settings()
        settings['selected_image'] = filename
        save_success = save_settings(settings)
        logger.info(f"Saved selected_image setting for {filename}: {save_success}")
        
        # Small delay to ensure settings file is written
        time.sleep(0.1)
        
        # Write a display command for the main handler to execute
        command_file = Path(COMMANDS_DIR) / 'display_file.json'
        command_data = {
            'action': 'display_file',
            'filename': filename,
            'timestamp': time.time()
        }
        
        with open(command_file, 'w') as f:
            json.dump(command_data, f)
        
        logger.info(f"Sent display command for: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send display command for {filename}: {e}")
        return False

@app.route('/upload', methods=['POST', 'PUT'])
def upload_file():
    """Handle file upload from TouchDesigner"""
    try:
        if request.method == 'POST':
            # Handle multipart form data (traditional upload)
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
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
                
                # Save file to watched folder
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # Generate thumbnail if it's an image
                generate_thumbnail(filepath, filename)
                
                # Check if auto-display is enabled and display the file
                settings = load_settings()
                if settings.get('auto_display_upload', True):
                    logger.info(f"Auto-display enabled, displaying uploaded file: {filename}")
                    success = display_file_on_eink(filename)
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
        
        elif request.method == 'PUT':
            # Handle raw file data (TouchDesigner WebclientDAT uploadFile)
            # Get filename from headers or use a default
            filename = request.headers.get('X-Filename', 'uploaded_file')
            
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
            
            # Save raw data to file
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            with open(filepath, 'wb') as f:
                f.write(request.data)
            
            # Generate thumbnail if it's an image
            generate_thumbnail(filepath, filename)
            
            # Check if auto-display is enabled and display the file
            settings = load_settings()
            if settings.get('auto_display_upload', True):
                logger.info(f"Auto-display enabled, displaying uploaded file: {filename}")
                success = display_file_on_eink(filename)
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
            success = display_file_on_eink(filename)
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
    """Get server status"""
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

@app.route('/displayed_file', methods=['GET'])
def get_displayed_file():
    """Get information about the currently displayed file"""
    try:
        # Read settings to get the selected image (priority system)
        settings = load_settings()
        selected_image = settings.get('selected_image')
        
        logger.info(f"Displayed file check - selected_image: {selected_image}")
        
        if selected_image:
            file_path = Path(UPLOAD_FOLDER) / selected_image
            if file_path.exists():
                logger.info(f"Returning selected image as currently displayed: {selected_image}")
                return jsonify({
                    'filename': selected_image,
                    'type': 'selected_image',
                    'exists': True
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
                'exists': True
            })
        
        logger.info("No files found, returning null")
        return jsonify({
            'filename': None,
            'type': 'none',
            'exists': False
        })
            
    except Exception as e:
        logger.error(f"Error getting displayed file info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear_screen', methods=['POST'])
def clear_screen():
    """Clear the e-ink display screen (without removing files)"""
    try:
        # Send clear command to the main display handler instead of direct EPD access
        command_file = Path(COMMANDS_DIR) / 'clear_display.json'
        command_data = {
            'action': 'clear_display',
            'timestamp': time.time()
        }
        
        with open(command_file, 'w') as f:
            json.dump(command_data, f)
        
        # Wait a moment for the command to be processed
        time.sleep(1)
        
        logger.info("E-ink display screen cleared")
        return jsonify({
            'message': 'E-ink display screen cleared successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Clear screen error: {e}")
        return jsonify({'error': str(e)}), 500

# ============ NEW API ROUTES ============

@app.route('/display_file', methods=['POST'])
def display_file():
    """Display a specific file on the e-ink display"""
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'error': 'Filename not provided'}), 400
        
        filename = data['filename']
        success = display_file_on_eink(filename)
        
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

# ============ WEB INTERFACE ROUTES ============

@app.route('/')
def index():
    """Main web interface"""
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Serve the favicon"""
    return send_from_directory('static', 'favicon.ico')

@app.route('/api/files')
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

if __name__ == '__main__':
    ensure_upload_folder()
    logger.info(f"Starting upload server...")
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"Allowed extensions: {ALLOWED_EXTENSIONS}")
    
    # Run server (accessible from network)
    app.run(host='0.0.0.0', port=5000, debug=False) 