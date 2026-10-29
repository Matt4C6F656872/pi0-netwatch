#!/usr/bin/env bash
set -e

# ==============================================================================
# pi0-netwatch Automated Installer & Systemd Setup
#
# This script installs pi0-netwatch, guides the user interactively through
# configuring Telegram notifications & targets in .env, and registers the
# background systemd service.
# ==============================================================================

# ANSI color codes for readable terminal feedback
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== pi0-netwatch Installer ===${NC}"

# If running through a pipe (e.g. curl -sSL ... | bash), reconnect stdin to /dev/tty
# so interactive prompts (read -p) can capture keyboard input from the user.
if [ ! -t 0 ] && [ -e /dev/tty ]; then
    exec < /dev/tty
fi

# ------------------------------------------------------------------------------
# 1. Environment & OS Compatibility Check
# ------------------------------------------------------------------------------
# pi0-netwatch utilizes Linux-specific ping flags (-c 1 -W 2) and systemd services.
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${RED}Error: This installer is designed for Linux / Raspberry Pi OS.${NC}"
    exit 1
fi

# ------------------------------------------------------------------------------
# 2. Repository Setup / Update
# ------------------------------------------------------------------------------
INSTALL_DIR="$HOME/pi0-netwatch"
echo -e "${BLUE}Installing to:${NC} ${INSTALL_DIR}"

if [ -d "$INSTALL_DIR" ]; then
    echo "Directory already exists. Pulling latest updates..."
    cd "$INSTALL_DIR"
    git pull origin main || true
else
    git clone https://github.com/Matt4C6F656872/pi0-netwatch.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ------------------------------------------------------------------------------
# 3. Interactive .env Configuration & Inline Guidance
# ------------------------------------------------------------------------------
if [ -f ".env" ]; then
    echo -e "\n${YELLOW}Notice: An existing .env file was found.${NC}"
    read -p "Do you want to reconfigure and overwrite it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        CREATE_ENV=true
    else
        CREATE_ENV=false
        echo "Keeping existing .env configuration."
    fi
else
    CREATE_ENV=true
fi

if [ "$CREATE_ENV" = true ]; then
    echo -e "\n${BLUE}==============================================${NC}"
    echo -e "${BLUE}        Step 1: Telegram Configuration        ${NC}"
    echo -e "${BLUE}==============================================${NC}"
    echo -e "${CYAN}• Bot Token:${NC} Required for sending notification messages."
    echo -e "  Guidance: Create a new bot with @BotFather on Telegram to obtain a token."
    echo -e "  Example:  123456789:ABCDEF_your_bot_token_here"
    read -p "Enter Telegram Bot Token: " TG_TOKEN

    echo -e "\n${CYAN}• Chat ID:${NC} The recipient user or group ID."
    echo -e "  Guidance: Message your bot, then get your numeric chat ID via @userinfobot."
    echo -e "  Example:  987654321"
    read -p "Enter Telegram Chat ID: " TG_CHAT_ID

    echo -e "\n${BLUE}==============================================${NC}"
    echo -e "${BLUE}        Step 2: Monitoring Targets            ${NC}"
    echo -e "${BLUE}==============================================${NC}"
    echo -e "${CYAN}• ICMP Ping Targets:${NC}"
    echo -e "  Guidance: Monitored via standard ICMP ping packets."
    echo -e "  Format:   Comma-separated Name(IP_or_Hostname)"
    echo -e "  Example:  Router(192.168.178.1),NAS(192.168.178.20)"
    echo -e "  (Leave blank if you do not want to monitor ICMP hosts)"
    read -p "Enter Ping Targets: " PING_TARGETS

    echo -e "\n${CYAN}• Service Targets (HTTP/HTTPS or TCP Port):${NC}"
    echo -e "  Guidance: Monitored via HTTP/HTTPS request or raw TCP socket connect."
    echo -e "            Self-signed SSL certificates and any domain (.intern, .local, raw IP) are supported."
    echo -e "  Format:   Comma-separated Name|URL or Name|IP:Port"
    echo -e "  Example:  Sonarr|http://192.168.178.20:8989/ping,Jellyfin|https://jellyfin.intern,SSH|192.168.178.20:22"
    echo -e "  (Leave blank if you do not want to monitor services)"
    read -p "Enter Service Targets: " SERVICE_TARGETS

    echo -e "\n${CYAN}• Check Interval:${NC}"
    echo -e "  Guidance: Frequency in seconds between monitoring cycles (default: 60)."
    read -p "Enter Check Interval [default: 60]: " PING_INTERVAL
    PING_INTERVAL=${PING_INTERVAL:-60}

    # Write configuration and restrict file permissions (protecting the Telegram bot token)
    cat << EOF > .env
TELEGRAM_TOKEN=${TG_TOKEN}
TELEGRAM_CHAT_ID=${TG_CHAT_ID}
PING_INTERVAL=${PING_INTERVAL}
PING_TARGETS=${PING_TARGETS}
SERVICE_TARGETS=${SERVICE_TARGETS}
EOF
    chmod 600 .env
    echo -e "${GREEN}✅ .env configuration saved successfully (chmod 600)!${NC}"
fi

# ------------------------------------------------------------------------------
# 4. Systemd Background Service Setup
# ------------------------------------------------------------------------------
# pi0-netwatch is configured to automatically restart on boot and network recovery.
SERVICE_FILE="/etc/systemd/system/pi0-netwatch.service"
CURRENT_USER="$USER"

echo -e "\n${BLUE}Setting up systemd background service...${NC}"

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

# Reload systemd daemon to pick up changes, then enable and restart service
sudo systemctl daemon-reload
sudo systemctl enable pi0-netwatch.service
sudo systemctl restart pi0-netwatch.service

echo -e "\n${GREEN}=============================================${NC}"
echo -e "${GREEN}✅ pi0-netwatch installed and started successfully!${NC}"
echo -e "${BLUE}Check status with:${NC} sudo systemctl status pi0-netwatch.service"
echo -e "${BLUE}Check logs with:${NC}   journalctl -u pi0-netwatch.service -f"
echo -e "${GREEN}=============================================${NC}"
