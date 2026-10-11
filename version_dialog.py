"""ATT&CK version picker and background workers. Operation flow: README.md."""
from pathlib import Path
from PySide6 import QtCore, QtWidgets
from attack_versions import cached_discovery, discover_versions, local_versions, prepare_version
from scripts.download_attack_data import write_json


class VersionWorker(QtCore.QThread):
    progress = QtCore.Signal(str, int, int)
    completed = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, root, version=None, discovery=None, parent=None, persist=True):
        super().__init__(parent)
        self.root = Path(root).resolve()
        self.version = version
        self.discovery = discovery
        self.persist = persist

    def report(self, message, current=0, total=0):
        if self.isInterruptionRequested():
            raise InterruptedError("Version operation cancelled")
        print(message + (f" ({current}/{total})" if total else ""), flush=True)
        self.progress.emit(message, current, total)

    def run(self):
        try:
            if self.version is None:
                value = discover_versions(self.root, self.report)
            else:
                catalog, pointer = prepare_version(self.root, self.version, self.discovery, self.report)
                self.report("[Version 4/4 Switch] Catalog validated; preparing interface", 1, 1)
                if self.persist:
                    active = self.root / "active.json"
                    self.report(f"Output file: {active}; temporary: {active.with_name(active.name + '.part')}")
                    write_json(active, pointer)
                value = (catalog, pointer)
            if self.isInterruptionRequested():
                return
            self.completed.emit(value)
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class VersionDialog(QtWidgets.QDialog):
    chosen = QtCore.Signal(object)

    def __init__(self, root, current, parent=None, auto_refresh=True):
        super().__init__(parent)
        self.root = Path(root).resolve()
        self.current = current
        self.worker = None
        self.closing = False
        self.setWindowTitle("MITRE ATT&CK Versions")
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.resize(760, 580)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(f"Current version: v{current or '—'}"))
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search version…")
        layout.addWidget(self.search)
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Version", "Available domains", "Updated (UTC)", "Local status"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 85)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 115)
        layout.addWidget(self.table, 1)
        self.source = QtWidgets.QLabel()
        self.source.setWordWrap(True)
        layout.addWidget(self.source)
        self.status = QtWidgets.QLabel("Ready")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.progress = QtWidgets.QProgressBar()
        layout.addWidget(self.progress)
        buttons = QtWidgets.QHBoxLayout()
        self.refresh_button = QtWidgets.QPushButton("Refresh online")
        self.switch_button = QtWidgets.QPushButton("Switch version")
        self.close_button = QtWidgets.QPushButton("Close")
        buttons.addWidget(self.refresh_button)
        buttons.addStretch()
        buttons.addWidget(self.switch_button)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)
        self.refresh_button.clicked.connect(self.refresh)
        self.switch_button.clicked.connect(self.choose)
        self.close_button.clicked.connect(self.reject)
        self.table.itemSelectionChanged.connect(self.update_switch)
        self.table.cellDoubleClicked.connect(lambda *_: self.choose())
        self.search.textChanged.connect(self.filter_rows)
        self.discovery = cached_discovery(self.root, lambda message, *_: print(message, flush=True))
        self.populate(self.discovery)
        # Opening the picker refreshes the official list; startup stays entirely offline.
        if auto_refresh:
            QtCore.QTimer.singleShot(0, self.refresh)

    def populate(self, discovery):
        self.discovery = discovery
        local = local_versions(self.root)
        rows = list(discovery.get("versions", []))
        known = {row["version"] for row in rows}
        from attack_versions import snapshot_pointer, version_key
        from attack_catalog import DOMAIN_LABELS
        for version in local - known:
            pointer = snapshot_pointer(self.root, version)
            rows.append({"version": version, "domains": {domain: {} for domain in DOMAIN_LABELS
                         if domain.split("-")[0] + "_bundle" in pointer}})
        rows.sort(key=lambda row: version_key(row["version"]), reverse=True)
        self.table.setRowCount(len(rows))
        current_row = 0
        for number, row in enumerate(rows):
            version = row["version"]
            values = ["v" + version, ", ".join(DOMAIN_LABELS[domain] for domain in DOMAIN_LABELS if domain in row["domains"]),
                      row["domains"].get("enterprise-attack", {}).get("modified", "")[:10],
                      "Current" if version == self.current else "Downloaded" if version in local else "Download"]
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setData(QtCore.Qt.ItemDataRole.UserRole, version)
                self.table.setItem(number, column, item)
            if version == self.current:
                current_row = number
        self.source.setText(f"{len(rows)} versions · " + discovery.get("source", ""))
        if rows:
            self.table.selectRow(current_row)
        self.filter_rows()
        self.update_switch()

    def filter_rows(self):
        query = self.search.text().strip().casefold()
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, query not in self.table.item(row, 0).text().casefold())
        self.update_switch()

    def update_switch(self):
        row = self.table.currentRow()
        busy = self.worker is not None and self.worker.isRunning()
        self.switch_button.setEnabled(not busy and row >= 0 and not self.table.isRowHidden(row)
                                      and self.table.item(row, 0).data(QtCore.Qt.ItemDataRole.UserRole) != self.current)

    def report(self, message, current=0, total=0):
        self.status.setText(message)
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        if self.parent():
            self.parent().report(message, current, total)

    def start_worker(self, version=None):
        if self.worker and self.worker.isRunning():
            return
        if self.worker:
            self.worker.deleteLater()
        self.worker = VersionWorker(self.root, version, self.discovery, self)
        self.worker.progress.connect(self.report)
        self.worker.completed.connect(self.populate if version is None else self.switched)
        self.worker.failed.connect(lambda error: self.report(f"Failed: {error}", 1, 1))
        self.worker.finished.connect(self.finished_work)
        self.refresh_button.setEnabled(False)
        self.switch_button.setEnabled(False)
        self.worker.start()

    def refresh(self):
        self.start_worker()

    def choose(self):
        if not self.switch_button.isEnabled():
            return
        version = self.table.item(self.table.currentRow(), 0).data(QtCore.Qt.ItemDataRole.UserRole)
        self.start_worker(version)

    def switched(self, value):
        if not self.closing:
            self.chosen.emit(value)
            self.accept()

    def finished_work(self):
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        if not self.closing and not self.status.text().startswith("Failed:"):
            self.report("Ready · select a version and click Switch version", 1, 1)
        self.refresh_button.setEnabled(True)
        self.update_switch()
        if self.closing:
            super().reject()

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.closing = True
            self.worker.requestInterruption()
            self.report("Cancelling; waiting for the active request to finish…", 0, 0)
            return
        super().reject()
