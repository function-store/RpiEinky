#!/bin/bash

# E-ink Display System Service Installer
# This script configures the systemd services for the current user

set -e

# Get current user information
CURRENT_USER=$(whoami)
CURRENT_HOME=$(eval echo ~$CURRENT_USER)
CURRENT_UID=$(id -u)

echo "Installing E-ink Display System services for user: $CURRENT_USER"
echo "Home directory: $CURRENT_HOME"
echo "User ID: $CURRENT_UID"

# Check if we're running as root
if [[ $EUID -eq 0 ]]; then
   echo "Error: This script should not be run as root"
   echo "Please run as the user who will own the services"
   exit 1
fi

# Check if RpiEinky directory exists
if [ ! -d "$CURRENT_HOME/RpiEinky" ]; then
    echo "Error: RpiEinky directory not found at $CURRENT_HOME/RpiEinky"
    echo "Please ensure the RpiEinky directory is in your home directory"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$CURRENT_HOME/RpiEinky/logs"

# Configure the service files
echo "Configuring service files..."

# Configure eink-display.service
sed -e "s|\${USER}|$CURRENT_USER|g" \
    -e "s|\${HOME}|$CURRENT_HOME|g" \
    -e "s|\${UID}|$CURRENT_UID|g" \
    "$CURRENT_HOME/RpiEinky/systemd/eink-display.service" > /tmp/eink-display.service

# Configure eink-upload.service
sed -e "s|\${USER}|$CURRENT_USER|g" \
    -e "s|\${HOME}|$CURRENT_HOME|g" \
    "$CURRENT_HOME/RpiEinky/systemd/eink-upload.service" > /tmp/eink-upload.service

# Copy the target file (no substitutions needed)
cp "$CURRENT_HOME/RpiEinky/systemd/eink-system.target" /tmp/eink-system.target

# Install the services
echo "Installing services to /etc/systemd/system/..."
sudo cp /tmp/eink-display.service /etc/systemd/system/
sudo cp /tmp/eink-upload.service /etc/systemd/system/
sudo cp /tmp/eink-system.target /etc/systemd/system/

# Set proper permissions
sudo chmod 644 /etc/systemd/system/eink-display.service
sudo chmod 644 /etc/systemd/system/eink-upload.service
sudo chmod 644 /etc/systemd/system/eink-system.target

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Enable the services
echo "Enabling services..."
sudo systemctl enable eink-display.service
sudo systemctl enable eink-upload.service
sudo systemctl enable eink-system.target

# Clean up temporary files
rm -f /tmp/eink-display.service /tmp/eink-upload.service /tmp/eink-system.target

echo ""
echo "Installation complete!"
echo ""
echo "Services installed:"
echo "  - eink-display.service"
echo "  - eink-upload.service"
echo "  - eink-system.target"
echo ""
echo "To start the services:"
echo "  sudo systemctl start eink-system.target"
echo ""
echo "To check status:"
echo "  sudo systemctl status eink-display.service"
echo "  sudo systemctl status eink-upload.service"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u eink-display.service -f"
echo "  sudo journalctl -u eink-upload.service -f"
echo "  tail -f $CURRENT_HOME/RpiEinky/logs/display.log" 