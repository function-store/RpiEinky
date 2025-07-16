#!/bin/bash

# E-ink Display System Control Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/eink_env"
DISPLAY_PID_FILE="/tmp/eink_display.pid"
SERVER_PID_FILE="/tmp/eink_server.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}📟 E-ink Display System Control${NC}"
    echo "=================================="
}

start_services() {
    print_status
    echo -e "${GREEN}🚀 Starting E-ink Display System...${NC}"
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        echo -e "${RED}❌ Virtual environment not found at $VENV_PATH${NC}"
        echo "Please run the installation first."
        exit 1
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Start display monitor
    echo -e "${YELLOW}🖥️  Starting display monitor...${NC}"
    python "$SCRIPT_DIR/display_latest.py" &
    DISPLAY_PID=$!
    echo $DISPLAY_PID > $DISPLAY_PID_FILE
    
    # Start upload server
    echo -e "${YELLOW}🌐 Starting upload server...${NC}"
    python "$SCRIPT_DIR/upload_server.py" &
    SERVER_PID=$!
    echo $SERVER_PID > $SERVER_PID_FILE
    
    sleep 2
    
    # Check if processes are running
    if kill -0 $DISPLAY_PID 2>/dev/null && kill -0 $SERVER_PID 2>/dev/null; then
        echo -e "${GREEN}✅ E-ink Display System is running!${NC}"
        echo "   Display Monitor PID: $DISPLAY_PID"
        echo "   Upload Server PID: $SERVER_PID"
        echo "   Use './eink_control.sh stop' to stop services"
    else
        echo -e "${RED}❌ Failed to start services${NC}"
        stop_services
        exit 1
    fi
}

stop_services() {
    print_status
    echo -e "${YELLOW}🛑 Stopping E-ink Display System...${NC}"
    
    # Stop display monitor
    if [ -f $DISPLAY_PID_FILE ]; then
        DISPLAY_PID=$(cat $DISPLAY_PID_FILE)
        if kill -0 $DISPLAY_PID 2>/dev/null; then
            echo "🖥️  Stopping display monitor (PID: $DISPLAY_PID)"
            kill $DISPLAY_PID
        fi
        rm -f $DISPLAY_PID_FILE
    fi
    
    # Stop upload server
    if [ -f $SERVER_PID_FILE ]; then
        SERVER_PID=$(cat $SERVER_PID_FILE)
        if kill -0 $SERVER_PID 2>/dev/null; then
            echo "🌐 Stopping upload server (PID: $SERVER_PID)"
            kill $SERVER_PID
        fi
        rm -f $SERVER_PID_FILE
    fi
    
    echo -e "${GREEN}✅ E-ink Display System stopped${NC}"
}

check_status() {
    print_status
    echo -e "${BLUE}📊 Service Status:${NC}"
    
    # Check display monitor
    if [ -f $DISPLAY_PID_FILE ]; then
        DISPLAY_PID=$(cat $DISPLAY_PID_FILE)
        if kill -0 $DISPLAY_PID 2>/dev/null; then
            echo -e "🖥️  Display Monitor: ${GREEN}RUNNING${NC} (PID: $DISPLAY_PID)"
        else
            echo -e "🖥️  Display Monitor: ${RED}STOPPED${NC}"
        fi
    else
        echo -e "🖥️  Display Monitor: ${RED}STOPPED${NC}"
    fi
    
    # Check upload server
    if [ -f $SERVER_PID_FILE ]; then
        SERVER_PID=$(cat $SERVER_PID_FILE)
        if kill -0 $SERVER_PID 2>/dev/null; then
            echo -e "🌐 Upload Server: ${GREEN}RUNNING${NC} (PID: $SERVER_PID)"
        else
            echo -e "🌐 Upload Server: ${RED}STOPPED${NC}"
        fi
    else
        echo -e "🌐 Upload Server: ${RED}STOPPED${NC}"
    fi
}

show_logs() {
    echo -e "${BLUE}📋 Recent Logs:${NC}"
    echo "=================================="
    
    # Show display monitor logs
    if [ -f $DISPLAY_PID_FILE ]; then
        DISPLAY_PID=$(cat $DISPLAY_PID_FILE)
        if kill -0 $DISPLAY_PID 2>/dev/null; then
            echo -e "${YELLOW}🖥️  Display Monitor Logs:${NC}"
            # Since we're running in background, logs go to stdout
            # In a real implementation, you'd redirect to log files
            echo "Display monitor is running..."
        fi
    fi
    
    # Show upload server logs
    if [ -f $SERVER_PID_FILE ]; then
        SERVER_PID=$(cat $SERVER_PID_FILE)
        if kill -0 $SERVER_PID 2>/dev/null; then
            echo -e "${YELLOW}🌐 Upload Server Logs:${NC}"
            echo "Upload server is running..."
        fi
    fi
}

restart_services() {
    stop_services
    sleep 2
    start_services
}

show_help() {
    print_status
    echo "Usage: $0 {start|stop|restart|status|logs|help}"
    echo ""
    echo "Commands:"
    echo "  start    - Start both display monitor and upload server"
    echo "  stop     - Stop both services"
    echo "  restart  - Restart both services"
    echo "  status   - Show service status"
    echo "  logs     - Show recent logs"
    echo "  help     - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start     # Start the system"
    echo "  $0 status    # Check if services are running"
    echo "  $0 stop      # Stop the system"
}

# Main script logic
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac 