from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import time
import random
import os

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
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    response = requests.post(url, data=data)
    if not response.ok:
        print(f"[HATA] Telegram mesajı gönderilemedi: {response.status_code} - {response.text}")
    time.sleep(1)

def setup_driver():
    try:
        options = Options()
        options.add_argument("--headless=new")  # Yeni headless mod
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920x1080")
        
        # Render için chromium binary yolu
        options.binary_location = "/usr/bin/chromium-browser"
        
        # WebDriverManager ile ChromeDriver kurulumu
        service = Service(ChromeDriverManager().install())
        
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Driver oluşturulurken hata: {str(e)}")
        raise

def check_profiles():
    driver = None
    try:
        driver = setup_driver()
        for profile in PROFILES:
            retries = 3
            for attempt in range(retries):
                try:
                    url = f"{BASE_URL}/{profile}"
                    print(f"[DEBUG] {url} kontrol ediliyor...")
                    
                    driver.get(url)
                    time.sleep(3)  # Sayfanın yüklenmesini bekle
                    
                    # Sayfa kaynağını al ve parse et
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
                            print(f"[BAŞARILI] {profile} için tweet gönderildi: {tweet_text[:50]}...")
                    
                    break  # Başarılı olduğunda döngüden çık
                
                except Exception as e:
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        wait_time = RETRY_WAIT + random.uniform(0, 5)
                        print(f"[HATA] {profile} için 429 Too Many Requests, {attempt + 1}/{retries} deneme, {wait_time} saniye bekleniyor...")
                        time.sleep(wait_time)
                    else:
                        print(f"[HATA] {profile} kontrol edilirken hata: {str(e)}")
                        break
            
            time.sleep(REQUEST_DELAY + random.uniform(0, 2))
    
    except Exception as e:
        print(f"[KRİTİK HATA] Profil kontrolü sırasında hata: {str(e)}")
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    print("🔁 Twitter Telegram Botu Başladı...")
    while True:
        check_profiles()
        time.sleep(CHECK_INTERVAL)
