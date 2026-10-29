#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import html
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id
        self.session = requests.Session()

    def send(self, title, message):
        safe_title = html.escape(str(title))
        safe_message = html.escape(str(message))
        text = f"<b>{safe_title}</b>\n{safe_message}"
        try:
            r = self.session.post(
                self.api_url,
                data={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "HTML"
                },
                timeout=10
            )
            r.raise_for_status()
            logging.info(f"Telegram sent: {title}")
        except requests.RequestException as e:
            logging.error(f"Telegram Error: {e}")

class ArrClient:
    def __init__(self, name, base_url, api_key):
        self.name = name
        self.base_url = (base_url or "").rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({'X-Api-Key': api_key or ""})
        self.last_grab_id = None

    def check_new_downloads(self):
        url = f"{self.base_url}/api/v3/history"
        params = {
            'page': 1,
            'pageSize': 20,
            'sortKey': 'date',
            'sortDir': 'desc'
        }

        try:
            r = self.session.get(url, params=params, timeout=10)
            r.raise_for_status()
            records = r.json().get('records', [])

            grab_records = [rec for rec in records if rec.get('eventType') == 'grabbed']
            if not grab_records:
                return []

            newest_id = grab_records[0]['id']

            # Initial run: store the latest ID without sending notifications
            if self.last_grab_id is None:
                self.last_grab_id = newest_id
                logging.info(f"{self.name} initialized. Last ID: {newest_id}")
                return []

            # Collect all grabs newer than last_grab_id, ordered oldest to newest
            new_titles = [
                rec.get('sourceTitle', 'Unknown Title')
                for rec in reversed(grab_records)
                if rec['id'] > self.last_grab_id
            ]

            if newest_id > self.last_grab_id:
                self.last_grab_id = newest_id

            return new_titles

        except requests.RequestException as e:
            logging.error(f"Network error in {self.name}: {e}")
            return []
        except ValueError as e:
            logging.error(f"JSON decode error in {self.name}: {e}")
            return []

def main():
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        logging.error("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing in .env")
        return

    notifier = TelegramNotifier(token, chat_id)

    clients = []
    for name, url_env, key_env in [
        ("Sonarr", "SONARR_URL", "SONARR_API_KEY"),
        ("Radarr", "RADARR_URL", "RADARR_API_KEY")
    ]:
        url = os.getenv(url_env)
        key = os.getenv(key_env)
        if url and key:
            clients.append(ArrClient(name, url, key))
        else:
            logging.warning(f"{name} skipped: missing {url_env} or {key_env}")

    interval = int(os.getenv('CHECK_INTERVAL', 300))
    logging.info(f"Service started. Interval: {interval}s")

    while True:
        for client in clients:
            try:
                new_titles = client.check_new_downloads()
                for title in new_titles:
                    notifier.send(f"New Download ({client.name})", title)
            except Exception as e:
                logging.error(f"Main Loop Error {client.name}: {e}")

        time.sleep(interval)

if __name__ == "__main__":
    main()