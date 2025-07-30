# E-Ink File Display System

A comprehensive e-ink display management system designed for Raspberry Pi with web interface supporting multiple Waveshare e-paper displays. Features drag-and-drop uploads, file gallery, and remote management.

## Purpose

- **Real-time file monitoring** - Watches `~/watched_files` folder for new files
- **Web management interface** - Modern responsive UI for remote file uploads and management
- **Multi-display support** - Supports 4-color grayscale and 7-color displays with automatic orientation handling
- **TouchDesigner integration** - HTTP upload server for remote file management
- **Auto-startup service** - Run automatically on system boot with systemd

## Installation

> **⚠️ Installation Disclaimer**: This system is designed for Raspberry Pi. Installation steps may vary based on your specific e-paper display model and Raspberry Pi model. The Waveshare library structure, file locations, and import names can differ between display models and library versions. **Note**: The 13.3" display uses a separate library structure located in `E-paper_Separate_Program/13.3inch_e-Paper_E/` and requires shared object files to be installed in `/usr/local/lib/`. Always refer to your display's specific documentation and adjust paths accordingly.

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
# Download specific files (recommended)



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

### 5. Test Installation
```bash
source eink_env/bin/activate
python display_latest.py
```

## Architecture

### Core Components
- **`display_latest.py`** - Main monitoring system with file watching
- **`upload_server.py`** - Flask web server with web UI and API
- **`unified_epd_adapter.py`** - Display abstraction layer for multiple e-paper models
- **`run_eink_system.py`** - Combined runner for both services

### File Structure
```
RpiEinky/
├── display_latest.py              # Main monitoring system
├── upload_server.py               # Web server with UI
├── unified_epd_adapter.py        # Display abstraction layer
├── run_eink_system.py             # Combined runner
├── clear_display.py               # Display clearing utility
├── templates/index.html           # Web interface template
├── static/                        # Web UI assets
├── requirements.txt               # Python dependencies
├── .epd_config.json              # Display configuration
└── ~/watched_files/              # Monitored folder
```

### Display Support
- **epd2in15g** - 2.15" grayscale (160×296, portrait native)
- **epd13in3E** - 13.3" 7-color (1200×1600, portrait native)  
- **epd7in3e** - 7.3" 7-color (800×480, landscape native)

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

### Auto-Start Service
```bash
# Automated setup
./setup_startup.sh

# Manual setup
sudo cp eink-display.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable eink-display.service
sudo systemctl start eink-display.service
```

### Service Management
```bash
# Management scripts
./manage_eink_system.sh start|stop|restart|status|logs
./restart_eink_system.sh

# Service commands
sudo systemctl start|stop|restart eink-display.service
sudo systemctl status eink-display.service
sudo journalctl -u eink-display.service -f
```

### Web Interface Access
```bash
# Start complete system
./eink_control.sh                    # Default: http://PI_IP:5000
./eink_control_nginx.sh              # Optional: nginx setup

# Access web interface
http://192.168.1.100:5000           # Replace with your Pi's IP
```

### Command Line Arguments

The system supports several command line arguments for customization:

```bash
# Basic usage
python display_latest.py

# Display specific file on startup
python display_latest.py --display-file ~/welcome.jpg
python display_latest.py -d ~/status.txt

# Monitor different folder
python display_latest.py --folder ~/my_files
python display_latest.py -f ~/Desktop/display_files

# Control screen clearing
python display_latest.py --clear-start           # Clear on startup
python display_latest.py --no-clear-exit         # Don't clear on exit

# Change display orientation
python display_latest.py --orientation landscape
python display_latest.py --orientation portrait

# Control timing features
python display_latest.py --disable-startup-timer true  # Disable startup timer
python display_latest.py --startup-delay 5       # 5-minute startup delay
python display_latest.py --refresh-interval 12   # 12-hour refresh interval

# Manufacturer timing and sleep mode
python display_latest.py --enable-manufacturer-timing true  # 180s minimum refresh (safety)
python display_latest.py --enable-sleep-mode false         # Disable sleep mode

# Specify display type (overrides config file)
python display_latest.py --display-type epd2in15g
python display_latest.py --display-type epd7in3e
python display_latest.py --display-type epd13in3E
```

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

## Quick Start

```bash
# 1. Install dependencies (Raspberry Pi)
sudo apt update && sudo apt install python3-venv poppler-utils
sudo raspi-config nonint do_spi 0

# 2. Set up environment
python3 -m venv eink_env
source eink_env/bin/activate
pip install -r requirements.txt

# 3. Install Waveshare library
wget https://files.waveshare.com/upload/7/71/E-Paper_code.zip
unzip E-Paper_code.zip -d e-Paper
cp -r e-Paper/RaspberryPi_JetsonNano/python/lib/waveshare_epd eink_env/lib/python3.*/site-packages/

# For 13.3" display, also install the separate program library
if [ -d "e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E" ]; then
    cp -r e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/* eink_env/lib/python3.*/site-packages/
    # Copy .so files to system library path for 13.3" display
    sudo cp e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/*.so /usr/local/lib/
    sudo ldconfig
fi

# 4. Configure display with your display from the supported display types
echo '{"display_type": "epd2in15g"}' > .epd_config.json

# 5. Start system
./eink_control.sh

# 6. Access web interface
# Open http://YOUR_PI_IP:5000 in browser
```

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