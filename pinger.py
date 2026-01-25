#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import socket
import subprocess
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# KONFIGURATION: Wie viele Versuche bevor Alarm geschlagen wird?
MAX_RETRIES = 3 

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send(self, title, message):
        text = f"<b>{title}</b>\n{message}"
        try:
            r = requests.post(self.api_url, data={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
            r.raise_for_status()
        except Exception as e:
            logging.error(f"Telegram Fehler: {e}")

class PingMonitor:
    def __init__(self, targets_string):
        self.targets = []
        if targets_string:
            for item in targets_string.split(','):
                item = item.strip()
                name = item.split('(')[0] if '(' in item else item
                ip = item.split('(')[1].replace(')', '') if '(' in item else item
                self.targets.append({'name': name, 'ip': ip, 'status': True}) # Startet als Online

    def check(self):
        changes = []
        for t in self.targets:
            # DOPPELCHECK LOGIK:
            is_alive = False
            for i in range(MAX_RETRIES):
                # Wir pingen; wenn einer von drei Pings durchkommt, ist das Gerät "Up"
                res = subprocess.run(['ping', '-c', '1', '-W', '2', t['ip']], stdout=subprocess.DEVNULL).returncode == 0
                if res:
                    is_alive = True
                    break
                if i < MAX_RETRIES - 1:
                    time.sleep(120) # Kurz warten vor dem nächsten Versuch

            if t['status'] != is_alive:
                t['status'] = is_alive
                icon = "✅ ONLINE" if is_alive else "🚨 OFFLINE"
                changes.append(f"{icon}: {t['name']} ({t['ip']})")
        
        return "\n".join(changes) if changes else None

class ServiceMonitor:
    def __init__(self, targets_string):
        self.services = []
        if targets_string:
            for item in targets_string.split(','):
                try:
                    name, addr = item.split('|')
                    ip, port = addr.split(':')
                    self.services.append({'name': name.strip(), 'ip': ip.strip(), 'port': int(port), 'status': True})
                except: continue

    def check(self):
        changes = []
        for s in self.services:
            is_up = False
            for i in range(MAX_RETRIES):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((s['ip'], s['port']))
                sock.close()
                if result == 0:
                    is_up = True
                    break
                if i < MAX_RETRIES - 1:
                    time.sleep(2)

            if s['status'] != is_up:
                s['status'] = is_up
                icon = "🟢 UP" if is_up else "🔴 DOWN"
                changes.append(f"{icon}: {s['name']} ({s['port']})")

        return "\n".join(changes) if changes else None

def main():
    notifier = TelegramNotifier(os.getenv('TELEGRAM_TOKEN'), os.getenv('TELEGRAM_CHAT_ID'))
    ping_mon = PingMonitor(os.getenv('PING_TARGETS'))
    serv_mon = ServiceMonitor(os.getenv('SERVICE_TARGETS'))
    interval = int(os.getenv('PING_INTERVAL', 60))

    logging.info(f"Pinger mit Doppelcheck gestartet (Retries: {MAX_RETRIES})")

    while True:
        try:
            p_report = ping_mon.check()
            if p_report: notifier.send("⚠️ Infrastruktur Alarm", p_report)

            s_report = serv_mon.check()
            if s_report: notifier.send("⚠️ Service Status Alarm", s_report)
                
        except Exception as e:
            logging.error(f"Loop Fehler: {e}")
        
        time.sleep(interval)

if __name__ == "__main__":
    main()
