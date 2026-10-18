"""table_model.py - feeds the list of rows into the QTableView (fast even for 15,000+ rows)."""
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt


class RowsTableModel(QAbstractTableModel):
    def __init__(self, columns):
        super().__init__()
        self.columns = columns
        self.rows = []

    def set_rows(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self.rows[index.row()][self.columns[index.column()]])
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self.columns[section]
            return str(section + 1)
        return None
