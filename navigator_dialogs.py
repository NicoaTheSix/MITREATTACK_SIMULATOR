"""Native Navigator import, annotations and comparisons. Workflow: README.md."""
from copy import copy, deepcopy
import math
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from navigator_visuals import GRADIENT_PRESETS

from attack_catalog import external_id, DOMAIN_LABELS, tactic_phases, domain_label
from attack_versions import cached_discovery, local_versions, prepare_version, version_key, snapshot_pointer
from navigator_integration import (read_layers, layer_version, import_preview, imported_document,
                                   update_annotation, compare_documents, compare_versions, write_json_atomic, document_layer, validate_layer)
from navigator_visuals import DEFAULT_GRADIENT
from ttp_documents import validate_document_name
from navigator_field_editor import FieldEditor
from navigator_preferences import DISPLAY_KEY, display_editor, editor_values
from context_templates import CONTEXT_KEY, ContextEditor


class IntegrationWorker(QtCore.QThread):
    progress = QtCore.Signal(str, int, int)
    completed = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task

    def report(self, message, current=0, total=0):
        if self.isInterruptionRequested():
            raise InterruptedError("Operation cancelled")
        self.progress.emit(message, current, total)

    def run(self):
        try:
            result = self.task(self.report)
            if not self.isInterruptionRequested():
                self.completed.emit(result)
        except Exception as error:
            if not self.isInterruptionRequested():
                self.failed.emit(f"{type(error).__name__}: {error}")


class IntegrationDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.worker = None
        self.closing = False
        self.status = QtWidgets.QLabel("Ready")
        self.status.setWordWrap(True)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(1)

    def report(self, message, current=0, total=0):
        self.status.setText(message)
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.parent().operation_report(message, current, total)

    def start_task(self, task, completed):
        if self.worker and self.worker.isRunning():
            return
        if self.worker:
            self.worker.deleteLater()
        self.worker = IntegrationWorker(task, self)
        self.worker.progress.connect(self.report)
        self.worker.completed.connect(completed)
        self.worker.failed.connect(lambda message: self.report("Failed: " + message, 1, 1))
        self.worker.finished.connect(self.task_finished)
        self.worker.start()

    def running_worker(self):
        return next((worker for worker in self.findChildren(IntegrationWorker) if worker.isRunning()), None)

    def task_finished(self):
        if self.closing:
            super().reject()

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.closing = True
            self.worker.requestInterruption()
            self.status.setText("Cancelling; waiting for the current processing stage to finish…")
            return
        super().reject()

    def closeEvent(self, event):
        if self.running_worker():
            self.reject()
            event.ignore()
        else:
            super().closeEvent(event)


class ImportLayerDialog(IntegrationDialog):
    imported = QtCore.Signal(object)
    imported_many = QtCore.Signal(object)

    def __init__(self, root, path, catalog, parent, install=None, origin=''):
        super().__init__(parent)
        from navigator_import import LayerImportResolver
        self.root, self.path, self.fallback_catalog = Path(root).resolve(), Path(path).expanduser().resolve(), catalog
        self.install = install
        self.origin = origin
        self.source_dialog = None
        candidates = [doc.catalog for doc in getattr(parent, 'documents', [])]
        official = getattr(parent, 'official_catalog', None)
        if official is not None:
            candidates.append(official)
        candidates.append(catalog)
        atlas = getattr(parent, 'current_atlas_catalog', None)
        if atlas is not None:
            candidates.append(atlas)
        self.resolver = LayerImportResolver(self.root, candidates)
        self.catalog = self.preview = None
        self.layers, self.results, self.versions, self.policies = [], {}, {}, {}
        self.pending_resolve = False
        self.busy = True
        self.setWindowTitle("Import Navigator Layer")
        self.resize(1100, 800)
        layout = QtWidgets.QVBoxLayout(self)
        path_label = QtWidgets.QLabel(str(self.path))
        path_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        hint = QtWidgets.QLabel('Check the layers to open. All are checked by default; each uses its own domain, version and dataset. '
            'Every checked layer must be ready before the whole batch opens. Existing documents stay open.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        framework_row = QtWidgets.QHBoxLayout()
        self.read_attack = QtWidgets.QCheckBox('Read ATT&CK')
        self.read_atlas = QtWidgets.QCheckBox('Read ATLAS')
        for box in (self.read_attack, self.read_atlas):
            box.setChecked(True)
            framework_row.addWidget(box)
            box.toggled.connect(self.framework_choices_changed)
        framework_row.addStretch()
        layout.addLayout(framework_row)
        choices = QtWidgets.QHBoxLayout()
        self.select_all_button = QtWidgets.QPushButton('Select all layers')
        self.select_none_button = QtWidgets.QPushButton('Deselect all layers')
        self.select_all_button.clicked.connect(lambda: self.check_layers(True))
        self.select_none_button.clicked.connect(lambda: self.check_layers(False))
        choices.addWidget(self.select_all_button)
        choices.addWidget(self.select_none_button)
        choices.addStretch()
        layout.addLayout(choices)
        self.layers_table = QtWidgets.QTableWidget(0, 5)
        self.layers_table.setHorizontalHeaderLabels(['Open', 'Layer', 'Domain / version', 'Dataset', 'Status'])
        self.layers_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.layers_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.layers_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.layers_table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.layers_table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.layers_table.setMaximumHeight(220)
        self.layers_table.itemChanged.connect(self.checked_changed)
        self.layers_table.cellClicked.connect(lambda row, column: self.layer.setCurrentIndex(row))
        layout.addWidget(self.layers_table)
        form = QtWidgets.QFormLayout()
        self.layer = QtWidgets.QComboBox()
        self.version = QtWidgets.QComboBox()
        self.discovery = cached_discovery(self.root, self.report)
        versions = local_versions(self.root) | {row["version"] for row in self.discovery.get("versions", [])} | {catalog.version}
        self.version.addItems(sorted(versions, key=version_key, reverse=True))
        self.policy = QtWidgets.QComboBox()
        for label, value in (("Enabled rows / saved Studio selection", "enabled"),
                             ("All listed rows", "all"), ("Rows with a score or color", "annotated")):
            self.policy.addItem(label, value)
        form.addRow("Layer preview", self.layer)
        form.addRow("ATT&CK version", self.version)
        form.addRow("Select techniques", self.policy)
        layout.addLayout(form)
        self.load_button = QtWidgets.QPushButton("Load selected versions / Preview")
        layout.addWidget(self.load_button)
        self.custom_button = QtWidgets.QPushButton('Resolve custom data…')
        self.custom_button.clicked.connect(self.open_custom_data)
        layout.addWidget(self.custom_button)
        self.table = QtWidgets.QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Tactic", "Enabled", "Score", "Comment", "Resolution"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(6, 155)
        layout.addWidget(self.table, 1)
        self.preview_summary = QtWidgets.QLabel()
        self.preview_summary.setWordWrap(True)
        layout.addWidget(self.preview_summary)
        self.summary = QtWidgets.QLabel("Choose layers and review their techniques before opening the batch.")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.import_button = buttons.addButton("Open selected layers", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.rejected.connect(self.reject)
        self.import_button.clicked.connect(self.commit)
        layout.addWidget(buttons)
        self.layer.currentIndexChanged.connect(self.layer_changed)
        self.version.currentTextChanged.connect(self.version_changed)
        self.policy.currentIndexChanged.connect(self.policy_changed)
        self.load_button.clicked.connect(self.load_catalog)
        self.set_busy(True)
        QtCore.QTimer.singleShot(0, self.read_file)

    def read_file(self):
        if not self.closing:
            self.report(f'Input file: {self.path}', 0, 0)
            self.report('Output files: None (multi-layer import preview in memory)', 0, 0)
            self.report('[Layer Batch 1/5] Reading and validating every layer in the JSON file', 0, 5)
            self.start_task(lambda notify: read_layers(self.path, notify), self.file_loaded)

    def selected_indices(self):
        return [i for i in range(len(self.layers))
                if self.layers_table.item(i, 0).checkState() == QtCore.Qt.CheckState.Checked
                and (self.read_atlas.isChecked() if self.layers[i]['domain'] == 'atlas-atlas' else self.read_attack.isChecked())]

    def framework_choices_changed(self):
        if not hasattr(self, 'layers_table'):
            return
        self.layers_table.blockSignals(True)
        for i, layer in enumerate(self.layers):
            allowed = self.read_atlas.isChecked() if layer['domain'] == 'atlas-atlas' else self.read_attack.isChecked()
            item = self.layers_table.item(i, 0)
            item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                          if allowed else QtCore.Qt.ItemFlag.NoItemFlags)
        self.layers_table.blockSignals(False)
        self.checked_changed()

    def set_busy(self, value):
        self.busy = value
        for control in (self.layer, self.layers_table, self.policy, self.load_button,
                        self.select_all_button, self.select_none_button, self.read_attack, self.read_atlas):
            control.setEnabled(not value and bool(self.layers))
        index = self.layer.currentIndex()
        self.version.setEnabled(not value and index >= 0 and bool(self.layers)
                                and 'attack' not in self.layers[index].get('versions', {}))
        self.refresh_batch_state()

    def file_loaded(self, layers):
        self.layers = layers
        self.results.clear()
        self.layer.blockSignals(True)
        self.layers_table.blockSignals(True)
        self.layer.clear()
        self.layers_table.setRowCount(len(layers))
        for index, layer in enumerate(layers):
            try:
                self.versions[index] = layer_version(layer, self.fallback_catalog.version)
            except ValueError:
                self.versions[index] = self.fallback_catalog.version
            self.policies[index] = 'enabled'
            self.layer.addItem(f"{index + 1}. {layer['name']} — {self.layer_domain_label(index)}")
            item = QtWidgets.QTableWidgetItem()
            item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.CheckState.Checked)
            self.layers_table.setItem(index, 0, item)
            self.layers_table.setItem(index, 1, QtWidgets.QTableWidgetItem(layer['name']))
        self.layers_table.blockSignals(False)
        self.layer.blockSignals(False)
        self.pending_resolve = True
        self.layer_changed()
        self.refresh_batch_state()

    def layer_changed(self, *_):
        index = self.layer.currentIndex()
        self.catalog = self.preview = None
        self.table.setRowCount(0)
        if index < 0 or not self.layers:
            return
        version = self.versions[index]
        self.version.blockSignals(True)
        if self.version.findText(version) < 0:
            self.version.addItem(version)
        self.version.setCurrentText(version)
        self.version.blockSignals(False)
        self.version.setEnabled(not self.busy and 'attack' not in self.layers[index].get('versions', {}))
        self.policy.blockSignals(True)
        self.policy.setCurrentIndex(self.policy.findData(self.policies[index]))
        self.policy.blockSignals(False)
        result = self.results.get(index, {})
        self.catalog, self.preview = result.get('catalog'), result.get('preview')
        self.render_preview()
        self.refresh_batch_state()

    def version_changed(self, *_):
        index = self.layer.currentIndex()
        if index < 0 or not self.layers:
            return
        self.versions[index] = self.version.currentText()
        self.results.pop(index, None)
        self.catalog = self.preview = None
        self.table.setRowCount(0)
        self.refresh_batch_state()

    def policy_changed(self, *_):
        index = self.layer.currentIndex()
        if index < 0 or not self.layers:
            return
        self.policies[index] = self.policy.currentData()
        self.update_preview()

    def check_layers(self, checked):
        if self.busy:
            return
        self.layers_table.blockSignals(True)
        for index in range(len(self.layers)):
            self.layers_table.item(index, 0).setCheckState(
                QtCore.Qt.CheckState.Checked if checked else QtCore.Qt.CheckState.Unchecked)
        self.layers_table.blockSignals(False)
        self.checked_changed()

    def checked_changed(self, *_):
        if self.busy:
            return
        self.refresh_batch_state()
        if any(index not in self.results for index in self.selected_indices()):
            self.resolve_selected()

    def refresh_batch_state(self):
        if not hasattr(self, 'import_button'):
            return
        from localization import tr
        selected = self.selected_indices()
        ready = sum(bool(self.results.get(index, {}).get('catalog')) for index in selected)
        self.import_button.setEnabled(not self.busy and bool(selected) and ready == len(selected))
        self.load_button.setEnabled(not self.busy and bool(selected))
        index = self.layer.currentIndex()
        custom = index >= 0 and bool(self.layers) and bool(self.layers[index].get('customDataURL')
                                                       or self.layers[index].get('x_ttp_studio_dataset'))
        self.custom_button.setVisible(bool(custom))
        self.custom_button.setEnabled(bool(custom) and not self.busy and not self.closing)
        for index, layer in enumerate(self.layers):
            data = self.results.get(index, {})
            status = data.get('error') or (('Ready' if 'attack' in layer.get('versions', {}) else
                     'Ready (version chosen in preview)') if data.get('catalog') else 'Needs preview')
            dataset = layer.get('x_ttp_studio_dataset') or layer.get('customDataURL') or tr('Official ATT&CK')
            for column, value in ((2, f"{self.layer_domain_label(index)} v{self.versions[index]}"),
                                  (3, dataset), (4, status)):
                item = QtWidgets.QTableWidgetItem(value)
                item.setToolTip(value)
                self.layers_table.blockSignals(True)
                self.layers_table.setItem(index, column, item)
                self.layers_table.blockSignals(False)
        if hasattr(self, 'summary'):
            self.summary.setText(tr('{selected} layers checked; {ready} ready. All checked layers open together in file order.').format(
                selected=len(selected), ready=ready))

    def layer_domain_label(self, index):
        layer = self.layers[index]
        catalog = self.results.get(index, {}).get('catalog')
        return (domain_label(layer['domain'], catalog) if catalog is not None else
                layer.get('x_ttp_studio_domain', {}).get('name', domain_label(layer['domain'])))

    def resolve_selected(self, download=False):
        if self.closing or self.busy or not self.layers:
            return
        indices = self.selected_indices()
        if not indices:
            return
        versions, policies = dict(self.versions), dict(self.policies)
        self.set_busy(True)
        self.start_task(lambda notify: self.resolver.preview(self.layers, indices, versions, policies, notify,
                        download=download, discovery=self.discovery), self.previews_loaded)

    def load_catalog(self):
        self.resolve_selected(download=True)

    def operation_report(self, message, current=0, total=0):
        self.report(message, current, total)

    def open_custom_data(self):
        if self.busy or self.closing or not self.custom_button.isEnabled():
            return
        if self.source_dialog and self.source_dialog.isVisible():
            self.source_dialog.raise_()
            return
        from custom_data_dialog import CustomDataDialog
        index = self.layer.currentIndex()
        layer = deepcopy(self.layers[index])
        current = self.results.get(index, {}).get('catalog')
        if current is not None and current.dataset_id and not layer.get('x_ttp_studio_dataset'):
            layer['x_ttp_studio_dataset'] = current.dataset_id
        dialog = CustomDataDialog(self.root, layer, self.versions[index], self.policies[index],
                                  self.path, self, self.origin)
        self.source_dialog = dialog
        dialog.source_accepted.connect(lambda result: self.bind_custom_data(index, result))
        dialog.show()

    def bind_custom_data(self, index, result):
        if self.closing:
            return
        # The child is modal: the version/policy and focused layer cannot change while reviewing.
        self.layers[index] = result['layer']
        catalog = result['catalog']
        self.resolver.catalogs[(catalog.dataset_id, catalog.version)] = catalog
        self.results[index] = {'catalog': catalog, 'preview': result['preview'], 'error': ''}
        self.layer_changed()
        self.report('[Custom Data 5/5] Verified Bundle bound to this layer preview', 5, 5)

    def previews_loaded(self, results):
        if self.closing:
            return
        self.results.update(results)
        self.layer_changed()
        self.report('[Layer Batch 3/5] Preview complete; no documents have been added', 3, 5)

    def task_finished(self):
        self.set_busy(False)
        if self.pending_resolve and not self.closing:
            self.pending_resolve = False
            QtCore.QTimer.singleShot(0, self.resolve_selected)
        super().task_finished()

    def update_preview(self, *_):
        index = self.layer.currentIndex()
        if self.catalog is None or index < 0:
            self.refresh_batch_state()
            return
        try:
            # Validate extension/selection policies as well as the visible table.
            imported_document(self.layers[index], self.catalog, self.policies[index])
            self.preview = import_preview(self.layers[index], self.catalog, self.policies[index])
            self.results[index] = {'catalog': self.catalog, 'preview': self.preview, 'error': ''}
        except (ValueError, TypeError, KeyError) as error:
            self.results[index] = {'catalog': None, 'preview': None, 'error': str(error)}
            self.catalog = self.preview = None
        self.render_preview()
        self.refresh_batch_state()

    def render_preview(self):
        self.table.setRowCount(0)
        if self.preview is None:
            self.preview_summary.setText(self.results.get(self.layer.currentIndex(), {}).get('error', 'Choose a layer to preview.'))
            return
        from localization import tr
        self.preview_summary.setText(tr('{selected} unique TTPs selected; {unresolved} unresolved rows remain as annotations and are not selected.').format(
            selected=len(self.preview['selected']), unresolved=self.preview['unresolved']))
        self.table.setRowCount(len(self.preview['rows']))
        for number, row in enumerate(self.preview['rows']):
            entry = row['entry']
            values = [entry['techniqueID'], row['name'], entry.get('tactic', 'All tactics'),
                      str(entry.get('enabled', True)), str(entry.get('score', '')), entry.get('comment', ''), row['status']]
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setToolTip(value)
                self.table.setItem(number, column, item)
        self.table.setToolTip(f"{len(self.preview['selected'])} unique TTPs selected; {self.preview['unresolved']} unresolved rows "
                              "will remain as annotations and will not be selected.")

    def commit(self):
        if not self.import_button.isEnabled() or self.busy:
            return
        indices = self.selected_indices()
        if len(getattr(self.parent(), 'documents', [])) + len(indices) > 50:
            self.report('Opening this batch would exceed 50 documents. Close some files and retry; no layers were added.', 1, 1)
            return
        from navigator_import import build_import_documents
        layers, versions, policies = deepcopy(self.layers), dict(self.versions), dict(self.policies)
        catalogs = {index: self.results[index]['catalog'] for index in indices}
        self.set_busy(True)
        self.start_task(lambda notify: build_import_documents(layers, indices, versions, policies, catalogs, notify),
                        self.documents_built)

    def documents_built(self, documents):
        if self.closing:
            return
        try:
            if self.install is not None:
                if not self.install(documents):
                    self.report('[Layer Batch] Installation failed; no layers were added', 1, 1)
                    return
            elif len(documents) == 1:
                self.imported.emit(documents[0])
            else:
                self.imported_many.emit(documents)
        except (ValueError, TypeError, RuntimeError) as error:
            self.report('[Layer Batch] Installation failed: ' + str(error), 1, 1)
            return
        self.report('[Layer Batch 5/5] All selected layers opened as independent documents', len(documents), len(documents))
        self.accept()

    def reject(self):
        self.pending_resolve = False
        self.closing = True
        if self.source_dialog and (self.source_dialog.isVisible() or self.source_dialog.running_worker()):
            self.source_dialog.reject()
            if self.source_dialog.running_worker():
                self.source_dialog.finished.connect(lambda _: self.reject(), QtCore.Qt.ConnectionType.SingleShotConnection)
                return
        super().reject()



class AnnotationDialog(QtWidgets.QDialog):
    def __init__(self, document, key, parent):
        super().__init__(parent)
        self.document, self.key = document, key
        obj = document.catalog.records[key]
        self.setWindowTitle(f"Navigator annotation — {external_id(obj)} {obj['name']}")
        self.resize(720, 700)
        layout = QtWidgets.QFormLayout(self)
        self.scope = QtWidgets.QComboBox()
        self.scope.addItem("All tactics", "")
        for phase in obj.get("kill_chain_phases", []):
            if phase["phase_name"] in tactic_phases(obj, document.catalog.domain):
                slug = phase["phase_name"]
                self.scope.addItem(document.catalog.tactics[slug]["name"], slug)
        self.comment = QtWidgets.QPlainTextEdit()
        self.score = QtWidgets.QLineEdit()
        self.color = QtWidgets.QLineEdit()
        self.color.setPlaceholderText("#RRGGBB or blank")
        self.score.setPlaceholderText("Number or blank")
        layout.addRow("Tactic scope", self.scope)
        layout.addRow("Comment", self.comment)
        layout.addRow("Score", self.score)
        color_row = QtWidgets.QHBoxLayout()
        color_row.addWidget(self.color)
        self.pick_color = QtWidgets.QPushButton("Choose…")
        self.pick_color.clicked.connect(self.choose_color)
        color_row.addWidget(self.pick_color)
        self.clear_color = QtWidgets.QPushButton("Clear")
        self.clear_color.clicked.connect(self.color.clear)
        color_row.addWidget(self.clear_color)
        layout.addRow("Color", color_row)
        self.links = FieldEditor('links')
        self.metadata = FieldEditor('metadata')
        self.fields_tabs = QtWidgets.QTabWidget()
        self.fields_tabs.addTab(self.links, 'Links')
        self.fields_tabs.addTab(self.metadata, 'Metadata')
        layout.addRow(self.fields_tabs)
        self.include = QtWidgets.QCheckBox("Include this TTP in the document")
        self.include.setChecked(key in document.selected)
        layout.addRow(self.include)
        self.enabled = QtWidgets.QCheckBox('Enabled in this layer (independent of inclusion)')
        layout.addRow(self.enabled)
        self.error = QtWidgets.QLabel()
        self.error.setWordWrap(True)
        layout.addRow(self.error)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.scope.currentIndexChanged.connect(self.load_scope)
        first = next((row for row in document.navigator_layer.get("techniques", [])
                      if row["techniqueID"] == external_id(obj)), {})
        existing_scope = self.scope.findData(first.get("tactic", ""))
        if existing_scope >= 0:
            self.scope.setCurrentIndex(existing_scope)
        self.load_scope()

    def load_scope(self, *_):
        row = next((entry for entry in reversed(self.document.navigator_layer.get("techniques", []))
                    if entry["techniqueID"] == external_id(self.document.catalog.records[self.key])
                    and entry.get("tactic", "") == self.scope.currentData()), None)
        if row is None:
            row = next((entry for entry in reversed(self.document.navigator_layer.get('techniques', []))
                        if entry['techniqueID'] == external_id(self.document.catalog.records[self.key]) and not entry.get('tactic')), {})
        self.enabled.setChecked(row.get('enabled', True))
        self.initial_enabled = row.get('enabled', True)
        self.comment.setPlainText(row.get("comment", ""))
        self.score.setText(str(row["score"]) if "score" in row else "")
        self.color.setText(row.get("color", ""))
        self.links.load(row.get('links', []))
        self.metadata.load([entry for entry in row.get('metadata', [])
                            if entry.get('name') != 'TTP Selection Studio selected'])
        self.reserved_metadata = [entry for entry in row.get('metadata', [])
                                  if entry.get('name') == 'TTP Selection Studio selected']

    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.color.text() or '#007acc'), self, 'Technique color')
        if color.isValid():
            self.color.setText(color.name())

    def save(self):
        try:
            score = float(self.score.text()) if self.score.text().strip() else None
            if score is not None and not math.isfinite(score):
                raise ValueError("Score must be a finite number.")
            candidate = copy(self.document)
            update_annotation(candidate, self.key, self.scope.currentData(), self.comment.toPlainText(), score,
                              self.color.text().strip(), self.links.values(), self.metadata.values() + self.reserved_metadata)
            from ttp_operations import batch_patch
            if self.scope.currentData() and self.enabled.isChecked() != self.initial_enabled:
                batch_patch(candidate, {self.key}, {'enabled': self.enabled.isChecked()}, self.scope.currentData())
            elif not self.scope.currentData() and self.enabled.isChecked() != self.initial_enabled:
                # The single editor edits the global annotation, without replacing
                # state overrides on other tactic-specific rows.
                identity = external_id(candidate.catalog.records[self.key])
                rows = candidate.navigator_layer.setdefault('techniques', [])
                entry = next((row for row in reversed(rows) if row['techniqueID'] == identity and not row.get('tactic')), None)
                if entry is None and not self.enabled.isChecked():
                    entry = {'techniqueID': identity}
                    rows.append(entry)
                if entry is not None:
                    entry['enabled'] = self.enabled.isChecked()
                validate_layer(candidate.navigator_layer)
        except Exception as error:
            self.error.setText(str(error))
            return
        self.result_layer = candidate.navigator_layer
        self.accept()


class LayerSettingsDialog(QtWidgets.QDialog):
    """Edit standard Navigator fields without dropping extension metadata."""
    def __init__(self, document, parent):
        super().__init__(parent)
        self.document = document
        self.result_layer = None
        self.setWindowTitle("Navigator layer settings")
        self.resize(680, 640)
        self.original = document_layer(document, validate=False)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.name = QtWidgets.QLineEdit(document.name)
        form.addRow("Layer / document name", self.name)
        self.description = QtWidgets.QPlainTextEdit(self.original.get('description', ''))
        self.description.setMaximumHeight(90)
        form.addRow("Description", self.description)
        gradient = self.original.get('gradient', DEFAULT_GRADIENT)
        self.gradient_preset = QtWidgets.QComboBox()
        self.gradient_preset.addItem('Custom · keep current settings')
        self.gradient_preset.addItems([entry[0] for entry in GRADIENT_PRESETS])
        form.addRow('Gradient preset', self.gradient_preset)
        self.minimum = QtWidgets.QLineEdit(str(gradient['minValue']))
        self.maximum = QtWidgets.QLineEdit(str(gradient['maxValue']))
        form.addRow("Minimum score", self.minimum)
        form.addRow("Maximum score", self.maximum)
        self.colors = QtWidgets.QLineEdit(', '.join(gradient['colors']))
        self.colors.setPlaceholderText('#ff6666, #ffe766, #8ec843')
        stops = QtWidgets.QHBoxLayout()
        stops.addWidget(self.colors)
        self.add_stop = QtWidgets.QPushButton("Add color…")
        self.add_stop.clicked.connect(self.add_color_stop)
        stops.addWidget(self.add_stop)
        form.addRow("Gradient stops", stops)
        self.gradient_preset.activated.connect(self.apply_gradient_preset)
        for editor in (self.colors,self.minimum,self.maximum):
            editor.textEdited.connect(lambda *_:self.gradient_preset.setCurrentIndex(0))
        self.hide_disabled = QtWidgets.QCheckBox("Hide disabled technique rows")
        self.hide_disabled.setChecked(self.original.get('hideDisabled', False))
        form.addRow(self.hide_disabled)
        aggregate = self.original.get('layout', {})
        self.show_aggregate = QtWidgets.QCheckBox('Show parent/sub-technique aggregate scores')
        self.show_aggregate.setChecked(aggregate.get('showAggregateScores', False))
        form.addRow(self.show_aggregate)
        self.aggregate_function = QtWidgets.QComboBox()
        for label, value in (('Average', 'average'), ('Maximum', 'max'), ('Minimum', 'min'), ('Sum', 'sum')):
            self.aggregate_function.addItem(label, value)
        self.aggregate_function.setCurrentIndex(self.aggregate_function.findData(aggregate.get('aggregateFunction', 'average')))
        form.addRow('Aggregate function', self.aggregate_function)
        self.count_unscored = QtWidgets.QCheckBox('Count enabled unscored family members as zero')
        self.count_unscored.setChecked(aggregate.get('countUnscored', False))
        form.addRow(self.count_unscored)
        self.aggregate_function.setEnabled(self.show_aggregate.isChecked())
        self.count_unscored.setEnabled(self.show_aggregate.isChecked())
        self.show_aggregate.toggled.connect(self.aggregate_function.setEnabled)
        self.show_aggregate.toggled.connect(self.count_unscored.setEnabled)
        layout.addLayout(form)
        tabs = QtWidgets.QTabWidget()
        legend_page = QtWidgets.QWidget()
        legend_layout = QtWidgets.QVBoxLayout(legend_page)
        legend_layout.addWidget(QtWidgets.QLabel("Legend · double-click a color cell to choose a color"))
        self.legend = QtWidgets.QTableWidget(0, 2)
        self.legend.setHorizontalHeaderLabels(['Label', 'Color'])
        self.legend.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.legend.cellDoubleClicked.connect(self.choose_legend_color)
        for entry in self.original.get('legendItems', []):
            self.add_legend(entry['label'], entry['color'])
        legend_layout.addWidget(self.legend, 1)
        legend_buttons = QtWidgets.QHBoxLayout()
        self.add_legend_button = QtWidgets.QPushButton('Add legend item')
        self.add_legend_button.clicked.connect(lambda: self.add_legend('', '#007acc'))
        legend_buttons.addWidget(self.add_legend_button)
        self.remove_legend_button = QtWidgets.QPushButton('Remove selected item')
        self.remove_legend_button.clicked.connect(lambda: self.legend.removeRow(self.legend.currentRow()) if self.legend.currentRow() >= 0 else None)
        legend_buttons.addWidget(self.remove_legend_button)
        self.clear_legend_button = QtWidgets.QPushButton('Clear all legend items')
        self.clear_legend_button.clicked.connect(lambda:self.legend.setRowCount(0))
        self.clear_legend_button.setToolTip('Clears the draft. Save applies; Cancel restores the original legend.')
        legend_buttons.addWidget(self.clear_legend_button)
        legend_buttons.addStretch()
        legend_layout.addLayout(legend_buttons)
        tabs.addTab(legend_page, 'Legend')
        display_page=QtWidgets.QWidget()
        display_form=QtWidgets.QFormLayout(display_page)
        self.show_names=QtWidgets.QCheckBox('Show technique and tactic names')
        self.show_names.setChecked(aggregate.get('showName',True))
        self.show_ids=QtWidgets.QCheckBox('Show technique and tactic IDs')
        self.show_ids.setChecked(aggregate.get('showID',False))
        self.show_tactic_background=QtWidgets.QCheckBox('Show tactic header background · Flat / Side')
        self.show_tactic_background.setChecked(self.original.get('showTacticRowBackground',False))
        self.tactic_background=QtWidgets.QLineEdit(self.original.get('tacticRowBackground','#dddddd'))
        for control in (self.show_names,self.show_ids,self.show_tactic_background): display_form.addRow(control)
        color_row=QtWidgets.QHBoxLayout()
        color_row.addWidget(self.tactic_background)
        color_button=QtWidgets.QPushButton('Choose color…')
        def choose_background():
            color=QtWidgets.QColorDialog.getColor(QtGui.QColor(self.tactic_background.text()),self,'Tactic header background')
            if color.isValid(): self.tactic_background.setText(color.name())
        color_button.clicked.connect(choose_background)
        color_row.addWidget(color_button)
        display_form.addRow('Header color · #RRGGBB',color_row)
        hint=QtWidgets.QLabel('Name and ID controls are independent. Mini hides labels and custom header color without changing these settings. '
                              'Yellow indicators identify comments, metadata or source Notes; blue identifies links. '
                              'Selection metadata alone does not create an annotation indicator.')
        hint.setWordWrap(True)
        display_form.addRow(hint)
        tabs.addTab(display_page,'Display')
        effects, self.effect_controls = display_editor(self.original)
        tabs.addTab(effects, 'Colors / indicators')
        self.context_editor = ContextEditor(self.original)
        tabs.addTab(self.context_editor.page, 'Context actions')
        self.links = FieldEditor('links')
        self.links.load(self.original.get('links', []))
        self.metadata = FieldEditor('metadata')
        self.metadata.load(self.original.get('metadata', []))
        tabs.addTab(self.links, 'Layer links')
        tabs.addTab(self.metadata, 'Layer metadata')
        layout.addWidget(tabs, 1)
        self.error = QtWidgets.QLabel()
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply_gradient_preset(self, index):
        if index <= 0: return
        self.document_parent_report('Input files: None; output files: None (gradient draft in memory)',0,0)
        self.document_parent_report('[Gradient Preset 1/2] Loading colors and score bounds',0,2)
        _,colors,low,high = GRADIENT_PRESETS[index-1]
        self.colors.setText(', '.join(colors))
        self.minimum.setText(str(low))
        self.maximum.setText(str(high))
        self.document_parent_report('[Gradient Preset 2/2] Draft ready; Save applies, Cancel discards',2,2)

    def document_parent_report(self, text, current, total):
        notify = getattr(self.parent(), 'operation_report', None)
        if notify: notify(text,current,total)

    def add_color_stop(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor('#007acc'), self, 'Gradient color stop')
        if color.isValid():
            self.gradient_preset.setCurrentIndex(0)
            self.colors.setText(self.colors.text().rstrip(', ') + ', ' + color.name())

    def add_legend(self, label, color):
        row = self.legend.rowCount()
        self.legend.insertRow(row)
        self.legend.setItem(row, 0, QtWidgets.QTableWidgetItem(label))
        self.legend.setItem(row, 1, QtWidgets.QTableWidgetItem(color))

    def choose_legend_color(self, row, column):
        if column != 1:
            return
        item = self.legend.item(row, column)
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(item.text()), self, 'Legend color')
        if color.isValid():
            item.setText(color.name())

    def save(self):
        try:
            name = validate_document_name(self.name.text())
            candidate = deepcopy(self.original)
            candidate['name'] = name
            candidate['description'] = self.description.toPlainText()
            for field, editor in (('links', self.links), ('metadata', self.metadata)):
                values = editor.values()
                if values:
                    candidate[field] = values
                else:
                    candidate.pop(field, None)
            candidate['gradient'] = {'minValue': float(self.minimum.text()), 'maxValue': float(self.maximum.text()),
                                     'colors': [color.strip() for color in self.colors.text().split(',')]}
            candidate['legendItems'] = [{'label': self.legend.item(row, 0).text(), 'color': self.legend.item(row, 1).text().strip()}
                                        for row in range(self.legend.rowCount())]
            candidate['hideDisabled'] = self.hide_disabled.isChecked()
            candidate.setdefault('layout',{}).update(showID=self.show_ids.isChecked(),showName=self.show_names.isChecked())
            candidate['showTacticRowBackground']=self.show_tactic_background.isChecked()
            candidate['tacticRowBackground']=self.tactic_background.text().strip()
            candidate[DISPLAY_KEY] = editor_values(self.effect_controls)
            actions = self.context_editor.values()
            if actions: candidate[CONTEXT_KEY] = actions
            else: candidate.pop(CONTEXT_KEY, None)
            if 'layout' in candidate or self.show_aggregate.isChecked() or self.count_unscored.isChecked():
                candidate.setdefault('layout', {}).update(showAggregateScores=self.show_aggregate.isChecked(),
                    countUnscored=self.count_unscored.isChecked(), aggregateFunction=self.aggregate_function.currentData())
            self.result_layer = validate_layer(candidate)
        except Exception as error:
            self.error.setText(str(error))
            return
        self.accept()


class SelectionCompareDialog(IntegrationDialog):
    def __init__(self, documents, parent):
        super().__init__(parent)
        self.documents = documents
        self.result_layer = None
        self.setWindowTitle("Compare TTP selections")
        self.resize(750, 520)
        layout = QtWidgets.QVBoxLayout(self)
        self.left, self.right = QtWidgets.QComboBox(), QtWidgets.QComboBox()
        for document in documents:
            label = f"{document.name} — {domain_label(document.catalog.domain, document.catalog)} v{document.catalog.version}"
            self.left.addItem(label)
            self.right.addItem(label)
        if len(documents) > 1:
            self.right.setCurrentIndex(1)
        layout.addWidget(self.left)
        layout.addWidget(self.right)
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Selection"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        layout.addWidget(self.status)
        self.export_button = QtWidgets.QPushButton("Export comparison Navigator Layer…")
        self.export_button.clicked.connect(self.export)
        layout.addWidget(self.export_button)
        self.left.currentIndexChanged.connect(self.compare)
        self.right.currentIndexChanged.connect(self.compare)
        self.compare()

    def compare(self, *_):
        self.result_layer = None
        self.export_button.setEnabled(False)
        self.report("Input files: None; output files: None (open documents in memory)")
        self.report("[Selection Compare 1/2] Comparing selected TTPs", 0, 1)
        try:
            left, right = self.documents[self.left.currentIndex()], self.documents[self.right.currentIndex()]
            self.result_layer, counts = compare_documents(left, right)
            lookup = {external_id(record): record for record in left.catalog.records.values()}
            self.table.setRowCount(len(self.result_layer["techniques"]))
            for number, row in enumerate(self.result_layer["techniques"]):
                for column, text in enumerate((row["techniqueID"], lookup[row["techniqueID"]]["name"], row["comment"])):
                    self.table.setItem(number, column, QtWidgets.QTableWidgetItem(text))
            self.report("[Selection Compare 2/2] " + "; ".join(f"{name}: {value}" for name, value in counts.items()), 1, 1)
            self.export_button.setEnabled(True)
        except Exception as error:
            self.table.setRowCount(0)
            self.report(str(error), 1, 1)

    def export(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export comparison layer", str(Path.home() / "comparison.navigator.json"), "JSON files (*.json)")
        if filename:
            try:
                write_json_atomic(self.result_layer, filename, self.report, "Selection Compare Export")
            except Exception as error:
                self.report(f"Failed: {error}", 1, 1)


class VersionCompareDialog(IntegrationDialog):
    def __init__(self, root, document, parent):
        super().__init__(parent)
        self.root = Path(root)
        self.domain = document.catalog.domain
        self.selected_ids = {external_id(document.catalog.records[key]) for key in document.selected}
        self.result_report = None
        self.setWindowTitle("Compare ATT&CK versions — mitreattack-python")
        self.resize(1050, 650)
        layout = QtWidgets.QVBoxLayout(self)
        self.old, self.new = QtWidgets.QComboBox(), QtWidgets.QComboBox()
        versions = sorted((version for version in local_versions(self.root)
                           if snapshot_pointer(self.root, version).get(self.domain.split('-')[0] + '_bundle')),
                          key=version_key, reverse=True)
        self.old.addItems(versions)
        self.new.addItems(versions)
        self.old.setCurrentText(document.catalog.version)
        self.new.setCurrentIndex(1 if len(versions) > 1 else 0)
        form = QtWidgets.QFormLayout()
        form.addRow("From version", self.old)
        form.addRow("To version", self.new)
        layout.addLayout(form)
        layout.addWidget(QtWidgets.QLabel(f"Compare downloaded {domain_label(self.domain)} snapshots. Download other versions using Version first."))
        self.compare_button = QtWidgets.QPushButton("Compare versions")
        self.compare_button.clicked.connect(self.compare)
        layout.addWidget(self.compare_button)
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Type", "Change", "ID", "Name"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 155)
        self.table.setColumnWidth(1, 185)
        layout.addWidget(self.table, 1)
        self.impact = QtWidgets.QLabel()
        self.impact.setWordWrap(True)
        layout.addWidget(self.impact)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        self.export_button = QtWidgets.QPushButton("Export version comparison JSON…")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export)
        layout.addWidget(self.export_button)
        self.old.currentTextChanged.connect(self.invalidate)
        self.new.currentTextChanged.connect(self.invalidate)

    def invalidate(self, *_):
        self.result_report = None
        self.export_button.setEnabled(False)
        self.table.setRowCount(0)
        self.impact.clear()

    def compare(self):
        if self.worker and self.worker.isRunning():
            return
        # Initialize the SDK's transitive modules once before the long-running
        # worker so first-import work has a separate visible stage.
        self.report("Input files: None; output files: None (SDK initialization)")
        self.report("[Version Compare Prepare] Loading official SDK", 0, 1)
        try:
            from mitreattack.diffStix.changelog_helper import DiffStix
        except Exception as error:
            self.report(f"Failed: {error}", 1, 1)
            return
        self.invalidate()
        old, new = self.old.currentText(), self.new.currentText()
        self.old.setEnabled(False)
        self.new.setEnabled(False)
        self.compare_button.setEnabled(False)
        self.start_task(lambda notify: compare_versions(self.root, old, new, self.selected_ids, notify, self.domain), self.completed)

    def task_finished(self):
        self.old.setEnabled(True)
        self.new.setEnabled(True)
        self.compare_button.setEnabled(True)
        super().task_finished()

    def completed(self, report):
        self.result_report = report
        rows = []
        type_labels = {"techniques": "Techniques", "software": "Software", "groups": "Groups", "campaigns": "Campaigns",
                       "mitigations": "Mitigations", "assets": "Assets", "datasources": "Data Sources",
                       "datacomponents": "Data Components", "detectionstrategies": "Detection Strategies", "analytics": "Analytics"}
        change_labels = {"additions": "Added", "major_version_changes": "Major version change",
                         "minor_version_changes": "Minor version change", "other_version_changes": "Other version change",
                         "patches": "Patched", "revocations": "Revoked", "deprecations": "Deprecated", "deletions": "Deleted", "unchanged": "Unchanged"}
        for kind, sections in report["changes"][report["domain"]].items():
            for change, records in sections.items():
                for record in records:
                    rows.append((type_labels.get(kind, kind), change_labels.get(change, change),
                                 external_id(record) or record.get("id", ""), record.get("name", "")))
        self.table.setRowCount(len(rows))
        for number, row in enumerate(rows):
            for column, text in enumerate(row):
                item = QtWidgets.QTableWidgetItem(text)
                item.setToolTip(text)
                self.table.setItem(number, column, item)
        unavailable = report["unavailable_selected_ids"]
        self.impact.setText(f"{len(rows)} object changes. Selected IDs unavailable in v{report['new_version']}: "
                            + (", ".join(unavailable) if unavailable else "None"))
        self.export_button.setEnabled(True)

    def export(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export version comparison", str(Path.home() / "attack-version-comparison.json"), "JSON files (*.json)")
        if filename:
            try:
                write_json_atomic(self.result_report, filename, self.report, "Version Compare Export")
            except Exception as error:
                self.report(f"Failed: {error}", 1, 1)
