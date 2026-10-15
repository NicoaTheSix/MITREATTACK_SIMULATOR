"""Reviewable batch annotation/state drafts. Operation flow: README.md."""
import math
from PySide6 import QtCore, QtWidgets
from attack_catalog import tactic_phases
from layer_analysis import snapshot_document
from navigator_dialogs import IntegrationDialog
from navigator_field_editor import FieldEditor
from ttp_operations import batch_patch, effective_row


class BatchEditDialog(IntegrationDialog):
    def __init__(self, document, keys, parent, clear=False):
        super().__init__(parent)
        self.document = snapshot_document(document)
        self.keys = set(keys)
        self.result_layer = None
        self.result_data = None
        self.setWindowTitle(('Clear selected annotations' if clear else 'Batch edit selected TTPs') + ' — ' + document.name)
        self.resize(760, 720)
        layout = QtWidgets.QVBoxLayout(self)
        self.summary = QtWidgets.QLabel(f'{len(keys)} included TTPs in this document. Matrix filters do not remove editing targets. Unchanged fields and export selection are preserved.')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.scope = QtWidgets.QComboBox()
        self.scope.addItem('Entire technique · all mapped scopes', None)
        for slug in document.catalog.tactic_order:
            count = sum(slug in tactic_phases(document.catalog.records[key], document.catalog.domain) for key in keys)
            if count:
                self.scope.addItem(document.catalog.tactics[slug]['name'] + f' · {count}/{len(keys)} TTPs', slug)
        layout.addWidget(self.scope)
        self.targets = QtWidgets.QListWidget()
        self.targets.setMaximumHeight(105)
        self.targets.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        layout.addWidget(self.targets)
        self.scope.currentIndexChanged.connect(self.update_targets)
        self.update_targets()
        tabs = QtWidgets.QTabWidget()
        self.fields_tabs = tabs
        general = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(general)
        self.modes = {}
        self.values = {}
        for field, label in [('enabled', 'Enabled state'), ('comment', 'Comment'), ('score', 'Score'), ('color', 'Color')]:
            mode = self.mode(field, clear)
            widget = QtWidgets.QComboBox() if field == 'enabled' else QtWidgets.QPlainTextEdit() if field == 'comment' else QtWidgets.QLineEdit()
            if field == 'enabled':
                widget.addItem('Enabled', True)
                widget.addItem('Disabled', False)
                widget.addItem('Toggle each affected scope', 'toggle')
            elif field == 'comment':
                widget.setMaximumHeight(150)
            else:
                widget.setPlaceholderText('Finite number (zero is valid)' if field == 'score' else '#RRGGBB')
            row = QtWidgets.QVBoxLayout()
            row.addWidget(mode)
            row.addWidget(widget)
            form.addRow(label, row)
            self.values[field] = widget
            mode.currentIndexChanged.connect(lambda index, control=widget: control.setEnabled(index == 1))
            widget.setEnabled(mode.currentIndex() == 1)
        tabs.addTab(general, 'State / annotations')
        for field in ('links', 'metadata'):
            page = QtWidgets.QWidget()
            page_layout = QtWidgets.QVBoxLayout(page)
            mode = self.mode(field, clear)
            page_layout.addWidget(mode)
            editor = FieldEditor(field)
            page_layout.addWidget(editor, 1)
            self.values[field] = editor
            mode.currentIndexChanged.connect(lambda index, control=editor: control.setEnabled(index == 1))
            editor.setEnabled(False)
            tabs.addTab(page, field.title())
        layout.addWidget(tabs, 1)
        hint = QtWidgets.QLabel('Clear state restores Enabled. Set Links/Metadata replaces the affected lists; reserved export-selection metadata is preserved.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.error = QtWidgets.QLabel()
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        self.save_button = QtWidgets.QPushButton('Apply to selected TTPs')
        self.save_button.clicked.connect(self.save)
        layout.addWidget(self.save_button)
        cancel = QtWidgets.QPushButton('Cancel')
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)

    def mode(self, field, clear):
        combo = QtWidgets.QComboBox()
        combo.addItems(['Keep unchanged', 'Set / replace', 'Clear / reset'])
        combo.setCurrentIndex(2 if clear else 0)
        self.modes[field] = combo
        return combo

    def update_targets(self, *_):
        from attack_catalog import external_id
        self.targets.clear()
        scope = self.scope.currentData()
        eligible = [key for key in self.keys if scope is None or scope in tactic_phases(self.document.catalog.records[key], self.document.catalog.domain)]
        self.summary.setText(f'{len(self.keys)} included TTPs · {len(eligible)} affected · {len(self.keys) - len(eligible)} unmapped skipped. '
                             'Matrix filters do not remove editing targets. Keep leaves fields unchanged.')
        for key in sorted(eligible, key=lambda value: external_id(self.document.catalog.records[value])):
            record = self.document.catalog.records[key]
            row = effective_row(self.document, key, scope or '')
            item = QtWidgets.QListWidgetItem(external_id(record) + '  ' + record['name'], self.targets)
            item.setToolTip(f"Enabled: {row.get('enabled', True)}\nScore: {row.get('score', 'Unscored')}\n"
                            f"Color: {row.get('color', '')}\nComment: {row.get('comment', '')}")

    def save(self):
        if self.worker and self.worker.isRunning():
            return
        try:
            patch = {}
            for field, mode in self.modes.items():
                if mode.currentIndex() == 0:
                    continue
                if mode.currentIndex() == 2:
                    patch[field] = None
                elif field == 'enabled':
                    patch[field] = self.values[field].currentData()
                elif field == 'comment':
                    patch[field] = self.values[field].toPlainText() or None
                elif field == 'score':
                    value = float(self.values[field].text())
                    if not math.isfinite(value):
                        raise ValueError('Score must be finite.')
                    patch[field] = value
                elif field == 'color':
                    patch[field] = self.values[field].text().strip()
                    if not patch[field]:
                        raise ValueError('Enter a color or choose Clear.')
                else:
                    patch[field] = self.values[field].values()
                    if not patch[field]:
                        raise ValueError('Add at least one ' + field + ' entry or choose Clear.')
            if not patch:
                raise ValueError('Choose at least one field to Set or Clear.')
        except (ValueError, TypeError) as error:
            self.error.setText(str(error))
            return
        self.error.clear()
        self.save_button.setEnabled(False)
        self.fields_tabs.setEnabled(False)
        self.scope.setEnabled(False)
        scope = self.scope.currentData()
        self.start_task(lambda notify: batch_patch(self.document, self.keys, patch, scope, notify), self.completed)

    def completed(self, result):
        self.result_data = result
        self.result_layer = result['layer']
        QtCore.QTimer.singleShot(0, self.finish)

    def finish(self):
        if self.closing:
            return
        if self.worker and self.worker.isRunning():
            QtCore.QTimer.singleShot(25, self.finish)
            return
        self.accept()

    def task_finished(self):
        super().task_finished()
        self.save_button.setEnabled(True)
        self.fields_tabs.setEnabled(True)
        self.scope.setEnabled(True)
