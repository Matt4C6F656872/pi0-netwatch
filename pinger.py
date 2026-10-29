#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import ssl
import time
import html
import socket
import subprocess
import logging
import urllib.request
import urllib.parse
import urllib.error

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

def load_env_file(filepath=".env"):
    """Reads a .env file into os.environ without external libraries."""
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip("'\""))

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send(self, title, message):
        safe_title = html.escape(str(title))
        safe_message = html.escape(str(message))
        payload = urllib.parse.urlencode({
            "chat_id": self.chat_id,
            "text": f"<b>{safe_title}</b>\n{safe_message}",
            "parse_mode": "HTML"
        }).encode("utf-8")

        req = urllib.request.Request(self.api_url, data=payload, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logging.info(f"Telegram sent: {title}")
        except urllib.error.URLError as e:
            logging.error(f"Telegram Fehler: {e}")

class PingMonitor:
    def __init__(self, targets_string):
        self.targets = []
        if targets_string:
            for item in targets_string.split(','):
                item = item.strip()
                if not item:
                    continue
                if '(' in item and item.endswith(')'):
                    name, ip = item[:-1].split('(', 1)
                else:
                    name, ip = item, item
                self.targets.append({
                    'name': name.strip(),
                    'ip': ip.strip(),
                    'status': True
                })

    def check(self):
        changes = []
        for t in self.targets:
            is_alive = False
            for i in range(MAX_RETRIES):
                res = subprocess.run(
                    ['ping', '-c', '1', '-W', '2', t['ip']],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                ).returncode == 0
                if res:
                    is_alive = True
                    break
                if i < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SECONDS)

            if t['status'] != is_alive:
                t['status'] = is_alive
                icon = "✅ ONLINE" if is_alive else "🚨 OFFLINE"
                changes.append(f"{icon}: {t['name']} ({t['ip']})")

        return "\n".join(changes) if changes else None

class ServiceMonitor:
    def __init__(self, targets_string):
        self.services = []
        # Allow self-signed certificates for internal (.intern) domains
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

        if targets_string:
            for item in targets_string.split(','):
                item = item.strip()
                if not item:
                    continue
                if '|' not in item:
                    logging.warning(f"Invalid SERVICE_TARGETS entry skipped: {item}")
                    continue

                name, target = item.split('|', 1)
                name = name.strip()
                target = target.strip()

                if target.startswith(('http://', 'https://')):
                    self.services.append({
                        'name': name,
                        'type': 'http',
                        'target': target,
                        'status': True
                    })
                elif ':' in target:
                    try:
                        ip, port = target.rsplit(':', 1)
                        self.services.append({
                            'name': name,
                            'type': 'tcp',
                            'ip': ip.strip(),
                            'port': int(port),
                            'target': target,
                            'status': True
                        })
                    except ValueError:
                        logging.warning(f"Invalid TCP SERVICE_TARGETS entry skipped: {item}")
                else:
                    logging.warning(f"Invalid SERVICE_TARGETS entry skipped: {item}")

    def _probe(self, service):
        if service['type'] == 'http':
            req = urllib.request.Request(
                service['target'],
                headers={'User-Agent': 'pi0Notifyarr/1.0'}
            )
            try:
                with urllib.request.urlopen(req, timeout=5, context=self.ssl_ctx) as resp:
                    return resp.status < 500
            except urllib.error.HTTPError as e:
                # 401/403/404 means the server is online and responding; 5xx means service/proxy failure
                return e.code < 500
            except Exception:
                return False
        else:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(3)
                    return sock.connect_ex((service['ip'], service['port'])) == 0
            except OSError:
                return False

    def check(self):
        changes = []
        for s in self.services:
            is_up = False
            for i in range(MAX_RETRIES):
                if self._probe(s):
                    is_up = True
                    break
                if i < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SECONDS)

            if s['status'] != is_up:
                s['status'] = is_up
                icon = "🟢 UP" if is_up else "🔴 DOWN"
                changes.append(f"{icon}: {s['name']} ({s['target']})")

        return "\n".join(changes) if changes else None

def main():
    load_env_file()
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        logging.error("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing in environment or .env")
        return

    notifier = TelegramNotifier(token, chat_id)
    ping_mon = PingMonitor(os.getenv('PING_TARGETS'))
    serv_mon = ServiceMonitor(os.getenv('SERVICE_TARGETS'))
    interval = int(os.getenv('PING_INTERVAL', 60))

    logging.info(
        f"Pinger gestartet: {len(ping_mon.targets)} Ping-Ziele, "
        f"{len(serv_mon.services)} Service-Ziele (Retries: {MAX_RETRIES})"
    )

    while True:
        try:
            p_report = ping_mon.check()
            if p_report:
                notifier.send("⚠️ Infrastruktur Alarm", p_report)

            s_report = serv_mon.check()
            if s_report:
                notifier.send("⚠️ Service Status Alarm", s_report)

        except Exception as e:
            logging.error(f"Loop Fehler: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    main()