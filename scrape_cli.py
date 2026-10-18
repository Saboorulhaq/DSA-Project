"""
scrape_cli.py - test the scraper WITHOUT the GUI.
  python scrape_cli.py 300        -> scrape 300 records into data/test_books.csv (fresh each time)
  python scrape_cli.py full       -> scrape the full target into data/books.csv (resumes if interrupted)
"""
import sys

from scraper.scraper_core import ScrapeControl, run_scrape
from scraper.storage import DataStore
from site_profile import PROFILE


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "300"
    profile = dict(PROFILE)
    if arg == "full":
        store = DataStore()
        progress = store.load_progress()
        start = progress["next_url"] if progress and progress.get("next_url") else profile["start_url"]
    else:
        profile["target_count"] = int(arg)
        store = DataStore("test_books.csv", "test_progress.json")
        store.clear()
        start = profile["start_url"]

    def show(count):
        print(f"\rCollected: {count:,} / {profile['target_count']:,}", end="", flush=True)

    result = run_scrape(profile, store, ScrapeControl(), start, show, print)
    print(f"\nResult: {result}   unique records: {store.count:,}")


if __name__ == "__main__":
    main()
