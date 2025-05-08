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
import subprocess

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
        if not response.ok:
            logger.error(f"Telegram error: {response.text}")
        return response.ok
    except Exception as e:
        logger.error(f"Telegram send error: {str(e)}")
        return False

def install_chrome():
    """Chrome kurulumu için yardımcı fonksiyon"""
    try:
        chrome_installed = subprocess.run(["which", "google-chrome"], capture_output=True).returncode == 0
        if not chrome_installed:
            logger.info("Chrome kuruluyor...")
            subprocess.run([
                "apt-get", "update",
                "&&", "apt-get", "install", "-y", "wget",
                "&&", "wget", "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb",
                "&&", "dpkg", "-i", "google-chrome-stable_current_amd64.deb",
                "||", "apt-get", "install", "-f", "-y"
            ], check=True)
        return True
    except Exception as e:
        logger.error(f"Chrome kurulum hatası: {str(e)}")
        return False

def setup_driver():
    """Chrome driver setup for Render"""
    # Chrome kurulumunu kontrol et
    install_chrome()
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    
    # Chrome binary yolları
    chrome_path = None
    for path in [
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome"
    ]:
        if os.path.exists(path):
            chrome_path = path
            break
    
    if chrome_path:
        options.binary_location = chrome_path
        logger.info(f"Using Chrome at: {chrome_path}")
    else:
        logger.error("Chrome binary bulunamadı!")
        raise RuntimeError("Chrome binary bulunamadı")

    try:
        # ChromeDriverManager ile driver kurulumu
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
                
                # Sayfa kontrolü
                if "captcha" in driver.page_source.lower():
                    logger.warning(f"Captcha engeli: {profile}")
                    continue
                
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
                        if send_telegram_message(message):
                            logger.info(f"Sent tweet: {profile}")
                        else:
                            logger.error(f"Failed to send: {profile}")
                
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
    if send_telegram_message(test_msg):
        return "Test mesajı gönderildi", 200
    return "Test mesajı gönderilemedi", 500

def run_bot():
    """Run bot in background"""
    logger.info("🔁 Bot başlatıldı")
    while True:
        check_profiles()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Chrome kontrolü
    chrome_path = subprocess.run(["which", "google-chrome"], capture_output=True, text=True)
    logger.info(f"Chrome path: {chrome_path.stdout or 'Not found'}")
    
    # Test mesajı
    send_telegram_message("🤖 Bot başlatıldı!")
    
    # Bot thread'i
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Flask uygulaması
    app.run(host='0.0.0.0', port=8080)
