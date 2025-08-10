from bs4 import BeautifulSoup
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
from itertools import zip_longest
import requests
from urllib.parse import urljoin, urlparse
import hashlib
import boto3

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from camoufox.sync_api import Camoufox

# Data storage - use S3 for persistent storage
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'pokemon-go-team-comp-data')
DATA_FILE = 'pokemon_data.json'
IMAGES_PREFIX = 'images/'

app = Flask(__name__)
CORS(app)

# Initialize AWS clients
s3_client = boto3.client('s3')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://google.com",
    "Connection": "keep-alive",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}

def load_cached_data():
    """Load data from S3"""
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=DATA_FILE)
        return json.loads(response['Body'].read().decode('utf-8'))
    except s3_client.exceptions.NoSuchKey:
        print("No cached data found in S3")
        return {}
    except Exception as e:
        print(f"Error loading data from S3: {e}")
        return {}

def save_cached_data(data):
    """Save data to S3"""
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=DATA_FILE,
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )
        print("Data saved to S3 successfully")
    except Exception as e:
        print(f"Error saving data to S3: {e}")

def is_data_missing_or_incomplete():
    """Check if data is missing or incomplete for any boss"""
    cached_data = load_cached_data()
    required_bosses = ['giovanni', 'arlo', 'cliff', 'sierra']
    
    # If no data at all
    if not cached_data:
        print("No cached data found - scraping needed")
        return True
    
    # Check each boss
    for boss in required_bosses:
        if boss not in cached_data:
            print(f"Missing data for {boss} - scraping needed")
            return True
        
        boss_data = cached_data[boss]
        # Check if essential fields are missing or empty
        if not boss_data.get('headers') or not boss_data.get('rows'):
            print(f"Incomplete data for {boss} - scraping needed")
            return True
        
        # Check if data is older than 7 days (fallback for stale data)
        last_updated = boss_data.get('last_updated')
        if last_updated:
            try:
                last_update_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                if datetime.now() - last_update_date > timedelta(days=7):
                    print(f"Stale data for {boss} (older than 7 days) - scraping needed")
                    return True
            except Exception as e:
                print(f"Error parsing last_updated for {boss}: {e} - scraping needed")
                return True
    
    print("All data present and recent")
    return False

def upload_image_to_s3(image_data, filename):
    """Upload image to S3 and return the filename"""
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{IMAGES_PREFIX}{filename}",
            Body=image_data,
            ContentType='image/jpeg'
        )
        return filename
    except Exception as e:
        print(f"Error uploading image {filename} to S3: {e}")
        return None

def download_and_upload_image(url, filename):
    """Download an image and upload it to S3"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        uploaded_filename = upload_image_to_s3(response.content, filename)
        return uploaded_filename
    except Exception as e:
        print(f"Error downloading/uploading image {url}: {e}")
        return None

def get_image_filename(url):
    """Generate a filename for an image URL"""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    parsed_url = urlparse(url)
    path = parsed_url.path
    ext = os.path.splitext(path)[1] if '.' in path else '.jpg'
    return f"{url_hash}{ext}"

def getPageContent(url, timeout=10):
    import subprocess
    import tempfile
    import sys
    import os
    
    # Set up environment for Xvfb if running in container
    env = os.environ.copy()
    if 'DISPLAY' not in env:
        env['DISPLAY'] = ':99'
    
    # Create a separate script to run camoufox in isolation
    script_content = '''
import sys
import os
from bs4 import BeautifulSoup
from camoufox.sync_api import Camoufox
from urllib.parse import urljoin
import json
import time

url = "%s"
timeout = %d

try:
    # Give some time for Xvfb to be ready if in container
    if os.environ.get('DISPLAY') == ':99':
        time.sleep(2)
    
    print(f"Starting scrape for URL: {url}", file=sys.stderr)
    
    # Configure Camoufox for headless container environment
    camoufox_options = {
        'headless': True, 
        'geoip': True,
        # Additional options for container environment
        'args': [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-software-rasterizer',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-java',
            '--memory-pressure-off',
            '--max_old_space_size=4096'
        ]
    }
    
    # If we're in a container environment, add extra stability options
    if os.environ.get('DISPLAY') == ':99':
        camoufox_options['args'].extend([
            '--single-process',
            '--no-zygote',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-sync'
        ])
    
    with Camoufox(**camoufox_options) as browser:
        print("Browser opened successfully", file=sys.stderr)
        page = browser.new_page()
        print(f"Navigating to {url}", file=sys.stderr)
        page.goto(url, timeout=timeout * 1000)
        # Wait a bit for dynamic content to load
        page.wait_for_timeout(3000)
        html = page.content()
        print(f"Page content retrieved, length: {len(html)}", file=sys.stderr)

    soup = BeautifulSoup(html, "html.parser")
    h2_texts = [tag.get_text(strip=True) for tag in soup.find_all("h2")]
    h1_texts = [tag.get_text(strip=True) for tag in soup.find_all("h1")]
    tbody_texts = [
        tag.get_text(separator="\\n", strip=True)
        for tag in soup.find_all("tbody")
    ]
    
    print(f"Found {len(h1_texts)} h1 tags, {len(h2_texts)} h2 tags, {len(tbody_texts)} tbody tags", file=sys.stderr)
    
    table_images = []
    tables = soup.find_all("table")
    for table in tables:
        images = table.find_all("img")
        table_imgs = []
        for img in images:
            src = img.get("src")
            if src:
                absolute_url = urljoin(url, src)
                table_imgs.append(absolute_url)
        table_images.append(table_imgs)
    
    result = {
        "h2": h2_texts, 
        "h1": h1_texts, 
        "tbody": tbody_texts,
        "table_images": table_images
    }
    
    print(json.dumps(result))
    
except Exception as e:
    import traceback
    error_details = {
        "error": str(e),
        "traceback": traceback.format_exc()
    }
    print(json.dumps(error_details), file=sys.stderr)
    sys.exit(1)
''' % (url, timeout)
    
    # Write script to temp file and execute it
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        temp_script = f.name
    
    try:
        result = subprocess.run([sys.executable, temp_script], 
                              capture_output=True, text=True, timeout=120, env=env)
        
        if result.returncode != 0:
            print(f"Camoufox subprocess failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")
            return {"h2": [], "h1": [], "tbody": [], "table_images": []}
            
        if not result.stdout.strip():
            print(f"Camoufox subprocess returned empty output")
            print(f"STDERR: {result.stderr}")
            return {"h2": [], "h1": [], "tbody": [], "table_images": []}
            
        return json.loads(result.stdout)
        
    except subprocess.TimeoutExpired as e:
        print(f"Camoufox subprocess timed out: {e}")
        return {"h2": [], "h1": [], "tbody": [], "table_images": []}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from camoufox subprocess: {e}")
        print(f"Raw output: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        # Try to extract JSON from the output by finding the last valid JSON object
        try:
            lines = result.stdout.strip().split('\n')
            for line in reversed(lines):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    return json.loads(line)
        except:
            pass
            
        return {"h2": [], "h1": [], "tbody": [], "table_images": []}
    finally:
        try:
            os.unlink(temp_script)
        except:
            pass

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
    """Fetch all data and cache it to S3"""
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
            if content and not content.get('error'):
                if boss == 'giovanni':
                    headers = content["h2"][2:7]
                elif boss == 'sierra':
                    headers = content["h2"][2:9]
                else:
                    headers = content["h2"][1:8]
                
                rows = [cleanBodyText(row) for row in content["tbody"][1:]]
                rows = [list(col) for col in zip_longest(*rows, fillvalue="")]
                
                # Download and upload images to S3
                downloaded_images = []
                for table_imgs in content["table_images"]:
                    table_downloaded = []
                    for img_url in table_imgs:
                        filename = get_image_filename(img_url)
                        uploaded_filename = download_and_upload_image(img_url, filename)
                        if uploaded_filename:
                            table_downloaded.append(uploaded_filename)
                        else:
                            table_downloaded.append(None)
                    downloaded_images.append(table_downloaded)
                
                # Process images as before...
                header_images = downloaded_images[0] if downloaded_images else []
                body_images = downloaded_images[1:] if len(downloaded_images) > 1 else []
                
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
                    "title": content["h1"][0] if content["h1"] else f"{boss.title()} Counters",
                    "url": url,
                    "headers": headers,
                    "rows": rows,
                    "header_images": header_images,
                    "body_images": transposed_body_images,
                    "last_updated": datetime.now().isoformat()
                }
                print(f"Successfully cached {boss} data")
            else:
                print(f"Failed to get content for {boss}")
        except Exception as e:
            print(f"Error fetching {boss} data: {e}")
    
    save_cached_data(cached_data)

def get_cached_boss_data(boss_name):
    """Get cached data for a specific boss"""
    cached_data = load_cached_data()
    
    if boss_name in cached_data:
        return cached_data[boss_name]
    
    return {"title": "", "url": "", "headers": [], "rows": [], "header_images": [], "body_images": []}

# ...existing code for routes...

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
    
    status['current_date'] = datetime.now().strftime('%Y-%m-%d')
    status['data_missing'] = is_data_missing_or_incomplete()
    return jsonify(status)

@app.route('/api/images/<filename>')
def serve_image(filename):
    """Serve images from S3"""
    try:
        # Generate a presigned URL for the image
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': f"{IMAGES_PREFIX}{filename}"},
            ExpiresIn=3600
        )
        return jsonify({"image_url": url})
    except Exception as e:
        print(f"Error serving image {filename}: {e}")
        return jsonify({"error": "Image not found"}), 404

if __name__ == "__main__":
    print("Starting Pokemon GO Team Comp Backend...")
    
    # Check if this is a scheduled scraping run or if data is missing
    if os.environ.get('RUN_SCRAPER', 'false').lower() == 'true' or is_data_missing_or_incomplete():
        print("Running scraping...")
        fetch_and_cache_data()
        
        # If this was just a scraping run, exit
        if os.environ.get('RUN_SCRAPER', 'false').lower() == 'true':
            print("Scraping completed, exiting...")
            exit(0)
    
    print("Starting Flask server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=False)