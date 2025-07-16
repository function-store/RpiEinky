#!/usr/bin/env python3
"""
Simple HTTP upload server for TouchDesigner to e-ink display system.
Receives files via HTTP POST and saves them to the watched folder for immediate display.
"""
import os
import time
from pathlib import Path
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configuration
UPLOAD_FOLDER = os.path.expanduser('~/watched_files')
ALLOWED_EXTENSIONS = {
    'txt', 'md', 'py', 'js', 'html', 'css',  # Text files
    'jpg', 'jpeg', 'png', 'bmp', 'gif',      # Images
    'pdf',                                    # PDFs
    'json', 'xml', 'csv'                     # Data files
}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_upload_folder():
    """Create upload folder if it doesn't exist"""
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

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

if __name__ == '__main__':
    ensure_upload_folder()
    logger.info(f"Starting upload server...")
    logger.info(f"Upload folder: {UPLOAD_FOLDER}")
    logger.info(f"Allowed extensions: {ALLOWED_EXTENSIONS}")
    
    # Run server (accessible from network)
    app.run(host='0.0.0.0', port=5000, debug=False) 