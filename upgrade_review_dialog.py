"""Full catalog review panel; in-memory drafts only. Workflow: README.md."""
from copy import deepcopy
import json

from PySide6 import QtCore, QtWidgets
from attack_catalog import external_id, tactic_phases
from navigator_integration import document_layer
from ttp_documents import TTPDocument
from ttp_selection import selected_cells, assign_cells
from upgrade_review import CATEGORIES


class UpgradeReviewPanel(QtWidgets.QWidget):
    changed = QtCore.Signal()

    def __init__(self, owner):
        super().__init__(owner)
        self.owner, self.items, self.states, self.drafts = owner, [], {}, {}
        layout = QtWidgets.QVBoxLayout(self)
        filters = QtWidgets.QHBoxLayout()
        self.category = QtWidgets.QComboBox()
        self.category.addItems(['All categories', *CATEGORIES])
        self.annotated_only = QtWidgets.QCheckBox('Only annotated techniques')
        filters.addWidget(self.category)
        filters.addWidget(self.annotated_only)
        layout.addLayout(filters)
        self.counts = QtWidgets.QLabel()
        self.counts.setWordWrap(True)
        layout.addWidget(self.counts)
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['Source technique', 'Change', 'Target technique', 'Annotated', 'Reviewed'])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        self.empty = QtWidgets.QLabel('No techniques match these review filters.')
        layout.addWidget(self.empty)
        self.edit = QtWidgets.QPushButton('Annotate added target…')
        self.edit.setEnabled(False)
        self.edit.clicked.connect(self.edit_target)
        layout.addWidget(self.edit)
        self.table.itemChanged.connect(self.item_changed)
        self.table.currentCellChanged.connect(self.show_item)
        self.category.currentIndexChanged.connect(self.filter_rows)
        self.annotated_only.toggled.connect(self.filter_rows)
        from localization import language_manager
        language_manager().changed.connect(self.filter_rows)

    def clear(self):
        self.items, self.states, self.drafts = [], {}, {}
        self.table.setRowCount(0)
        self.edit.setEnabled(False)
        self.counts.clear()

    def load(self, preview):
        self.clear()
        self.items = preview['items']
        self.states = {item['id']: {'id': item['id'], 'reviewed': item['reviewed']} for item in self.items}
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.items))
        for index, item in enumerate(self.items):
            values = [item['id'] + '  ' + item['source_name'], item['category'],
                      item['target_id'] + '  ' + item['target_name'], 'Yes' if item['annotated'] else '', '']
            for column, value in enumerate(values):
                cell = QtWidgets.QTableWidgetItem(value)
                cell.setFlags(cell.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                if column == 4:
                    cell.setFlags(cell.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                    cell.setCheckState(QtCore.Qt.CheckState.Checked if item['reviewed'] else QtCore.Qt.CheckState.Unchecked)
                self.table.setItem(index, column, cell)
        self.table.blockSignals(False)
        self.filter_rows()
        if self.items:
            self.table.setCurrentCell(0, 0)

    def item_changed(self, cell):
        if cell.column() != 4 or cell.row() >= len(self.items):
            return
        item = self.items[cell.row()]
        checked = cell.checkState() == QtCore.Qt.CheckState.Checked
        self.states[item['id']]['reviewed'] = checked
        for index in item['row_indices']:
            self.owner.controls[index]['reviewed'].setChecked(checked)
        self.filter_rows()

    def unreview(self, identity):
        if identity not in self.states:
            return
        self.states[identity]['reviewed'] = False
        index = next(i for i, item in enumerate(self.items) if item['id'] == identity)
        self.table.blockSignals(True)
        self.table.item(index, 4).setCheckState(QtCore.Qt.CheckState.Unchecked)
        self.table.blockSignals(False)
        self.filter_rows()

    def matches(self, item):
        category = self.category.currentIndex()
        return ((not category or item['category'] == CATEGORIES[category - 1])
                and (not self.annotated_only.isChecked() or item['annotated'] or bool(self.drafts.get(item['id']) and
                     any(self.annotation_meaningful(row) for row in document_layer(self.drafts[item['id']])['techniques'])))
                and (not self.owner.pending_only.isChecked() or not self.states[item['id']]['reviewed']))

    @staticmethod
    def annotation_meaningful(row):
        from matrix_display import annotation_flags
        return annotation_flags(row)['annotated']

    def filter_rows(self, *_):
        visible = 0
        for index, item in enumerate(self.items):
            hidden = not self.matches(item)
            self.table.setRowHidden(index, hidden)
            visible += not hidden
        self.empty.setVisible(not visible)
        from localization import tr
        self.counts.setText(' · '.join(tr(category) + ': ' +
            str(sum(self.states[i['id']]['reviewed'] for i in self.items if i['category'] == category)) + '/' +
            str(sum(i['category'] == category for i in self.items)) for category in CATEGORIES) +
            ' · ' + tr('Reviewed') + ': ' + str(sum(s['reviewed'] for s in self.states.values())) + '/' + str(len(self.items)))
        self.show_item(self.table.currentRow(), refresh=False)
        self.changed.emit()

    def mark_visible(self):
        # Freeze the set before pending-only filtering hides newly reviewed rows.
        indices = [i for i in range(len(self.items)) if not self.table.isRowHidden(i)]
        self.table.blockSignals(True)
        for index in indices:
            item = self.items[index]
            self.states[item['id']]['reviewed'] = True
            self.table.item(index, 4).setCheckState(QtCore.Qt.CheckState.Checked)
            for source_index in item['row_indices']:
                check = self.owner.controls[source_index]['reviewed']
                check.blockSignals(True)
                check.setChecked(True)
                check.blockSignals(False)
        self.table.blockSignals(False)
        self.filter_rows()

    def show_item(self, row, *_, refresh=True):
        if row < 0 or row >= len(self.items):
            self.edit.setEnabled(False)
            return
        item = self.items[row]
        self.edit.setEnabled(bool(item['target_id']) or bool(item['row_indices']))
        self.edit.setText('Annotate added target…' if item['category'] == 'Added' else 'Edit target annotation…')
        current = {**item, 'reviewed': self.states[item['id']]['reviewed']}
        self.owner.change_details.setPlainText(json.dumps(current, ensure_ascii=False, indent=2))
        if refresh:
            self.owner.comparison.show_item(item['id'])

    def edit_target(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.items[row]
        if item['category'] != 'Added' and item['row_indices']:
            index = item['row_indices'][0]
            self.owner.review_tabs.setCurrentIndex(1)
            self.owner.table.setCurrentCell(index, 0)
            self.owner.show_changes(index)
            self.owner.comparison.edit_target()
        else:
            self.edit_added()

    def edit_added(self):
        row = self.table.currentRow()
        if row < 0 or not self.items[row]['target_id']:
            return
        from navigator_dialogs import AnnotationDialog
        self.owner.report('Input files: None; output files: None (target annotation draft in memory)', 0, 0)
        self.owner.report('[Upgrade edit 1/2] Preparing target annotation', 0, 2)
        item, catalog = self.items[row], self.owner.target_catalog
        key = next(key for key, obj in catalog.records.items() if external_id(obj) == item['target_id'])
        draft = self.drafts.get(item['id']) or TTPDocument('Added review', catalog)
        dialog = AnnotationDialog(draft, key, self)
        if item['category'] != 'Added':
            dialog.include.hide()
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            self.owner.report('[Upgrade edit 2/2] Cancelled; previous target draft preserved', 2, 2)
            return
        was_included = key in draft.selected
        draft.navigator_layer = dialog.result_layer
        if was_included != dialog.include.isChecked():
            cells = selected_cells(draft)
            scope = dialog.scope.currentData() or ''
            changes = {(key, slug) for slug in tactic_phases(catalog.records[key], catalog.domain) if not scope or scope == slug}
            assign_cells(draft, cells | changes if dialog.include.isChecked() else cells - changes)
        self.drafts[item['id']] = draft
        self.owner.invalidate_conflicts()
        self.unreview(item['id'])
        self.owner.comparison.refresh()
        self.owner.report('[Upgrade edit 2/2] Target draft saved; review the technique again', 2, 2)

    def decisions(self):
        result = deepcopy(list(self.states.values()))
        for review in result:
            draft = self.drafts.get(review['id'])
            if draft:
                review['annotation_rows'] = deepcopy(draft.navigator_layer.get('techniques', []))
                review['selected_scopes'] = sorted(slug for _, slug in selected_cells(draft))
        return result
