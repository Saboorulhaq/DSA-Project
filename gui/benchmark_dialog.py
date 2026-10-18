"""benchmark_dialog.py - pop-up window with the benchmark comparison table."""
from PyQt6.QtWidgets import (QAbstractItemView, QDialog, QHeaderView, QLabel, QPushButton,
                             QTableWidget, QTableWidgetItem, QVBoxLayout)

HEADERS = ["Algorithm", "Time (ms)", "Comparisons", "Swaps", "Time complexity", "Space", "Stable?", "Correct?"]


class BenchmarkDialog(QDialog):
    def __init__(self, results, column, scope_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Benchmark results")
        self.resize(950, 360)
        layout = QVBoxLayout(self)
        rows = results[0]["rows"] if results else 0
        layout.addWidget(QLabel(
            f"Column: {column}   |   Rows sorted: {rows:,}   |   Scope: {scope_text}\n"
            "Every algorithm received an identical copy of the same data."))
        table = QTableWidget(len(results), len(HEADERS))
        table.setHorizontalHeaderLabels(HEADERS)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for r, res in enumerate(results):
            values = [res["algorithm"], f"{res['ms']:.3f}", f"{res['comparisons']:,}", f"{res['swaps']:,}",
                      res["complexity"], res["space"], "Yes" if res["stable"] else "No",
                      "Yes" if res["correct"] else "NO - BUG"]
            for c, value in enumerate(values):
                table.setItem(r, c, QTableWidgetItem(value))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(table)
        layout.addWidget(QLabel("Swaps note: Insertion/Shell count each shift as one swap; "
                                "Merge sort counts each element copy as one swap."))
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)
