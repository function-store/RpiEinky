#!/bin/bash

# Start E-ink Display Manager with Internet Access
# Simple script to start the Flask server for internet access

set -e

echo "🌐 Starting E-ink Display Manager (Internet Mode)"
echo "================================================"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Check if we're in the right directory
if [[ ! -f "upload_server.py" ]]; then
    echo -e "${RED}❌ upload_server.py not found${NC}"
    echo "Please run this script from the RpiEinky directory"
    exit 1
fi

# Check if virtual environment exists
if [[ ! -d "eink_env" ]]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Please run the installation first"
    exit 1
fi

# Check if .env file exists
if [[ ! -f ".env" ]]; then
    echo -e "${BLUE}🔐 Setting up admin password...${NC}"
    python3 setup_admin_password.py
fi

# Check if tunnel service is running
echo -e "${BLUE}🚇 Checking Cloudflare tunnel...${NC}"
if systemctl is-active --quiet cloudflared.service 2>/dev/null; then
    echo -e "${GREEN}✅ Tunnel service is running${NC}"
else
    echo -e "${RED}❌ Tunnel service not running${NC}"
    echo "Start it with: sudo systemctl start cloudflared.service"
    echo "Or run the setup: ./setup_internet_access.sh"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source eink_env/bin/activate

# Set production environment
export FLASK_ENV=production
export FLASK_HOST=127.0.0.1
export FLASK_PORT=5000

# Start Flask server
echo -e "${BLUE}🌐 Starting Flask server...${NC}"
echo "Server will run on localhost:5000 (accessible via Cloudflare tunnel)"
echo "Press Ctrl+C to stop"
echo

python3 upload_server.py
