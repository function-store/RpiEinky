# No-Reboot E-ink System Management Guide

This guide shows you how to manage your e-ink display system without ever needing to reboot your Raspberry Pi.

## 🚀 Quick Start Commands

Make the management scripts executable first:
```bash
chmod +x manage_eink_system.sh restart_eink_system.sh
```

### Basic Management
```bash
# Check system status
./manage_eink_system.sh status

# Start the system
./manage_eink_system.sh start

# Stop the system
./manage_eink_system.sh stop

# Restart the system (most common command)
./manage_eink_system.sh restart

# View logs
./manage_eink_system.sh logs

# Clear the display
./manage_eink_system.sh clear

# Show network info
./manage_eink_system.sh ip

# Clean up orphaned processes
./manage_eink_system.sh cleanup
```

## 🔧 Detailed Management Options

### 1. **System Status Check**
```bash
./manage_eink_system.sh status
```
**What it shows:**
- Systemd service status
- Display monitor process status
- Upload server process status
- Hardware access (SPI, GPIO)
- Virtual environment status
- Watched folder status and file count

### 2. **Clean Restart**
```bash
./manage_eink_system.sh restart
```
**What it does:**
- Safely stops all processes
- Clears the display
- Restarts both display monitor and upload server
- Checks hardware access
- Verifies processes are running
- Logs all actions

### 3. **View System Logs**
```bash
./manage_eink_system.sh logs
```
**What it shows:**
- Systemd service logs (last 20 lines)
- Management script logs
- Recent file activity in watched folder

### 4. **Network Information**
```bash
./manage_eink_system.sh ip
```
**What it shows:**
- Raspberry Pi hostname
- IP address
- Web interface URL
- Web interface status

## 🛠️ Advanced Restart Options

### Dedicated Restart Script
```bash
# Full restart with detailed logging
./restart_eink_system.sh restart

# Check restart status
./restart_eink_system.sh status

# View restart logs
./restart_eink_system.sh logs

# Clean up orphaned processes
./restart_eink_system.sh cleanup
```

### Systemd Service Management
```bash
# Restart via systemd (if service is enabled)
sudo systemctl restart eink-display.service

# Check service status
sudo systemctl status eink-display.service

# View service logs
sudo journalctl -u eink-display.service -f

# Enable service for auto-start
sudo systemctl enable eink-display.service

# Disable service auto-start
sudo systemctl disable eink-display.service
```

## 🔍 Troubleshooting Without Reboots

### Problem: Display not responding
```bash
# 1. Check status
./manage_eink_system.sh status

# 2. Clear display
./manage_eink_system.sh clear

# 3. Restart system
./manage_eink_system.sh restart

# 4. Check logs
./manage_eink_system.sh logs
```

### Problem: Web interface not accessible
```bash
# 1. Check network info
./manage_eink_system.sh ip

# 2. Check upload server status
./manage_eink_system.sh status

# 3. Restart system
./manage_eink_system.sh restart

# 4. Check logs for errors
./manage_eink_system.sh logs
```

### Problem: Orphaned processes
```bash
# Clean up orphaned processes
./manage_eink_system.sh cleanup

# Or use the dedicated cleanup
./restart_eink_system.sh cleanup
```

### Problem: Hardware access issues
```bash
# Check hardware status
./manage_eink_system.sh status

# If SPI/GPIO issues, restart system
./manage_eink_system.sh restart

# Check logs for hardware errors
./manage_eink_system.sh logs
```

## 📋 Common Scenarios

### After Code Updates
```bash
# 1. Stop the system
./manage_eink_system.sh stop

# 2. Update your code (git pull, etc.)

# 3. Restart the system
./manage_eink_system.sh restart

# 4. Verify it's working
./manage_eink_system.sh status
```

### After Configuration Changes
```bash
# 1. Make changes via web interface or settings file

# 2. Restart to apply changes
./manage_eink_system.sh restart

# 3. Check logs for any issues
./manage_eink_system.sh logs
```

### After Power Issues
```bash
# 1. Check if system is running
./manage_eink_system.sh status

# 2. If not running, start it
./manage_eink_system.sh start

# 3. If issues, do a full restart
./manage_eink_system.sh restart
```

### Before Making Hardware Changes
```bash
# 1. Stop the system safely
./manage_eink_system.sh stop

# 2. Make hardware changes

# 3. Start the system
./manage_eink_system.sh start

# 4. Verify hardware access
./manage_eink_system.sh status
```

## 🔄 Automatic Restart Features

The system includes built-in restart capabilities:

### 1. **Systemd Auto-Restart**
- If the service crashes, systemd automatically restarts it
- Configurable restart delays and limits
- Automatic recovery from temporary failures

### 2. **Process Monitoring**
- PID files track running processes
- Automatic cleanup of stale PID files
- Graceful shutdown with timeout fallback

### 3. **Hardware Recovery**
- Automatic display reinitialization on errors
- SPI interface recovery
- GPIO access verification

## 📊 Monitoring and Logging

### Log Files Location
- **Systemd logs**: `journalctl -u eink-display.service`
- **Management logs**: `/tmp/eink_management.log`
- **Restart logs**: `/tmp/eink_restart.log`
- **Application logs**: Check individual Python scripts

### Real-time Monitoring
```bash
# Follow systemd logs in real-time
sudo journalctl -u eink-display.service -f

# Follow management logs
tail -f /tmp/eink_management.log

# Monitor system status
watch -n 5 './manage_eink_system.sh status'
```

## 🎯 Best Practices

### 1. **Always Use Management Scripts**
- Don't manually kill processes
- Use the provided scripts for clean operations
- Let the scripts handle cleanup

### 2. **Check Status Before Actions**
- Always run `./manage_eink_system.sh status` first
- Understand what's currently running
- Identify any issues before restarting

### 3. **Use Logs for Troubleshooting**
- Check logs before and after operations
- Look for error patterns
- Use logs to verify successful operations

### 4. **Regular Maintenance**
- Periodically check system status
- Clean up orphaned processes if needed
- Monitor log file sizes

### 5. **Safe Restart Sequence**
1. Check current status
2. Stop system cleanly
3. Wait for cleanup (2-3 seconds)
4. Start system
5. Verify all components are running
6. Check logs for any issues

## 🚨 Emergency Procedures

### Complete System Reset
```bash
# 1. Stop everything
./manage_eink_system.sh stop

# 2. Clean up all processes
./manage_eink_system.sh cleanup

# 3. Clear display
./manage_eink_system.sh clear

# 4. Start fresh
./manage_eink_system.sh start

# 5. Verify everything
./manage_eink_system.sh status
```

### Hardware Reset
```bash
# 1. Stop system
./manage_eink_system.sh stop

# 2. Wait 10 seconds for hardware to reset
sleep 10

# 3. Start system
./manage_eink_system.sh start
```

## ✅ Verification Checklist

After any restart operation, verify:

- [ ] Display monitor is running
- [ ] Upload server is running
- [ ] Web interface is accessible
- [ ] SPI interface is available
- [ ] GPIO access is working
- [ ] Virtual environment is accessible
- [ ] Watched folder exists and is accessible
- [ ] No error messages in logs
- [ ] Display shows content correctly

## 🎉 Benefits of No-Reboot Management

1. **Faster Operations**: No waiting for system boot
2. **Preserved State**: File uploads and settings maintained
3. **Selective Restart**: Only restart what's needed
4. **Better Debugging**: Immediate feedback and logs
5. **Reduced Wear**: Less stress on SD card and hardware
6. **Professional Operation**: Clean, controlled restarts

With these tools and procedures, you should never need to reboot your Raspberry Pi to manage the e-ink display system! 