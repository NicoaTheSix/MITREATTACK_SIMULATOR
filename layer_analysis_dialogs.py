"""Background formula creation and matrix exports. Workflow: README.md."""
from pathlib import Path
import string

from PySide6 import QtCore, QtWidgets

from attack_catalog import DOMAIN_LABELS, domain_label
from layer_analysis import calculate_layer, snapshot_document
from matrix_exports import export_matrix, matrix_scene, svg_content
from navigator_dialogs import IntegrationDialog


class FormulaDialog(IntegrationDialog):
    def __init__(self, documents, current, parent):
        super().__init__(parent)
        self.setWindowTitle('Create layer from score formula')
        self.resize(820, 860)
        self.result_document = None
        self.documents = [snapshot_document(doc) for doc in documents
                          if doc.catalog.domain == current.catalog.domain and doc.catalog.version == current.catalog.version
                          and doc.catalog.dataset_id == current.catalog.dataset_id][:26]
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(f'{domain_label(current.catalog.domain, current.catalog)} v{current.catalog.version} · '
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
        self.options_tabs = QtWidgets.QTabWidget()
        calculation_page = QtWidgets.QWidget()
        calculation_layout = QtWidgets.QVBoxLayout(calculation_page)
        calculation_layout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
        form = QtWidgets.QFormLayout()
        self.name = QtWidgets.QLineEdit('Computed layer')
        number = 2
        existing = {doc.name.casefold() for doc in documents}
        while self.name.text().casefold() in existing:
            self.name.setText(f'Computed layer {number}')
            number += 1
        self.expression = QtWidgets.QLineEdit('a+b' if len(self.documents) > 1 else 'a')
        self.expression.setPlaceholderText('a+b · (a>b) and (a>=75) · a>b ? 25 : 10 · max(a,b)')
        self.syntax = QtWidgets.QComboBox()
        self.syntax.addItem('Navigator scalar · mathjs 15.2 semantics', 'navigator')
        self.syntax.addItem('Studio scalar · preserve earlier arithmetic semantics', 'studio')
        self.calculation_mode = QtWidgets.QComboBox()
        self.calculation_mode.addItem('Studio · chosen scope and missing-score policy', 'studio')
        self.calculation_mode.addItem('Navigator · official missing scores and scope', 'navigator')
        self._mode_was_navigator = False
        self._studio_syntax = 'navigator'
        self.scope = QtWidgets.QComboBox()
        self.scope.addItem('Selected TTP union from referenced sources', 'selected')
        self.scope.addItem('Entire matrix · all techniques and mapped tactics', 'matrix')
        self.missing = QtWidgets.QComboBox()
        self.missing.addItem('Keep unscored when a referenced score is missing', 'unscored')
        self.missing.addItem('Treat missing/disabled source scores as zero', 'zero')
        self.gradient_mode = QtWidgets.QComboBox()
        self.gradient_mode.addItem('Follow calculation mode', 'auto')
        self.gradient_mode.addItem('Studio · source colors and range including zero/one', 'studio')
        self.gradient_mode.addItem('Navigator · official result range and binary colors', 'navigator')
        form.addRow('New layer name', self.name)
        form.addRow('Score expression', self.expression)
        form.addRow('Calculation mode', self.calculation_mode)
        form.addRow('Formula syntax', self.syntax)
        form.addRow('Calculation scope', self.scope)
        form.addRow('Missing scores', self.missing)
        form.addRow('Automatic gradient mode', self.gradient_mode)
        calculation_layout.addLayout(form)
        hint = QtWidgets.QLabel('Constants: pi, e, tau, phi, true, false. Functions include sin/cos/tan, inverse/hyperbolic functions, '
            'log2/log10/log1p, expm1, cbrt, sign, fix and mod. Navigator syntax lowercases input, supports chained comparisons '
            'and infix mod, rounds halves away from zero and uses tolerant comparisons. Studio preserves earlier round/not/% semantics '
            'and also supports case-sensitive nthRoot. If layer e is listed, use exp(1) for Euler’s constant. '
            'Comparisons return 1/0. Entire matrix and missing-score policies remain independent; all mentioned variables are checked.')
        hint.setWordWrap(True)
        calculation_layout.addWidget(hint)
        self.mode_hint = QtWidgets.QLabel()
        self.mode_hint.setWordWrap(True)
        calculation_layout.addWidget(self.mode_hint)
        self.gradient_hint = QtWidgets.QLabel(
            'Follow calculation mode uses Navigator gradients in Navigator mode and Studio gradients in Studio mode. '
            'Navigator uses actual score bounds; a 0–1 range uses transparent white/blue. '
            'Constant or empty results keep the default 0–100 red/yellow/green. A selected source gradient overrides this setting.')
        self.gradient_hint.setWordWrap(True)
        calculation_layout.addWidget(self.gradient_hint)
        self.calculation_mode.currentIndexChanged.connect(self.update_calculation_mode)
        self.update_calculation_mode()
        calculation_layout.addStretch()
        self.calculation_scroll = QtWidgets.QScrollArea()
        self.calculation_scroll.setWidgetResizable(True)
        self.calculation_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.calculation_scroll.setWidget(calculation_page)
        self.options_tabs.addTab(self.calculation_scroll, 'Formula and scope')
        inheritance_page = QtWidgets.QWidget()
        inheritance_form = QtWidgets.QFormLayout(inheritance_page)
        self.inheritance = {}
        for field, label in (('gradient', 'Score gradient'), ('color', 'Manual colors'), ('comment', 'Comments'),
                             ('links', 'Links'), ('metadata', 'Metadata'), ('enabled', 'Enabled states'),
                             ('filters', 'Filters / hide disabled'), ('legendItems', 'Legend')):
            choice = QtWidgets.QComboBox()
            choice.addItem('Use automatic gradient mode' if field == 'gradient' else 'Do not inherit', '')
            for alias, doc in zip(string.ascii_lowercase, self.documents):
                choice.addItem(f'{alias}: {doc.name}', alias)
            self.inheritance[field] = choice
            inheritance_form.addRow(label, choice)
        self.inheritance['gradient'].currentIndexChanged.connect(self.update_gradient_inheritance)
        warning = QtWidgets.QLabel('Properties are copied independently from the chosen sources, within the calculation scope. '
                                   'Manual colors override score colors; disabled states hide their colors. '
                                   'An explicitly inherited gradient keeps its original bounds. '
                                   'Links/Metadata also copy layer-level lists. No source layer is changed.')
        warning.setWordWrap(True)
        inheritance_form.addRow(warning)
        self.options_tabs.addTab(inheritance_page, 'Inherit properties')
        layout.addWidget(self.options_tabs, 2)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        self.create_button = QtWidgets.QPushButton('Create result layer')
        self.create_button.clicked.connect(self.calculate)
        layout.addWidget(self.create_button)
        close = QtWidgets.QPushButton('Cancel / Close')
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def update_calculation_mode(self):
        navigator = self.calculation_mode.currentData() == 'navigator'
        if navigator:
            if not self._mode_was_navigator:
                self._studio_syntax = self.syntax.currentData()
            self.syntax.setCurrentIndex(self.syntax.findData('navigator'))
        elif self._mode_was_navigator:
            self.syntax.setCurrentIndex(self.syntax.findData(self._studio_syntax))
        for control in (self.syntax, self.scope, self.missing):
            control.setEnabled(not navigator)
        self.mode_hint.setText(
            'Navigator mode: try an empty-scope constant first (including lazy branches); constants score the entire matrix. '
            'Otherwise use all referenced scored technique/tactic cells, even if unselected, disabled or hidden; '
            'missing inputs become zero and all-missing cells stay unscored/enabled. '
            'Scope and missing-score controls are inactive. Navigator scalar syntax is required. '
            'Automatic gradient is configured separately; an inherited gradient takes priority.'
            if navigator else
            'Studio mode: apply the chosen scope and missing-score policy. Disabled source scores count as missing. '
            'Formula syntax remains independently selectable.')
        self._mode_was_navigator = navigator

    def update_gradient_inheritance(self):
        self.gradient_mode.setEnabled(not bool(self.inheritance['gradient'].currentData()))

    def calculate(self):
        if self.worker and self.worker.isRunning():
            return
        self.create_button.setEnabled(False)
        name, expression, missing = self.name.text(), self.expression.text(), self.missing.currentData()
        syntax = self.syntax.currentData()
        scope = self.scope.currentData()
        mode = self.calculation_mode.currentData()
        gradient_mode = self.gradient_mode.currentData()
        inheritance = {field: choice.currentData() for field, choice in self.inheritance.items() if choice.currentData()}
        self.options_tabs.setEnabled(False)
        self.start_task(lambda notify: calculate_layer(self.documents, expression, name, missing, notify, scope, inheritance, syntax, mode, gradient_mode), self.complete)
        self.worker.finished.connect(lambda: self.create_button.setEnabled(self.result_document is None))
        self.worker.finished.connect(lambda: self.options_tabs.setEnabled(True))

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
        self.svg_settings=None
        if kind == 'svg':
            from export_dialogs import SvgSettings
            from PySide6.QtSvgWidgets import QSvgWidget
            self.resize(850,850)
            hint.setText('Configure SVG presentation and preview before exporting. All sizes use the selected units. '
                         'Current platform/search/colors/overlay are captured when this dialog opens. '
                         'Expanded-only mode uses the captured per-tactic expansion. Existing output is published atomically.')
            self.svg_pages=QtWidgets.QTabWidget()
            self.svg_settings=SvgSettings()
            self.svg_pages.addTab(self.svg_settings,'Settings')
            self.preview=QSvgWidget()
            self.preview.setMinimumSize(200,180)
            self.svg_pages.addTab(self.preview,'Preview')
            layout.addWidget(self.svg_pages,1)
            self.preview_button=QtWidgets.QPushButton('Preview SVG · no file written')
            self.preview_button.clicked.connect(self.preview_svg)
            layout.addWidget(self.preview_button)
            self.svg_settings.changed.connect(self.settings_changed)
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
        options=dict(self.options)
        if self.svg_settings:
            options['svg_options']=self.svg_settings.options()
            self.svg_settings.setEnabled(False)
            self.preview_button.setEnabled(False)
        self.start_task(lambda notify: export_matrix(self.document, self.target, self.kind, notify, **options), self.complete)
        self.worker.finished.connect(lambda: self.export_button.setEnabled(self.output_path is None))
        if self.svg_settings:
            self.worker.finished.connect(lambda:self.svg_settings.setEnabled(True))
            self.worker.finished.connect(lambda:self.preview_button.setEnabled(True))

    def settings_changed(self):
        self.output_path=None
        self.export_button.setEnabled(True)
        self.status.setText('Settings changed; preview again or export to apply.')

    def preview_svg(self):
        if self.worker and self.worker.isRunning(): return
        from svg_export import validate_svg_options
        options=dict(self.options)
        svg_options=self.svg_settings.options()
        def task(notify):
            notify('Input files: None (captured matrix/layer snapshots)',0,0)
            notify('Output files: None (SVG preview in memory)',0,0)
            notify('[SVG Preview 1/3] Validating settings',0,3)
            if svg_options is not None: validate_svg_options(svg_options)
            expanded=options.pop('expanded',None)
            scene=matrix_scene(self.document,**options,notify=notify,
                subtechniques=svg_options['subtechniques'] if svg_options else 'all',expanded=expanded)
            notify('[SVG Preview 2/3] Rendering vector preview · SVG theme: '+(svg_options or {}).get('theme','dark'),1,3)
            payload=svg_content(scene,svg_options)
            notify('[SVG Preview 3/3] Complete',3,3)
            return payload
        self.svg_settings.setEnabled(False)
        self.export_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.start_task(task,self.show_preview)
        self.worker.finished.connect(lambda:self.svg_settings.setEnabled(True))
        self.worker.finished.connect(lambda:self.export_button.setEnabled(self.output_path is None))
        self.worker.finished.connect(lambda:self.preview_button.setEnabled(True))

    def show_preview(self,payload):
        self.preview.load(QtCore.QByteArray(payload))
        self.svg_pages.setCurrentIndex(1)

    def complete(self, path):
        self.output_path = path
        self.report(f'Complete: {path}', 4, 4)
        if self.svg_settings:
            self.preview.load(str(path))
