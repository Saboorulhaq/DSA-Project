"""task_worker.py - runs ANY function in a background thread so the window never freezes."""
from PyQt6.QtCore import QThread, pyqtSignal


class TaskWorker(QThread):
    done = pyqtSignal(object)     # carries the function's result
    failed = pyqtSignal(str)      # carries an error message

    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args

    def run(self):
        try:
            self.done.emit(self.func(*self.args))
        except Exception as error:          # show errors in the GUI instead of crashing
            self.failed.emit(str(error))
