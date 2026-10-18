import re
from urllib.parse import unquote

BASE = "https://en.wikipedia.org/wiki/List_of_minor_planets:_"

def wiki_next(url):
    m = re.search(r":_(\d+)–(\d+)$", unquote(url))
    if not m:
        return None
    hi = int(m.group(2))
    return f"{BASE}{hi + 1}–{hi + 1000}"

PROFILE = {
    "name": "Wikipedia - List of minor planets",
    "start_url": BASE + "1–1000",
    "item_selector": "table.wikitable tr",
    "next_selector": None,
    "next_url_builder": wiki_next,
    "unique_field": "designation",   # must be a TEXT field (header rows become "N/A" and are skipped)
    "delay_seconds": 1.0,
    "target_count": 16000,
    "fields": {
        "designation": ("td:nth-of-type(1)", None, "text"),
        "number":      ("td:nth-of-type(1)", None, "int"),
        "provisional": ("td:nth-of-type(2)", None, "text"),
        "named_after": ("td:nth-of-type(3)", None, "text"),
        "disc_date":   ("td:nth-of-type(4)", None, "text"),
        "site":        ("td:nth-of-type(5)", None, "text"),
        "discoverer":  ("td:nth-of-type(6)", None, "text"),
        "category":    ("td:nth-of-type(7)", None, "text"),
        "diameter_km": ("td:nth-of-type(8)", None, "float"),
    },
}

COLUMNS = list(PROFILE["fields"].keys())
COLUMN_TYPES = {name: spec[2] for name, spec in PROFILE["fields"].items()}
NUMERIC_TYPES = ("int", "float")