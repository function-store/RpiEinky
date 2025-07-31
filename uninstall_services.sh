#!/bin/bash

# E-ink Display System Service Uninstaller
# This script removes the systemd services

set -e

echo "Uninstalling E-ink Display System services..."

# Stop and disable services
echo "Stopping and disabling services..."
sudo systemctl stop eink-display.service 2>/dev/null || true
sudo systemctl stop eink-upload.service 2>/dev/null || true
sudo systemctl stop eink-system.target 2>/dev/null || true

sudo systemctl disable eink-display.service 2>/dev/null || true
sudo systemctl disable eink-upload.service 2>/dev/null || true
sudo systemctl disable eink-system.target 2>/dev/null || true

# Remove service files
echo "Removing service files..."
sudo rm -f /etc/systemd/system/eink-display.service
sudo rm -f /etc/systemd/system/eink-upload.service
sudo rm -f /etc/systemd/system/eink-system.target

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

echo ""
echo "Uninstallation complete!"
echo "All E-ink Display System services have been removed." 