#!/bin/bash

# E-ink Display System Management Script
# Provides easy commands for managing the system without requiring reboots

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$HOME/eink_env"
SERVICE_NAME="eink-display.service"
DISPLAY_PID_FILE="/tmp/eink_display.pid"
SERVER_PID_FILE="/tmp/eink_server.pid"
LOG_FILE="/tmp/eink_management.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "${BLUE}📟 E-ink Display System Manager${NC}"
    echo "======================================"
}

# Function to check if a process is running
is_process_running() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        kill -0 "$pid" 2>/dev/null
    else
        return 1
    fi
}

# Function to get process status
get_process_status() {
    local pid_file="$1"
    local process_name="$2"
    
    if is_process_running "$pid_file"; then
        local pid=$(cat "$pid_file")
        echo -e "${GREEN}✅ $process_name: RUNNING${NC} (PID: $pid)"
        return 0
    else
        echo -e "${RED}❌ $process_name: STOPPED${NC}"
        return 1
    fi
}

# Function to check if run_eink_system.py is running
is_run_eink_system_running() {
    pgrep -f "run_eink_system.py" >/dev/null 2>&1
}

# Function to get combined system status
get_combined_system_status() {
    local display_status=0
    local server_status=0
    
    # Check if run_eink_system.py is running
    if is_run_eink_system_running; then
        local pid=$(pgrep -f "run_eink_system.py")
        echo -e "${GREEN}✅ Display Monitor: RUNNING${NC} (via run_eink_system.py, PID: $pid)"
        echo -e "${GREEN}✅ Upload Server: RUNNING${NC} (via run_eink_system.py, PID: $pid)"
        return 0
    else
        # Fall back to individual PID file checks
        get_process_status "$DISPLAY_PID_FILE" "Display Monitor"
        display_status=$?
        get_process_status "$SERVER_PID_FILE" "Upload Server"
        server_status=$?
        return $((display_status + server_status))
    fi
}

# Function to check systemd service status
get_systemd_status() {
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}✅ Systemd Service: RUNNING${NC}"
        return 0
    else
        echo -e "${RED}❌ Systemd Service: STOPPED${NC}"
        return 1
    fi
}

# Function to start the system
start_system() {
    print_header
    echo -e "${GREEN}🚀 Starting E-ink Display System...${NC}"
    log_message "Starting e-ink system"
    
    # Check if already running
    if get_systemd_status >/dev/null 2>&1 || \
       (is_process_running "$DISPLAY_PID_FILE" && is_process_running "$SERVER_PID_FILE"); then
        echo -e "${YELLOW}⚠️  System is already running${NC}"
        echo "Use 'restart' to restart the system"
        return 0
    fi
    
    # Try systemd service first
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo -e "${BLUE}🔧 Starting via systemd service...${NC}"
        systemctl start "$SERVICE_NAME"
        sleep 3
        
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo -e "${GREEN}✅ System started successfully via systemd${NC}"
            log_message "System started successfully via systemd"
            return 0
        else
            echo -e "${YELLOW}⚠️  Systemd start failed, trying manual start${NC}"
        fi
    fi
    
    # Fall back to manual start
    echo -e "${BLUE}🔄 Starting manually...${NC}"
    
    # Check virtual environment
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}❌ Virtual environment not found${NC}"
        return 1
    fi
    
    # Create log directories
    mkdir -p "$SCRIPT_DIR/logs"
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Start display monitor in background with proper logging
    echo -e "${YELLOW}🖥️  Starting display monitor...${NC}"
    nohup python "$SCRIPT_DIR/display_latest.py" > "$SCRIPT_DIR/logs/display.log" 2>&1 &
    DISPLAY_PID=$!
    echo $DISPLAY_PID > "$DISPLAY_PID_FILE"
    log_message "Display monitor started with PID: $DISPLAY_PID"
    
    # Start upload server in background with proper logging
    echo -e "${YELLOW}🌐 Starting upload server...${NC}"
    nohup python "$SCRIPT_DIR/upload_server.py" > "$SCRIPT_DIR/logs/server.log" 2>&1 &
    SERVER_PID=$!
    echo $SERVER_PID > "$SERVER_PID_FILE"
    log_message "Upload server started with PID: $SERVER_PID"
    
    sleep 3
    
    # Check if processes are running
    if is_process_running "$DISPLAY_PID_FILE" && is_process_running "$SERVER_PID_FILE"; then
        echo -e "${GREEN}✅ System started successfully manually${NC}"
        echo -e "${BLUE}📋 Logs available at:${NC}"
        echo -e "   Display: $SCRIPT_DIR/logs/display.log"
        echo -e "   Server:  $SCRIPT_DIR/logs/server.log"
        log_message "System started successfully manually"
        return 0
    else
        echo -e "${RED}❌ Failed to start system${NC}"
        log_message "ERROR: Failed to start system"
        return 1
    fi
}

# Function to stop the system
stop_system() {
    print_header
    echo -e "${YELLOW}🛑 Stopping E-ink Display System...${NC}"
    log_message "Stopping e-ink system"
    
    # Stop systemd service if running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${BLUE}🔧 Stopping systemd service...${NC}"
        systemctl stop "$SERVICE_NAME"
        sleep 3
    fi
    
    # Stop manual processes
    if [ -f "$DISPLAY_PID_FILE" ]; then
        local pid=$(cat "$DISPLAY_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}🖥️  Stopping display monitor (PID: $pid)...${NC}"
            kill -TERM "$pid"
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid"
            fi
        fi
        rm -f "$DISPLAY_PID_FILE"
    fi
    
    if [ -f "$SERVER_PID_FILE" ]; then
        local pid=$(cat "$SERVER_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}🌐 Stopping upload server (PID: $pid)...${NC}"
            kill -TERM "$pid"
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid"
            fi
        fi
        rm -f "$SERVER_PID_FILE"
    fi
    
    echo -e "${GREEN}✅ System stopped${NC}"
    log_message "System stopped"
}

# Function to restart the system
restart_system() {
    print_header
    echo -e "${PURPLE}🔄 Restarting E-ink Display System...${NC}"
    log_message "Restarting e-ink system"
    
    stop_system
    sleep 2
    start_system
}

# Function to show status
show_status() {
    print_header
    echo -e "${BLUE}📊 System Status:${NC}"
    echo "=================="
    
    # Check systemd service
    get_systemd_status
    
    # Check combined system status
    get_combined_system_status
    
    echo ""
    echo -e "${BLUE}🔧 Hardware Status:${NC}"
    echo "=================="
    
    # Check SPI interface
    if [ -e "/dev/spidev0.0" ]; then
        echo -e "${GREEN}✅ SPI Interface: Available${NC}"
    else
        echo -e "${RED}❌ SPI Interface: Not Available${NC}"
    fi
    
    # Check GPIO access
    if groups | grep -q gpio; then
        echo -e "${GREEN}✅ GPIO Access: Available${NC}"
    else
        echo -e "${YELLOW}⚠️  GPIO Access: Limited${NC}"
    fi
    
    # Check virtual environment
    if [ -d "$VENV_PATH" ]; then
        echo -e "${GREEN}✅ Virtual Environment: Available${NC}"
    else
        echo -e "${RED}❌ Virtual Environment: Not Found${NC}"
    fi
    
    # Check watched folder
    local watched_folder="$HOME/watched_files"
    if [ -d "$watched_folder" ]; then
        local file_count=$(find "$watched_folder" -maxdepth 1 -type f | wc -l)
        echo -e "${GREEN}✅ Watched Folder: $watched_folder ($file_count files)${NC}"
    else
        echo -e "${YELLOW}⚠️  Watched Folder: Not Found${NC}"
    fi
}

# Function to show logs
show_logs() {
    print_header
    echo -e "${BLUE}📋 System Logs:${NC}"
    echo "================"
    
    # Show systemd service logs
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo -e "${YELLOW}🔧 Systemd Service Logs:${NC}"
        journalctl -u "$SERVICE_NAME" --no-pager -n 20
        echo ""
    fi
    
    # Show management logs
    if [ -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}🔄 Management Logs:${NC}"
        tail -n 20 "$LOG_FILE"
        echo ""
    fi
    
    # Show application logs
    if [ -f "$SCRIPT_DIR/logs/display.log" ]; then
        echo -e "${YELLOW}🖥️  Display Monitor Logs:${NC}"
        tail -n 15 "$SCRIPT_DIR/logs/display.log"
        echo ""
    fi
    
    if [ -f "$SCRIPT_DIR/logs/server.log" ]; then
        echo -e "${YELLOW}🌐 Upload Server Logs:${NC}"
        tail -n 15 "$SCRIPT_DIR/logs/server.log"
        echo ""
    fi
    
    # Show recent file activity
    local watched_folder="$HOME/watched_files"
    if [ -d "$watched_folder" ]; then
        echo -e "${YELLOW}📁 Recent File Activity:${NC}"
        find "$watched_folder" -maxdepth 1 -type f -printf "%T@ %p\n" | sort -nr | head -5 | while read timestamp file; do
            local date=$(date -d "@${timestamp%.*}" '+%Y-%m-%d %H:%M:%S')
            local filename=$(basename "$file")
            echo "  $date - $filename"
        done
    fi
}

# Function to follow logs in real-time
follow_logs() {
    print_header
    echo -e "${BLUE}📋 Following Logs in Real-Time:${NC}"
    echo "Press Ctrl+C to stop following logs"
    echo "=================================="
    
    # Check which log files exist
    local log_files=()
    
    if [ -f "$SCRIPT_DIR/logs/display.log" ]; then
        log_files+=("$SCRIPT_DIR/logs/display.log")
    fi
    
    if [ -f "$SCRIPT_DIR/logs/server.log" ]; then
        log_files+=("$SCRIPT_DIR/logs/server.log")
    fi
    
    if [ -f "$LOG_FILE" ]; then
        log_files+=("$LOG_FILE")
    fi
    
    if [ ${#log_files[@]} -eq 0 ]; then
        echo -e "${RED}❌ No log files found${NC}"
        return 1
    fi
    
    # Follow all log files
    if [ ${#log_files[@]} -eq 1 ]; then
        echo -e "${YELLOW}Following: ${log_files[0]}${NC}"
        tail -f "${log_files[0]}"
    else
        echo -e "${YELLOW}Following multiple log files:${NC}"
        for log_file in "${log_files[@]}"; do
            echo "  - $log_file"
        done
        echo ""
        tail -f "${log_files[@]}"
    fi
}

# Function to clear display
clear_display() {
    print_header
    echo -e "${YELLOW}🧹 Clearing E-ink Display...${NC}"
    log_message "Clearing display"
    
    if [ -d "$VENV_PATH" ]; then
        source "$VENV_PATH/bin/activate"
        
        if python "$SCRIPT_DIR/clear_display.py"; then
            echo -e "${GREEN}✅ Display cleared successfully${NC}"
            log_message "Display cleared successfully"
        else
            echo -e "${RED}❌ Failed to clear display${NC}"
            log_message "ERROR: Failed to clear display"
            return 1
        fi
    else
        echo -e "${RED}❌ Virtual environment not found${NC}"
        return 1
    fi
}

# Function to show IP address
show_ip() {
    print_header
    echo -e "${BLUE}🌐 Network Information:${NC}"
    echo "======================"
    
    # Get IP address
    local ip_address=$(hostname -I | awk '{print $1}')
    local hostname=$(hostname)
    
    echo -e "${GREEN}🏠 Hostname:${NC} $hostname"
    echo -e "${GREEN}📡 IP Address:${NC} $ip_address"
    echo -e "${GREEN}🌐 Web Interface:${NC} http://$ip_address:5000"
    
    # Check if web interface is accessible
    if is_process_running "$SERVER_PID_FILE"; then
        echo -e "${GREEN}✅ Web Interface: Running${NC}"
    else
        echo -e "${RED}❌ Web Interface: Not Running${NC}"
    fi
}

# Function to cleanup orphaned processes
cleanup() {
    print_header
    echo -e "${YELLOW}🧹 Cleaning up orphaned processes...${NC}"
    log_message "Cleaning up orphaned processes"
    
    # Find and kill orphaned Python processes
    local orphaned_pids=$(pgrep -f "display_latest.py\|upload_server.py\|run_eink_system.py" | grep -v $$)
    
    if [ -n "$orphaned_pids" ]; then
        echo -e "${YELLOW}Found orphaned processes:${NC}"
        for pid in $orphaned_pids; do
            echo "  PID: $pid"
            kill -TERM "$pid" 2>/dev/null
            sleep 1
            if kill -0 "$pid" 2>/dev/null; then
                kill -KILL "$pid" 2>/dev/null
            fi
        done
    else
        echo -e "${GREEN}No orphaned processes found${NC}"
    fi
    
    # Clean up stale PID files
    rm -f "$DISPLAY_PID_FILE" "$SERVER_PID_FILE"
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
    log_message "Cleanup completed"
}

# Function to show help
show_help() {
    print_header
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Start the e-ink system"
    echo "  stop      - Stop the e-ink system"
    echo "  restart   - Restart the e-ink system"
    echo "  status    - Show system status"
    echo "  logs      - Show recent logs"
    echo "  follow    - Follow logs in real-time"
    echo "  clear     - Clear the e-ink display"
    echo "  ip        - Show network information"
    echo "  cleanup   - Clean up orphaned processes"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start     # Start the system"
    echo "  $0 status    # Check system status"
    echo "  $0 restart   # Restart the system"
    echo "  $0 logs      # View recent logs"
    echo "  $0 follow    # Follow logs in real-time"
    echo ""
    echo "This script manages the e-ink system without requiring system reboots."
}

# Main script logic
case "${1:-help}" in
    start)
        start_system
        ;;
    stop)
        stop_system
        ;;
    restart)
        restart_system
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    follow)
        follow_logs
        ;;
    clear)
        clear_display
        ;;
    ip)
        show_ip
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac 