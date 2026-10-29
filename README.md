# pi0Notifyarr

Lightweight Python monitoring and Telegram notification suite designed for the Raspberry Pi Zero W.

## Features
- **Arr Monitor (`main.py`):** Polls Sonarr and Radarr APIs for newly grabbed releases and sends HTML-formatted alerts via Telegram.
- **Infrastructure & Port Monitor (`pinger.py`):** Monitors host availability via ICMP ping and TCP service ports via sockets, sending Telegram alerts on state changes (`ONLINE`/`OFFLINE` and `UP`/`DOWN`) with configurable retry checks.

## Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/Matt4C6F656872/pi0Notifyarr.git](https://github.com/Matt4C6F656872/pi0Notifyarr.git)
   cd pi0Notifyarr

Create a virtual environment and install dependencies:
    Bash

    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt

    Copy .env.example to .env and fill in your credentials and targets:
    Bash

    cp .env.example .env
    nano .env

Configuration Format (.env)

    PING_TARGETS: Comma-separated list formatted as Name(IP_or_Hostname).

        Example: Router(192.168.178.1),Server(192.168.178.10)

    SERVICE_TARGETS: Comma-separated list formatted as Name|IP_or_Hostname:Port.

        Example: Plex|192.168.178.10:32400,Sonarr|192.168.178.10:8989

Usage

Run either script directly using the virtual environment:
Bash

./venv/bin/python pinger.py
./venv/bin/python main.py