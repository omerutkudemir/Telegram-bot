from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import time
import random
import os
from flask import Flask, request
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
REQUEST_DELAY = 5  # 5 saniye gecikme
RETRY_WAIT = 60  # 60 saniye bekle

last_seen_tweets = {profile: set() for profile in PROFILES}

def send_telegram_message(text):
    """Telegram'a mesaj gönder"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data, timeout=10)
        if not response.ok:
            print(f"Telegram error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Telegram send error: {str(e)}")

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
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable"
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            options.binary_location = path
            break
    
    # Use ChromeDriverManager with specific version
    service = Service(ChromeDriverManager(version='114.0.5735.90').install())
    
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def check_profiles():
    """Check Twitter profiles and send new tweets"""
    driver = None
    try:
        driver = setup_driver()
        for profile in PROFILES:
            try:
                url = f"{BASE_URL}/{profile}"
                print(f"Checking {url}...")
                
                driver.get(url)
                time.sleep(3)
                
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
                        print(f"Sent tweet: {tweet_text[:50]}...")
                
                time.sleep(REQUEST_DELAY + random.uniform(0, 2))
                
            except Exception as e:
                print(f"Error checking {profile}: {str(e)}")
                time.sleep(RETRY_WAIT)
                
    except Exception as e:
        print(f"Critical error: {str(e)}")
    finally:
        if driver:
            driver.quit()

@app.route('/')
def health_check():
    """Health check endpoint for Render"""
    return "Twitter Bot is running", 200

def run_bot():
    """Run the bot in background"""
    print("🔁 Twitter Telegram Botu Başladı...")
    while True:
        check_profiles()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Start bot in background thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask app for Render port binding
    app.run(host='0.0.0.0', port=8080)
