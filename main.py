from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import time
import os
import logging
import subprocess

# Log ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
PROFILES = ["bpthaber", "Reuters", "trtspor"]  # Test için 3 profil
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL = 600  # 10 dakika
REQUEST_DELAY = 15  # Her istek arasında 15 saniye

def setup_chrome():
    """Render için Chrome kurulumu"""
    try:
        # Chrome kurulu mu kontrol et
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

def get_driver():
    """Chrome driver ayarları"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.binary_location = "/usr/bin/google-chrome"  # Render için sabit yol

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        logger.error(f"Driver hatası: {str(e)}")
        raise

def send_telegram_message(text):
    """Telegram mesaj gönderimi"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram bilgileri eksik!")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            return True
        logger.error(f"Telegram hatası: {response.status_code}")
    except Exception as e:
        logger.error(f"Telegram bağlantı hatası: {str(e)}")
    return False

def check_profiles():
    """Profil kontrollerini yürüt"""
    if not setup_chrome():
        logger.error("Chrome kurulumu başarısız!")
        return

    driver = None
    try:
        driver = get_driver()
        for profile in PROFILES:
            try:
                url = f"https://nitter.net/{profile}"
                logger.info(f"{profile} kontrol ediliyor...")
                
                driver.get(url)
                time.sleep(3)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                tweets = soup.find_all("div", class_="tweet-content")
                
                if tweets:
                    tweet_text = tweets[0].get_text().strip()
                    message = f"🕊️ Yeni Tweet ({profile}):\n<b>{tweet_text}</b>"
                    if send_telegram_message(message):
                        logger.info(f"Gönderildi: {profile}")
                
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                logger.error(f"{profile} hatası: {str(e)}")
                time.sleep(30)  # Hata durumunda 30 saniye bekle
                
    except Exception as e:
        logger.critical(f"Kritik hata: {str(e)}")
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    # Başlangıç kontrolü
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Lütfen Render'da TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID ayarlayın!")
    else:
        logger.info("Bot başlatılıyor...")
        send_telegram_message("🤖 Bot başlatıldı")
        while True:
            check_profiles()
            time.sleep(CHECK_INTERVAL)
