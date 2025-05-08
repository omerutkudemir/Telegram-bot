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

app = Flask(__name__)

# Config
PROFILES = [
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
TELEGRAM_CHAT_ID = "-1002517689872"
CHECK_INTERVAL = 600  # 10 dakika
REQUEST_DELAY = 5  # Her profil arasında 5 saniye gecikme
RETRY_WAIT = 60  # 429 hatasında 60 saniye bekle

last_seen_tweets = {profile: set() for profile in PROFILES}

def send_telegram_message(text):
    """Telegram'a mesaj gönder"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data, timeout=10)
        if not response.ok:
            print(f"[TELEGRAM HATA] {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[TELEGRAM HATA] Mesaj gönderilemedi: {str(e)}")

def setup_driver():
    """Chrome driver kurulumu (Render uyumlu)"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    
    # Render için Chrome binary yolları
    chrome_paths = [
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome"
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            options.binary_location = path
            print(f"Chrome binary bulundu: {path}")
            break
    
    try:
        # ChromeDriverManager ile driver kurulumu
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"[DRIVER HATA] Chrome başlatılamadı: {str(e)}")
        raise

def check_profiles():
    """Tüm profilleri kontrol et ve yeni tweetleri gönder"""
    driver = None
    try:
        driver = setup_driver()
        for profile in PROFILES:
            retries = 3
            for attempt in range(retries):
                try:
                    url = f"{BASE_URL}/{profile}"
                    print(f"[KONTROL] {url} kontrol ediliyor...")
                    
                    driver.get(url)
                    time.sleep(3)  # Sayfanın yüklenmesini bekle
                    
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    tweets = soup.find_all("div", class_="tweet-content")
                    tweet_links = soup.find_all("a", class_="tweet-link")
                    
                    for tweet, link in zip(tweets[:5], tweet_links[:5]):
                        tweet_text = tweet.get_text().strip()
                        tweet_url = BASE_URL + link['href']
                        
                        if tweet_url not in last_seen_tweets[profile]:
                            last_seen_tweets[profile].add(tweet_url)
                            message = f"🕊️ Yeni Tweet ({profile}): <b>{tweet_text}</b>\n\n{tweet_url}"
                            send_telegram_message(message)
                            print(f"[GÖNDERİLDİ] {profile}: {tweet_text[:50]}...")
                    
                    break  # Başarılı olduğunda döngüden çık
                
                except Exception as e:
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        wait_time = RETRY_WAIT + random.uniform(0, 5)
                        print(f"[429 HATA] {profile} için yeniden deneme ({attempt+1}/{retries}), {wait_time}s bekleniyor...")
                        time.sleep(wait_time)
                    else:
                        print(f"[PROFIL HATA] {profile} kontrolü başarısız: {str(e)}")
                        break
            
            time.sleep(REQUEST_DELAY + random.uniform(0, 2))
    
    except Exception as e:
        print(f"[KRİTİK HATA] Bot çalışırken hata: {str(e)}")
    
    finally:
        if driver:
            driver.quit()

@app.route('/')
def health_check():
    """Render health check endpoint"""
    return "🤖 Twitter Bot Aktif | /log için logları görüntüle", 200

@app.route('/log')
def show_log():
    """Son 100 satır log göster"""
    import subprocess
    result = subprocess.run(['tail', '-n', '100', '/var/log/render.log'], 
                          capture_output=True, text=True)
    return f"<pre>{result.stdout}</pre>"

def run_bot():
    """Botu arka planda çalıştır"""
    print("🔁 Twitter Telegram Botu Başladı...")
    while True:
        check_profiles()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Botu thread'de başlat
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Flask uygulamasını başlat (Render port bağlama için)
    app.run(host='0.0.0.0', port=8080)
