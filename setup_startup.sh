#!/bin/bash
# Setup script to install e-ink display system to run on startup

echo "🚀 Setting up E-ink Display System for startup..."

# Get the current directory
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📁 Current directory: $CURRENT_DIR"

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x "$CURRENT_DIR/display_latest.py"
chmod +x "$CURRENT_DIR/run_eink_system.py"
chmod +x "$CURRENT_DIR/clear_display.py"

# Update the service file with the current directory
echo "📝 Updating service file with current directory..."
sed -i "s|/home/pi/RpiEinky|$CURRENT_DIR|g" "$CURRENT_DIR/eink-display.service"

# Detect and update virtual environment path
echo "🔍 Detecting virtual environment location..."
if [ -d "$CURRENT_DIR/eink_env" ]; then
    VENV_PATH="$CURRENT_DIR/eink_env"
    echo "Found venv in project folder: $VENV_PATH"
elif [ -d "$HOME/eink_env" ]; then
    VENV_PATH="$HOME/eink_env"
    echo "Found venv in home directory: $VENV_PATH"
else
    echo "❌ Virtual environment not found in $CURRENT_DIR/eink_env or $HOME/eink_env"
    echo "Please create it first with: python3 -m venv eink_env"
    exit 1
fi

# Update the service file with the correct venv path
sed -i "s|/home/danrasp/eink_env|$VENV_PATH|g" "$CURRENT_DIR/eink-display.service"

# Copy service file to systemd directory
echo "📋 Installing systemd service..."
sudo cp "$CURRENT_DIR/eink-display.service" /etc/systemd/system/

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable the service to start on boot
echo "✅ Enabling service to start on boot..."
sudo systemctl enable eink-display.service

echo ""
echo "🎉 Setup complete! The e-ink display system will now start on boot."
echo ""
echo "📋 Useful commands:"
echo "   Start service:    sudo systemctl start eink-display.service"
echo "   Stop service:     sudo systemctl stop eink-display.service"
echo "   Check status:     sudo systemctl status eink-display.service"
echo "   View logs:        sudo journalctl -u eink-display.service -f"
echo "   Clear display:    ./clear_display.py"
echo ""
echo "🔄 Reboot your system to test the startup service." 