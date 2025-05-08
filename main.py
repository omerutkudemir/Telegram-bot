from bs4 import BeautifulSoup
import requests
import time
import random
import os
from flask import Flask
import threading
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

app = Flask(__name__)

# Yapılandırma
PROFILES = [
    "bpthaber",
    "Reuters",
    "trtspor",
    "sporarena"
]

# Farklı Nitter örnekleri (instances)
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.42l.fr",
    "https://nitter.poast.org",
    "https://nitter.nixnet.services"
]

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL = 600  # 10 dakika
MIN_DELAY = 20  # Minimum bekleme süresi (saniye)
MAX_DELAY = 40  # Maksimum bekleme süresi (saniye)

last_seen_tweets = {profile: set() for profile in PROFILES}

# Log ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Oturum ayarı
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

def get_random_headers():
    """Rastgele gerçekçi tarayıcı başlıkları oluştur"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "DNT": str(random.randint(0, 1)),
        "Connection": "keep-alive"
    }

def send_telegram_message(text):
    """Telegram'a mesaj gönder"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram bilgileri eksik!")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = session.post(url, data=data, timeout=15)
        if response.status_code == 200:
            return True
        logger.error(f"Telegram hatası: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Telegram gönderim hatası: {str(e)}")
    return False

def fetch_profile(profile):
    """Nitter'dan profil verilerini getir"""
    instance = random.choice(NITTER_INSTANCES)
    url = f"{instance}/{profile}"
    try:
        response = session.get(
            url,
            headers=get_random_headers(),
            timeout=20,
            allow_redirects=True
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.warning(f"{instance} {profile} için başarısız: {str(e)}")
        return None

def process_profile(profile):
    """Bir profil için tweetleri işle"""
    html = fetch_profile(profile)
    if not html:
        return
        
    soup = BeautifulSoup(html, 'html.parser')
    tweets = soup.find_all("div", class_="tweet-content")
    tweet_links = soup.find_all("a", class_="tweet-link")
    
    if not tweets:
        logger.info(f"{profile} için tweet bulunamadı")
        return
        
    for tweet, link in zip(tweets[:3], tweet_links[:3]):
        tweet_text = tweet.get_text().strip()
        tweet_url = link['href'] if link['href'].startswith('http') else f"https://nitter.net{link['href']}"
        
        if tweet_url not in last_seen_tweets[profile]:
            last_seen_tweets[profile].add(tweet_url)
            message = f"🕊️ Yeni Tweet ({profile}):\n<b>{tweet_text}</b>\n\n🔗 {tweet_url}"
            if send_telegram_message(message):
                logger.info(f"Gönderildi: {profile} - {tweet_text[:50]}...")
            else:
                logger.error(f"Gönderilemedi: {profile}")

def check_profiles():
    """Tüm profilleri kontrol et"""
    logger.info("Profil kontrolü başladı")
    for profile in PROFILES:
        process_profile(profile)
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        logger.info(f"{delay:.1f} saniye bekleniyor...")
        time.sleep(delay)
    logger.info("Profil kontrolü tamamlandı")

@app.route('/')
def health_check():
    return "🤖 Twitter Bot Aktif", 200

@app.route('/test')
def test_message():
    """Test endpointi"""
    if send_telegram_message("🔍 Bot çalışıyor ve test mesajı gönderiyor!"):
        return "Test mesajı başarıyla gönderildi", 200
    return "Test mesajı gönderilemedi", 500

def run_bot():
    """Botu arka planda çalıştır"""
    logger.info("🤖 Bot başlatıldı")
    while True:
        check_profiles()
        logger.info(f"{CHECK_INTERVAL} saniye bekleniyor...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Başlangıç testi
    send_telegram_message("🚀 Twitter Bot başlatıldı")
    
    # Bot thread'i
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Flask uygulaması
    app.run(host='0.0.0.0', port=8080)
