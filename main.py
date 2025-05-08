from bs4 import BeautifulSoup
import requests
import time
import random
import os
from flask import Flask
import threading
import logging

app = Flask(__name__)

# Config
PROFILES = [
    "omerutkuDemir",
    "bpthaber",
    "2_sayfaofficial", 
    "Reuters",
    "trtspor",
    "ConflictTR",
    "buzzspor",
    "sporarena",
    "demarkesports",
    "F1tutkumuz"
]

BASE_URL = "https://nitter.net"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7456125265:AAHRuoYPWjshQb-R36MVpYL0n3CNesmM-eI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002517689872")
CHECK_INTERVAL = 60  # 1 dakika (test için)
REQUEST_DELAY = 5
RETRY_WAIT = 60

last_seen_tweets = {profile: set() for profile in PROFILES}

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_telegram_message(text):
    """Telegram'a mesaj gönder"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data, timeout=10)
        logger.info(f"Telegram response: {response.status_code}")
        return response.ok
    except Exception as e:
        logger.error(f"Telegram error: {str(e)}")
        return False

def get_tweets(profile):
    """Nitter'dan tweetleri requests ile çek"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        response = requests.get(f"{BASE_URL}/{profile}", headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Fetch error for {profile}: {str(e)}")
        return None

def check_profiles():
    """Tüm profilleri kontrol et"""
    for profile in PROFILES:
        try:
            html = get_tweets(profile)
            if not html:
                continue
                
            soup = BeautifulSoup(html, 'html.parser')
            tweets = soup.find_all("div", class_="tweet-content")
            tweet_links = soup.find_all("a", class_="tweet-link")
            
            for tweet, link in zip(tweets[:3], tweet_links[:3]):
                tweet_text = tweet.get_text().strip()
                tweet_url = BASE_URL + link['href']
                
                if tweet_url not in last_seen_tweets[profile]:
                    last_seen_tweets[profile].add(tweet_url)
                    message = f"🕊️ Yeni Tweet ({profile}):\n<b>{tweet_text}</b>\n\n🔗 {tweet_url}"
                    if send_telegram_message(message):
                        logger.info(f"Sent: {profile} - {tweet_text[:50]}...")
            
            time.sleep(REQUEST_DELAY)
            
        except Exception as e:
            logger.error(f"Error processing {profile}: {str(e)}")
            time.sleep(RETRY_WAIT)

@app.route('/')
def health_check():
    return "🤖 Twitter Bot Aktif (Requests)", 200

@app.route('/test')
def test_message():
    """Test endpoint"""
    if send_telegram_message("🔄 Bot test mesajı gönderiyor!"):
        return "Test mesajı gönderildi", 200
    return "Test mesajı gönderilemedi", 500

def run_bot():
    """Botu arka planda çalıştır"""
    logger.info("🔁 Bot başlatıldı")
    while True:
        check_profiles()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Test mesajı
    send_telegram_message("🤖 Bot başlatıldı (Requests Modu)")
    
    # Bot thread'i
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Flask uygulaması
    app.run(host='0.0.0.0', port=8080)
