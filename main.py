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
PROFILES = ["bpthaber", "Reuters", "trtspor"]
BASE_URL = "https://nitter.net"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL = 600  # 10 dakika
REQUEST_DELAY = 20    # Her profil arasında bekleme

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")  # Özellikle headless modda bazı ortamlarda yardımcı olabilir
    options.add_argument("--window-size=1920,1080") # Headless için bazen gerekebilir

    # Chrome binary'sini bul
    chrome_binary_path = shutil.which("google-chrome")
    if not chrome_binary_path:
        # Alternatif olarak 'google-chrome-stable' adıyla da PATH'te olabilir
        chrome_binary_path = shutil.which("google-chrome-stable")
    
    # PATH'te bulunamazsa, bilinen yaygın yolları kontrol et
    if not chrome_binary_path:
        common_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/opt/google/chrome/chrome" # Bazen buraya da kurulabilir
        ]
        for path_option in common_paths:
            if os.path.exists(path_option):
                chrome_binary_path = path_option
                logger.info(f"Chrome binary manuel olarak şu yolda bulundu: {chrome_binary_path}")
                break
    
    if not chrome_binary_path or not os.path.exists(chrome_binary_path):
        error_msg = (
            "Chrome binary PATH üzerinde veya bilinen yaygın yollarda bulunamadı. "
            f"shutil.which('google-chrome') sonucu: {shutil.which('google-chrome')}, "
            f"shutil.which('google-chrome-stable') sonucu: {shutil.which('google-chrome-stable')}."
        )
        logger.critical(error_msg)
        raise FileNotFoundError(error_msg)
    
    logger.info(f"Kullanılacak Chrome binary: {chrome_binary_path}")
    options.binary_location = chrome_binary_path
    
    # ChromeDriver'ı bul
    chromedriver_exe_path = shutil.which("chromedriver")
    
    if not chromedriver_exe_path:
        common_cd_paths = [
            "/usr/bin/chromedriver",
            "/usr/local/bin/chromedriver" # ChromeDriver bazen buraya da kurulabilir
        ]
        for cd_path_option in common_cd_paths:
            if os.path.exists(cd_path_option):
                chromedriver_exe_path = cd_path_option
                logger.info(f"ChromeDriver manuel olarak şu yolda bulundu: {chromedriver_exe_path}")
                break

    if not chromedriver_exe_path or not os.path.exists(chromedriver_exe_path):
        error_msg_cd = (
            "ChromeDriver PATH üzerinde veya bilinen yaygın yollarda bulunamadı. "
            f"shutil.which('chromedriver') sonucu: {shutil.which('chromedriver')}."
        )
        logger.critical(error_msg_cd)
        raise FileNotFoundError(error_msg_cd)

    logger.info(f"Kullanılacak ChromeDriver: {chromedriver_exe_path}")
    
    # ChromeDriver loglamasını etkinleştirmek (sorun giderme için faydalı olabilir)
    service_args = ["--verbose", "--log-path=/tmp/chromedriver.log"]
    service = Service(
        executable_path=chromedriver_exe_path,
        service_args=service_args
    )
    
    logger.info("WebDriver (Chrome) başlatılıyor...")
    try:
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("WebDriver (Chrome) başarıyla başlatıldı.")
        return driver
    except Exception as e:
        logger.critical(f"WebDriver (Chrome) başlatılırken kritik bir hata oluştu: {str(e)}")
        # /tmp/chromedriver.log dosyasını kontrol edin (eğer imaj içinde erişiminiz varsa)
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
    """Profil tweetlerini çek"""
    try:
        url = f"{BASE_URL}/{profile}"
        logger.info(f"{profile} için veri çekiliyor: {url}")
        
        driver.get(url)
        
        # DÜZELTİLMİŞ KISIM (Parantez hatası giderildi)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "tweet-content"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tweets = soup.find_all("div", class_="tweet-content", limit=3)
        
        return [tweet.get_text().strip() for tweet in tweets] if tweets else []
        
    except Exception as e:
        logger.error(f"{profile} çekme hatası: {str(e)}")
        return []

def main():
    logger.info("Bot başlatılıyor...")
    
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
                tweets = scrape_profile(driver, profile)
                if tweets:
                    message = f"🐦 {profile} son tweetler:\n\n" + "\n\n".join(tweets)
                    if send_telegram_message(message):
                        logger.info(f"{profile} tweetleri gönderildi")
                time.sleep(REQUEST_DELAY)
            
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
