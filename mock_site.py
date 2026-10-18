"""
mock_site.py - a fake bookstore website that runs on YOUR computer, for testing.
Run it in a second terminal:   python mock_site.py
It has 330 pages x 50 books, a few duplicate books, missing values and random
HTTP 500 errors, so you can test every feature of the scraper safely.
"""
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PER_PAGE = 50
TOTAL_PAGES = 330
ADJ = ["Silent", "Hidden", "Last", "Golden", "Broken", "Secret", "Lost", "Eternal", "Modern", "Ancient"]
NOUN = ["River", "Garden", "Empire", "Code", "Journey", "Mirror", "Theory", "Harvest", "Compass", "Library"]
PLACE = ["Paris", "Lahore", "Tokyo", "the North", "Mars", "Babylon", "Karachi", "the Deep", "Oxford"]
FIRST = ["Ali", "Sara", "John", "Maria", "Omar", "Lina", "Hassan", "Emma", "Zain", "Noor", "Peter", "Aisha"]
LAST = ["Khan", "Smith", "Ahmed", "Brown", "Raza", "Lee", "Garcia", "Malik", "Chen", "Hussain"]
CATS = ["Fiction", "Science", "History", "Biography", "Technology", "Poetry", "Art", "Travel",
        "Business", "Health", "Religion", "Education"]
PUBS = ["Penguin", "Oxford Press", "Pearson", "Wiley", "Springer", "Orient", "HarperCollins", "Vintage"]
LANGS = ["English", "Urdu", "French", "Arabic", "German"]


def make_book(no):
    r = random.Random(no)
    b = {
        "id": f"B{no:06d}",
        "title": f"{r.choice(ADJ)} {r.choice(NOUN)} of {r.choice(PLACE)}",
        "author": f"{r.choice(FIRST)} {r.choice(LAST)}",
        "category": r.choice(CATS),
        "publisher": r.choice(PUBS),
        "language": r.choice(LANGS),
        "price": f"${r.uniform(5, 80):.2f}",
        "rating": f"{r.uniform(1, 5):.1f}",
        "reviews": f"{r.randint(0, 5000):,}",
        "pages": str(r.randint(80, 1200)),
        "year": str(r.randint(1950, 2025)),
    }
    for field in ["author", "publisher", "language", "price", "rating", "reviews", "pages", "year"]:
        if r.random() < 0.04:          # 4% of optional values are missing
            b[field] = None
    return b


def render_page(p):
    html = ["<html><body><h1>Mock Bookstore</h1>"]
    for k in range(PER_PAGE):
        idx = (p - 1) * PER_PAGE + k
        no = idx - PER_PAGE if (p % 40 == 0 and k < 3) else idx   # a few duplicates
        b = make_book(no)
        html.append('<div class="book">')
        html.append(f'<span class="id">{b["id"]}</span>')
        html.append(f'<a class="title" href="/book/{no}">{b["title"]}</a>')
        for f in ["author", "category", "publisher", "language", "price", "rating", "reviews", "pages", "year"]:
            if b[f] is not None:
                html.append(f'<span class="{f}">{b[f]}</span>')
        html.append("</div>")
    if p < TOTAL_PAGES:
        html.append(f'<a class="next" href="/page/{p + 1}">Next</a>')
    html.append("</body></html>")
    return "\n".join(html).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if random.random() < 0.01:                 # 1% random server errors
            self.send_response(500); self.end_headers(); return
        path = self.path.rstrip("/")
        try:
            p = 1 if path in ("", "/page") else int(path.split("/")[-1])
            assert 1 <= p <= TOTAL_PAGES
        except Exception:
            self.send_response(404); self.end_headers(); return
        body = render_page(p)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Mock site running at http://127.0.0.1:8000/page/1  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
