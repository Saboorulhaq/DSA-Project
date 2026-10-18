import os
import sys
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (university DSA project)"}


def main():
    if len(sys.argv) < 2:
        print('Usage: python check_site.py "URL" "css selector of ONE item (optional)"')
        return
    url = sys.argv[1]
    selector = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
    except requests.exceptions.RequestException as error:
        print("Network error:", error)
        return

    print("HTTP status:", response.status_code)
    print("Page size (characters):", len(response.text))
    soup = BeautifulSoup(response.text, "html.parser")
    print("Page title:", soup.title.get_text(strip=True) if soup.title else "(none)")

    lower = response.text.lower()
    for word in ["captcha", "unusual traffic", "slide to verify", "access denied"]:
        if word in lower:
            print(f"WARNING: the page contains '{word}' (possible bot check)")

    if selector:
        print(f"Items matching '{selector}':", len(soup.select(selector)))

    os.makedirs("data", exist_ok=True)
    with open("data/debug_page.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved the downloaded page to data/debug_page.html")

    parts = urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        robots = requests.get(robots_url, headers=HEADERS, timeout=20)
        print("\nrobots.txt status:", robots.status_code)
        print(robots.text[:600])
    except requests.exceptions.RequestException as error:
        print("Could not read robots.txt:", error)


if __name__ == "__main__":
    main()