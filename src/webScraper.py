from bs4 import BeautifulSoup
from flask import Flask, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import threading
import time
import schedule

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from camoufox.sync_api import Camoufox

# Data storage file
DATA_FILE = 'pokemon_data.json'

def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222")

    # point to the OS-installed chromedriver
    service = Service("/usr/bin/chromedriver")
    driver  = webdriver.Chrome(service=service, options=options)
    return driver

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://google.com",
    "Connection": "keep-alive",
    "DNT": "1",  # Do Not Track
    "Upgrade-Insecure-Requests": "1",
}

def load_cached_data():
    """Load data from JSON file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}

def save_cached_data(data):
    """Save data to JSON file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Error saving data: {e}")

def should_update_data():
    """Check if we should update data (start or end of month)"""
    now = datetime.now()
    
    # Check if it's the start of the month (1st-3rd)
    if 1 <= now.day <= 3:
        return True
    
    # Check if it's the end of the month (last 3 days)
    next_month = now.replace(day=28) + timedelta(days=4)
    last_day_of_month = (next_month - timedelta(days=next_month.day)).day
    if now.day >= last_day_of_month - 2:
        return True
    
    return False

def getPageContent(url, timeout=10):
    with Camoufox(headless=True, geoip=True) as browser:
        page = browser.new_page()
        page.goto(url, timeout=timeout * 1000)    # timeout in ms
        html = page.content()                      # get rendered HTML

    # parse with BeautifulSoup as before
    soup = BeautifulSoup(html, "html.parser")
    h2_texts = [tag.get_text(strip=True) for tag in soup.find_all("h2")]
    h1_texts = [tag.get_text(strip=True) for tag in soup.find_all("h1")]
    tbody_texts = [
        tag.get_text(separator="\n", strip=True)
        for tag in soup.find_all("tbody")
    ]
    return {"h2": h2_texts, "h1": h1_texts, "tbody": tbody_texts}

def cleanBodyText(text):
    chunks = []
    buf = []
    newline_count = 0

    for ch in text[14:]:
        if ch == "\n":
            newline_count += 1
            if newline_count % 2 == 0:
                chunks.append("".join(buf))
                buf = []
            else:
                buf.append("\n")
        else:
            buf.append(ch)

    if buf:
        chunks.append("".join(buf))
    return chunks

def fetch_and_cache_data():
    """Fetch all data and cache it"""
    print(f"Fetching data at {datetime.now()}")
    
    cached_data = load_cached_data()
    
    # URLs for each boss
    urls = {
        'giovanni': "https://pokemongohub.net/post/guide/rocket-boss-giovanni-counters/",
        'arlo': "https://pokemongohub.net/post/guide/rocket-leader-arlo-counters/",
        'cliff': "https://pokemongohub.net/post/guide/rocket-leader-cliff-counters/",
        'sierra': "https://pokemongohub.net/post/guide/rocket-leader-sierra-counters/"
    }
    
    for boss, url in urls.items():
        try:
            content = getPageContent(url)
            if content:
                if boss == 'giovanni':
                    headers = content["h2"][2:7]
                else:
                    headers = content["h2"][1:8]
                    
                rows = [cleanBodyText(row) for row in content["tbody"][1:]]
                rows = [list(col) for col in zip(*rows)]
                
                cached_data[boss] = {
                    "title": content["h1"][0],
                    "url": url,
                    "headers": headers,
                    "rows": rows,
                    "last_updated": datetime.now().isoformat()
                }
                print(f"Successfully cached {boss} data")
        except Exception as e:
            print(f"Error fetching {boss} data: {e}")
    
    save_cached_data(cached_data)

def get_cached_boss_data(boss_name):
    """Get cached data for a specific boss"""
    cached_data = load_cached_data()
    
    if boss_name in cached_data:
        return cached_data[boss_name]
    
    # If no cached data, fetch it now
    fetch_and_cache_data()
    cached_data = load_cached_data()
    return cached_data.get(boss_name, {"title": "", "url": "", "headers": [], "rows": []})

# Schedule data fetching
def run_scheduler():
    """Run the scheduler in a separate thread"""
    schedule.every().day.at("00:00").do(lambda: fetch_and_cache_data() if should_update_data() else None)
    schedule.every().day.at("12:00").do(lambda: fetch_and_cache_data() if should_update_data() else None)
    
    while True:
        schedule.run_pending()
        time.sleep(3600)  # Check every hour

# Start scheduler in background thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

@app.route('/api/giovanniTeam')
def get_giovanni_data():
    data = get_cached_boss_data('giovanni')
    return jsonify(data)

@app.route('/api/arloTeam')
def get_arlo_data():
    data = get_cached_boss_data('arlo')
    return jsonify(data)

@app.route('/api/cliffTeam')
def get_cliff_data():
    data = get_cached_boss_data('cliff')
    return jsonify(data)

@app.route('/api/sierraTeam')
def get_sierra_data():
    data = get_cached_boss_data('sierra')
    return jsonify(data)

@app.route('/api/refresh')
def force_refresh():
    """Manually trigger a data refresh"""
    fetch_and_cache_data()
    return jsonify({"message": "Data refreshed successfully"})

@app.route('/api/status')
def get_status():
    """Get the last update time for all data"""
    cached_data = load_cached_data()
    status = {}
    for boss in ['giovanni', 'arlo', 'cliff', 'sierra']:
        if boss in cached_data and 'last_updated' in cached_data[boss]:
            status[boss] = cached_data[boss]['last_updated']
        else:
            status[boss] = "Never updated"
    return jsonify(status)

if __name__ == "__main__":
    # Initial data fetch if no cached data exists
    cached_data = load_cached_data()
    if not cached_data:
        print("No cached data found, performing initial fetch...")
        fetch_and_cache_data()
    
    app.run(port=5000)