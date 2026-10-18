"""
main_window.py - the main window. It connects every button to a function.

Data lists used by this window:
  store.rows     -> rows being collected by the scraper (scraper thread writes here)
  all_rows       -> a copy used for sorting/filtering (the "full dataset")
  view_rows      -> what the table currently shows (all_rows, or the filtered result)
"""
import time

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton,
                             QSpinBox, QTableView, QToolButton, QVBoxLayout, QWidget)

from algorithms.filters import NUMBER_OPS, NUMERIC, STRING_OPS, filter_rows, make_condition
from algorithms.searching import binary_search_exact, linear_search_exact
from algorithms.sorting import ALGORITHMS, benchmark, complexity_text, sort_rows
from gui.benchmark_dialog import BenchmarkDialog
from gui.scraper_worker import ScraperWorker
from gui.table_model import RowsTableModel
from gui.task_worker import TaskWorker
from scraper.storage import DataStore
from site_profile import COLUMN_TYPES, COLUMNS, PROFILE

FILTER_ROWS = 4          # number of condition rows in the filter panel
SORT_LEVELS = 3          # number of levels in multi-level sort


class ConditionRow(QWidget):
    """One line of the filter panel:  [AND/OR] [NOT] [column] [operator] [value]"""

    def __init__(self, index):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.index = index
        if index == 0:
            layout.addWidget(QLabel("IF "))
            self.connector = None
        else:
            self.connector = QComboBox()
            self.connector.addItems(["AND", "OR"])
            layout.addWidget(self.connector)
        self.not_box = QCheckBox("NOT")
        self.column = QComboBox()
        self.column.addItems(COLUMNS)
        self.op = QComboBox()
        self.value = QLineEdit()
        self.value.setPlaceholderText("value (leave empty to ignore this row)")
        for widget in (self.not_box, self.column, self.op, self.value):
            layout.addWidget(widget)
        self.column.currentTextChanged.connect(self.update_operators)
        self.update_operators()

    def update_operators(self):
        numeric = COLUMN_TYPES[self.column.currentText()] in NUMERIC
        self.op.clear()
        self.op.addItems(NUMBER_OPS if numeric else STRING_OPS)

    def get_condition(self):
        value = self.value.text().strip()
        if not value:
            return None
        connector = self.connector.currentText() if self.connector else "AND"
        return make_condition(self.column.currentText(), self.op.currentText(), value,
                              self.not_box.isChecked(), connector)

    def clear(self):
        self.value.clear()
        self.not_box.setChecked(False)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DSA Project 1 - Catalogue Scraper, Search and Sorting")
        self.resize(1300, 850)
        self.profile = PROFILE
        self.target = PROFILE["target_count"]
        self.store = DataStore()
        self.all_rows = list(self.store.rows)
        self.view_rows = list(self.all_rows)
        self.active_conditions = None
        self.scraper = None
        self.task = None
        self.scrape_state = "idle"          # idle / running / paused
        self.paused_ready = False
        self.last_sorted_column = None
        self.last_ascending = True
        self.model = RowsTableModel(COLUMNS)
        self.build_ui()
        self.refresh_table()
        self.update_scrape_ui()
        self.set_count(self.store.count)
        self.status_label.setText(f"Loaded {self.store.count:,} saved records." if self.store.count
                                  else "No saved data yet. Press Start to scrape.")

    # ------------------------------------------------------------ building the screen
    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.addWidget(self.build_scrape_box())
        self.filter_box = self.build_filter_box()
        self.sort_box = self.build_sort_box()
        root.addWidget(self.filter_box)
        root.addWidget(self.sort_box)
        self.result_label = QLabel("Sort / search results appear here.")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("font-weight: bold; padding: 4px;")
        root.addWidget(self.result_label)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().sectionClicked.connect(self.on_header_clicked)
        root.addWidget(self.table, 1)
        self.rows_label = QLabel("")
        root.addWidget(self.rows_label)

    def build_scrape_box(self):
        box = QGroupBox("1. Scraping")
        grid = QGridLayout(box)
        grid.addWidget(QLabel("Start URL:"), 0, 0)
        self.url_edit = QLineEdit(self.profile["start_url"])
        grid.addWidget(self.url_edit, 0, 1, 1, 5)
        self.start_btn = QPushButton("Start")
        self.pause_btn = QPushButton("Pause")
        self.resume_btn = QPushButton("Resume")
        self.stop_btn = QPushButton("Stop")
        self.clear_btn = QPushButton("Delete saved data")
        self.start_btn.clicked.connect(self.start_scraping)
        self.pause_btn.clicked.connect(self.pause_scraping)
        self.resume_btn.clicked.connect(self.resume_scraping)
        self.stop_btn.clicked.connect(self.stop_scraping)
        self.clear_btn.clicked.connect(self.clear_data)
        for i, button in enumerate([self.start_btn, self.pause_btn, self.resume_btn,
                                    self.stop_btn, self.clear_btn]):
            grid.addWidget(button, 1, i)
        self.progress = QProgressBar()
        self.progress.setMaximum(self.target)
        self.progress.setFormat("%v / %m records")
        grid.addWidget(self.progress, 2, 0, 1, 4)
        self.count_label = QLabel("")
        grid.addWidget(self.count_label, 2, 4, 1, 2)
        self.status_label = QLabel("")
        grid.addWidget(self.status_label, 3, 0, 1, 6)
        return box

    def build_filter_box(self):
        box = QGroupBox("2. Search and filter  (string: contains / equals / starts with / ends with; "
                        "numbers: = != > >= < <=)")
        layout = QVBoxLayout(box)
        self.condition_rows = [ConditionRow(i) for i in range(FILTER_ROWS)]
        for row in self.condition_rows:
            layout.addWidget(row)
        line = QHBoxLayout()
        line.addWidget(QLabel("Search algorithm (for a single 'equals' / '=' condition):"))
        self.search_algo = QComboBox()
        self.search_algo.addItems(["Linear Search", "Binary Search"])
        line.addWidget(self.search_algo)
        apply_btn = QPushButton("Apply filter / Search")
        clear_btn = QPushButton("Clear filter")
        apply_btn.clicked.connect(self.apply_filter)
        clear_btn.clicked.connect(self.clear_filter)
        line.addWidget(apply_btn)
        line.addWidget(clear_btn)
        line.addStretch()
        layout.addLayout(line)
        return box

    def build_sort_box(self):
        box = QGroupBox("3. Sorting, multi-level sorting and benchmark")
        grid = QGridLayout(box)
        grid.addWidget(QLabel("Column:"), 0, 0)
        self.sort_col = QComboBox()
        self.sort_col.addItems(COLUMNS)
        grid.addWidget(self.sort_col, 0, 1)
        self.sort_order = QComboBox()
        self.sort_order.addItem("Ascending", True)
        self.sort_order.addItem("Descending", False)
        grid.addWidget(self.sort_order, 0, 2)
        grid.addWidget(QLabel("Algorithm:"), 0, 3)
        self.algo_combo = QComboBox()
        for name, info in ALGORITHMS.items():
            tag = "extra" if info["extra"] else "class"
            self.algo_combo.addItem(f"{name}  [{info['avg']}, {'stable' if info['stable'] else 'unstable'}, {tag}]", name)
        grid.addWidget(self.algo_combo, 0, 4)
        grid.addWidget(QLabel("Scope:"), 0, 5)
        self.scope_combo = QComboBox()
        self.scope_combo.addItem("Full dataset", "full")
        self.scope_combo.addItem("Filtered results only", "filtered")
        grid.addWidget(self.scope_combo, 0, 6)
        sort_btn = QPushButton("Sort")
        sort_btn.clicked.connect(self.sort_single)
        grid.addWidget(sort_btn, 0, 7)
        self.algo_info = QLabel("")
        grid.addWidget(self.algo_info, 1, 0, 1, 8)
        self.algo_combo.currentIndexChanged.connect(self.update_algo_info)
        self.update_algo_info()

        self.level_cols, self.level_orders = [], []
        for level in range(SORT_LEVELS):
            grid.addWidget(QLabel(f"Level {level + 1}:"), 2 + level, 0)
            col = QComboBox()
            col.addItem("(none)")
            col.addItems(COLUMNS)
            order = QComboBox()
            order.addItem("Ascending", True)
            order.addItem("Descending", False)
            grid.addWidget(col, 2 + level, 1)
            grid.addWidget(order, 2 + level, 2)
            self.level_cols.append(col)
            self.level_orders.append(order)
        multi_btn = QPushButton("Multi-level sort (uses algorithm + scope above)")
        multi_btn.clicked.connect(self.sort_multi)
        grid.addWidget(multi_btn, 2, 3, 1, 3)

        grid.addWidget(QLabel("Benchmark rows (max):"), 3, 3)
        self.bench_rows = QSpinBox()
        self.bench_rows.setRange(10, 1000000)
        self.bench_rows.setValue(2000)
        self.bench_rows.setSingleStep(500)
        grid.addWidget(self.bench_rows, 3, 4)
        bench_btn = QPushButton("Benchmark all algorithms on selected column")
        bench_btn.clicked.connect(self.run_benchmark)
        grid.addWidget(bench_btn, 3, 5, 1, 3)

        columns_btn = QToolButton()
        columns_btn.setText("Show / hide columns")
        columns_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(columns_btn)
        for index, name in enumerate(COLUMNS):
            action = QAction(name, menu)
            action.setCheckable(True)
            action.setChecked(True)
            action.toggled.connect(lambda checked, i=index: self.table.setColumnHidden(i, not checked))
            menu.addAction(action)
        columns_btn.setMenu(menu)
        grid.addWidget(columns_btn, 4, 0, 1, 2)
        return box

    def update_algo_info(self):
        name = self.algo_combo.currentData()
        info = ALGORITHMS[name]
        self.algo_info.setText(f"{name}: {complexity_text(name)} | space {info['space']} | "
                               f"stable: {'Yes' if info['stable'] else 'No'}")

    # ------------------------------------------------------------ table helpers
    def refresh_table(self):
        self.model.set_rows(self.view_rows)
        shown, total = len(self.view_rows), len(self.all_rows)
        self.rows_label.setText(f"Showing {shown:,} of {total:,} records"
                                + ("  (filter active)" if self.active_conditions else ""))

    def set_count(self, count):
        self.progress.setValue(min(count, self.target))
        self.count_label.setText(f"Collected: {count:,}")

    # ------------------------------------------------------------ scraping controls
    def update_scrape_ui(self):
        s = self.scrape_state
        self.start_btn.setEnabled(s == "idle")
        self.pause_btn.setEnabled(s == "running")
        self.resume_btn.setEnabled(s == "paused")
        self.stop_btn.setEnabled(s in ("running", "paused"))
        self.clear_btn.setEnabled(s == "idle")
        self.url_edit.setEnabled(s == "idle")
        self.set_panels_enabled(s == "idle" or (s == "paused" and self.paused_ready))

    def set_panels_enabled(self, enabled):
        busy = self.task is not None and self.task.isRunning()
        self.filter_box.setEnabled(enabled and not busy)
        self.sort_box.setEnabled(enabled and not busy)

    def start_scraping(self):
        url = self.url_edit.text().strip()
        if not url.startswith("http"):
            QMessageBox.warning(self, "URL", "Please enter a URL that starts with http:// or https://")
            return
        count = self.store.count
        progress = self.store.load_progress()
        start_url = url
        if count > 0:
            can_resume = bool(progress and progress.get("next_url")) and count < self.target
            if can_resume:
                answer = QMessageBox.question(
                    self, "Saved progress found",
                    f"{count:,} records are already saved.\n\nYes = continue where you stopped\n"
                    "No = delete them and start again",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    | QMessageBox.StandardButton.Cancel)
                if answer == QMessageBox.StandardButton.Cancel:
                    return
                if answer == QMessageBox.StandardButton.Yes:
                    start_url = progress["next_url"]
                else:
                    self.store.clear()
            else:
                answer = QMessageBox.question(self, "Data exists",
                                              f"{count:,} records are already saved. Delete them and scrape again?")
                if answer != QMessageBox.StandardButton.Yes:
                    return
                self.store.clear()
        self.all_rows, self.view_rows, self.active_conditions = list(self.store.rows), list(self.store.rows), None
        self.refresh_table()
        self.set_count(self.store.count)
        self.scraper = ScraperWorker(self.profile, self.store, start_url)
        self.scraper.progress.connect(self.set_count)
        self.scraper.status.connect(self.status_label.setText)
        self.scraper.paused_now.connect(self.on_really_paused)
        self.scraper.finished_state.connect(self.on_scrape_finished)
        self.scrape_state, self.paused_ready = "running", False
        self.update_scrape_ui()
        self.scraper.start()

    def pause_scraping(self):
        if self.scraper:
            self.scraper.control.pause()
            self.scrape_state, self.paused_ready = "paused", False
            self.status_label.setText("Pausing after the current page...")
            self.update_scrape_ui()

    def on_really_paused(self):
        """The scraper thread has stopped working: now it is safe to show/sort the data."""
        self.all_rows = list(self.store.rows)
        self.view_rows = list(self.all_rows)
        self.active_conditions = None
        self.paused_ready = True
        self.refresh_table()
        self.update_scrape_ui()

    def resume_scraping(self):
        if self.scraper:
            self.scrape_state, self.paused_ready = "running", False
            self.update_scrape_ui()
            self.scraper.control.resume()

    def stop_scraping(self):
        if self.scraper:
            self.scraper.control.stop()
            self.status_label.setText("Stopping...")
            self.stop_btn.setEnabled(False)

    def on_scrape_finished(self, state):
        self.scrape_state, self.paused_ready = "idle", False
        self.all_rows = list(self.store.rows)
        self.view_rows = list(self.all_rows)
        self.active_conditions = None
        self.set_count(self.store.count)
        self.refresh_table()
        self.update_scrape_ui()
        if state == "error":
            QMessageBox.warning(self, "Network problem",
                                "A page kept failing. Your progress is saved - press Start and choose Yes to continue.")

    def clear_data(self):
        if QMessageBox.question(self, "Delete", "Delete all saved data?") == QMessageBox.StandardButton.Yes:
            self.store.clear()
            self.all_rows, self.view_rows, self.active_conditions = [], [], None
            self.refresh_table()
            self.set_count(0)
            self.status_label.setText("Saved data deleted.")

    def closeEvent(self, event):
        if self.scraper and self.scraper.isRunning():
            self.scraper.control.stop()
            self.scraper.wait(15000)       # data is saved page by page, so nothing is lost
        event.accept()

    # ------------------------------------------------------------ search and filter
    def apply_filter(self):
        conditions = [c for c in (row.get_condition() for row in self.condition_rows) if c]
        if not conditions:
            QMessageBox.information(self, "Filter", "Type a value in at least one row.")
            return
        start = time.perf_counter()
        note = "Linear scan"
        try:
            single = conditions[0] if len(conditions) == 1 else None
            if single and single["op"] in ("equals", "=") and not single["negate"]:
                kind = COLUMN_TYPES[single["column"]]
                if kind in NUMERIC:
                    float(single["value"])
                if self.search_algo.currentText() == "Binary Search":
                    result, comps = binary_search_exact(self.all_rows, single["column"], single["value"], kind)
                    note = f"Binary Search ({comps:,} comparisons, on a sorted copy)"
                else:
                    result, comps = linear_search_exact(self.all_rows, single["column"], single["value"], kind)
                    note = f"Linear Search ({comps:,} comparisons)"
            else:
                result = filter_rows(self.all_rows, conditions, COLUMN_TYPES)
        except ValueError as error:
            QMessageBox.warning(self, "Filter", str(error))
            return
        ms = (time.perf_counter() - start) * 1000
        self.active_conditions = conditions
        self.view_rows = result
        self.refresh_table()
        self.result_label.setText(f"Filter: {len(result):,} matching records | {note} | {ms:.3f} ms")

    def clear_filter(self):
        for row in self.condition_rows:
            row.clear()
        self.active_conditions = None
        self.view_rows = list(self.all_rows)
        self.refresh_table()
        self.result_label.setText("Filter cleared.")

    # ------------------------------------------------------------ sorting
    def on_header_clicked(self, section):
        column = COLUMNS[section]
        ascending = not self.last_ascending if column == self.last_sorted_column else True
        self.sort_col.setCurrentText(column)
        self.sort_order.setCurrentIndex(0 if ascending else 1)
        if self.sort_box.isEnabled():
            self.sort_single()

    def sort_single(self):
        column = self.sort_col.currentText()
        ascending = self.sort_order.currentData()
        self.last_sorted_column, self.last_ascending = column, ascending
        self.start_sort([(column, COLUMN_TYPES[column], ascending)])

    def sort_multi(self):
        specs = []
        for col_box, order_box in zip(self.level_cols, self.level_orders):
            name = col_box.currentText()
            if name != "(none)":
                specs.append((name, COLUMN_TYPES[name], order_box.currentData()))
        if not specs:
            QMessageBox.information(self, "Multi-level sort", "Choose at least one column in Level 1.")
            return
        self.start_sort(specs)

    def start_sort(self, specs):
        scope = self.scope_combo.currentData()
        rows = self.all_rows if scope == "full" else self.view_rows
        if not rows:
            QMessageBox.information(self, "Sort", "There are no rows to sort.")
            return
        algo = self.algo_combo.currentData()
        text = " then ".join(f"{c} ({'asc' if a else 'desc'})" for c, _, a in specs)
        self.run_background(sort_rows, (rows, specs, algo),
                            lambda res: self.sort_done(res, scope, text),
                            f"Sorting {len(rows):,} rows with {algo} by {text} ... please wait")

    def sort_done(self, result, scope, text):
        sorted_rows, stats = result
        if scope == "full":
            self.all_rows = sorted_rows
            self.view_rows = (filter_rows(self.all_rows, self.active_conditions, COLUMN_TYPES)
                              if self.active_conditions else list(self.all_rows))
        else:
            self.view_rows = sorted_rows
        name = stats["algorithm"]
        info = ALGORITHMS[name]
        self.refresh_table()
        self.result_label.setText(
            f"{name} | by {text} | scope: {'FULL dataset' if scope == 'full' else 'filtered results'} | "
            f"rows: {stats['rows']:,} | time: {stats['ms']:.3f} ms | comparisons: {stats['comparisons']:,} | "
            f"swaps: {stats['swaps']:,} | {complexity_text(name)} | stable: {'Yes' if info['stable'] else 'No'}")

    # ------------------------------------------------------------ benchmark
    def run_benchmark(self):
        column = self.sort_col.currentText()
        scope = self.scope_combo.currentData()
        rows = self.all_rows if scope == "full" else self.view_rows
        rows = rows[: self.bench_rows.value()]
        if not rows:
            QMessageBox.information(self, "Benchmark", "There are no rows to benchmark.")
            return
        specs = [(column, COLUMN_TYPES[column], True)]
        scope_text = "full dataset" if scope == "full" else "filtered results"
        self.run_background(benchmark, (rows, specs),
                            lambda res: BenchmarkDialog(res, column, scope_text, self).exec(),
                            f"Benchmarking 7 algorithms on {len(rows):,} rows ... please wait")

    # ------------------------------------------------------------ background tasks
    def run_background(self, func, args, on_done, message):
        self.result_label.setText(message)
        self.task = TaskWorker(func, *args)
        self.task.done.connect(lambda result: self.background_done(on_done, result))
        self.task.failed.connect(self.background_failed)
        self.set_panels_enabled(False)
        self.task.start()

    def background_done(self, on_done, result):
        self.task.wait()
        self.set_panels_enabled(self.scrape_state == "idle" or (self.scrape_state == "paused" and self.paused_ready))
        on_done(result)

    def background_failed(self, message):
        self.task.wait()
        self.update_scrape_ui()
        QMessageBox.warning(self, "Error", message)
