#!/bin/bash

# E-ink Display System Restart Script
# Ensures clean restarts without requiring system reboot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$HOME/eink_env"
SERVICE_NAME="eink-display.service"
DISPLAY_PID_FILE="/tmp/eink_display.pid"
SERVER_PID_FILE="/tmp/eink_server.pid"
LOG_FILE="/tmp/eink_restart.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

print_status() {
    echo -e "${BLUE}🔄 E-ink Display System Restart${NC}"
    echo "=================================="
}

# Function to check if a process is running
is_process_running() {
    local pid_file="$1"
    local process_name="$2"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Process is running
        fi
    fi
    return 1  # Process is not running
}

# Function to stop a process cleanly
stop_process() {
    local pid_file="$1"
    local process_name="$2"
    local timeout=10
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_message "Stopping $process_name (PID: $pid)..."
            
            # Try graceful shutdown first
            kill -TERM "$pid"
            
            # Wait for graceful shutdown
            local count=0
            while kill -0 "$pid" 2>/dev/null && [ $count -lt $timeout ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                log_message "Force killing $process_name (PID: $pid)..."
                kill -KILL "$pid"
                sleep 1
            fi
            
            # Remove PID file
            rm -f "$pid_file"
            log_message "$process_name stopped"
        else
            log_message "$process_name was not running"
            rm -f "$pid_file"
        fi
    else
        log_message "$process_name PID file not found"
    fi
}

# Function to check hardware access
check_hardware_access() {
    log_message "Checking hardware access..."
    
    # Check SPI interface
    if [ ! -e "/dev/spidev0.0" ]; then
        echo -e "${RED}❌ SPI interface not available${NC}"
        log_message "ERROR: SPI interface not available"
        return 1
    fi
    
    # Check GPIO access
    if ! groups | grep -q gpio; then
        echo -e "${YELLOW}⚠️  User not in gpio group${NC}"
        log_message "WARNING: User not in gpio group"
    fi
    
    # Check if waveshare library is available
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}❌ Virtual environment not found${NC}"
        log_message "ERROR: Virtual environment not found"
        return 1
    fi
    
    echo -e "${GREEN}✅ Hardware access OK${NC}"
    log_message "Hardware access check passed"
    return 0
}

# Function to clear display safely
clear_display_safely() {
    log_message "Clearing display safely..."
    
    if [ -d "$VENV_PATH" ]; then
        source "$VENV_PATH/bin/activate"
        
        # Try to clear display using the clear script
        if python "$SCRIPT_DIR/clear_display.py" >/dev/null 2>&1; then
            log_message "Display cleared successfully"
        else
            log_message "WARNING: Could not clear display (this is normal if hardware is busy)"
        fi
    fi
}

# Function to restart systemd service
restart_systemd_service() {
    log_message "Restarting systemd service..."
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${YELLOW}🔄 Restarting systemd service...${NC}"
        systemctl restart "$SERVICE_NAME"
        
        # Wait for service to start
        sleep 3
        
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo -e "${GREEN}✅ Systemd service restarted successfully${NC}"
            log_message "Systemd service restarted successfully"
            return 0
        else
            echo -e "${RED}❌ Systemd service restart failed${NC}"
            log_message "ERROR: Systemd service restart failed"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  Systemd service not running, starting...${NC}"
        systemctl start "$SERVICE_NAME"
        
        sleep 3
        
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo -e "${GREEN}✅ Systemd service started successfully${NC}"
            log_message "Systemd service started successfully"
            return 0
        else
            echo -e "${RED}❌ Systemd service start failed${NC}"
            log_message "ERROR: Systemd service start failed"
            return 1
        fi
    fi
}

# Function to restart manual processes
restart_manual_processes() {
    log_message "Restarting manual processes..."
    
    # Stop existing processes
    stop_process "$DISPLAY_PID_FILE" "Display Monitor"
    stop_process "$SERVER_PID_FILE" "Upload Server"
    
    # Wait a moment for cleanup
    sleep 2
    
    # Check hardware access
    if ! check_hardware_access; then
        return 1
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Start display monitor
    echo -e "${YELLOW}🖥️  Starting display monitor...${NC}"
    log_message "Starting display monitor..."
    python "$SCRIPT_DIR/display_latest.py" &
    DISPLAY_PID=$!
    echo $DISPLAY_PID > "$DISPLAY_PID_FILE"
    
    # Start upload server
    echo -e "${YELLOW}🌐 Starting upload server...${NC}"
    log_message "Starting upload server..."
    python "$SCRIPT_DIR/upload_server.py" &
    SERVER_PID=$!
    echo $SERVER_PID > "$SERVER_PID_FILE"
    
    # Wait for processes to start
    sleep 3
    
    # Check if processes are running
    if is_process_running "$DISPLAY_PID_FILE" "Display Monitor" && \
       is_process_running "$SERVER_PID_FILE" "Upload Server"; then
        echo -e "${GREEN}✅ Manual processes restarted successfully${NC}"
        log_message "Manual processes restarted successfully"
        return 0
    else
        echo -e "${RED}❌ Manual process restart failed${NC}"
        log_message "ERROR: Manual process restart failed"
        return 1
    fi
}

# Function to show service status
show_status() {
    echo -e "${BLUE}📊 Service Status:${NC}"
    
    # Check systemd service
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "🔧 Systemd Service: ${GREEN}RUNNING${NC}"
    else
        echo -e "🔧 Systemd Service: ${RED}STOPPED${NC}"
    fi
    
    # Check manual processes
    if is_process_running "$DISPLAY_PID_FILE" "Display Monitor"; then
        local pid=$(cat "$DISPLAY_PID_FILE")
        echo -e "🖥️  Display Monitor: ${GREEN}RUNNING${NC} (PID: $pid)"
    else
        echo -e "🖥️  Display Monitor: ${RED}STOPPED${NC}"
    fi
    
    if is_process_running "$SERVER_PID_FILE" "Upload Server"; then
        local pid=$(cat "$SERVER_PID_FILE")
        echo -e "🌐 Upload Server: ${GREEN}RUNNING${NC} (PID: $pid)"
    else
        echo -e "🌐 Upload Server: ${RED}STOPPED${NC}"
    fi
}

# Function to show logs
show_logs() {
    echo -e "${BLUE}📋 Recent Logs:${NC}"
    echo "=================================="
    
    # Show systemd service logs
    echo -e "${YELLOW}🔧 Systemd Service Logs:${NC}"
    journalctl -u "$SERVICE_NAME" --no-pager -n 20
    
    # Show restart log
    if [ -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}🔄 Restart Logs:${NC}"
        tail -n 20 "$LOG_FILE"
    fi
}

# Main restart function
perform_restart() {
    print_status
    log_message "Starting e-ink system restart"
    
    # Clear display first
    clear_display_safely
    
    # Try systemd service first
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo -e "${BLUE}🔧 Using systemd service restart${NC}"
        if restart_systemd_service; then
            echo -e "${GREEN}✅ Restart completed successfully via systemd${NC}"
            log_message "Restart completed successfully via systemd"
            return 0
        else
            echo -e "${YELLOW}⚠️  Systemd restart failed, trying manual restart${NC}"
            log_message "Systemd restart failed, trying manual restart"
        fi
    fi
    
    # Fall back to manual process restart
    echo -e "${BLUE}🔄 Using manual process restart${NC}"
    if restart_manual_processes; then
        echo -e "${GREEN}✅ Restart completed successfully via manual processes${NC}"
        log_message "Restart completed successfully via manual processes"
        return 0
    else
        echo -e "${RED}❌ Restart failed${NC}"
        log_message "ERROR: Restart failed"
        return 1
    fi
}

# Function to clean up orphaned processes
cleanup_orphaned_processes() {
    log_message "Cleaning up orphaned processes..."
    
    # Find and kill orphaned Python processes related to e-ink
    local orphaned_pids=$(pgrep -f "display_latest.py\|upload_server.py\|run_eink_system.py" | grep -v $$)
    
    if [ -n "$orphaned_pids" ]; then
        echo -e "${YELLOW}🧹 Cleaning up orphaned processes...${NC}"
        for pid in $orphaned_pids; do
            log_message "Killing orphaned process PID: $pid"
            kill -TERM "$pid" 2>/dev/null
            sleep 1
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid" 2>/dev/null
            fi
        done
    fi
    
    # Clean up stale PID files
    rm -f "$DISPLAY_PID_FILE" "$SERVER_PID_FILE"
}

# Main script logic
case "${1:-restart}" in
    restart)
        perform_restart
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    cleanup)
        cleanup_orphaned_processes
        echo -e "${GREEN}✅ Cleanup completed${NC}"
        ;;
    help|--help|-h)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  restart  - Restart the e-ink system (default)"
        echo "  status   - Show service status"
        echo "  logs     - Show recent logs"
        echo "  cleanup  - Clean up orphaned processes"
        echo "  help     - Show this help message"
        echo ""
        echo "This script ensures clean restarts without requiring system reboot."
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac 