# E-ink Display System Service Installation

This document describes how to install the E-ink Display System as systemd services.

## Overview

The system consists of two main services:
- `eink-display.service` - Main display service that runs the e-ink display system
- `eink-upload.service` - Upload server for receiving new content
- `eink-system.target` - Target that manages both services together

## Prerequisites

1. Ensure the RpiEinky directory is in your home directory (`~/RpiEinky`)
2. Make sure you have the Python virtual environment set up (`~/eink_env`)
3. Ensure you have the necessary hardware permissions (gpio, spi, i2c groups)

## Installation

### Automatic Installation

1. Make the installation script executable:
   ```bash
   chmod +x ~/RpiEinky/install_services.sh
   ```

2. Run the installation script:
   ```bash
   ~/RpiEinky/install_services.sh
   ```

The script will:
- Detect your current user and home directory
- Configure the service files with the correct paths
- Install the services to `/etc/systemd/system/`
- Enable the services to start on boot
- Create the logs directory if it doesn't exist

### Manual Installation

If you prefer to install manually:

1. Configure the service files:
   ```bash
   # Replace placeholders with your actual values
   sed -e "s|\${USER}|$(whoami)|g" \
       -e "s|\${HOME}|$HOME|g" \
       -e "s|\${UID}|$(id -u)|g" \
       ~/RpiEinky/systemd/eink-display.service > /tmp/eink-display.service
   
   sed -e "s|\${USER}|$(whoami)|g" \
       -e "s|\${HOME}|$HOME|g" \
       ~/RpiEinky/systemd/eink-upload.service > /tmp/eink-upload.service
   ```

2. Install the services:
   ```bash
   sudo cp /tmp/eink-display.service /etc/systemd/system/
   sudo cp /tmp/eink-upload.service /etc/systemd/system/
   sudo cp ~/RpiEinky/systemd/eink-system.target /etc/systemd/system/
   ```

3. Set permissions and reload:
   ```bash
   sudo chmod 644 /etc/systemd/system/eink-*.service
   sudo chmod 644 /etc/systemd/system/eink-system.target
   sudo systemctl daemon-reload
   ```

4. Enable the services:
   ```bash
   sudo systemctl enable eink-display.service
   sudo systemctl enable eink-upload.service
   sudo systemctl enable eink-system.target
   ```

## Usage

### Starting Services

Start both services:
```bash
sudo systemctl start eink-system.target
```

Or start individual services:
```bash
sudo systemctl start eink-display.service
sudo systemctl start eink-upload.service
```

### Checking Status

Check service status:
```bash
sudo systemctl status eink-display.service
sudo systemctl status eink-upload.service
```

### Viewing Logs

View service logs:
```bash
# Systemd logs
sudo journalctl -u eink-display.service -f
sudo journalctl -u eink-upload.service -f

# Application logs
tail -f ~/RpiEinky/logs/display.log
```

### Stopping Services

Stop the services:
```bash
sudo systemctl stop eink-system.target
```

## Uninstallation

To remove the services:

1. Make the uninstall script executable:
   ```bash
   chmod +x ~/RpiEinky/uninstall_services.sh
   ```

2. Run the uninstall script:
   ```bash
   ~/RpiEinky/uninstall_services.sh
   ```

Or manually:
```bash
sudo systemctl stop eink-display.service eink-upload.service
sudo systemctl disable eink-display.service eink-upload.service eink-system.target
sudo rm /etc/systemd/system/eink-*.service /etc/systemd/system/eink-system.target
sudo systemctl daemon-reload
```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure your user is in the required groups:
   ```bash
   sudo usermod -a -G gpio,spi,i2c,dialout $USER
   ```

2. **Service Fails to Start**: Check the logs:
   ```bash
   sudo journalctl -u eink-display.service -n 50
   ```

3. **Path Issues**: Ensure the RpiEinky directory is in your home directory and the virtual environment exists.

### Service Configuration

The services are configured with the following environment variables:
- `${USER}` - Current username
- `${HOME}` - User's home directory
- `${UID}` - User ID

These are automatically replaced during installation.

## File Locations

- Service files: `/etc/systemd/system/`
- Application logs: `~/RpiEinky/logs/display.log`
- System logs: `journalctl -u eink-display.service` 