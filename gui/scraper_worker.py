"""scraper_worker.py - runs the scraper in a background thread and reports to the GUI."""
from PyQt6.QtCore import QThread, pyqtSignal

from scraper.scraper_core import ScrapeControl, run_scrape


class ScraperWorker(QThread):
    progress = pyqtSignal(int)          # number of records collected so far
    status = pyqtSignal(str)            # text for the status label
    paused_now = pyqtSignal()           # the scraper has really stopped to wait
    finished_state = pyqtSignal(str)    # 'done', 'finished', 'stopped' or 'error'

    def __init__(self, profile, store, start_url):
        super().__init__()
        self.profile = profile
        self.store = store
        self.start_url = start_url
        self.control = ScrapeControl()

    def run(self):
        state = run_scrape(self.profile, self.store, self.control, self.start_url,
                           self.progress.emit, self.status.emit, self.paused_now.emit)
        self.finished_state.emit(state)
