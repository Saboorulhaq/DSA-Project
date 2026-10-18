"""
storage.py - saves scraped records to a CSV file and remembers progress.
  data/books.csv      -> every record (one per line)
  data/progress.json  -> the next page URL, so we can RESUME later
"""
import csv
import json
import os

from site_profile import COLUMNS, COLUMN_TYPES, PROFILE

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


class DataStore:
    def __init__(self, csv_name="books.csv", progress_name="progress.json"):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.csv_path = os.path.join(DATA_DIR, csv_name)
        self.progress_path = os.path.join(DATA_DIR, progress_name)
        self.unique_field = PROFILE["unique_field"]
        self.rows = []
        self.seen = set()
        self.load()

    @property
    def count(self):
        return len(self.rows)

    def load(self):
        """Read saved CSV (if any) and convert numbers back from text."""
        self.rows.clear()
        self.seen.clear()
        if not os.path.exists(self.csv_path):
            return
        with open(self.csv_path, newline="", encoding="utf-8") as f:
            for raw in csv.DictReader(f):
                row = {}
                for col in COLUMNS:
                    value = raw.get(col, "")
                    kind = COLUMN_TYPES[col]
                    if kind == "int":
                        value = int(float(value)) if value not in ("", None) else 0
                    elif kind == "float":
                        value = float(value) if value not in ("", None) else 0.0
                    row[col] = value
                key = row[self.unique_field]
                if key not in self.seen:
                    self.seen.add(key)
                    self.rows.append(row)

    def add_records(self, records):
        """Add only NEW records (duplicates are skipped). Returns how many were added."""
        new = []
        for rec in records:
            key = rec[self.unique_field]
            if key == "N/A" or key in self.seen:
                continue
            self.seen.add(key)
            self.rows.append(rec)
            new.append(rec)
        if new:
            write_header = not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=COLUMNS)
                if write_header:
                    writer.writeheader()
                writer.writerows(new)
        return len(new)

    def save_progress(self, next_url):
        with open(self.progress_path, "w", encoding="utf-8") as f:
            json.dump({"next_url": next_url, "count": self.count}, f)

    def load_progress(self):
        if not os.path.exists(self.progress_path):
            return None
        try:
            with open(self.progress_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def clear(self):
        self.rows.clear()
        self.seen.clear()
        for path in (self.csv_path, self.progress_path):
            if os.path.exists(path):
                os.remove(path)
