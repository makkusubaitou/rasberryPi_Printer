#!/bin/bash
#
# Print Server Setup Script for Raspberry Pi
# Run this script on your Raspberry Pi to set everything up.
#

set -e

echo "========================================"
echo "  Print Server Setup for Raspberry Pi"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if [[ ! -f /etc/rpi-issue ]] && [[ ! -d /opt/vc ]]; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi.${NC}"
    echo "Continuing anyway..."
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/home/pi/print-server"

# =============================================================================
# Step 1: System Dependencies
# =============================================================================
echo ""
echo -e "${GREEN}[1/6] Installing system dependencies...${NC}"
sudo apt update
sudo apt install -y python3 python3-pip python3-venv cups

# Add pi user to lpadmin group (for printer access)
sudo usermod -a -G lpadmin pi

# =============================================================================
# Step 2: Create installation directory and copy files
# =============================================================================
echo ""
echo -e "${GREEN}[2/6] Setting up print server...${NC}"

mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/print_server.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/config.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"

# Create Python virtual environment
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$INSTALL_DIR/requirements.txt"
deactivate

# =============================================================================
# Step 3: Generate API Key
# =============================================================================
echo ""
echo -e "${GREEN}[3/6] Generating API key...${NC}"

API_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo ""
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  YOUR API KEY (SAVE THIS!)${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "  $API_KEY"
echo ""
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "You will need this key to send print requests from your website."
echo ""

# Save API key to a file for reference
echo "$API_KEY" > "$INSTALL_DIR/.api_key"
chmod 600 "$INSTALL_DIR/.api_key"

# =============================================================================
# Step 4: Setup systemd service
# =============================================================================
echo ""
echo -e "${GREEN}[4/6] Setting up systemd service...${NC}"

# Create the service file with the actual API key
cat > /tmp/print-server.service << EOF
[Unit]
Description=Print Server - Receives print jobs via webhook
After=network.target cups.service
Wants=cups.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PRINT_API_KEY=$API_KEY"
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --bind 127.0.0.1:3000 --workers 2 print_server:app
Restart=always
RestartSec=5

NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/print-server.service /etc/systemd/system/print-server.service
sudo systemctl daemon-reload
sudo systemctl enable print-server
sudo systemctl start print-server

echo "Print server service installed and started!"

# =============================================================================
# Step 5: Install Cloudflare Tunnel
# =============================================================================
echo ""
echo -e "${GREEN}[5/6] Installing Cloudflare Tunnel (cloudflared)...${NC}"

# Download and install cloudflared for ARM
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o /tmp/cloudflared
sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared

echo ""
echo "Cloudflared installed!"
echo ""

# =============================================================================
# Step 6: Show next steps
# =============================================================================
echo ""
echo -e "${GREEN}[6/6] Setup complete!${NC}"
echo ""
echo "========================================"
echo "  NEXT STEPS"
echo "========================================"
echo ""
echo "1. CHECK YOUR PRINTER"
echo "   Run: lpstat -p -d"
echo "   Make sure your network printer is detected."
echo "   If not, add it via CUPS web interface: http://localhost:631"
echo ""
echo "2. CONFIGURE CLOUDFLARE TUNNEL"
echo "   a) Login to Cloudflare:"
echo "      cloudflared tunnel login"
echo ""
echo "   b) Create a tunnel:"
echo "      cloudflared tunnel create print-server"
echo ""
echo "   c) Route your subdomain (replace with your domain):"
echo "      cloudflared tunnel route dns print-server printer.yourdomain.com"
echo ""
echo "   d) Create tunnel config file:"
echo "      mkdir -p ~/.cloudflared"
echo "      cat > ~/.cloudflared/config.yml << 'TUNNELCFG'"
echo "      tunnel: print-server"
echo "      credentials-file: /home/pi/.cloudflared/<TUNNEL_ID>.json"
echo "      ingress:"
echo "        - hostname: printer.yourdomain.com"
echo "          service: http://localhost:5000"
echo "        - service: http_status:404"
echo "      TUNNELCFG"
echo ""
echo "   e) Install tunnel as a service:"
echo "      sudo cloudflared service install"
echo "      sudo systemctl start cloudflared"
echo ""
echo "3. TEST YOUR SETUP"
echo "   curl -X GET http://localhost:3000/health"
echo ""
echo "   Or from your website:"
echo "   curl -X POST https://printer.yourdomain.com/print \\"
echo "        -H 'X-API-Key: $API_KEY' \\"
echo "        -F 'image=@test.png'"
echo ""
echo "========================================"
echo ""
echo -e "${GREEN}Your API Key is saved in: $INSTALL_DIR/.api_key${NC}"
echo ""

