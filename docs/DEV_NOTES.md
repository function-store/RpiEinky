# E-Ink File Display System

A comprehensive e-ink display management system with both file monitoring and **web interface** supporting multiple Waveshare e-paper displays. Features a modern web UI for drag-and-drop uploads, file gallery with thumbnails, and complete remote management of your e-ink display with automatic orientation handling.

## 🎯 Features

### 🌐 **Web Management Interface**
- **Modern responsive web UI** - Beautiful dark mode interface accessible from any device
- **Drag & drop file uploads** - Simply drag files to upload and display
- **Visual file gallery** - Grid view with thumbnails for all uploaded files
- **Click to display** - Select any file from history to show on e-ink display
- **Bulk file management** - Multi-select and delete files with confirmation
- **Real-time status** - Live connection status and upload progress
- **Mobile-friendly** - Works perfectly on phones, tablets, and desktop
- **File previews** - Automatic thumbnail generation for images
- **Configurable settings** - Control image processing, auto-display, thumbnail quality, and timing options
- **Smart image processing** - Center-crop or letterbox modes for perfect display fit
- **Manufacturer timing options** - Configurable 180-second minimum refresh and sleep mode settings

### 📟 **Core Display System**
- **Real-time file monitoring** - Watches `~/watched_files` folder (or custom folder) for new files
- **Persistent file storage** - Files remain on Pi until explicitly cleaned up (latest file always displayed)
- **TouchDesigner integration** - HTTP upload server for remote file management
- **Command line interface** - Full control via command line arguments
- **Initial file display** - Show a specific file immediately on startup
- **Flexible screen control** - Choose when to clear screen (startup, exit, both, or never)
- **Auto-startup service** - Run automatically on system boot with systemd
- **Management scripts** - Easy start, stop, restart, and monitoring without system reboot
- **Simple clear script** - Quick command to clear the display
- **IP address display** - Shows device IP on startup for easy remote access
- **Automatic timing features** - Configurable startup display and refresh intervals to prevent ghosting
- **Manufacturer timing options** - Optional 180-second minimum refresh and sleep mode for display health
- **Smart image processing** - Configurable center-crop or letterbox modes
- **Auto-display control** - Choose whether uploaded files display automatically
- **Multi-format support**:
  - **Images** (jpg, png, bmp, gif): Auto-resized with configurable crop modes
  - **Text files** (txt, md, py, js, html, css): Full content with word wrapping
  - **PDFs**: First page converted to image (requires pdf2image)
  - **Other files**: File information display (name, size, type, date)
- **Multi-display support** - Supports 4-color grayscale and 7-color displays with automatic orientation handling
- **Automatic orientation handling** - Seamlessly works with portrait-native (2.15") and landscape-native (7.3",13.3") displays
- **Display orientation control** - Normal or upside-down orientation for all supported displays
- **Robust error handling** - Visual error messages on display
- **Clean shutdown** - Properly cleans display on exit (configurable)
- **File management API** - List files, get latest file info, cleanup old files

## ⚙️ Settings & Configuration

### ⏰ **Automatic Timing Features**

The system includes configurable timing features to improve display reliability and follow manufacturer recommendations:

#### **🚀 Configurable Startup Display**
- **Purpose**: Shows welcome screen immediately, then displays priority file after configurable delay
- **Behavior**: Welcome screen → wait → priority file (selected image, recent upload, or latest file)
- **Default**: 1 minute delay
- **Use case**: Provides clear startup sequence and ensures priority file is displayed
- **Configuration**: Use `--startup-delay <minutes>` to set custom delay (e.g., `--startup-delay 5` for 5 minutes)

#### **🔄 Configurable Refresh**
- **Purpose**: Prevents e-ink display ghosting by refreshing the display at a configurable interval
- **Behavior**: Clears the display and re-displays the current content to maintain image quality
- **Default**: 24 hours (manufacturer recommendation)
- **Use case**: Manufacturer recommendation to prevent permanent ghosting on e-ink displays
- **Implementation**: Uses clear and re-display method since the waveshare library doesn't have a dedicated refresh method
- **Configuration**: Use `--refresh-interval <hours>` to set custom interval (e.g., `--refresh-interval 12` for 12 hours)

#### **🎛️ Timing Control**
- **Startup Timer**: Use `--enable-startup-timer false` to disable startup timer (show priority file immediately)
- **Refresh Timer**: Use `--enable-refresh-timer false` to disable automatic refresh
- **Startup Delay**: Use `--startup-delay <minutes>` to set custom startup delay
- **Refresh Interval**: Use `--refresh-interval <hours>` to set custom refresh interval
- **Independent Control**: Each timer can be enabled/disabled separately
- **Threading**: Both features run in background threads and don't interfere with normal operation
- **Logging**: All timing events are logged for monitoring and debugging

#### **🔧 Manufacturer Timing Requirements (Optional)**
- **180-Second Minimum**: Enforces 3-minute minimum between display refreshes (manufacturer requirement)
- **Smart Queuing**: Rapid uploads are queued and displayed after timing allows
- **Automatic Retries**: Failed operations retry after minimum interval
- **Default**: Disabled (allows immediate uploads)
- **Configuration**: Enable via web interface settings

#### **😴 Sleep Mode (Optional)**
- **Power Efficiency**: Puts display to sleep between operations to reduce power consumption
- **Display Health**: Prevents damage from long-term power-on
- **Wake Time**: Adds ~0.5-1 second wake time per operation
- **Default**: Enabled (recommended for display longevity)
- **Configuration**: Enable/disable via web interface settings

**Common Startup Delays:**
- `--startup-delay 0` - No delay, welcome screen then priority file immediately
- `--startup-delay 1` - 1 minute delay (default): welcome screen → wait 1 min → priority file
- `--startup-delay 5` - 5 minute delay: welcome screen → wait 5 min → priority file
- `--startup-delay 10` - 10 minute delay: welcome screen → wait 10 min → priority file

**Common Refresh Intervals:**
- `--refresh-interval 6` - Refresh every 6 hours (for high-usage environments)
- `--refresh-interval 12` - Refresh every 12 hours (moderate usage)
- `--refresh-interval 24` - Refresh every 24 hours (default, manufacturer recommendation)
- `--refresh-interval 48` - Refresh every 48 hours (low-usage environments)

### 🎛️ **Web Interface Settings**
Access settings via the **Settings** button in the web interface:

#### **🖼️ Image Processing Mode**
- **Center Crop (Default):** Large images are cropped to fill the entire display
- **Fit with Letterbox:** Images are scaled to fit with black bars if needed

#### **🔄 Auto-Display Uploads**
- **Enabled (Default):** Files automatically display when uploaded
- **Disabled:** Files are saved but not displayed (manual display only)

#### **🖼️ Thumbnail Quality**
- **Range:** 50-95 (JPEG quality)
- **Default:** 85 (good balance of quality/size)

#### **🚀 Startup Timer**
- **Enabled (Default):** Shows welcome screen immediately, then displays priority file after startup delay
- **Disabled:** Displays priority file immediately (no welcome screen or delay)

#### **🔄 Refresh Timer**
- **Enabled (Default):** Automatically refreshes display at configured interval
- **Disabled:** No automatic refresh (may cause ghosting over time)

#### **🔧 Manufacturer Timing Requirements**
- **Enabled:** Enforces 180-second minimum between refreshes, queues rapid uploads
- **Disabled (Default):** No timing restrictions, immediate display

#### **😴 Sleep Mode**
- **Enabled (Default):** Puts display to sleep between operations for power efficiency
- **Disabled:** Display stays active between operations (faster but uses more power)

#### **📋 Settings File Location**
Settings are stored in the dedicated application configuration directory:

**Location:** `~/.config/rpi-einky/settings.json`

**Benefits:**
- ✅ **Persistent settings** - Settings won't be lost if watched folder changes
- ✅ **Clean separation** - Application config separate from user files
- ✅ **Standard location** - Follows Linux configuration conventions
- ✅ **No conflicts** - Settings won't be processed as display files

**Automatic creation:** The system automatically creates the settings file with defaults if it doesn't exist, is empty, or has missing fields.

#### **📋 Command File System**
The system uses a command file system for communication between components:

**Location:** `~/.config/rpi-einky/commands/`

**Command Files:**
- `display_file.json` - Display a specific file on e-ink
- `refresh_display.json` - Reload settings and redisplay current content
- `clear_display.json` - Clear the e-ink display
- `get_display_info.json` - Request display information
- `update_display_info.json` - Update display info with current settings

**Response Files:**
- `display_info_response.json` - Display information response

**How it works:**
1. **Web server** writes command files to `~/.config/rpi-einky/commands/`
2. **Display handler** monitors the commands directory for new files
3. **Display handler** processes commands and writes response files
4. **Web server** reads response files for status information

**Benefits:**
- ✅ **Reliable communication** - File-based communication between processes
- ✅ **No network overhead** - Direct file system communication
- ✅ **Persistent commands** - Commands survive process restarts
- ✅ **Clean architecture** - Separation between web UI and display logic

## 🛠️ Hardware Requirements

- Raspberry Pi (any model)
- Waveshare e-paper display (supported models below)
- Proper wiring as per Waveshare documentation

### Supported Display Models

The system supports multiple e-paper display models through the unified display adapter:

#### **Currently Supported:**
- **Waveshare 2.15" e-paper display (4-color grayscale)** - `epd2in15g`
  - Resolution: 160×296 pixels (47,360 total pixels)
  - Native orientation: Portrait
- **Waveshare 13.3" e-paper display (7-color)** - `epd13in3E`
  - Resolution: 1200×1600 pixels (1,920,000 total pixels)
  - Native orientation: Landscape
- **Waveshare 7.3" e-paper display (7-color)** - `epd7in3e`
  - Resolution: 800×480 pixels (384,000 total pixels)
  - Native orientation: Landscape

#### **Display Configuration:**
The display type is automatically detected from the configuration file `~/watched_files/.epd_config.json`:

```json
{
  "display_type": "epd2in15g"
}
```

#### **Automatic Orientation Handling:**
The system automatically handles different native orientations:
- **Portrait-native displays** (2.15", 13.3"): System automatically converts to landscape for consistent UI
- **Landscape-native displays** (7.3"): Used directly without conversion
- **Seamless switching**: Change display types without code modifications
- **Consistent experience**: All displays show content in landscape orientation regardless of native orientation

#### **Adding New Display Support:**
To add support for additional display models, see the [Unified Display System Documentation](README_UNIFIED_DISPLAY.md).

## 📦 Installation

> **📢 Update Notice**: The system now preserves uploaded files instead of deleting them. Files accumulate over time and the latest file is always displayed. Use the `/cleanup_old_files` endpoint to manage storage.

### Troubleshooting Library Installation

If you encounter import errors, the library structure may be different. Here are common variations:

**Different folder names:**
```bash
# Instead of "waveshare_epd", the folder might be named:
# - "waveshare_epd"
# - "epd"
# - "lib"
# - "python"

# Check what's actually in your downloaded/extracted folder:
ls -la 2in15_e-Paper_G/
ls -la e-Paper/
```

**Different file locations:**
```bash
# The library might be in different subdirectories:
# - RaspberryPi_JetsonNano/python/lib/
# - RaspberryPi/python/lib/
# - python/lib/
# - lib/
# - directly in the root folder

# Find the actual location:
find . -name "epd2in15g.py" -type f
find . -name "waveshare_epd" -type d
```

**Alternative installation methods:**
```bash
# Method 1: Copy the entire python folder
cp -r 2in15_e-Paper_G/RaspberryPi_JetsonNano/python/* eink_env/lib/python3.*/site-packages/

# Method 2: Add to Python path instead of copying
export PYTHONPATH="${PYTHONPATH}:$(pwd)/2in15_e-Paper_G/RaspberryPi_JetsonNano/python/lib"

# Method 3: Install as a package (if setup.py exists)
cd 2in15_e-Paper_G/RaspberryPi_JetsonNano/python
pip install -e .
```

**Verify the correct import:**
```bash
# Test different possible import paths:
python -c "from waveshare_epd import epd2in15g; print('Success!')"
python -c "import epd2in15g; print('Success!')"
python -c "from epd import epd2in15g; print('Success!')"
```

### Additional Steps
See [🌐 Raspberry Network Setup (Optional)](#-raspberry-network-setup-optional) for instructions how to set up a static IP.


## 🚀 Usage

### Basic Usage

1. **Start the monitoring system:**
   ```bash
   source eink_env/bin/activate
   python display_latest.py
   ```

2. **Add files to display:**
   - Copy any file to `~/watched_files/` (in your home directory)
   - The file will automatically appear on your e-ink display

3. **Stop the system:**
   - Press `Ctrl+C` to stop monitoring
   - Display will be cleared and put to sleep (unless `--no-clear-exit` is used)

4. **Clear the display:**
   ```bash
   python clear_display.py
   ```

### Command Line Options

The system supports several command line arguments for customization:

```bash
# Show all available options
python display_latest.py --help

# Display a specific file on startup, then monitor for new files
python display_latest.py --display-file ~/Pictures/my_image.jpg
python display_latest.py -d ~/Documents/welcome.txt

# Monitor a different folder
python display_latest.py --folder ~/my_display_files
python display_latest.py -f ~/Desktop/to_display

# Control screen clearing behavior
python display_latest.py --clear-start           # Clear screen on startup
python display_latest.py --no-clear-exit         # Don't clear screen on exit
python display_latest.py --clear-start --no-clear-exit  # Clear on start only

# Change display orientation
python display_latest.py --orientation landscape    # Normal (not upside-down)

# Control timing features
python display_latest.py --enable-startup-timer false  # Disable startup timer (show priority file immediately)
python display_latest.py --startup-delay 5       # 5-minute startup delay (welcome screen → wait 5 min → priority file)
python display_latest.py --refresh-interval 12   # Set refresh interval to 12 hours

# Combine multiple options
python display_latest.py -d ~/welcome.jpg -f ~/my_files --clear-start --no-clear-exit --startup-delay 2 --refresh-interval 6

# Combine multiple options
python display_latest.py -d ~/welcome.jpg -f ~/my_files --clear-start --no-clear-exit
```

### Command Line Arguments

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--display-file` | `-d` | Display this file on startup, then monitor for new files | None |
| `--folder` | `-f` | Folder to monitor for new files | `~/watched_files` |
| `--clear-start` | - | Clear screen on startup | False |
| `--no-clear-exit` | - | Don't clear screen when exiting | False |
| `--orientation` | - | Display orientation (landscape, landscape_upside_down, portrait, portrait_upside_down) | landscape |
| `--enable-startup-timer` | - | Enable automatic startup display timer (true/false) | true |
| `--enable-refresh-timer` | - | Enable automatic refresh timer (true/false) | true |
| `--startup-delay` | - | Minutes to wait before displaying priority file on startup (shows welcome screen first) | 1 |
| `--refresh-interval` | - | Hours between display refreshes to prevent ghosting | 24 |
| `--enable-manufacturer-timing` | - | Enable manufacturer timing requirements (180s minimum) | False |
| `--disable-sleep-mode` | - | Disable sleep mode between operations (faster but uses more power) | False |
| `--display-type` | - | Specify display type (epd2in15g, epd13in3E, epd7in3e) | Loaded from config file |
| `--help` | `-h` | Show help message and exit | - |

### Supported File Types

| Type | Extensions | Display Method |
|------|------------|----------------|
| Images | `.jpg`, `.png`, `.bmp`, `.gif` | Resized, centered |
| Text | `.txt`, `.md`, `.py`, `.js`, `.html`, `.css` | Full content, word-wrapped |
| PDFs | `.pdf` | First page as image (requires pdf2image) |
| Other | Any other extension | File information display |

## 🔄 Auto-Start Service

The system includes an automated startup service that will run the e-ink display system automatically when your Raspberry Pi boots up.

### Quick Setup

1. **Run the automated setup:**
   ```bash
   ./setup_startup.sh
   ```
   
   The setup script will automatically:
   - Detect your virtual environment location (`~/eink_env` or `./eink_env`)
   - Update service file with correct paths
   - Install and enable the systemd service
   - Set up proper permissions for hardware access

2. **Reboot to test:**
   ```bash
   sudo reboot
   ```

The system will automatically start monitoring for files after boot!

### Manual Setup

If you prefer to set up the service manually:

1. **Update the service file with your paths:**
   ```bash
   # Edit the service file to match your installation directory
   nano eink-display.service
   ```

2. **Install the service:**
   ```bash
   sudo cp eink-display.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable eink-display.service
   ```

3. **Start the service:**
   ```bash
   sudo systemctl start eink-display.service
   ```

### Service Management

| Command | Purpose |
|---------|---------|
| `sudo systemctl start eink-display.service` | Start the service |
| `sudo systemctl stop eink-display.service` | Stop the service |
| `sudo systemctl restart eink-display.service` | Restart the service |
| `sudo systemctl status eink-display.service` | Check service status |
| `sudo systemctl disable eink-display.service` | Disable auto-start |
| `sudo journalctl -u eink-display.service -f` | View real-time logs |

**Common Issues:**
- If you get a "203 error code", check that the virtual environment path in the service file is correct
- The service requires proper hardware group membership (gpio, spi, i2c, dialout)
- Hardware access may require a reboot after adding users to hardware groups

### Customizing Auto-Start

You can customize how the service starts by editing the service file:

```bash
sudo nano /etc/systemd/system/eink-display.service
```

**Example configurations:**

```ini
# Basic monitoring (default) - using virtual environment
ExecStart=/home/pi/eink_env/bin/python /home/pi/RpiEinky/run_eink_system.py

# Show welcome image on startup
ExecStart=/home/pi/eink_env/bin/python /home/pi/RpiEinky/display_latest.py --display-file /home/pi/welcome.jpg

# Kiosk mode: Show welcome, don't clear on exit
ExecStart=/home/pi/eink_env/bin/python /home/pi/RpiEinky/display_latest.py --display-file /home/pi/kiosk/welcome.jpg --no-clear-exit

# Monitor custom folder with clean start
ExecStart=/home/pi/eink_env/bin/python /home/pi/RpiEinky/display_latest.py --folder /home/pi/kiosk_files --clear-start
```

**Important:** The setup script automatically detects whether your virtual environment is in the project folder (`RpiEinky/eink_env`) or your home directory (`~/eink_env`) and updates the service file accordingly.

After making changes, reload the service:
```bash
sudo systemctl daemon-reload
sudo systemctl restart eink-display.service
```

## 🛠️ Management Scripts

The system includes several management scripts for easy control and monitoring:

### **🔄 Restart Script**
```bash
# Clean restart without system reboot
./restart_eink_system.sh

# Check system status
./restart_eink_system.sh status

# View recent logs
./restart_eink_system.sh logs

# Clean up orphaned processes
./restart_eink_system.sh cleanup
```

### **🎛️ Management Script**
```bash
# Start the system
./manage_eink_system.sh start

# Stop the system
./manage_eink_system.sh stop

# Restart the system
./manage_eink_system.sh restart

# Check system status
./manage_eink_system.sh status

# View recent logs
./manage_eink_system.sh logs

# Follow logs in real-time
./manage_eink_system.sh follow

# Clear the display
./manage_eink_system.sh clear

# Show network information
./manage_eink_system.sh ip

# Clean up orphaned processes
./manage_eink_system.sh cleanup
```

### **🧹 Clear Display Script**

```bash
# Clear the display immediately
python clear_display.py
```

This script:
- Initializes the e-ink display
- Clears the screen (makes it white)
- Puts the display to sleep
- Exits cleanly

Perfect for:
- Resetting the display after testing
- Cleaning up before shutdown
- Quick display maintenance

## 🎨 TouchDesigner Integration

The system includes a complete TouchDesigner integration for remote file uploads via HTTP. This allows you to push files from TouchDesigner directly to your e-ink display over the network.

### Setup TouchDesigner Integration

1. **Start the upload server on your Pi:**
   ```bash
   source eink_env/bin/activate
   python upload_server.py
   ```

2. **Find your Pi's IP address:**
   ```bash
   hostname -I
   ```

3. **Test the server (optional):**
   ```bash
   # On your computer (not Pi)
   python test_upload_server.py 192.168.1.100  # Replace with your Pi's IP
   ```

4. **TouchDesigner Component:**
   - TODO: create separate tox and document it

### TouchDesigner Features

   - TODO

### Upload Server Endpoints

#### **Original API Endpoints (TouchDesigner Compatible)**
| Endpoint | Method | Purpose | Data Format |
|----------|---------|---------|-------------|
| `/upload` | POST | Upload files | multipart/form-data |
| `/upload_text` | POST | Upload text content | JSON: `{"content": "text", "filename": "name.txt"}` |
| `/status` | GET | Server status | Returns JSON status |
| `/list_files` | GET | List all files in watched folder | No data |
| `/latest_file` | GET | Get info about most recent file | No data |
| `/displayed_file` | GET | Get info about currently displayed file (priority system) | No data |
| `/cleanup_old_files` | POST | Remove old files, keep recent N files | JSON: `{"keep_count": 10}` |
| `/clear_screen` | POST | Clear the e-ink display | No data |

#### **New Web Interface Endpoints**
| Endpoint | Method | Purpose | Data Format |
|----------|---------|---------|-------------|
| `/` | GET | Web interface homepage | HTML page |
| `/api/files` | GET | Enhanced file listing with thumbnails | JSON with thumbnail URLs |
| `/display_file` | POST | Display specific file on e-ink | JSON: `{"filename": "file.jpg"}` |
| `/delete_file` | POST | Delete specific file | JSON: `{"filename": "file.jpg"}` |
| `/delete_multiple` | POST | Delete multiple files | JSON: `{"filenames": ["file1.jpg", "file2.txt"]}` |
| `/thumbnails/<filename>` | GET | Serve thumbnail images | Image file |
| `/files/<filename>` | GET | Serve original files | File download |

#### **📺 Display Information API**
| Endpoint | Method | Purpose | Data Format |
|----------|---------|---------|-------------|
| `/display_info` | GET | Get display resolution, orientation, and device info | Returns JSON with display details |

**Display Info Response Format:**
```json
{
  "display_type": "epd2in15g",
  "resolution": {
    "width": 250,
    "height": 122
  },
  "native_resolution": {
    "width": 122,
    "height": 250
  },
  "orientation": "landscape",
  "native_orientation": "portrait",
  "device_type": "epd2in15g",
  "source": "display_handler",
  "last_updated": 1703123456.789
}
```

**Response Fields:**
- `display_type` - Current display model (epd2in15g, epd7in3e, epd13in3E)
- `resolution` - Current display resolution in landscape orientation
- `native_resolution` - Native display resolution (before orientation conversion)
- `orientation` - Current display orientation setting
- `native_orientation` - Display's native orientation (portrait/landscape)
- `device_type` - Device type from unified library
- `source` - Data source (display_handler, settings_fallback)
- `last_updated` - Timestamp of last update

**Use Cases:**
- **TouchDesigner integration** - Poll display info for UI configuration
- **Remote monitoring** - Check display status and capabilities
- **Orientation validation** - Verify current orientation settings
- **Display type detection** - Identify connected display model

**TouchDesigner Integration:**
The display info API is designed for TouchDesigner polling. The TouchDesigner extension can automatically poll this endpoint to get real-time display information for UI configuration and status monitoring.

### File Management Behavior

**🔄 New Behavior: Files Are Preserved**
- **Files are NOT deleted** after upload - they remain on the Pi permanently
- **Latest file is always displayed** - the most recently uploaded file appears on screen
- **Files accumulate over time** - you can build up a collection of files
- **Timestamp-based naming** - files get unique names to avoid conflicts (e.g., `image_1703123456.jpg`)

**How It Works:**
1. **Upload a file** → It's automatically displayed on the e-ink screen
2. **Upload another file** → The newer file is displayed (previous one remains stored)
3. **Files accumulate** → Previous files remain available in the watched folder
4. **Display shows latest** → The system always shows the most recent file

### 🎯 **Priority Display System**

The system uses a smart priority system to determine which file to display:

**Priority Order:**
1. **Selected Image** (highest priority) - User explicitly selected via web interface or `--display-file`
2. **Recent Upload** - Last uploaded file (if auto-display enabled AND no selection made)
3. **Latest File** - Most recent file in the folder (fallback)
4. **Welcome Screen** - If no files available

**Examples:**
- **User selects "image1.jpg"** → Always displays "image1.jpg" (until changed)
- **New upload "image2.jpg"** → Still shows "image1.jpg" (selection takes priority)
- **User clears selection** → Shows "image2.jpg" (recent upload)
- **No recent uploads** → Shows most recent file in folder

**Startup Behavior:**
- **With startup timer** → Welcome screen → wait → priority file
- **Without startup timer** → Priority file immediately
- **`--display-file`** → Shows specified file AND sets it as selected

**Managing Storage:**
- Use `/list_files` to see all files in the watched folder (sorted by newest first)
- Use `/latest_file` to get info about the most recent file
- Use `/displayed_file` to get info about the currently displayed file (respects priority system)
- Use `/cleanup_old_files` to remove old files while keeping recent ones (recommended for long-term use)
- Use `/clear_screen` to clear the display without removing files

**Storage Management Example:**
```bash
# Keep only the 10 most recent files
curl -X POST http://192.168.1.100:5000/cleanup_old_files \
  -H "Content-Type: application/json" \
  -d '{"keep_count": 10}'

# Clear the display
curl -X POST http://192.168.1.100:5000/clear_screen

# Get info about currently displayed file (respects priority system)
curl http://192.168.1.100:5000/displayed_file

# Get info about most recent file (ignores priority system)
curl http://192.168.1.100:5000/latest_file
```

### Running Both Systems

To use TouchDesigner integration, you need to run both the display monitor and the upload server:

**Terminal 1 - Display Monitor:**
```bash
source eink_env/bin/activate
python display_latest.py
```

**Terminal 2 - Upload Server:**
```bash
source eink_env/bin/activate
python upload_server.py
```

The display monitor watches for files and shows them on the e-ink display. The upload server receives files from TouchDesigner and saves them to the watched folder, triggering the display to update.

**Alternative: Combined Runner Script**
```bash
# Use the combined runner for both services
source eink_env/bin/activate
python run_eink_system.py
```

**Alternative: Combined with initial file display**
```bash
# Start display monitor with server running in background
python display_latest.py -d ~/welcome.jpg &
python upload_server.py
```

**💡 Storage Management Tips:**
- Files accumulate over time, so consider periodic cleanup
- Use `/list_files` endpoint to monitor storage usage
- Set up automatic cleanup with `/cleanup_old_files` to maintain system performance
- Monitor disk space: `df -h ~/watched_files`

## 🌐 Web Management Interface

The system now includes a comprehensive web interface for managing your e-ink display remotely. This provides an intuitive way to upload files, browse your file gallery, and control the display from any device on your network.

### 🚀 Quick Start

1. **Start the web server:**
   ```bash
   # Use the combined system that runs both file monitoring and web server
   ./eink_control.sh
   ```

2. **Find your Pi's IP address:**
   ```bash
   # IP address is displayed on the e-ink screen on startup
   # Or check manually:
   hostname -I
   ```

3. **Access the web interface:**
   - **Default:** `http://YOUR_PI_IP:5000`
   - **Example:** `http://192.168.1.100:5000`
   - **Optional:** Set up nginx for cleaner URLs (see [Nginx Setup](#nginx-reverse-proxy-setup-optional))

### ✨ Web Interface Features

#### **📤 File Upload**
- **Drag & Drop**: Simply drag files from your computer to the upload area
- **Click to Browse**: Traditional file picker with multi-select support
- **Real-time Progress**: Upload progress bar with file-by-file status
- **Auto Display**: Uploaded files automatically appear on the e-ink display
- **Supported Formats**: Images (jpg, png, bmp, gif), text files, PDFs, and more

#### **🖼️ File Gallery**
- **Visual Grid**: Thumbnail previews for images, icons for other file types
- **File Information**: Name, size, and modification date for each file
- **Newest First**: Files sorted by upload time (most recent first)
- **Click to Display**: Click any file to instantly show it on the e-ink display
- **Smart Thumbnails**: Automatic generation and caching of image previews

#### **🔧 File Management**
- **Individual Actions**: Display or delete files with confirmation dialogs
- **Bulk Operations**: Select multiple files for batch deletion
- **Selection Mode**: Toggle multi-select mode for bulk operations
- **Smart Cleanup**: Automatic cleanup options to manage storage

#### **⚡ System Controls**
- **Clear Display**: Clear the e-ink screen without deleting files
- **Settings Panel**: Configure image processing, auto-display, and thumbnail quality
- **Clean Folder**: Remove all files from the watched folder (with confirmation)
- **Refresh Files**: Reload the file gallery to see updates

#### **⚙️ Settings Configuration**
- **Image Processing Mode**: Choose between center-crop (fill display) or letterbox (show all)
- **Auto-Display Uploads**: Enable/disable automatic display of uploaded files
- **Thumbnail Quality**: Adjust JPEG quality for image previews (50-95)
- **Persistent Settings**: All settings are saved and persist across restarts
- **Connection Status**: Live status indicator showing server connectivity

#### **📱 Responsive Design**
- **Mobile Optimized**: Works perfectly on phones and tablets
- **Touch Friendly**: Large buttons and easy touch navigation
- **Desktop Enhanced**: Full feature set on desktop browsers
- **Real-time Updates**: Live status indicators and notifications

### 🎨 User Interface Overview

The web interface consists of several main sections:

#### **Header**
- **E-ink Display Manager** title with status indicator
- **Connection Status**: Green (connected), yellow (connecting), red (error)
- **Live Status Updates**: Connection status checked every 30 seconds

#### **Upload Section**  
- **Large Drop Zone**: Drag files here or click to browse
- **Progress Indicator**: Upload progress with file count and status
- **File Type Support**: Visual indication of supported formats

#### **Control Panel**
- **Clear Display**: Blue button to clear the e-ink screen
- **Clean Folder**: Red button to delete all files (with confirmation)
- **Refresh Files**: Reload the file gallery
- **Selection Mode**: Toggle for bulk file operations

#### **File Gallery**
- **Grid Layout**: Visual cards showing file previews
- **File Cards**: Each card shows thumbnail/icon, name, size, date
- **Action Buttons**: "Display" and "Delete" buttons on each file
- **Empty State**: Helpful message when no files are present

#### **Bulk Operations**
- **Selection Controls**: Appear when files are selected
- **Multi-select**: Checkboxes appear in selection mode
- **Batch Actions**: Delete selected files with confirmation

### 🔗 API Endpoints

The web interface uses these API endpoints (also available for external integration):

| Endpoint | Method | Purpose | Parameters |
|----------|---------|---------|------------|
| `/` | GET | Web interface homepage | None |
| `/api/files` | GET | Enhanced file listing with thumbnails | None |
| `/display_file` | POST | Display specific file on e-ink | `{"filename": "file.jpg"}` |
| `/delete_file` | POST | Delete specific file | `{"filename": "file.jpg"}` |
| `/delete_multiple` | POST | Delete multiple files | `{"filenames": ["file1.jpg", "file2.txt"]}` |
| `/thumbnails/<filename>` | GET | Serve thumbnail images | None |
| `/files/<filename>` | GET | Serve original files | None |

### 🛠️ Technical Details

#### **File Structure**
```
RpiEinky/
├── upload_server.py           # Enhanced Flask server with web UI
├── templates/
│   └── index.html            # Main web interface template
├── static/
│   ├── css/
│   │   └── style.css         # Modern responsive styles  
│   └── js/
│       └── app.js            # Complete JavaScript functionality
└── ~/watched_files/
    └── .thumbnails/          # Auto-generated thumbnails (hidden folder)
```

#### **Thumbnail Generation**
- **Automatic**: Thumbnails generated on upload for images
- **Cached**: Thumbnails stored in `.thumbnails/` folder
- **Smart Sizing**: Max 200x200px, maintains aspect ratio
- **Format**: JPEG format for consistent browser compatibility
- **Background**: White background for transparent PNGs

#### **Storage Management**
- **Persistent Files**: Uploaded files remain until manually deleted
- **Thumbnail Cleanup**: Thumbnails automatically removed when files deleted
- **Bulk Operations**: Multi-select for efficient file management
- **Storage Monitoring**: File count and size information in interface

### 🎯 Usage Examples

#### **Upload and Display Workflow**
1. Open web interface: `http://192.168.1.100:5000`
2. Drag an image file to the upload area
3. Watch upload progress and automatic display on e-ink
4. File appears in gallery for future re-display

#### **File Management Workflow**
1. Browse file gallery to see all uploaded files
2. Click "Display" on any file to show it on e-ink
3. Use selection mode to select multiple old files
4. Delete selected files to free up storage space

#### **Mobile Usage**
1. Access same URL from phone/tablet browser
2. Touch-friendly interface with large buttons
3. Drag & drop works on mobile browsers
4. Full functionality available on all screen sizes

### 🔧 Web Interface Configuration

#### **Access Method Options**
- **Default (Port-based):** `http://PI_IP:5000` - Use `./eink_control.sh`
- **Nginx (Path-based):** `http://PI_IP/eink/` - Use `./eink_control_nginx.sh` (see [Nginx Setup](#nginx-reverse-proxy-setup-optional))

#### **Change Web Server Port**
Edit `upload_server.py`:
```python
app.run(host='0.0.0.0', port=5000, debug=False)  # Change port here
```

#### **Configure Default Settings**
Edit the `DEFAULT_SETTINGS` in `upload_server.py`:
```python
DEFAULT_SETTINGS = {
    'image_crop_mode': 'center_crop',  # 'center_crop' or 'fit_with_letterbox'
    'auto_display_upload': True,       # Automatically display uploaded files
    'thumbnail_quality': 85,           # JPEG quality for thumbnails
    'max_file_size_mb': 16            # Maximum file size in MB
}
```

#### **Customize Upload Limits**
Edit `upload_server.py`:
```python
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
```

#### **Enable Debug Mode**
For development only:
```python
app.run(host='0.0.0.0', port=5000, debug=True)  # Enable debug mode
```

### 🐛 Web Interface Troubleshooting

#### **Cannot Access Web Interface**
```bash
# Check if server is running
curl http://localhost:5000/status

# Check Pi's IP address
hostname -I

# Test from Pi browser
curl http://127.0.0.1:5000

# Check firewall (usually not needed on local network)
sudo ufw status
```

#### **Uploads Fail**
```bash
# Check file permissions on watched folder
ls -la ~/watched_files/
chmod 755 ~/watched_files/

# Check disk space
df -h ~/watched_files/

# Check server logs
./eink_control.sh status  # Check service status
```

#### **Thumbnails Not Showing**
```bash
# Check thumbnail folder exists and is writable
ls -la ~/watched_files/.thumbnails/
chmod 755 ~/watched_files/.thumbnails/

# Check PIL/Pillow installation
source eink_env/bin/activate
python -c "from PIL import Image; print('PIL OK')"

# Manually test thumbnail generation
python -c "
from upload_server import generate_thumbnail
result = generate_thumbnail('/path/to/image.jpg', 'image.jpg')
print(f'Thumbnail: {result}')
"
```

#### **Web Interface Slow**
```bash
# Check system resources
top
free -h

# Reduce thumbnail quality in upload_server.py
# Change: img.save(thumb_path, 'JPEG', quality=85)
# To: img.save(thumb_path, 'JPEG', quality=70)
```

### 🐛 Settings & Auto-Display Troubleshooting

**Auto-display not working:**
```bash
# Check if auto-display is enabled in settings
cat ~/.config/rpi-einky/settings.json

# Check display monitor logs for auto-display messages
# Look for: "Auto-displayed file:" or "Auto-display disabled"
```

**Settings not saving:**
```bash
# Check settings file permissions
ls -la ~/.config/rpi-einky/settings.json

# Check if settings file exists
cat ~/.config/rpi-einky/settings.json
```

**Image processing issues:**
```bash
# Verify crop mode setting
grep "image_crop_mode" ~/.config/rpi-einky/settings.json

# Check display logs for crop mode messages
# Look for: "Center-cropped image" or "Letterboxed image"
```

## 🔧 Configuration

### Change Monitored Folder

Use the `--folder` or `-f` command line argument:
```bash
python display_latest.py --folder ~/my_custom_folder
python display_latest.py -f ~/Desktop/display_files
```

Or edit the default in `display_latest.py`:
```python
parser.add_argument('--folder', '-f', default='~/your_custom_folder', ...)
```

**Note:** The folder path always uses `~` to ensure it's relative to your home directory, regardless of where you run the script from.

### Display Orientation

The system supports 4 different orientation modes for flexible mounting options:

#### **🔄 Orientation Options:**
- **`landscape`** - Normal horizontal orientation (default)
- **`landscape_upside_down`** - Horizontal upside-down
- **`portrait`** - Vertical orientation (rotated 90° clockwise)
- **`portrait_upside_down`** - Vertical upside-down (rotated 270° clockwise)

#### **💻 Command Line Usage:**
```bash
# Default: landscape (normal)
python display_latest.py

# Normal landscape
python display_latest.py --orientation landscape

# Portrait mode (vertical mounting)
python display_latest.py --orientation portrait

# Portrait upside-down
python display_latest.py --orientation portrait_upside_down
```

#### **🌐 Web Interface:**
The orientation can also be set via the web interface in the **Display Settings** section.

#### **🎯 Use Cases:**
- **Landscape modes**: Traditional horizontal mounting
- **Portrait modes**: Vertical mounting (e.g., wall-mounted displays, narrow spaces)
- **Upside-down variants**: For different mounting orientations

#### **✅ Benefits:**
- **Flexible mounting**: Mount the display in any orientation
- **Efficient rotation**: Uses PIL rotation for smooth image transformation
- **Consistent behavior**: All content types (images, text, errors) properly oriented
- **Easy configuration**: Change via command line or web interface

### Screen Clearing Behavior

Control when the screen is cleared:
```bash
# Clear screen on startup (useful for clean start)
python display_latest.py --clear-start

# Don't clear screen on exit (leave last image visible)
python display_latest.py --no-clear-exit

# Both: clear on start, leave content on exit
python display_latest.py --clear-start --no-clear-exit
```

### Display Initial File

Display a specific file immediately on startup:
```bash
# Show welcome image, then monitor for new files
python display_latest.py --display-file ~/Pictures/welcome.jpg

# Show status text, then monitor
python display_latest.py -d ~/status.txt
```

### Customize Display Settings

For advanced customization, modify font sizes, colors, or layout in the `EinkDisplayHandler` class:
```python
self.font_small = ImageFont.truetype(font_path, 12)
self.font_medium = ImageFont.truetype(font_path, 16)
self.font_large = ImageFont.truetype(font_path, 20)
```

## 📁 File Structure

```
RpiEinky/
├── display_latest.py              # Main monitoring system with IP display
├── upload_server.py               # Enhanced Flask server with web UI
├── run_eink_system.py             # Combined runner for both services
├── clear_display.py               # Simple script to clear the display
├── show_ip.py                     # Standalone IP address display script
├── restart_eink_system.sh         # Clean restart script (no reboot needed)
├── manage_eink_system.sh          # Comprehensive management script
├── eink_control.sh                # Smart control script (auto-restart)
├── eink_control_nginx.sh          # Nginx-compatible control script
├── activate_env.sh                # Foolproof venv activation script
├── setup_nginx.sh                 # Nginx reverse proxy setup script (optional)
├── eink-display.service           # Systemd service file for auto-start
├── setup_startup.sh               # Automated setup script for auto-start
└── ~/.config/rpi-einky/          # Application configuration directory
    ├── settings.json              # Web interface settings (auto-generated)
    └── commands/                  # Command files for display control
├── test_display_system.py         # Test file generator
├── test_upload_server.py          # Upload server test script
├── templates/                     # Web interface templates
│   └── index.html                # Main web interface
├── static/                        # Web interface static files
│   ├── css/
│   │   └── style.css             # Modern responsive styles
│   └── js/
│       └── app.js                # Complete JavaScript functionality
├── requirements.txt               # Python dependencies
├── README.md                      # This documentation
└── ~/watched_files/               # Monitored folder (in home directory)
    └── .thumbnails/              # Auto-generated thumbnails (hidden)
```

## 🐛 Troubleshooting

### Virtual Environment Issues

**Problem:** `bash: eink_env/bin/activate: No such file or directory`

**Solution:** Clean start approach:
```bash
rm -rf eink_env
sudo apt install python3-venv
python3 -m venv eink_env
source eink_env/bin/activate
pip install -r requirements.txt
```

### Package Installation Issues

**Problem:** `externally-managed-environment` error

**Solution:** Always use virtual environment (see installation steps above)

### SPI Module Issues

**Problem:** `ModuleNotFoundError: No module named 'spidev'`

**Solution:** Install spidev and enable SPI:
```bash
# Install spidev in virtual environment
source eink_env/bin/activate
pip install spidev

# Enable SPI interface
sudo raspi-config nonint do_spi 0
# Or manually: sudo raspi-config → Interface Options → SPI → Enable

# Reboot to apply SPI changes
sudo reboot
```

### Display Type Issues

**Problem:** Display not working after switching display types

**Solution:** Check display configuration and restart system:
```bash
# Check current config
cat ~/watched_files/.epd_config.json

# Update to correct display type
echo '{"display_type": "epd7in3e"}' > ~/watched_files/.epd_config.json

# Restart the system
./restart_eink_system.sh
```

**Problem:** Images appear rotated or incorrectly sized

**Solution:** The system automatically handles orientation - verify correct display type:
```bash
# For 2.15" grayscale display (portrait native)
echo '{"display_type": "epd2in15g"}' > ~/watched_files/.epd_config.json

# For 7.3" color display (landscape native)  
echo '{"display_type": "epd7in3e"}' > ~/watched_files/.epd_config.json

# For 13.3" color display (portrait native)
echo '{"display_type": "epd13in3E"}' > ~/watched_files/.epd_config.json
```

### GPIO Module Issues

**Problem:** `ModuleNotFoundError: No module named 'gpiozero'`

**Solution:** Install gpiozero:
```bash
# Install gpiozero in virtual environment
source eink_env/bin/activate
pip install gpiozero

# Or install all missing dependencies at once:
pip install -r requirements.txt
```

### GPIO Pin Factory Issues

**Problem:** `PinFactoryFallback` warnings or `OSError: [Errno 22] Invalid argument`

**Solution:** Install RPi.GPIO:
```bash
# Install RPi.GPIO (the standard GPIO library for Raspberry Pi)
source eink_env/bin/activate
pip install RPi.GPIO

# Make sure you're running as root or in the gpio group
sudo usermod -a -G gpio $USER
# Log out and back in for group changes to take effect

# Or run your script with sudo (not recommended for development)
sudo python display_latest.py
```

### GPIO Edge Detection Issues

**Problem:** `RuntimeError: Failed to add edge detection` or `No module named 'lgpio'`

**Solution:** Install lgpio and fix permissions:
```bash
# Install lgpio (modern GPIO library)
source eink_env/bin/activate
pip install lgpio

# Add user to gpio group
sudo usermod -a -G gpio $USER

# Reboot to apply changes
sudo reboot

# Test after reboot
python -c 'from waveshare_epd import epd2in15g; print("Success!")'
```

**Alternative:** Run with sudo temporarily:
```bash
sudo /home/danrasp/eink_env/bin/python display_latest.py
```

### Waveshare Library Issues

**Problem:** `ModuleNotFoundError: No module named 'waveshare_epd'`

**Solution:** Install the Waveshare library:
```bash
# Make sure you have the Waveshare files (choose one):
# Option A: Download specific files
wget https://files.waveshare.com/wiki/common/2in15_e-Paper_G.zip
unzip 2in15_e-Paper_G.zip -d 2in15_e-Paper_G
# Option B: Clone full repo
git clone https://github.com/waveshare/e-Paper.git

# Install into virtual environment
source eink_env/bin/activate
# For downloaded files (Option A):
cp -r 2in15_e-Paper_G/RaspberryPi_JetsonNano/python/lib/waveshare_epd eink_env/lib/python3.*/site-packages/
# For cloned repo (Option B):
cp -r e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd eink_env/lib/python3.*/site-packages/

# Test it works
python -c "from waveshare_epd import epd2in15g; print('Success!')"
```

### Display Not Working

**Problem:** Display shows nothing or errors

**Solutions:**
1. Check wiring connections
2. Verify Waveshare library is installed correctly (see above)
3. Check that SPI is enabled: `sudo raspi-config` → Interface Options → SPI
4. Run the original test: `python epd_2in15g_test.py`

### PDF Support Issues

**Problem:** PDFs show as file info instead of content

**Solution:** Install PDF dependencies:
```bash
sudo apt install poppler-utils
pip install pdf2image
```

### Permission Issues

**Problem:** Cannot create/access files

**Solution:** Check folder permissions:
```bash
chmod 755 ~/watched_files
```

### Storage Management Issues

**Problem:** Too many files accumulating in watched folder

**Solution:** Use the cleanup endpoint or manually manage files:
```bash
# Check current files
curl http://192.168.1.100:5000/list_files

# Keep only 10 most recent files
curl -X POST http://192.168.1.100:5000/cleanup_old_files \
  -H "Content-Type: application/json" \
  -d '{"keep_count": 10}'

# Or manually check disk usage
du -sh ~/watched_files
ls -la ~/watched_files | wc -l  # Count files
```

**Problem:** Need to remove all files

**Solution:** Manual cleanup (use carefully):
```bash
# Remove all files in watched folder
rm -f ~/watched_files/*

# Or use the clear display script
python clear_display.py
```

### Auto-Start Service Issues

**Problem:** Service fails to start with "203 error code"

**Solution:** This usually means the virtual environment path is wrong:
```bash
# Check if virtual environment exists at the path in service file
ls -la /home/your_username/eink_env/bin/python

# If it doesn't exist, either:
# 1. Run the setup script again (it auto-detects the correct path)
./setup_startup.sh

# 2. Or manually fix the service file
sudo nano /etc/systemd/system/eink-display.service
# Update ExecStart line to use correct path to your virtual environment
```

**Problem:** Service fails to start on boot

**Solution:** Check service status and logs:
```bash
# Check service status
sudo systemctl status eink-display.service

# View service logs
sudo journalctl -u eink-display.service -f

# Check if paths are correct in service file
sudo nano /etc/systemd/system/eink-display.service
```

**Problem:** Service starts but display doesn't work

**Solution:** Check permissions and hardware access:
```bash
# Make sure user has GPIO access
sudo usermod -a -G gpio,spi,i2c,dialout your_username

# Check if SPI is enabled
sudo raspi-config nonint do_spi 0

# Test hardware access manually
source ~/eink_env/bin/activate  # or ./eink_env/bin/activate
python -c "from waveshare_epd import epd2in15g; epd = epd2in15g.EPD(); print('Hardware OK')"

# Restart service after changes
sudo systemctl restart eink-display.service
```

**Problem:** Service receives files but doesn't display them

**Solution:** Check hardware permissions and environment:
```bash
# The service needs proper hardware group membership
sudo usermod -a -G gpio,spi,i2c,dialout your_username

# Reboot to apply group changes
sudo reboot

# Check service logs for hardware access errors
sudo journalctl -u eink-display.service -f
```

## 📋 Dependencies

### Python Packages (installed via pip)
- `watchdog==3.0.0` - File system monitoring
- `Pillow==10.0.0` - Image processing and thumbnail generation
- `pdf2image==1.16.3` - PDF rendering (optional)
- `spidev==3.5` - SPI communication for e-ink display
- `gpiozero==1.6.2` - GPIO control for Raspberry Pi
- `RPi.GPIO==0.7.1` - GPIO library for Raspberry Pi
- `lgpio==0.2.2.0` - Modern GPIO library for Raspberry Pi
- `Flask==2.3.3` - Web server for web interface and TouchDesigner integration
- `requests==2.31.0` - HTTP client for testing and advanced features

### System Packages (installed via apt)
- `python3-venv` - Virtual environment support
- `poppler-utils` - PDF processing utilities

### Hardware Library
- Waveshare e-Paper library (from their GitHub)

### TouchDesigner Requirements
- TouchDesigner (any recent version)
- Network connection between TouchDesigner computer and Raspberry Pi

## 📝 Examples

### Common Usage Patterns

```bash
# Start the complete system with web interface (RECOMMENDED)
./eink_control.sh                    # Default: access at :5000
./eink_control_nginx.sh              # Optional: nginx setup for /eink/ path

# Management scripts (no reboot needed)
./manage_eink_system.sh start        # Start the system
./manage_eink_system.sh restart      # Restart the system
./manage_eink_system.sh status       # Check status
./manage_eink_system.sh logs         # View logs
./manage_eink_system.sh follow       # Follow logs in real-time

# Clean restart without system reboot
./restart_eink_system.sh

# Show device IP address on e-ink display  
python display_latest.py --show-ip
python show_ip.py

# Basic monitoring with default settings
python display_latest.py

# Use specific display type (overrides config file)
python display_latest.py --display-type epd2in15g    # 2.15" grayscale display
python display_latest.py --display-type epd13in3E    # 13.3" color display  
python display_latest.py --display-type epd7in3e     # 7.3" color display

# Show a welcome image immediately, then monitor for new files (also sets it as selected image)
python display_latest.py --display-file ~/Pictures/welcome.jpg

# Monitor a specific folder with clean start
python display_latest.py --folder ~/kiosk_files --clear-start

# Display in different orientations
python display_latest.py --orientation landscape
python display_latest.py --orientation portrait
python display_latest.py --orientation portrait_upside_down

# Control timing features
python display_latest.py --enable-startup-timer false  # Disable startup timer (show priority file immediately)
python display_latest.py --enable-refresh-timer false  # Disable refresh timer only
python display_latest.py --startup-delay 5       # 5-minute startup delay (welcome screen → wait 5 min → priority file)
python display_latest.py --refresh-interval 12   # 12-hour refresh interval

# Control manufacturer requirements and sleep mode
python display_latest.py --enable-manufacturer-timing  # Enable 180s minimum refresh
python display_latest.py --disable-sleep-mode         # Disable sleep mode (faster)

# Full featured: custom folder, initial file, controlled clearing, timing
python display_latest.py -f ~/display_queue -d ~/status.txt --clear-start --no-clear-exit --orientation portrait --startup-delay 2 --refresh-interval 6 --enable-startup-timer false --enable-manufacturer-timing

# Just clear the display
python clear_display.py

# Complete example with all timing options
python display_latest.py \
  --folder ~/my_display_files \
  --display-file ~/welcome.jpg \
  --clear-start \
  --no-clear-exit \
  --orientation portrait \
  --enable-startup-timer false \
  --refresh-interval 12 \
  --enable-manufacturer-timing \
  --disable-sleep-mode

### Display Type Switching

```bash
# Change display type by updating config file
echo '{"display_type": "epd7in3e"}' > ~/watched_files/.epd_config.json

# Or use command line override (temporary)
python display_latest.py --display-type epd7in3e

# System will automatically:
# - Handle orientation differences (portrait vs landscape native)  
# - Adjust image processing for different resolutions
# - Use appropriate color palettes (grayscale vs 7-color)
# - Maintain consistent landscape UI experience
```

### Web Interface Examples

```bash
# Default access (port-based)
http://192.168.1.100:5000

# Optional nginx access (cleaner URLs)
http://192.168.1.100/eink/

# Pi services homepage (with nginx setup)
http://192.168.1.100/

# Upload file via web interface (drag & drop or click to browse)
# Files automatically display on e-ink and appear in gallery

# Display any previous file via web interface
# Click "Display" button on any file in the gallery

# Configure settings via web interface
# Click "Settings" button to adjust image processing and auto-display

# Delete old files via web interface  
# Use selection mode to select multiple files, then delete

# System management via web interface
# Use "Clear Display" and "Clean Folder" buttons
```

### Adding Different File Types

```bash
# Add a text file (always uses ~ for home directory)
echo "Hello E-Ink World!" > ~/watched_files/greeting.txt

# Add an image  
cp /path/to/image.jpg ~/watched_files/

# Add a Python script
cp script.py ~/watched_files/

# Add a PDF
cp document.pdf ~/watched_files/
```

### Advanced Examples

```bash
# Kiosk mode: Show welcome screen, monitor specific folder, leave content on exit
python display_latest.py \
  --display-file ~/kiosk/welcome.jpg \
  --folder ~/kiosk/queue \
  --no-clear-exit

# Status display: Clear screen, show status, monitor for updates
python display_latest.py \
  --clear-start \
  --display-file ~/status/current.txt \
  --folder ~/status/updates

# Photo frame: Normal orientation, show default photo, monitor photos folder
python display_latest.py \
  --orientation landscape \
  --display-file ~/photos/default.jpg \
  --folder ~/photos/new \
  --no-clear-exit
```

### Viewing Logs

```bash
# Real-time logs (manual run)
python display_latest.py

# Management script logs
./manage_eink_system.sh logs         # View recent logs
./manage_eink_system.sh follow       # Follow logs in real-time

# System service logs
sudo journalctl -u eink-display.service -f

# Service status
sudo systemctl status eink-display.service

# Check specific log files
tail -f ~/RpiEinky/logs/display.log  # Display monitor logs
tail -f ~/RpiEinky/logs/server.log   # Upload server logs
```

## 🌐 Raspberry Network Setup (Optional)

Setting a static IP address is recommended for the TouchDesigner integration and remote access to your e-ink display system.

### Method 1: Using nmcli (Recommended for Raspberry Pi OS Lite)

NetworkManager's command line interface is the modern way to configure network settings on Raspberry Pi OS Lite.

1. **Check current connection:**
   ```bash
   # List all network connections
   nmcli connection show
   
   # Check current IP configuration
   ip addr show
   ```

2. **Set static IP using nmcli:**
   ```bash
   # Replace 'preconfigured' with your connection name from step 1
   # Replace IP addresses with your desired static IP and network settings
   sudo nmcli con mod preconfigured ipv4.addresses 192.168.1.100/24
   sudo nmcli con mod preconfigured ipv4.gateway 192.168.1.1
   sudo nmcli con mod preconfigured ipv4.dns "192.168.1.1,8.8.8.8"
   sudo nmcli con mod preconfigured ipv4.method manual
   
   # Apply changes
   sudo nmcli con down preconfigured && sudo nmcli con up preconfigured
   ```

3. **Verify the configuration:**
   ```bash
   ip addr show
   ping google.com
   ```

### Method 2: Using dhcpcd.conf (Traditional Method)

This method works on all Raspberry Pi OS versions:

1. **Edit the dhcpcd configuration:**
   ```bash
   sudo nano /etc/dhcpcd.conf
   ```

2. **Add static IP configuration at the end of the file:**
   ```bash
   # Static IP configuration for eth0 (Ethernet)
   interface eth0
   static ip_address=192.168.1.100/24
   static routers=192.168.1.1
   static domain_name_servers=192.168.1.1 8.8.8.8
   
   # For WiFi, use wlan0 instead:
   # interface wlan0
   # static ip_address=192.168.1.100/24
   # static routers=192.168.1.1
   # static domain_name_servers=192.168.1.1 8.8.8.8
   ```

3. **Restart networking:**
   ```bash
   sudo systemctl restart dhcpcd
   # Or reboot
   sudo reboot
   ```

### Method 3: Using raspi-config (GUI Method)

For a user-friendly approach:

1. **Open Raspberry Pi configuration:**
   ```bash
   sudo raspi-config
   ```

2. **Navigate to network settings:**
   - Select "Advanced Options"
   - Select "Network Config"
   - Choose your preferred network configuration method

### Network Configuration Tips

**Finding your network settings:**
```bash
# Find your current gateway (router IP)
ip route | grep default

# Find your current DNS servers
cat /etc/resolv.conf

# Find available network interfaces
ip link show
```

**Common network ranges:**
- `192.168.1.x/24` (gateway: 192.168.1.1)
- `192.168.0.x/24` (gateway: 192.168.0.1)
- `10.0.0.x/24` (gateway: 10.0.0.1)

**Recommended static IP setup for e-ink display:**
- **Static IP**: Choose an IP outside your router's DHCP range (e.g., 192.168.1.100)
- **Gateway**: Your router's IP (usually 192.168.1.1 or 192.168.0.1)
- **DNS**: Your router's IP + public DNS (8.8.8.8, 1.1.1.1)

**Why set a static IP?**
- **TouchDesigner integration**: Consistent IP for HTTP uploads
- **Remote access**: SSH and file management from other devices
- **Service reliability**: No IP changes after router reboots
- **Network troubleshooting**: Easier to remember and access

**Testing connectivity:**
```bash
# Test local network
ping 192.168.1.1

# Test internet
ping google.com

# Test DNS resolution
nslookup google.com
```

## 🐛 Troubleshooting

### Common Errors

#### **EPD7in3eAdapter Clear Method Error**
```
Error during cleanup: 'EPD7in3eAdapter' object has no attribute 'Clear'
```

**Cause**: The waveshare_epd library for epd7in3e uses lowercase `clear()` method, but some code expects uppercase `Clear()`.

**Solution**: The unified adapter system now handles both method names automatically. If you encounter this error:

1. **Update to latest version**: The fix is included in the current unified_epd_adapter.py
2. **Test the fix**: Run the test script to verify compatibility:
   ```bash
   python test_epd7in3e_fix.py
   ```
3. **Check your display type**: Ensure your config file has the correct display type:
   ```bash
   cat ~/watched_files/.epd_config.json
   ```

**Technical Details**: The adapter now tries both `Clear()` and `clear()` methods on the underlying display object, providing backward compatibility with different waveshare_epd library versions.

## 🤝 Contributing

Feel free to submit issues and pull requests to improve the system!

## ⚠️ Disclaimer

**HARDWARE DAMAGE DISCLAIMER**: This software is provided "as is" without warranty of any kind. The authors and contributors are not responsible for any damage to hardware, including but not limited to e-paper displays, Raspberry Pi devices, or any other electronic components. Users assume all risks associated with the use of this software.

**IMPORTANT SAFETY NOTES**:
- Always follow the manufacturer's wiring instructions for your specific display model
- Ensure proper power supply and voltage requirements are met
- Do not force connections or modify hardware without proper knowledge
- Test with low-risk operations before running intensive display operations
- Monitor display temperature and operation during extended use
- Follow e-paper display refresh timing guidelines to prevent damage

**MANUFACTURER TIMING**: The system includes optional manufacturer timing requirements (180-second minimum refresh intervals) to help prevent display damage. It is recommended to enable these features for long-term display health.

## 📄 License

MIT License - Feel free to use and modify as needed.