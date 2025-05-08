from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
import time
import os
import logging
import sys

# Log ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Config
PROFILES = ["bpthaber", "Reuters", "trtspor"]  # İzlenecek hesaplar
BASE_URL = "https://nitter.net"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL = 600  # 10 dakika (saniye)
REQUEST_DELAY = 20  # Her profil arasında bekleme süresi

def setup_driver():
    """Chrome driver kurulumu"""
    options = Options()
    
    # Render optimizasyonları
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    
    # Chrome binary yolu (Dockerfile ile kuruldu)
    options.binary_location = "/usr/bin/google-chrome"
    
    # ChromeDriver ayarları
    service = Service(
        executable_path="/usr/bin/chromedriver",
        service_args=["--verbose", "--log-path=chromedriver.log"]
    )
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.error(f"Driver başlatma hatası: {str(e)}")
        raise

def send_telegram_message(text):
    """Telegram'a mesaj gönder"""
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        logger.error("Telegram bilgileri eksik!")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return True
        logger.error(f"Telegram hatası: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Telegram bağlantı hatası: {str(e)}")
    return False

def scrape_profile(driver, profile):
    """Tek bir profil için tweetleri çek"""
    try:
        url = f"{BASE_URL}/{profile}"
        logger.info(f"{profile} için veri çekiliyor: {url}")
        
        driver.get(url)
        
        # Sayfanın yüklenmesini bekle
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "tweet-content"))
        
        # Sayfa kaynağını parse et
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tweets = soup.find_all("div", class_="tweet-content", limit=3)
        
        if not tweets:
            logger.warning(f"{profile} için tweet bulunamadı")
            return []
            
        return [tweet.get_text().strip() for tweet in tweets]
        
    except Exception as e:
        logger.error(f"{profile} çekme hatası: {str(e)}")
        return []

def main():
    """Ana işlem döngüsü"""
    logger.info("Bot başlatılıyor...")
    
    # Başlangıç kontrolü
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        logger.error("HATA: Telegram bilgileri eksik!")
        return
    
    driver = None
    try:
        driver = setup_driver()
        logger.info("Chrome başarıyla başlatıldı")
        
        send_telegram_message("🤖 Bot başlatıldı")
        
        while True:
            for profile in PROFILES:
                try:
                    tweets = scrape_profile(driver, profile)
                    if tweets:
                        message = f"🐦 {profile} son tweetler:\n\n" + "\n\n".join(tweets)
                        if send_telegram_message(message):
                            logger.info(f"{profile} tweetleri gönderildi")
                            
                    time.sleep(REQUEST_DELAY)
                    
                except Exception as e:
                    logger.error(f"{profile} işlenirken hata: {str(e)}")
                    time.sleep(30)  # Hata durumunda bekle
            
            logger.info(f"{CHECK_INTERVAL} saniye bekleniyor...")
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Bot durduruluyor...")
    except Exception as e:
        logger.critical(f"Kritik hata: {str(e)}")
    finally:
        if driver:
            driver.quit()
        logger.info("Bot sonlandırıldı")

if __name__ == "__main__":
    main()
