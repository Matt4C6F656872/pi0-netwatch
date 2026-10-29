#!/usr/bin/env bash
set -e

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== pi0-netwatch Installer ===${NC}"

# 1. Check if running on Linux / Raspberry Pi
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${RED}Error: This installer is designed for Linux / Raspberry Pi OS.${NC}"
    exit 1
fi

# 2. Determine installation directory (default to /home/$USER/pi0-netwatch or /opt)
INSTALL_DIR="$HOME/pi0-netwatch"
echo -e "${BLUE}Installing to: ${INSTALL_DIR}${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo "Directory already exists. Pulling latest updates..."
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    git clone https://github.com/Matt4C6F656872/pi0-netwatch.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 3. Interactive .env configuration
if [ -f ".env" ]; then
    read -p "An existing .env file was found. Do you want to overwrite it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        CREATE_ENV=true
    else
        CREATE_ENV=false
    fi
else
    CREATE_ENV=true
fi

if [ "$CREATE_ENV" = true ]; then
    echo -e "${BLUE}--- Telegram Configuration ---${NC}"
    read -p "Enter Telegram Bot Token: " TG_TOKEN
    read -p "Enter Telegram Chat ID: " TG_CHAT_ID

    echo -e "${BLUE}--- Monitoring Targets ---${NC}"
    read -p "Enter Ping Targets (e.g. Router(192.168.178.1)): " PING_TARGETS
    read -p "Enter Service Targets (e.g. Sonarr|http://192.168.178.20:8989/ping): " SERVICE_TARGETS

    cat << EOF > .env
TELEGRAM_TOKEN=${TG_TOKEN}
TELEGRAM_CHAT_ID=${TG_CHAT_ID}
PING_INTERVAL=60
PING_TARGETS=${PING_TARGETS}
SERVICE_TARGETS=${SERVICE_TARGETS}
EOF
    chmod 600 .env
    echo -e "${GREEN}✅ .env configuration saved successfully!${NC}"
fi

# 4. Set up systemd service
SERVICE_FILE="/etc/systemd/system/pi0-netwatch.service"
CURRENT_USER="$USER"

echo -e "${BLUE}Setting up systemd background service...${NC}"

sudo bash -c "cat > $SERVICE_FILE" << EOF
[Unit]
Description=pi0-netwatch Network & Service Monitor
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${INSTALL_DIR}/.env
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/pinger.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable pi0-netwatch.service
sudo systemctl restart pi0-netwatch.service

echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}✅ pi0-netwatch installed and started successfully!${NC}"
echo -e "${BLUE}Check status with:${NC} sudo systemctl status pi0-netwatch.service"
echo -e "${BLUE}Check logs with:${NC}   journalctl -u pi0-netwatch.service -f"
echo -e "${GREEN}=============================================${NC}"