# E-Ink Managed File Display System

A comprehensive e-ink display management system designed for [Raspberry Pi](https://www.raspberrypi.com/) with web interface supporting multiple [WaveShare](https://www.waveshare.com/) e-paper displays. Features drag-and-drop uploads, file gallery, and remote management.

![E-Ink Display System](https://github.com/function-store/RpiEinky/raw/main/docs/header.jpg)

## Table of Contents

- [Purpose](#purpose)
- [Features](#features)
- [Installation](#installation)
- [TouchDesigner Integration](#touchdesigner-integration)
- [Architecture](#architecture)
- [Command Line Arguments](#command-line-arguments)
- [Web Server API](#web-server-api)
- [Services](#services)
- [Extending Display Support](#extending-display-support)
- [Troubleshooting](#troubleshooting)
- [Dependencies](#dependencies)
- [Raspberry Pi Resources](#raspberry-pi-resources)
- [License](#license)

## Purpose

- **Real-time file monitoring** - Watches `~/watched_files` folder for new files
- **Web management interface** - Modern responsive UI for remote file uploads and management
- **Multi-display support** - Supports 4-color grayscale and 7-color displays with automatic orientation handling (see )
- **TouchDesigner integration** - HTTP upload client for remote file management
- **Auto-startup service** - Run automatically on system boot with systemd

### Supported Devices

#### WaveShare

- **epd2in15g** - 2.15" grayscale (160×296, portrait native) - [link](https://www.waveshare.com/2.15inch-e-paper-hat-plus-g.htm)
- **epd7in3e** - 7.3" 7-color (800×480, landscape native) - [link](https://www.waveshare.com/7.3inch-e-paper-hat-e.htm)
- **epd13in3E** - 13.3" 7-color (1200×1600, portrait native) - [link](https://www.waveshare.com/13.3inch-e-paper-hat-plus-e.htm)

> See [Extending Display Support](#extending-display-support) for instructions how to integrate other models to the unified controller interface!

#### Raspberry Pi

Tested with [Raspberryi Pi Zero](https://www.raspberrypi.com/products/raspberry-pi-zero/) and [Raspberry Pi 5](https://www.raspberrypi.com/products/raspberry-pi-5/), should work with all models!

## Features

### Web Interface
- **Drag & Drop Uploads** - Simply drag files from your computer to upload
- **File Gallery** - Browse all uploaded files with thumbnails
- **One-Click Display** - Click any file to display it immediately on the e-ink screen
- **File Management** - Delete individual files or multiple files at once
- **Responsive Design** - Works on desktop, tablet, and mobile devices
- **Network Access** - Access from any device on your local network (TODO remote network)

### Display Capabilities
- **Multiple File Types** - Images (JPG, PNG, BMP), text files, PDFs, and more
- **Auto-Resizing** - Images automatically resize to fit your display
- **Text Rendering** - Text files display with proper word wrapping
- **PDF Support** - First page of PDFs rendered as images
- **Orientation Handling** - Automatic portrait/landscape adjustment

### TouchDesigner Integration
- **Direct Upload** - Send images directly from TouchDesigner
- **Component Library** - Reusable TouchDesigner components included

## Installation

> **⚠️ Installation Disclaimer**: This system is designed for Raspberry Pi. Installation steps may vary based on your specific e-paper display model and Raspberry Pi model. The Waveshare library structure, file locations, and import names can differ between display models and library versions.
> **‼️IMPORTANT**: Always refer to your display's specific documentation and adjust paths and procedures accordingly.

### 0. Directory

After downloading or cloning this repository make soure you are inside the folder for the installation and operation.

```bash
cd ~/RpiEinky
```

### 1. Install System Dependencies
```bash
sudo apt update
sudo apt install python3-venv poppler-utils
# Enable SPI
# ⚠️ IMPORTANT: hardware configuration steps may vary significantly depending on your specific Display Model, please consult manufacturer instructions! ⚠️
sudo raspi-config nonint do_spi 0  # Enable SPI interface
```

### 2. Get Waveshare e-Paper Library
```bash
# Clone full waveshare e-Paper repository
git clone https://github.com/waveshare/e-Paper.git
```

### 3. Set Up Virtual Environment
```bash
rm -rf eink_env
python3 -m venv eink_env
source eink_env/bin/activate
pip install -r requirements.txt

# Install Waveshare library (adjust paths based on your download)
cp -r e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd eink_env/lib/python3.*/site-packages/
cp -r e-Paper/RaspberryPi_JetsonNano/python/pic ./

# For 13.3" display, also install the separate program library
if [ -d "e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E" ]; then
    cp -r e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/* eink_env/lib/python3.*/site-packages/
    # Copy .so files to system library path for 13.3" display
    sudo cp e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/*.so /usr/local/lib/
    sudo ldconfig
    echo "Installed 13.3\" display library and shared objects"
fi

# Test installation
python -c "from waveshare_epd import epd2in15g; print('Success')"

# Test installation for 13.3" display
python -c "import epd13in3E; print('13.3\" display library Success')"
```

### 3.1. 13.3" Display Special Installation
If you're using the 13.3" display, you need to install wiringpi first:

```bash
# Install wiringpi (required for 13.3" display)
git clone https://github.com/WiringPi/WiringPi.git
cd WiringPi
./build

# Verify installation
ls -la /usr/local/lib/libwiringPi.so
gpio -v

# Copy 13.3" display .so files
cd ~/RpiEinky
sudo cp e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/*.so /usr/local/lib/
sudo ldconfig

# Test 13.3" display library
source eink_env/bin/activate
python -c "import epd13in3E; print('13.3\" display library Success')"
```

### 4. Configure Display Type
```bash
# Create display configuration
echo '{"display_type": "epd2in15g"}' > .epd_config.json
```
> Refer to the name used for your device's python import name found in the python libraries

### 5. Test Installation
```bash
source eink_env/bin/activate
python display_latest.py
```

### 6. Start the Complete System
After successful installation, start the full system with web interface:

```bash
# Start the complete system (display monitor + web server)
source eink_env/bin/activate
python run_eink_system.py
```

### 7. Access the Web Interface
Once running, access the web interface from any device on your network:

```bash
# Find your Raspberry Pi's IP address
hostname -I

# Access the web interface (replace with your Pi's IP)
http://192.168.1.100:5000
```

### 8. Upload and Display Files
- **Drag & Drop**: Simply drag files into the web interface
- **File Gallery**: Browse and manage uploaded files
- **Direct Display**: Click any file to display it immediately
- **TouchDesigner Integration**: Use the TouchDesigner component in the `td/modules/releases` folder

### 9. Set Up Auto-Start (Optional)
To run automatically on boot:

```bash
# Install as systemd services
chmod +x ~/RpiEinky/install_services.sh
~/RpiEinky/install_services.sh

# REQUIRED: Set up admin password and API key for authentication
python3 setup_admin_password.py

# The system will now start automatically on boot
```

**🔐 Authentication Required:** As of the latest version, the web interface requires authentication. You **must** run `python3 setup_admin_password.py` to set up admin credentials before accessing the web interface, even for local-only usage.

## TouchDesigner Integration

The `td` folder contains an example `.toe` file and `td/modules/release` a reusable `.tox` file to send images from TouchDesigner as well as manage the folder structure. For further configuration please refer to the `Settings` section of the web interface.

## Internet Access Setup

To access your E-ink display from anywhere on the internet with secure authentication:

**📖 See [INTERNET_SETUP_README.md](INTERNET_SETUP_README.md) for complete setup guide**

**🚀 Quick Start:**
```bash
# 1. Get a domain and add it to Cloudflare (free .tk domain works)
# 2. Run the setup (includes admin password creation)
./setup_internet_access.sh

# 3. Start the internet-enabled server
./start_internet_server.sh
```

**Result:** Secure access at `https://eink.yourdomain.com` with:
- **Admin login page** for web interface management
- **API key authentication** for TouchDesigner integration
- **Automatic HTTPS** and security hardening

### Authentication System

The internet-enabled version includes secure authentication:

**Web Interface:**
- **Login page** at `https://yourdomain.com/login`
- **Admin password** protection for all management functions
- **Session-based** authentication with secure cookies
- **Logout button** in the header

**TouchDesigner Integration:**
- **API key authentication** for automated uploads
- **Smart upload method**: Uses PUT locally, POST through tunnel
- **Automatic tunnel detection** for optimal compatibility
- **No login required** - use custom headers

**Password Management:**
```bash
# Set up or change admin password and API key
python3 setup_admin_password.py
```

**Note:** TouchDesigner uploads automatically work through both local network and internet tunnel with the same configuration.

## Architecture

### Core Components
- **`display_latest.py`** - Main monitoring system with file watching
- **`upload_server.py`** - Flask web server with web UI and API
- **`unified_epd_adapter.py`** - Display abstraction layer for multiple e-paper models
- **`run_eink_system.py`** - Combined runner for both services
- **`manage_eink_system.sh`** - Primary system management script with comprehensive control interface

### File Structure
```
RpiEinky/
├── display_latest.py              # Main monitoring system
├── upload_server.py               # Web server with UI
├── unified_epd_adapter.py        # Display abstraction layer
├── run_eink_system.py             # Combined runner
├── manage_eink_system.sh          # Primary system management script
├── clear_display.py               # Display clearing utility
├── templates/index.html           # Web interface template
├── static/                        # Web UI assets
├── requirements.txt               # Python dependencies
├── .epd_config.json              # Display configuration
└── ~/watched_files/              # Monitored folder
```

### Manufacturer Safety Features
The system includes optional manufacturer-recommended safety features to prevent display damage:

- **180-Second Minimum Refresh**: Enforces 3-minute minimum between display refreshes (manufacturer requirement)
- **Smart Queuing**: Rapid uploads are queued and displayed after timing allows
- **Automatic Retries**: Failed operations retry after minimum interval
- **Sleep Mode**: Puts display to sleep between operations for power efficiency and display health

**Enable safety features:**
```bash
python display_latest.py --enable-manufacturer-timing true --enable-sleep-mode true
```

### File Types Supported
- **Images**: jpg, png, bmp, gif (auto-resized)
- **Text**: txt, md, py, js, html, css (word-wrapped)
- **PDFs**: First page as image (requires pdf2image)
- **Other**: File information display

## Command Line Arguments

The `display_latest.py` screen management script supports several command line arguments for customization.

### Common Arguments

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--display-file` | `-d` | Display this file on startup | None |
| `--folder` | `-f` | Folder to monitor for new files | `~/watched_files` |
| `--clear-start` | - | Clear screen on startup | False |
| `--no-clear-exit` | - | Don't clear screen when exiting | False |
| `--orientation` | - | Display orientation | landscape |
| `--disable-startup-timer` | - | Disable startup display timer (true/false) | false |
| `--disable-refresh-timer` | - | Disable refresh timer (true/false) | false |
| `--startup-delay` | - | Minutes to wait before displaying priority file | 1 |
| `--refresh-interval` | - | Hours between display refreshes | 24 |
| `--enable-manufacturer-timing` | - | Enable 180s minimum refresh (true/false) | false |
| `--enable-sleep-mode` | - | Enable sleep mode (true/false) | true |
| `--display-type` | - | Specify display type | From config file |
| `--help` | `-h` | Show help message | - |

## Web Server API

### Core Endpoints
| Endpoint | Method | Purpose |
|----------|---------|---------|
| `/` | GET | Web interface homepage |
| `/api/files` | GET | File listing with thumbnails |
| `/display_file` | POST | Display specific file |
| `/delete_file` | POST | Delete specific file |
| `/delete_multiple` | POST | Delete multiple files |
| `/thumbnails/<filename>` | GET | Serve thumbnail images |
| `/files/<filename>` | GET | Serve original files |

### General API Endpoints
| Endpoint | Method | Purpose |
|----------|---------|---------|
| `/upload` | POST | Upload files (multipart/form-data) |
| `/upload_text` | POST | Upload text content (JSON) |
| `/status` | GET | Server status |
| `/list_files` | GET | List all files |
| `/latest_file` | GET | Get most recent file info |
| `/displayed_file` | GET | Get currently displayed file |
| `/cleanup_old_files` | POST | Remove old files |
| `/clear_screen` | POST | Clear e-ink display |

### Display Information API
```json
GET /display_info
{
  "display_type": "epd2in15g",
  "resolution": {"width": 250, "height": 122},
  "native_resolution": {"width": 122, "height": 250},
  "orientation": "landscape",
  "native_orientation": "portrait"
}
```

## Services

### Auto-Start Service Installation

The system includes flexible service installation that automatically adapts to your username and home directory.

#### Automatic Installation (Recommended)
```bash
# Make the installation script executable
chmod +x ~/RpiEinky/install_services.sh

# Run the installation script
~/RpiEinky/install_services.sh
```

The installation script will:
- Detect your current user and home directory
- Configure service files with the correct paths
- Install both display and upload services
- Enable services to start on boot
- Create logs directory if needed

#### Manual Installation
```bash
# Configure service files for your user
sed -e "s|\${USER}|$(whoami)|g" \
    -e "s|\${HOME}|$HOME|g" \
    -e "s|\${UID}|$(id -u)|g" \
    ~/RpiEinky/systemd/eink-display.service > /tmp/eink-display.service

sed -e "s|\${USER}|$(whoami)|g" \
    -e "s|\${HOME}|$HOME|g" \
    ~/RpiEinky/systemd/eink-upload.service > /tmp/eink-upload.service

# Install services
sudo cp /tmp/eink-display.service /etc/systemd/system/
sudo cp /tmp/eink-upload.service /etc/systemd/system/
sudo cp ~/RpiEinky/systemd/eink-system.target /etc/systemd/system/

# Set permissions and enable
sudo chmod 644 /etc/systemd/system/eink-*.service
sudo chmod 644 /etc/systemd/system/eink-system.target
sudo systemctl daemon-reload
sudo systemctl enable eink-display.service eink-upload.service eink-system.target
```

#### Service Management Commands
```bash
# Start both services
sudo systemctl start eink-system.target

# Individual service control
sudo systemctl start|stop|restart eink-display.service
sudo systemctl start|stop|restart eink-upload.service

# Check status
sudo systemctl status eink-display.service
sudo systemctl status eink-upload.service

# View logs
sudo journalctl -u eink-display.service -f
sudo journalctl -u eink-upload.service -f
tail -f ~/RpiEinky/logs/display.log

# Uninstall services
chmod +x ~/RpiEinky/uninstall_services.sh
~/RpiEinky/uninstall_services.sh
```

> **Note**: The service files now use environment variables (`${USER}`, `${HOME}`, `${UID}`) that are automatically replaced during installation, making them work with any username.

### System Management Script (`manage_eink_system.sh`)

The `manage_eink_system.sh` script provides a comprehensive interface for managing the e-ink display system without requiring system reboots or direct interaction with systemd. It handles virtual environment activation, process management, and provides detailed status information.

#### Available Commands

| Command | Description |
|---------|-------------|
| `start` | Start the e-ink system (tries systemd first, falls back to manual) |
| `stop` | Stop the e-ink system (both systemd and manual processes) |
| `restart` | Restart the e-ink system |
| `status` | Show comprehensive system status including hardware checks |
| `logs` | Display recent logs from all components |
| `follow` | Follow logs in real-time (press Ctrl+C to stop) |
| `clear` | Clear the e-ink display |
| `ip` | Show network information and web interface URL |
| `cleanup` | Clean up orphaned processes and stale PID files |
| `help` | Show help message |

#### Usage Examples

```bash
# Start the system
./manage_eink_system.sh start
```

#### Status Information

The `status` command provides comprehensive system information:

- **Systemd Service Status**: Whether the systemd service is running
- **Display Monitor Status**: Status of the file monitoring system
- **Upload Server Status**: Status of the web interface server
- **Hardware Status**: SPI interface and GPIO access availability
- **Virtual Environment**: Location and availability of the Python environment
- **Watched Folder**: Status of the monitored file directory

#### Log Management

The script manages logs from multiple sources:

- **Systemd Service Logs**: From the systemd service (if active)
- **Management Logs**: Script's own activity log
- **Display Monitor Logs**: File monitoring and display operations
- **Upload Server Logs**: Web interface and API operations
- **File Activity**: Recent file changes in the watched folder

#### Process Management

The script intelligently manages processes:

- **Systemd Priority**: Attempts to use systemd service first
- **Manual Fallback**: Falls back to manual process management if systemd fails
- **PID File Management**: Tracks processes using PID files
- **Graceful Shutdown**: Uses SIGTERM first, then SIGKILL if needed
- **Orphaned Process Cleanup**: Identifies and removes stale processes

#### Virtual Environment Detection

The script automatically detects the virtual environment:

- Checks project directory (`./eink_env`)
- Falls back to home directory (`~/eink_env`)
- Provides clear error messages if not found

#### Network Information

The `ip` command displays:

- Raspberry Pi hostname
- IP address
- Web interface URL
- Web interface status

### Web Interface Access
```bash
# Start complete system
./eink_control.sh                    # Default: http://PI_IP:5000

# Access web interface
http://192.168.1.100:5000           # Replace with your Pi's IP
```

# Extending Display Support

The system uses a unified adapter pattern (`unified_epd_adapter.py`) that makes it easy to add support for new e-paper displays. Each display type has its own adapter class that implements a common interface.

#### Adding New Display Support

To add support for a new display:

1. **Install the display library** from Waveshare or the manufacturer
2. **Create a new adapter class** that inherits from `EPDAdapter`
3. **Implement the required methods**:
   - `init()` - Initialize the display
   - `display(image)` - Display an image
   - `clear(color)` - Clear the display
   - `sleep()` - Put display to sleep
   - `getbuffer(image)` - Convert image to display buffer
   - Properties: `display_type`, `width`, `height`, `WHITE`, `BLACK`, `RED`, `YELLOW`, `native_orientation`

4. **Add display configuration** to the `DISPLAY_CONFIGS` dictionary in `UnifiedEPD`

#### Example Adapter Structure

```python
class EPDNewDisplayAdapter(EPDAdapter):
    def __init__(self):
        # Import the actual display module
        try:
            from waveshare_epd import epdnewdisplay
            self.epd = epdnewdisplay.EPD()
        except ImportError:
            raise ImportError("New display library not found")

    @property
    def display_type(self) -> str:
        return "epdnewdisplay"

    def init(self) -> int:
        return self.epd.init()

    def display(self, image) -> None:
        self.epd.display(image)

    def clear(self, color: Optional[int] = None) -> None:
        self.epd.Clear(color or self.WHITE)

    def sleep(self) -> None:
        self.epd.sleep()

    def getbuffer(self, image: Image.Image):
        return self.epd.getbuffer(image)

    @property
    def width(self) -> int:
        return self.epd.width

    @property
    def height(self) -> int:
        return self.epd.height

    # ... other required properties
```

#### Using AI/LLM Assistance

**💡 AI/LLM Integration Tip**: Large Language Models (LLMs) can be extremely helpful when integrating new displays:

- **Library Analysis**: Provide the LLM with the display library code to understand the API
- **Adapter Generation**: Ask the LLM to generate the adapter class based on the library structure
- **Error Debugging**: Use LLMs to troubleshoot import issues and hardware communication problems
- **Documentation**: Generate documentation for new display types

**Example LLM Prompt**:
```
"I have a new e-paper display library with this structure:
[library code]

Please help me create an adapter class that follows the EPDAdapter pattern:
[adapter interface]

The new display should support these features:
- Resolution: [width]x[height]
- Colors: [color support]
- Native orientation: [portrait/landscape]"
```

#### Integration Steps

1. **Study the library**: Understand the display's API and initialization requirements
2. **Create adapter**: Implement the `EPDAdapter` interface for your display
3. **Test integration**: Verify the adapter works with the unified system
4. **Update configuration**: Add the display to the supported displays list
5. **Document**: Add the new display to this documentation

#### Common Integration Challenges

Please refer to section [13.3" Display Special Installation](#31-133-display-special-installation) to see an example of integration challenges.

## Troubleshooting

### Common Issues

**Virtual Environment Issues**
```bash
# Clean start
rm -rf eink_env
python3 -m venv eink_env
source eink_env/bin/activate
pip install -r requirements.txt
```

**SPI Module Issues**
```bash
# Install spidev
source eink_env/bin/activate
pip install spidev

# Enable SPI
# ⚠️ IMPORTANT: SPI configuration steps may vary significantly depending on your specific Raspberry Pi model and OS version ⚠️
sudo raspi-config nonint do_spi 0
sudo reboot
```

**GPIO Issues**
```bash
# Install GPIO libraries
source eink_env/bin/activate
pip install RPi.GPIO lgpio gpiozero

# Add user to hardware groups
sudo usermod -a -G gpio,spi,i2c,dialout $USER
sudo reboot

# If you get "RuntimeError: Failed to add edge detection"
# Try reinstalling gpiozero:
pip uninstall gpiozero
pip install gpiozero
```

**Waveshare Library Issues**
```bash
# Test library installation
python -c "from waveshare_epd import epd2in15g; print('Success!')"

# If fails, check library paths
find . -name "epd2in15g.py" -type f
find . -name "waveshare_epd" -type d
```

**13.3" Display Specific Issues**
```bash
# Test 13.3" display library
python -c "import epd13in3E; print('13.3\" library found!')"

# If fails, check if separate program library is installed
find . -name "epd13in3E.py" -type f
find . -name "epdconfig.py" -type f

# Install 13.3" library manually if needed
cp -r e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/* eink_env/lib/python3.*/site-packages/

# If you get "libwiringPi.so: cannot open shared object file" error:
# First install wiringpi:
git clone https://github.com/WiringPi/WiringPi.git
cd WiringPi
./build
cd ~/RpiEinky

# Then copy the .so files:
sudo cp e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/*.so /usr/local/lib/
sudo ldconfig
```

**Display Not Working**
```bash
# Check display configuration
cat .epd_config.json

# Update display type
echo '{"display_type": "epd2in15g"}' > .epd_config.json

# Test hardware access
python -c "from waveshare_epd import epd2in15g; epd = epd2in15g.EPD(); print('Hardware OK')"
```

**Service Issues**
```bash
# Check service status
sudo systemctl status eink-display.service

# View service logs
sudo journalctl -u eink-display.service -f

# Check virtual environment path in service file
sudo nano /etc/systemd/system/eink-display.service
```

**Web Interface Issues**
```bash
# Test server locally
curl http://localhost:5000/status

# Check Pi's IP address
hostname -I

# Test from Pi browser
curl http://127.0.0.1:5000
```

### Storage Management
```bash
# Check disk usage
du -sh ~/watched_files
ls -la ~/watched_files | wc -l

# Clean up old files via API
curl -X POST http://192.168.1.100:5000/cleanup_old_files \
  -H "Content-Type: application/json" \
  -d '{"keep_count": 10}'

# Manual cleanup
rm -f ~/watched_files/*
```

### Network Setup (Optional)
```bash
# Set static IP using nmcli
sudo nmcli con mod preconfigured ipv4.addresses 192.168.1.100/24
sudo nmcli con mod preconfigured ipv4.gateway 192.168.1.1
sudo nmcli con mod preconfigured ipv4.method manual
sudo nmcli con down preconfigured && sudo nmcli con up preconfigured
```

## Dependencies

### Python Packages
- `watchdog==3.0.0` - File system monitoring
- `Pillow==10.0.0` - Image processing
- `pdf2image==1.16.3` - PDF rendering
- `spidev==3.5` - SPI communication
- `gpiozero==1.6.2` - GPIO control
- `RPi.GPIO==0.7.1` - GPIO library
- `lgpio==0.2.2.0` - Modern GPIO library
- `Flask==2.3.3` - Web server
- `requests==2.31.0` - HTTP client

### System Packages
- `python3-venv` - Virtual environment support
- `poppler-utils` - PDF processing utilities

### Hardware Library
- Waveshare e-Paper library (from their GitHub)

## Raspberry Pi Resources

### Hardware Setup
- **Raspberry Pi Official Documentation**: https://www.raspberrypi.com/documentation/
- **SPI Interface Setup**: https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#spi-interfaces
- **GPIO Pinout**: https://pinout.xyz/ - Interactive GPIO pinout diagram
- **Waveshare**: https://www.waveshare.com - Specific wiring for your display model

### Software Configuration
- **Raspberry Pi OS**: https://www.raspberrypi.com/software/
- **raspi-config Tool**: `sudo raspi-config` - System configuration utility
- **Network Configuration**: https://www.raspberrypi.com/documentation/computers/configuration.html#network-configuration
- **Static IP Setup**: https://www.raspberrypi.com/documentation/computers/configuration.html#static-ip-addresses


## License

MIT License - Feel free to use and modify as needed.
