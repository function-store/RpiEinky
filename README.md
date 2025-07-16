# E-Ink File Display System

A Python system that monitors a folder for new files and automatically displays them on a Waveshare 2.15" e-paper display. Supports images, text files, PDFs, and more with intelligent formatting for e-ink displays.

## 🎯 Features

- **Real-time file monitoring** - Watches `~/watched_files` folder (or custom folder) for new files
- **Persistent file storage** - Files remain on Pi until explicitly cleaned up (latest file always displayed)
- **TouchDesigner integration** - HTTP upload server for remote file management
- **Command line interface** - Full control via command line arguments
- **Initial file display** - Show a specific file immediately on startup
- **Flexible screen control** - Choose when to clear screen (startup, exit, both, or never)
- **Multi-format support**:
  - **Images** (jpg, png, bmp, gif): Auto-resized and centered with filename
  - **Text files** (txt, md, py, js, html, css): Full content with word wrapping
  - **PDFs**: First page converted to image (requires pdf2image)
  - **Other files**: File information display (name, size, type, date)
- **4-color e-ink display** - Uses white, black, red, and yellow colors
- **Display orientation control** - Normal or upside-down orientation
- **Robust error handling** - Visual error messages on display
- **Clean shutdown** - Properly cleans display on exit (configurable)
- **File management API** - List files, get latest file info, cleanup old files

## 🛠️ Hardware Requirements

- Raspberry Pi (any model)
- Waveshare 2.15" e-paper display (4-color)
- Proper wiring as per Waveshare documentation

## 📦 Installation

> **📢 Update Notice**: The system now preserves uploaded files instead of deleting them. Files accumulate over time and the latest file is always displayed. Use the `/cleanup_old_files` endpoint to manage storage.

### Step 1: Install System Dependencies

```bash
sudo apt update
sudo apt install python3-venv poppler-utils

# Enable SPI interface (required for e-ink display)
sudo raspi-config
# Navigate to: Interface Options → SPI → Enable
# Or enable directly:
sudo raspi-config nonint do_spi 0
```

### Step 2: Get Waveshare e-Paper Library

**Option A: Download specific files (Recommended for 2.15" display)**
```bash
# Download the specific files for your display
wget https://files.waveshare.com/wiki/common/2in15_e-Paper_G.zip
unzip 2in15_e-Paper_G.zip -d 2in15_e-Paper_G
```
*Advantages: Smaller download, specific to your display model, includes tested examples*

**Option B: Clone full repository**
```bash
# Clone the complete Waveshare repository
git clone https://github.com/waveshare/e-Paper.git
```
*Advantages: All displays supported, latest updates, full documentation*

### Step 3: Set Up Virtual Environment and Install Libraries

```bash
# Clean start (recommended)
rm -rf eink_env
python3 -m venv eink_env
source eink_env/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Waveshare e-Paper library into virtual environment
# Choose the path based on which option you used in Step 2:

# If you downloaded specific files (Option A):
cp -r 2in15_e-Paper_G/RaspberryPi_JetsonNano/python/lib/waveshare_epd eink_env/lib/python3.*/site-packages/
cp -r 2in15_e-Paper_G/RaspberryPi_JetsonNano/python/pic ./

# OR if you cloned the full repo (Option B):
cp -r e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd eink_env/lib/python3.*/site-packages/
cp -r e-Paper/RaspberryPi_JetsonNano/python/pic ./

# Test that the library works
python -c "from waveshare_epd import epd2in15g; print('Waveshare library installed successfully!')"
```

### Step 4: Test Installation

```bash
# Start the monitor (in one terminal)
source eink_env/bin/activate
python display_latest.py

# Create test files (in another terminal)
source eink_env/bin/activate
python test_display_system.py
```

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
python display_latest.py --normal-orientation    # Normal (not upside-down)

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
| `--normal-orientation` | - | Display in normal orientation (not upside-down) | False |
| `--help` | `-h` | Show help message and exit | - |

### Supported File Types

| Type | Extensions | Display Method |
|------|------------|----------------|
| Images | `.jpg`, `.png`, `.bmp`, `.gif` | Resized, centered, with filename |
| Text | `.txt`, `.md`, `.py`, `.js`, `.html`, `.css` | Full content, word-wrapped |
| PDFs | `.pdf` | First page as image (requires pdf2image) |
| Other | Any other extension | File information display |

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

| Endpoint | Method | Purpose | Data Format |
|----------|---------|---------|-------------|
| `/upload` | POST | Upload files | multipart/form-data |
| `/upload_text` | POST | Upload text content | JSON: `{"content": "text", "filename": "name.txt"}` |
| `/status` | GET | Server status | Returns JSON status |
| `/list_files` | GET | List all files in watched folder | No data |
| `/latest_file` | GET | Get info about most recent file | No data |
| `/cleanup_old_files` | POST | Remove old files, keep recent N files | JSON: `{"keep_count": 10}` |

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

**Managing Storage:**
- Use `/list_files` to see all files in the watched folder (sorted by newest first)
- Use `/latest_file` to get info about the currently displayed file
- Use `/cleanup_old_files` to remove old files while keeping recent ones (recommended for long-term use)

**Storage Management Example:**
```bash
# Keep only the 10 most recent files
curl -X POST http://192.168.1.100:5000/cleanup_old_files \
  -H "Content-Type: application/json" \
  -d '{"keep_count": 10}'
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

Use the `--normal-orientation` command line argument:
```bash
# Default: upside-down orientation
python display_latest.py

# Normal orientation (not upside-down)
python display_latest.py --normal-orientation
```

**Benefits of the orientation system:**
- ✅ **Efficient** - Uses simple PIL rotation instead of complex buffer manipulation
- ✅ **Consistent** - All content (text, images, errors) automatically oriented correctly
- ✅ **Reliable** - Simple rotation that works across all content types
- ✅ **Command-line controlled** - Easy to change without editing code

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
├── display_latest.py              # Main monitoring system
├── upload_server.py               # HTTP upload server for TouchDesigner
├── test_display_system.py         # Test file generator
├── test_upload_server.py          # Upload server test script
├── touchdesigner_eink_script.py   # TouchDesigner project builder
├── EinkDisplay_TouchDesigner.toe  # TouchDesigner project template
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── ~/watched_files/               # Monitored folder (in home directory, created automatically)
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
```

## 📋 Dependencies

### Python Packages (installed via pip)
- `watchdog==3.0.0` - File system monitoring
- `Pillow==10.0.0` - Image processing
- `pdf2image==1.16.3` - PDF rendering (optional)
- `spidev==3.5` - SPI communication for e-ink display
- `gpiozero==1.6.2` - GPIO control for Raspberry Pi
- `RPi.GPIO==0.7.1` - GPIO library for Raspberry Pi
- `lgpio==0.2.2.0` - Modern GPIO library for Raspberry Pi
- `Flask==2.3.3` - Web server for TouchDesigner integration
- `requests==2.31.0` - HTTP client for testing and advanced features

### System Packages (installed via apt)
- `python3-venv` - Virtual environment support
- `poppler-utils` - PDF processing utilities

### Hardware Library
- Waveshare e-Paper library (from their GitHub)

### TouchDesigner Requirements
- TouchDesigner (any recent version)
- Network connection between TouchDesigner computer and Raspberry Pi

## 🔄 Auto-Start (Optional)

To run automatically on boot, create a systemd service:

```bash
sudo nano /etc/systemd/system/eink-display.service
```

Add (customize the ExecStart line with your desired options):
```ini
[Unit]
Description=E-Ink File Display System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/RpiEinky
# Basic usage:
ExecStart=/home/pi/RpiEinky/eink_env/bin/python display_latest.py
# Or with custom options:
# ExecStart=/home/pi/RpiEinky/eink_env/bin/python display_latest.py --display-file /home/pi/welcome.jpg --no-clear-exit
Restart=always

[Install]
WantedBy=multi-user.target
```

**Example service configurations:**

```ini
# Kiosk mode: Show welcome screen, don't clear on exit
ExecStart=/home/pi/RpiEinky/eink_env/bin/python display_latest.py --display-file /home/pi/kiosk/welcome.jpg --no-clear-exit

# Status display: Clear on start, show status file
ExecStart=/home/pi/RpiEinky/eink_env/bin/python display_latest.py --clear-start --display-file /home/pi/status.txt

# Photo frame: Normal orientation, show default photo
ExecStart=/home/pi/RpiEinky/eink_env/bin/python display_latest.py --normal-orientation --display-file /home/pi/photos/default.jpg --no-clear-exit
```

Enable and start:
```bash
sudo systemctl enable eink-display.service
sudo systemctl start eink-display.service
```

## 📝 Examples

### Common Usage Patterns

```bash
# Basic monitoring with default settings
python display_latest.py

# Show a welcome image immediately, then monitor for new files
python display_latest.py --display-file ~/Pictures/welcome.jpg

# Monitor a specific folder with clean start
python display_latest.py --folder ~/kiosk_files --clear-start

# Display in normal orientation, don't clear on exit
python display_latest.py --normal-orientation --no-clear-exit

# Full featured: custom folder, initial file, controlled clearing
python display_latest.py -f ~/display_queue -d ~/status.txt --clear-start --no-clear-exit
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
  --normal-orientation \
  --display-file ~/photos/default.jpg \
  --folder ~/photos/new \
  --no-clear-exit
```

### Viewing Logs

```bash
# Real-time logs
python display_latest.py

# System service logs
sudo journalctl -u eink-display.service -f
```

## 🤝 Contributing

Feel free to submit issues and pull requests to improve the system!

## 📄 License

MIT License - Feel free to use and modify as needed.