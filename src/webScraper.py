from bs4 import BeautifulSoup
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import threading
import time
import schedule
from itertools import zip_longest
import requests
from urllib.parse import urljoin, urlparse
import hashlib

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from camoufox.sync_api import Camoufox

# Data storage file
DATA_FILE = 'pokemon_data.json'
IMAGES_DIR = 'cached_images'

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

def ensure_images_dir():
    """Create images directory if it doesn't exist"""
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)
        print("Image directory created at:", IMAGES_DIR)

def clear_cached_images():
    """Delete all cached images"""
    if os.path.exists(IMAGES_DIR):
        try:
            for filename in os.listdir(IMAGES_DIR):
                file_path = os.path.join(IMAGES_DIR, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            print(f"Cleared all cached images from {IMAGES_DIR}")
        except Exception as e:
            print(f"Error clearing cached images: {e}")
    ensure_images_dir()  # Recreate the directory if it was deleted

def download_image(url, filename):
    """Download an image and save it locally"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        filepath = os.path.join(IMAGES_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        return filepath
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return None

def get_image_filename(url):
    """Generate a filename for an image URL"""
    # Create a hash of the URL to ensure unique filenames
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    # Get file extension
    parsed_url = urlparse(url)
    path = parsed_url.path
    ext = os.path.splitext(path)[1] if '.' in path else '.jpg'
    return f"{url_hash}{ext}"

def should_update_data():
    """Check if we should update data (1st, 2nd, 3rd, and last day of month)"""
    now = datetime.now()
    
    # Check if it's the 1st, 2nd, or 3rd day of the month
    if 1 <= now.day <= 3:
        return True
    
    # Check if it's the last day of the month
    # Get the last day of the current month
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_month = now.replace(month=now.month + 1, day=1)
    
    last_day_of_month = (next_month - timedelta(days=1)).day
    
    if now.day == last_day_of_month:
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
    
    # Extract images from tables
    table_images = []
    tables = soup.find_all("table")
    for table in tables:
        images = table.find_all("img")
        table_imgs = []
        for img in images:
            src = img.get("src")
            if src:
                # Convert relative URLs to absolute
                absolute_url = urljoin(url, src)
                table_imgs.append(absolute_url)
        table_images.append(table_imgs)
    
    return {
        "h2": h2_texts, 
        "h1": h1_texts, 
        "tbody": tbody_texts,
        "table_images": table_images
    }

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
    
    # Clear all cached images before scraping new ones
    clear_cached_images()
    ensure_images_dir()
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
                elif boss == 'sierra':
                    headers = content["h2"][2:9]
                else:
                    headers = content["h2"][1:8]
                
                rows = [cleanBodyText(row) for row in content["tbody"][1:]]
                rows = [list(col) for col in zip_longest(*rows, fillvalue="")]
                
                # Download and store images
                downloaded_images = []
                for table_imgs in content["table_images"]:
                    table_downloaded = []
                    for img_url in table_imgs:
                        filename = get_image_filename(img_url)
                        filepath = download_image(img_url, filename)
                        if filepath:
                            table_downloaded.append(filename)
                        else:
                            table_downloaded.append(None)
                    downloaded_images.append(table_downloaded)
                print(downloaded_images)
                
                # Separate header images from body images
                header_images = []
                body_images = []
                
                header_images = downloaded_images[0] if downloaded_images else []
                body_images = downloaded_images[1:] if len(downloaded_images) > 1 else []
                
                # Transpose body images to match row structure
                transposed_body_images = []
                if body_images:
                    max_body_images = max(len(table_body) for table_body in body_images) if body_images else 0
                    for img_index in range(max_body_images):
                        row_images = []
                        for table_body_images in body_images:
                            if img_index < len(table_body_images):
                                row_images.append(table_body_images[img_index])
                            else:
                                row_images.append(None)
                        transposed_body_images.append(row_images)
                
                cached_data[boss] = {
                    "title": content["h1"][0],
                    "url": url,
                    "headers": headers,
                    "rows": rows,
                    "header_images": header_images,
                    "body_images": transposed_body_images,
                    "last_updated": datetime.now().isoformat()
                }
                print(f"Successfully cached {boss} data with {len(header_images)} header images and {sum(len(row) for row in transposed_body_images)} body images")
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
    def scheduled_update():
        if should_update_data():
            print(f"Scheduled update triggered on {datetime.now().strftime('%Y-%m-%d')}")
            fetch_and_cache_data()
        else:
            print(f"Skipping update - not first 3 days or last day of month ({datetime.now().strftime('%Y-%m-%d')})")
    
    schedule.every().day.at("00:00").do(scheduled_update)
    schedule.every().day.at("12:00").do(scheduled_update)
    
    print("Scheduler started - will check for updates twice daily")
    print("Updates will only run on the 1st, 2nd, 3rd, and last day of each month")
    
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

@app.route('/api/clear-images')
def clear_images():
    """Manually clear all cached images"""
    clear_cached_images()
    return jsonify({"message": "Cached images cleared successfully"})

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
    
    # Add information about whether today is an update day
    status['is_update_day'] = should_update_data()
    status['current_date'] = datetime.now().strftime('%Y-%m-%d')
    
    return jsonify(status)

@app.route('/api/images/<filename>')
def serve_image(filename):
    """Serve cached images"""
    return send_from_directory(IMAGES_DIR, filename)

if __name__ == "__main__":
    # Initial data fetch if no cached data exists
    cached_data = load_cached_data()
    if not cached_data:
        print("No cached data found, performing initial fetch...")
        fetch_and_cache_data()
    
    app.run(port=5000)