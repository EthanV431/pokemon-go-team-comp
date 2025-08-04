import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from flask import Flask, jsonify
from flask_cors import CORS
from functools import lru_cache

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MyNewsBot/1.0)"
}

def getLatestArticle(query):
    # 1) build the search URL
    url = f"https://gamerant.com/search/?q={quote_plus(query)}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    # 2) parse the search‐results page
    soup = BeautifulSoup(resp.text, "html.parser")

    # 3) grab the first <h5 class="display-card-title"> → <a>
    link_tag = soup.select_one("h5.display-card-title > a")
    if not link_tag:
        return None

    # 4) extract clean title text
    title = link_tag.get_text(strip=True)

    # 5) build absolute URL
    href = link_tag["href"]
    if href.startswith("/"):
        href = "https://gamerant.com" + href

    return title, href

def getPageContent(url, timeout=10):
    """
    Fetch the given URL and extract text from all <h3> and <tbody> elements.

    Returns a dict with two lists: 'h3' and 'tbody'.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Scraper/1.0)"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # get all <h3> text
    h3_texts = [tag.get_text(strip=True) for tag in soup.find_all("h3")]

    # get all <tbody> text (preserving line breaks between rows)
    tbody_texts = [
        tag.get_text(separator="\n", strip=True)
        for tag in soup.find_all("tbody")
    ]

    return {"h3": h3_texts, "tbody": tbody_texts}


def cleanBodyText(text):
    chunks = []
    buf = []
    newline_count = 0

    for ch in text:
        if ch == "\n":
            newline_count += 1
            if newline_count % 3 == 0:
                chunks.append("".join(buf))
                buf = []
            else:
                buf.append("\n")
        else:
            buf.append(ch)

    if buf:
        chunks.append("".join(buf))

    return chunks


@lru_cache(maxsize=1)
def fetch_latest():
    return getLatestArticle("how to beat giovanni pokemon go")

@app.route('/api/data')
def get_data():
    latest = fetch_latest()    # cached on second call
    data = [[], []]
    if latest:
        title, url = latest
        content = getPageContent(url)
        if content:
            for i in range(1, len(content["h3"]) - 3):
                data[0].append(content["h3"][i])
            for i in range(1, len(content["tbody"])):
                data[1].append(cleanBodyText(content["tbody"][i]))
        return jsonify({
            "title": title,
            "url":   url,
            "headers": data[0],
            "rows":    data[1]
        })
    return jsonify({"headers": [], "rows": []})

"""
@app.route('/api/title')
def get_title():
    latest = fetch_latest()
    if latest:
        title, url = latest
        return jsonify({"title": title, "url": url})
    return jsonify({"title": None})
"""

if __name__ == "__main__":
    app.run(port=5000)
