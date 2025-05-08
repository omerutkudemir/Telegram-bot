from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
    "omerutkuDemir",  # Virgül eklendi
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
        logger.info(f"Telegram response: {response.status_code} - {response.text}")
        if not response.ok:
            logger.error(f"Telegram error: {response.status_code} - {response.text}")
        return response.json()
    except Exception as e:
        logger.error(f"Telegram send error: {str(e)}")
        return None

def setup_driver():
    """Chrome driver setup for Render"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    
    # Render compatible Chrome paths
    chrome_paths = [
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome"
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            options.binary_location = path
            logger.info(f"Using Chrome binary at: {path}")
            break
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        logger.error(f"Driver init error: {str(e)}")
        raise

def check_profiles():
    """Check profiles and send new tweets"""
    driver = None
    try:
        driver = setup_driver()
        for profile in PROFILES:
            try:
                url = f"{BASE_URL}/{profile}"
                logger.info(f"Checking: {url}")
                
                driver.get(url)
                time.sleep(3)
                
                # Debug: Save page source
                with open(f"{profile}_debug.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                tweets = soup.find_all("div", class_="tweet-content")
                tweet_links = soup.find_all("a", class_="tweet-link")
                
                if not tweets:
                    logger.warning(f"No tweets found for {profile}")
                    continue
                
                for tweet, link in zip(tweets[:3], tweet_links[:3]):
                    tweet_text = tweet.get_text().strip()
                    tweet_url = BASE_URL + link['href']
                    
                    if tweet_url not in last_seen_tweets[profile]:
                        last_seen_tweets[profile].add(tweet_url)
                        message = f"🕊️ Yeni Tweet ({profile}):\n<b>{tweet_text}</b>\n\n🔗 {tweet_url}"
                        result = send_telegram_message(message)
                        if result and result.get('ok'):
                            logger.info(f"Sent tweet: {profile} - {tweet_text[:50]}...")
                        else:
                            logger.error(f"Failed to send tweet: {profile}")
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                logger.error(f"Error checking {profile}: {str(e)}")
                time.sleep(RETRY_WAIT)
                
    except Exception as e:
        logger.critical(f"Critical error: {str(e)}")
    finally:
        if driver:
            driver.quit()

@app.route('/')
def health_check():
    return "🤖 Twitter Bot Aktif", 200

@app.route('/test')
def test_message():
    """Test message endpoint"""
    test_msg = "🔄 Bot test mesajı gönderiyor!"
    result = send_telegram_message(test_msg)
    return f"Test mesajı gönderildi: {result}"

def run_bot():
    """Run bot in background"""
    logger.info("🔁 Bot başlatıldı")
    while True:
        check_profiles()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Initial test
    send_telegram_message("🤖 Bot Render'da başlatıldı!")
    
    # Start bot thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=8080)
