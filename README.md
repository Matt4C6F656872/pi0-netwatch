# pi0-netwatch

Zero-dependency Python infrastructure and service monitor with Telegram notifications, optimized for the Raspberry Pi Zero W.

## Features

- **Zero External Dependencies:** Uses only the Python 3 standard library (`urllib`, `socket`, `ssl`, `subprocess`) for minimal RAM and CPU usage (~12 MB RAM).
- **ICMP Host Monitoring:** Checks device availability via `ping` with configurable retry attempts before alerting.
- **HTTP/HTTPS & TCP Port Monitoring:** Supports full HTTP/HTTPS URLs (including self-signed certificates on internal domains like `.intern`) as well as raw `IP:Port` TCP socket checks.
- **Telegram Alerts:** Sends HTML-escaped status change alerts (`ONLINE`/`OFFLINE` and `UP`/`DOWN`) via the Telegram Bot API.

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Matt4C6F656872/pi0-netwatch.git
   cd pi0-netwatch
   ```

2. **Create and configure your `.env` file:**
   ```bash
   cp .env.example .env
   chmod 600 .env
   nano .env
   ```

3. **Run with Python 3:**
   ```bash
   /usr/bin/python3 pinger.py
   ```

## Configuration

Edit `.env` to configure your credentials, check intervals, and monitoring targets:

```dotenv
TELEGRAM_TOKEN=123456789:ABCDEF_your_bot_token_here
TELEGRAM_CHAT_ID=987654321

# Check interval in seconds
PING_INTERVAL=60

# Host monitoring via ICMP Ping: Name(IP_or_Hostname)
PING_TARGETS=Router(192.168.178.1),NAS(192.168.178.20)

# Service monitoring via HTTP/HTTPS URL or TCP IP:Port
SERVICE_TARGETS=Sonarr|http://192.168.178.20:8989/ping,Jellyfin|https://jellyfin.intern,SSH-NAS|192.168.178.20:22
```
