#!/bin/bash

# E-ink Display Manager - Internet Access Setup
# Clean, simple setup for Cloudflare Tunnel with permanent URL

set -e

echo "🚀 E-ink Display Manager - Internet Access Setup"
echo "================================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo -e "${BLUE}📋 Prerequisites Check${NC}"
echo "Before we start, you need:"
echo "• Cloudflare account (free)"
echo "• Domain name added to Cloudflare (free .tk domain works)"
echo
echo "If you don't have a domain yet:"
echo "1. Get a free domain from dot.tk or buy a cheap .xyz domain"
echo "2. Add it to your Cloudflare account"
echo "3. Wait for DNS to activate (5-30 minutes)"
echo
read -p "Do you have a domain added to your Cloudflare account? (y/n): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}⏸️  Please add a domain to Cloudflare first, then run this script again.${NC}"
    echo
    echo "Quick domain options:"
    echo "• Free: dot.tk, freenom.com"
    echo "• Cheap: namecheap.com (.xyz domains ~$2/year)"
    echo
    exit 0
fi

# Step 1: Install cloudflared
echo -e "${BLUE}📦 Step 1: Installing cloudflared...${NC}"
if command_exists cloudflared; then
    echo -e "${GREEN}✅ cloudflared is already installed${NC}"
    cloudflared version
else
    # Detect Pi architecture
    ARCH=$(uname -m)
    DPKG_ARCH=$(dpkg --print-architecture 2>/dev/null || echo "unknown")

    echo "Detected architecture: $ARCH (dpkg: $DPKG_ARCH)"

    if [[ "$ARCH" == "aarch64" ]] || [[ "$ARCH" == "arm64" ]]; then
        echo "Installing ARM64 package..."
        wget -q -O /tmp/cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
        sudo dpkg -i /tmp/cloudflared.deb
        rm /tmp/cloudflared.deb
    elif [[ "$DPKG_ARCH" == "armhf" ]] || [[ "$ARCH" == "armv6l" ]] || [[ "$ARCH" == "armv7l" ]]; then
        echo "Installing ARM binary for Pi Zero/older models..."
        wget -q -O /tmp/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm
        chmod +x /tmp/cloudflared
        sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
    else
        echo -e "${RED}❌ Unsupported architecture: $ARCH${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ cloudflared installed successfully${NC}"
    cloudflared version
fi

echo

# Step 2: Authentication
echo -e "${BLUE}🔐 Step 2: Cloudflare Authentication${NC}"
echo "Opening browser for Cloudflare login..."
echo "If you're on a headless Pi, copy the URL and open it on another device."
echo
read -p "Press Enter to continue..."

cloudflared tunnel login

if [ ! -f ~/.cloudflared/cert.pem ]; then
    echo -e "${RED}❌ Authentication failed - cert.pem not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Authentication successful${NC}"
echo

# Step 3: Create tunnel
echo -e "${BLUE}🚇 Step 3: Creating tunnel...${NC}"
TUNNEL_NAME="eink-display-$(date +%s)"
echo "Creating tunnel: $TUNNEL_NAME"

cloudflared tunnel create "$TUNNEL_NAME"

# Get tunnel ID
TUNNEL_ID=$(cloudflared tunnel list | grep "$TUNNEL_NAME" | awk '{print $1}')
echo -e "${GREEN}✅ Tunnel created with ID: $TUNNEL_ID${NC}"

echo

# Step 4: Configure tunnel
echo -e "${BLUE}⚙️  Step 4: Tunnel configuration...${NC}"

# Get domain from user
echo "Enter your domain name (the one you added to Cloudflare):"
read -p "Domain: " DOMAIN_NAME

if [[ -z "$DOMAIN_NAME" ]]; then
    echo -e "${RED}❌ Domain name required${NC}"
    exit 1
fi

echo
echo "Do you want to use:"
echo "1. Main domain: https://$DOMAIN_NAME"
echo "2. Subdomain: https://eink.$DOMAIN_NAME"
read -p "Choose (1 or 2): " -n 1 -r DOMAIN_CHOICE
echo

if [[ $DOMAIN_CHOICE == "1" ]]; then
    HOSTNAME="$DOMAIN_NAME"
    echo "Your E-ink display will be accessible at: https://$HOSTNAME"
elif [[ $DOMAIN_CHOICE == "2" ]]; then
    HOSTNAME="eink.$DOMAIN_NAME"
    echo "Your E-ink display will be accessible at: https://$HOSTNAME"
else
    echo -e "${RED}❌ Invalid choice, using main domain${NC}"
    HOSTNAME="$DOMAIN_NAME"
    echo "Your E-ink display will be accessible at: https://$HOSTNAME"
fi

# Create config file
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: /home/$USER/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: $HOSTNAME
    service: http://localhost:5000
    originRequest:
      # Cloudflare settings for file uploads
      httpHostHeader: $HOSTNAME
      connectTimeout: 60s
      tlsTimeout: 60s
      tcpKeepAlive: 30s
      keepAliveConnections: 10
      keepAliveTimeout: 90s
      # Don't buffer large uploads
      noHappyEyeballs: false
      # Handle large file uploads
      disableChunkedEncoding: false
      # Trust the upstream server
      noTLSVerify: false
  - service: http_status:404
EOF

echo -e "${GREEN}✅ Configuration created${NC}"

# Step 5: DNS setup
echo -e "${BLUE}🌐 Step 5: DNS configuration...${NC}"
echo "Creating DNS route for $HOSTNAME..."

if cloudflared tunnel route dns "$TUNNEL_ID" "$HOSTNAME" 2>/dev/null; then
    echo -e "${GREEN}✅ DNS record created${NC}"
else
    echo -e "${YELLOW}⚠️  DNS record creation failed - likely due to existing record${NC}"
    echo
    echo "Please manually:"
    echo "1. Go to Cloudflare Dashboard → $DOMAIN_NAME → DNS → Records"
    echo "2. Delete any existing A or CNAME record for $HOSTNAME"
    echo "3. Run: cloudflared tunnel route dns $TUNNEL_ID $HOSTNAME"
    echo
    read -p "Press Enter after you've fixed the DNS records..."
fi

echo

# Step 6: System service
echo -e "${BLUE}🔧 Step 6: Creating system service...${NC}"

sudo tee /etc/systemd/system/cloudflared.service > /dev/null << EOF
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/local/bin/cloudflared tunnel run $TUNNEL_ID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cloudflared.service
echo -e "${GREEN}✅ System service created and enabled${NC}"

echo

# Step 7: Set up authentication
echo -e "${BLUE}🔐 Step 7: Setting up admin authentication...${NC}"
python3 setup_admin_password.py

echo

# Step 8: Start services
echo -e "${BLUE}🚀 Step 8: Starting services...${NC}"

# Start tunnel
sudo systemctl start cloudflared.service
sleep 3

if systemctl is-active --quiet cloudflared.service; then
    echo -e "${GREEN}✅ Tunnel service started${NC}"
else
    echo -e "${RED}❌ Tunnel service failed to start${NC}"
    echo "Check logs: sudo journalctl -u cloudflared.service"
    exit 1
fi

echo

# Final summary
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo "================================"
echo
echo -e "${BLUE}Your E-ink Display Manager is now accessible at:${NC}"
echo -e "${GREEN}https://$HOSTNAME${NC}"
echo
echo -e "${BLUE}To start your Flask server:${NC}"
echo "source eink_env/bin/activate"
echo "export FLASK_ENV=production"
echo "python3 upload_server.py"
echo
echo -e "${BLUE}Useful commands:${NC}"
echo "• Check tunnel: sudo systemctl status cloudflared.service"
echo "• View logs: sudo journalctl -u cloudflared.service -f"
echo "• Restart tunnel: sudo systemctl restart cloudflared.service"
echo
echo -e "${YELLOW}⚠️  Security reminder:${NC}"
echo "• Use a strong admin password"
echo "• Your Flask server binds to localhost only (secure)"
echo "• HTTPS is automatically provided by Cloudflare"
echo
echo -e "${GREEN}Enjoy your internet-accessible E-ink display! 🌍${NC}"
