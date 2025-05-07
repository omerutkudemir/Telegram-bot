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
CHECK_INTERVAL = 300  # 5 dakika
REQUEST_DELAY = 5  # Her profil arasında 5 saniye gecikme

last_seen_tweets = {profile: set() for profile in PROFILES}


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    response = requests.post(url, data=data)
    if not response.ok:
        print(f"[HATA] Telegram mesajı gönderilemedi: {response.status_code} - {response.text}")


def setup_driver():
    options = Options()
    options.headless = True
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def check_profiles():
    driver = setup_driver()
    try:
        for profile in PROFILES:
            try:
                url = f"{BASE_URL}/{profile}"
                print(f"[DEBUG] {url} kontrol ediliyor...")
                driver.get(url)
                time.sleep(3)  # Sayfanın yüklenmesini bekle
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # Tweet'leri bul
                tweets = soup.find_all("div", class_="tweet-content")
                tweet_links = soup.find_all("a", class_="tweet-link")

                for tweet, link in zip(tweets[:5], tweet_links[:5]):  # Son 5 tweet'i kontrol et
                    tweet_text = tweet.get_text().strip()
                    tweet_url = BASE_URL + link['href']
                    if tweet_url not in last_seen_tweets[profile]:
                        last_seen_tweets[profile].add(tweet_url)
                        message = f"🕊️ Yeni Tweet ({profile}): <b>{tweet_text}</b>\n\n{tweet_url}"
                        send_telegram_message(message)
                        print(f"[BAŞARILI] {profile} için tweet gönderildi: {tweet_text[:50]}...")

            except Exception as e:
                print(f"[HATA] {profile} kontrol edilirken hata: {e}")

            time.sleep(REQUEST_DELAY + random.uniform(0, 2))  # Rastgele gecikme

    finally:
        driver.quit()


if __name__ == "__main__":
    print("🔁 Twitter Telegram Botu Başladı...")
    while True:
        check_profiles()
        time.sleep(CHECK_INTERVAL)