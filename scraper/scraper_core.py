"""
scraper_core.py - downloads pages, extracts records, supports pause/resume/stop.
It does NOT use any GUI code, so you can test it from the terminal (scrape_cli.py).
"""
import re
import threading
import time
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "DSAUniversityProject/1.0 (your_email@example.com)"}

class ScrapeError(Exception):
    pass


class ScrapeControl:
    """Flags that the GUI sets and the scraper loop checks."""

    def __init__(self):
        self._paused = threading.Event()
        self._stopped = threading.Event()

    def pause(self):
        self._paused.set()

    def resume(self):
        self._paused.clear()

    def stop(self):
        self._stopped.set()
        self._paused.clear()

    @property
    def paused(self):
        return self._paused.is_set()

    @property
    def stopped(self):
        return self._stopped.is_set()


def clean_value(raw, kind):
    """Turn raw text into a clean value. Missing -> 'N/A' (text) or 0 (numbers)."""
    raw = " ".join(str(raw).split()) if raw is not None else ""
    if kind == "text":
        return raw if raw else "N/A"
    match = re.search(r"-?\d[\d,]*\.?\d*", raw)
    if not match:
        return 0
    number = match.group().replace(",", "")
    try:
        return int(float(number)) if kind == "int" else float(number)
    except ValueError:
        return 0


def fetch_html(url, retries=4):
    """Download a page. Retries on network errors, HTTP 429 and HTTP 5xx."""
    last_error = "unknown error"
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            if response.status_code == 200:
                return response.text
            last_error = f"HTTP {response.status_code}"
            if response.status_code not in (429, 500, 502, 503, 504):
                break                      # e.g. 404: retrying will not help
        except requests.exceptions.RequestException as error:
            last_error = str(error)
        time.sleep(min(2 ** attempt * 0.5, 8))   # wait 0.5s, 1s, 2s, 4s ...
    raise ScrapeError(f"{url} failed: {last_error}")


def bump_page(url, param):
    """Return the same URL with its page number (query parameter `param`) increased by 1."""
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[param] = str(int(query.get(param, "1")) + 1)
    return urlunparse(parts._replace(query=urlencode(query)))


def parse_page(html, base_url, profile):
    """Return (list_of_records, next_page_url_or_None)."""
    soup = BeautifulSoup(html, "html.parser")
    records = []
    for item in soup.select(profile["item_selector"]):
        record = {}
        for name, (selector, attribute, kind) in profile["fields"].items():
            tag = item.select_one(selector)
            if tag is None:
                raw = None
            else:
                raw = tag.get(attribute) if attribute else tag.get_text()
            record[name] = clean_value(raw, kind)
        records.append(record)
    page_param = profile.get("page_param")
    if page_param:
        # Page-number mode: ...&page=1 -> ...&page=2. A page with no items means "the end".
        next_url = bump_page(base_url, page_param) if records else None
    else:
        builder = profile.get("next_url_builder")
        if builder:
            next_url = builder(base_url)
        else:
            next_tag = soup.select_one(profile["next_selector"])
            next_url = urljoin(base_url, next_tag["href"]) if next_tag and next_tag.get("href") else None
    return records, next_url


def run_scrape(profile, store, control, start_url, on_progress=None, on_status=None, on_paused=None):
    """
    Main loop. Returns one of: 'done', 'finished', 'stopped', 'error'.
      done     -> reached the target count
      finished -> site has no more pages (fewer records than target)
      stopped  -> user pressed Stop (progress saved)
      error    -> a page kept failing (progress saved, press Start to continue)
    """
    say = on_status or (lambda text: None)
    progress = on_progress or (lambda n: None)
    target = profile["target_count"]
    url = start_url
    announced_pause = False
    pages_without_new = 0

    while url and store.count < target:
        while control.paused and not control.stopped:
            if not announced_pause:
                say("Paused. Click Resume to continue.")
                if on_paused:
                    on_paused()
                announced_pause = True
            time.sleep(0.2)
        announced_pause = False
        if control.stopped:
            store.save_progress(url)
            say("Stopped. Progress saved.")
            return "stopped"

        say(f"Scraping: {url}")
        try:
            html = fetch_html(url)
        except ScrapeError as error:
            if profile.get("page_param") and store.count > 0 and "HTTP 404" in str(error):
                break                      # numbered pages ran out (site answers 404 after the last page)
            store.save_progress(url)
            say(f"Network problem, progress saved. {error}")
            return "error"

        records, next_url = parse_page(html, url, profile)
        added = store.add_records(records)
        pages_without_new = 0 if added else pages_without_new + 1
        if pages_without_new >= 3:         # the site keeps repeating old items -> stop
            store.save_progress(None)
            say("Three pages in a row gave no new records. Stopping.")
            break
        store.save_progress(next_url)
        progress(store.count)
        url = next_url

        delay = profile.get("delay_seconds", 0)
        waited = 0.0
        while waited < delay and not control.stopped:
            time.sleep(0.05)
            waited += 0.05

    if store.count >= target:
        say(f"Done. Collected {store.count:,} records.")
        return "done"
    say(f"No more pages. Collected only {store.count:,} records.")
    return "finished"
