"""Background formula creation and matrix exports. Workflow: README.md."""
from pathlib import Path
import string

from PySide6 import QtCore, QtWidgets

from attack_catalog import DOMAIN_LABELS
from layer_analysis import calculate_layer, snapshot_document
from matrix_exports import export_matrix
from navigator_dialogs import IntegrationDialog


class FormulaDialog(IntegrationDialog):
    def __init__(self, documents, current, parent):
        super().__init__(parent)
        self.setWindowTitle('Create layer from score formula')
        self.resize(720, 540)
        self.result_document = None
        self.documents = [snapshot_document(doc) for doc in documents
                          if doc.catalog.domain == current.catalog.domain and doc.catalog.version == current.catalog.version
                          and doc.catalog.dataset_id == current.catalog.dataset_id][:26]
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(f'{DOMAIN_LABELS[current.catalog.domain]} v{current.catalog.version} · '
                                          f'{len(self.documents)} compatible source layers (maximum 26)'))
        table = QtWidgets.QTableWidget(len(self.documents), 2)
        table.setHorizontalHeaderLabels(['Variable', 'Source layer'])
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        for number, doc in enumerate(self.documents):
            table.setItem(number, 0, QtWidgets.QTableWidgetItem(string.ascii_lowercase[number]))
            table.setItem(number, 1, QtWidgets.QTableWidgetItem(doc.name))
        self.sources_table = table
        layout.addWidget(table, 1)
        form = QtWidgets.QFormLayout()
        self.name = QtWidgets.QLineEdit('Computed layer')
        number = 2
        existing = {doc.name.casefold() for doc in documents}
        while self.name.text().casefold() in existing:
            self.name.setText(f'Computed layer {number}')
            number += 1
        self.expression = QtWidgets.QLineEdit('a+b' if len(self.documents) > 1 else 'a')
        self.expression.setPlaceholderText('a+b · (a+b)/2 · a*(1-b)')
        self.missing = QtWidgets.QComboBox()
        self.missing.addItem('Keep unscored when a referenced score is missing', 'unscored')
        self.missing.addItem('Treat missing/disabled source scores as zero', 'zero')
        form.addRow('New layer name', self.name)
        form.addRow('Score expression', self.expression)
        form.addRow('Missing scores', self.missing)
        layout.addLayout(form)
        hint = QtWidgets.QLabel('Use numbers, +, -, *, / and parentheses. Calculations use stored scores for '
                               'TTPs selected in referenced sources; displayed family aggregates are separate. '
                               'Sources stay unchanged. The result gets its own score gradient and provenance.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        self.create_button = QtWidgets.QPushButton('Create result layer')
        self.create_button.clicked.connect(self.calculate)
        layout.addWidget(self.create_button)
        close = QtWidgets.QPushButton('Cancel / Close')
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def calculate(self):
        if self.worker and self.worker.isRunning():
            return
        self.create_button.setEnabled(False)
        name, expression, missing = self.name.text(), self.expression.text(), self.missing.currentData()
        self.start_task(lambda notify: calculate_layer(self.documents, expression, name, missing, notify), self.complete)
        self.worker.finished.connect(lambda: self.create_button.setEnabled(self.result_document is None))

    def complete(self, document):
        if self.closing:
            return
        self.result_document = document
        parent = self.parent()
        parent.install_imported_document(document)
        parent.matrix_view.show_all_layers.setChecked(False)
        if parent.loaded_ok:
            parent.open_matrix()
        else:
            parent.layer_matrix_pending = True
        self.accept()


class MatrixExportDialog(IntegrationDialog):
    def __init__(self, document, target, kind, options, parent):
        super().__init__(parent)
        self.setWindowTitle('Export matrix ' + kind.upper())
        self.resize(680, 260)
        self.output_path = None
        self.document = snapshot_document(document)
        self.target, self.kind = Path(target).resolve(), kind
        self.options = dict(options)
        if self.options.get('sources') is not None:
            self.options['sources'] = [snapshot_document(doc) for doc in self.options['sources']]
        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel(f'Output file: {self.target}')
        label.setWordWrap(True)
        label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(label)
        hint = QtWidgets.QLabel('Exports the current platform/search/colors/overlay view with all matching '
                               'sub-techniques expanded. Existing files are replaced only after rendering succeeds. '
                               'Document names and save markers are preserved.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        self.export_button = QtWidgets.QPushButton('Export ' + kind.upper())
        self.export_button.clicked.connect(self.export)
        layout.addWidget(self.export_button)
        close = QtWidgets.QPushButton('Cancel / Close')
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def export(self):
        if self.worker and self.worker.isRunning():
            return
        self.export_button.setEnabled(False)
        self.start_task(lambda notify: export_matrix(self.document, self.target, self.kind, notify, **self.options), self.complete)
        self.worker.finished.connect(lambda: self.export_button.setEnabled(self.output_path is None))

    def complete(self, path):
        self.output_path = path
        self.report(f'Complete: {path}', 4, 4)
