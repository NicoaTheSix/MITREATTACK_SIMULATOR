"""Structured Links/Metadata table editor. Workflow: README.md."""
from copy import deepcopy
from PySide6 import QtCore, QtWidgets
from navigator_fields import web_url, validate_fields


class FieldEditor(QtWidgets.QWidget):
    def __init__(self, field, parent=None):
        super().__init__(parent)
        self.field = field
        self.keys = ('label', 'url') if field == 'links' else ('name', 'value')
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([self.keys[0].title(), self.keys[1].title(), 'Divider'])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        bar = QtWidgets.QHBoxLayout()
        for text, callback in [('Add', lambda: self.add({})), ('Add divider', lambda: self.add({'divider': True})),
                               ('Remove row', self.remove)]:
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(callback)
            bar.addWidget(button)
        layout.addLayout(bar)
        self.original = []

    def load(self, entries):
        self.table.setRowCount(0)
        self.original = deepcopy(entries)
        for entry in entries:
            self.add(entry)

    def add(self, entry):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, key in enumerate(self.keys):
            item = QtWidgets.QTableWidgetItem(entry.get(key, ''))
            if col == 0:
                item.setData(QtCore.Qt.ItemDataRole.UserRole, deepcopy(entry))
            self.table.setItem(row, col, item)
        item = QtWidgets.QTableWidgetItem()
        item.setCheckState(QtCore.Qt.CheckState.Checked if entry.get('divider') is True else QtCore.Qt.CheckState.Unchecked)
        self.table.setItem(row, 2, item)

    def remove(self):
        if self.table.currentRow() >= 0:
            self.table.removeRow(self.table.currentRow())

    def values(self):
        result = []
        for row in range(self.table.rowCount()):
            original = self.table.item(row, 0).data(QtCore.Qt.ItemDataRole.UserRole) or {}
            entry = deepcopy(original)
            if self.table.item(row, 2).checkState() == QtCore.Qt.CheckState.Checked:
                for key in self.keys:
                    entry.pop(key, None)
                entry['divider'] = True
            else:
                entry.pop('divider', None)
                entry.update({key: self.table.item(row, col).text() for col, key in enumerate(self.keys)})
                if not entry[self.keys[0]].strip():
                    raise ValueError('Every entry needs a name or label; remove unused rows.')
                # Preserve imported non-web links; new/changed links use HTTP(S).
                if self.field == 'links' and entry.get('url') != original.get('url'):
                    web_url(entry['url'])
            result.append(entry)
        validate_fields({self.field: result})
        return result
