#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import requests
import logging
from dotenv import load_dotenv

# Konfiguration laden
load_dotenv()

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    def send(self, title, message):
        text = f"<b>{title}</b>\n{message}"
        try:
            # Timeout 10s set
            r = requests.post(self.api_url, data={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }, timeout=10)
            r.raise_for_status()
            logging.info(f"Telegram sent: {title}")
        except Exception as e:
            logging.error(f"Telegram Error: {e}")

class ArrClient:
    def __init__(self, name, base_url, api_key):
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.headers = {'X-Api-Key': api_key}
        self.last_grab_id = None 

    def check_new_downloads(self):
        url = f"{self.base_url}/api/v3/history"
        # eventType entfernt, pageSize auf 20
        params = {
            'page': 1, 
            'pageSize': 20, 
            'sortKey': 'date', 
            'sortDir': 'desc'
        }

        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()

            # Filter local: Find newest record with eventType 'grabbed'
            latest_grab_record = None
            for record in data.get('records', []):
                if record.get('eventType') == 'grabbed':
                    latest_grab_record = record
                    break 

            if not latest_grab_record:
                return None 

            grab_id = latest_grab_record['id']
            title = latest_grab_record.get('sourceTitle', 'Unknown Title')

            # Initial run: just store ID
            if self.last_grab_id is None:
                self.last_grab_id = grab_id
                logging.info(f"{self.name} initialized. Last ID: {grab_id}")
                return None

            # Check for new ID
            if grab_id != self.last_grab_id:
                if grab_id > self.last_grab_id:
                    self.last_grab_id = grab_id
                    return title
            
            return None

        except Exception as e:
            logging.error(f"Error in loop {self.name}: {e}")
            return None

def main():
    notifier = TelegramNotifier(
        os.getenv('TELEGRAM_TOKEN'), 
        os.getenv('TELEGRAM_CHAT_ID')
    )
    
    clients = [
        ArrClient("Sonarr", os.getenv('SONARR_URL'), os.getenv('SONARR_API_KEY')),
        ArrClient("Radarr", os.getenv('RADARR_URL'), os.getenv('RADARR_API_KEY'))
    ]

    interval = int(os.getenv('CHECK_INTERVAL', 300))
    logging.info(f"Service started. Interval: {interval}s")

    while True:
        for client in clients:
            try:
                new_title = client.check_new_downloads()
                if new_title:
                    notifier.send(f"New Download ({client.name})", new_title)
            except Exception as e:
                logging.error(f"Main Loop Error {client.name}: {e}")
        
        time.sleep(interval)

if __name__ == "__main__":
    main()