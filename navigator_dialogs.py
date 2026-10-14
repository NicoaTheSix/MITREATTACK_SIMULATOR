"""Native Navigator import, annotations and comparisons. Workflow: README.md."""
from copy import copy
import math
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from attack_catalog import external_id, DOMAIN_LABELS, tactic_phases
from attack_versions import cached_discovery, local_versions, prepare_version, version_key, snapshot_pointer
from navigator_integration import (read_layers, layer_version, import_preview, imported_document,
                                   update_annotation, compare_documents, compare_versions, write_json_atomic)


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

    def task_finished(self):
        if self.closing:
            super().reject()

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.closing = True
            self.worker.requestInterruption()
            self.status.setText("Cancelling; waiting for the current SDK stage to finish…")
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.reject()
            event.ignore()
        else:
            super().closeEvent(event)


class ImportLayerDialog(IntegrationDialog):
    imported = QtCore.Signal(object)

    def __init__(self, root, path, catalog, parent):
        super().__init__(parent)
        self.root, self.path, self.fallback_catalog = Path(root), Path(path), catalog
        self.catalog = None
        self.layers = []
        self.preview = None
        self.setWindowTitle("Import Navigator Layer")
        self.resize(1050, 650)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(str(self.path.resolve())))
        form = QtWidgets.QFormLayout()
        self.layer = QtWidgets.QComboBox()
        self.version = QtWidgets.QComboBox()
        self.discovery = cached_discovery(self.root, self.report)
        versions = local_versions(self.root) | {row["version"] for row in self.discovery.get("versions", [])}
        versions.add(catalog.version)
        self.version.addItems(sorted(versions, key=version_key, reverse=True))
        self.policy = QtWidgets.QComboBox()
        for label, value in (("Enabled rows / saved Studio selection", "enabled"),
                             ("All listed rows", "all"), ("Rows with a score or color", "annotated")):
            self.policy.addItem(label, value)
        form.addRow("Layer", self.layer)
        form.addRow("ATT&CK version", self.version)
        form.addRow("Select techniques", self.policy)
        layout.addLayout(form)
        self.load_button = QtWidgets.QPushButton("Load version / Preview")
        layout.addWidget(self.load_button)
        self.table = QtWidgets.QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Tactic", "Enabled", "Score", "Comment", "Resolution"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(6, 155)
        layout.addWidget(self.table, 1)
        self.summary = QtWidgets.QLabel("Choose a layer/version and review the techniques before importing.")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.import_button = buttons.addButton("Import as new document", QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        self.import_button.setEnabled(False)
        buttons.rejected.connect(self.reject)
        self.import_button.clicked.connect(self.commit)
        layout.addWidget(buttons)
        self.layer.currentIndexChanged.connect(self.layer_changed)
        self.version.currentTextChanged.connect(self.version_changed)
        self.policy.currentIndexChanged.connect(self.update_preview)
        self.load_button.clicked.connect(self.load_catalog)
        QtCore.QTimer.singleShot(0, lambda: self.start_task(lambda notify: read_layers(self.path, notify), self.file_loaded))

    def file_loaded(self, layers):
        self.layers = layers
        self.layer.blockSignals(True)
        self.layer.clear()
        for layer in layers:
            self.layer.addItem(f"{layer['name']} — {DOMAIN_LABELS[layer['domain']]}")
        self.layer.blockSignals(False)
        self.layer_changed()

    def layer_changed(self, *_):
        self.catalog = None
        self.import_button.setEnabled(False)
        self.table.setRowCount(0)
        if not self.layers:
            return
        layer = self.layers[self.layer.currentIndex()]
        try:
            version = layer_version(layer, self.fallback_catalog.version)
            if self.version.findText(version) < 0:
                self.version.addItem(version)
            self.version.setCurrentText(version)
            self.version.setEnabled("attack" not in layer.get("versions", {}))
            self.summary.setText("Recorded version will be used." if not self.version.isEnabled() else
                                 "No ATT&CK version recorded: choose the snapshot to use for ID resolution.")
        except ValueError as error:
            self.report(str(error), 1, 1)
            self.load_button.setEnabled(False)
            return
        self.load_button.setEnabled(True)
        if version == self.fallback_catalog.version:
            try:
                self.catalog = self.fallback_catalog.for_domain(layer["domain"])
                self.update_preview()
            except ValueError as error:
                self.report(str(error), 1, 1)

    def version_changed(self, *_):
        self.catalog = None
        self.import_button.setEnabled(False)

    def load_catalog(self):
        if not self.layers or (self.worker and self.worker.isRunning()):
            return
        version = self.version.currentText()
        self.import_button.setEnabled(False)
        self.layer.setEnabled(False)
        self.version.setEnabled(False)
        self.load_button.setEnabled(False)
        self.start_task(lambda notify: prepare_version(self.root, version, self.discovery, notify), self.catalog_loaded)

    def catalog_loaded(self, value):
        try:
            self.catalog = value[0].for_domain(self.layers[self.layer.currentIndex()]["domain"])
            self.update_preview()
        except ValueError as error:
            self.catalog = None
            self.report(str(error), 1, 1)

    def task_finished(self):
        self.layer.setEnabled(bool(self.layers))
        self.load_button.setEnabled(bool(self.layers))
        if self.layers:
            self.version.setEnabled("attack" not in self.layers[self.layer.currentIndex()].get("versions", {}))
        super().task_finished()

    def update_preview(self, *_):
        if not self.catalog or not self.layers:
            return
        layer = self.layers[self.layer.currentIndex()]
        try:
            self.preview = import_preview(layer, self.catalog, self.policy.currentData())
        except Exception as error:
            self.report(str(error), 1, 1)
            self.import_button.setEnabled(False)
            return
        self.report("[Navigator Import 2/4] Resolving rows against the chosen snapshot", 0, len(self.preview["rows"]))
        self.table.setRowCount(len(self.preview["rows"]))
        for number, row in enumerate(self.preview["rows"]):
            entry = row["entry"]
            values = [entry["techniqueID"], row["name"], entry.get("tactic", "All tactics"),
                      str(entry.get("enabled", True)), str(entry.get("score", "")), entry.get("comment", ""), row["status"]]
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setToolTip(value)
                self.table.setItem(number, column, item)
        self.summary.setText(f"{len(self.preview['selected'])} unique TTPs selected; {self.preview['unresolved']} unresolved rows "
                             "will remain as annotations and will not be selected. Import creates a separate document.")
        self.report("[Navigator Import 3/4] Preview ready; review before importing", 1, 1)
        self.import_button.setEnabled(True)

    def commit(self):
        if not self.catalog or not self.preview or (self.worker and self.worker.isRunning()):
            return
        document = imported_document(self.layers[self.layer.currentIndex()], self.catalog, self.policy.currentData())
        self.imported.emit(document)
        self.report("[Navigator Import 4/4] Imported as a new document", 1, 1)
        self.accept()


class AnnotationDialog(QtWidgets.QDialog):
    def __init__(self, document, key, parent):
        super().__init__(parent)
        self.document, self.key = document, key
        obj = document.catalog.records[key]
        self.setWindowTitle(f"Navigator annotation — {external_id(obj)} {obj['name']}")
        self.resize(590, 430)
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
        layout.addRow("Color", self.color)
        self.include = QtWidgets.QCheckBox("Include this TTP in the document")
        self.include.setChecked(key in document.selected)
        layout.addRow(self.include)
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
        row = next((entry for entry in self.document.navigator_layer.get("techniques", [])
                    if entry["techniqueID"] == external_id(self.document.catalog.records[self.key])
                    and entry.get("tactic", "") == self.scope.currentData()), {})
        self.comment.setPlainText(row.get("comment", ""))
        self.score.setText(str(row["score"]) if "score" in row else "")
        self.color.setText(row.get("color", ""))

    def save(self):
        try:
            score = float(self.score.text()) if self.score.text().strip() else None
            if score is not None and not math.isfinite(score):
                raise ValueError("Score must be a finite number.")
            candidate = copy(self.document)
            update_annotation(candidate, self.key, self.scope.currentData(), self.comment.toPlainText(), score, self.color.text().strip())
        except Exception as error:
            self.error.setText(str(error))
            return
        self.result_layer = candidate.navigator_layer
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
            label = f"{document.name} — {DOMAIN_LABELS[document.catalog.domain]} v{document.catalog.version}"
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
        layout.addWidget(QtWidgets.QLabel(f"Compare downloaded {DOMAIN_LABELS[self.domain]} snapshots. Download other versions using Version first."))
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
