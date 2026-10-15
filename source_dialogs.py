"""Source previews and reviewed layer migration. Operation flow: README.md."""
from pathlib import Path
from PySide6 import QtCore, QtWidgets
from attack_catalog import DOMAIN_LABELS, external_id, tactic_phases, catalog_identity
from attack_versions import cached_discovery, local_versions, prepare_version
from custom_sources import load_custom, load_layer_url
from layer_analysis import snapshot_document
from layer_upgrade import upgrade_preview, migrate_layer
from navigator_dialogs import IntegrationDialog


class SourceDialog(IntegrationDialog):
    imported = QtCore.Signal(object)
    layer_ready = QtCore.Signal(object)

    def __init__(self, root, version, parent):
        super().__init__(parent)
        self.root, self.result = root, None
        self.setWindowTitle('Load Navigator URL or custom ATT&CK STIX')
        self.resize(760, 520)
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.kind = QtWidgets.QComboBox()
        self.kind.addItems(['Navigator Layer URL', 'Custom STIX Bundle / Collection'])
        form.addRow('Source type', self.kind)
        self.location = QtWidgets.QLineEdit()
        self.location.setPlaceholderText('https://… or an absolute local STIX JSON path')
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.location)
        browse = QtWidgets.QPushButton('Browse…')
        browse.clicked.connect(self.browse)
        row.addWidget(browse)
        form.addRow('Input location', row)
        self.version = QtWidgets.QLineEdit(version)
        form.addRow('Fallback release version', self.version)
        layout.addLayout(form)
        self.load_button = QtWidgets.QPushButton('Load and validate preview')
        self.load_button.clicked.connect(self.load)
        layout.addWidget(self.load_button)
        self.collection = QtWidgets.QComboBox()
        self.collection.hide()
        layout.addWidget(self.collection)
        self.domain = QtWidgets.QComboBox()
        layout.addWidget(self.domain)
        self.preview = QtWidgets.QPlainTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        self.commit_button = QtWidgets.QPushButton('Open as a new document')
        self.commit_button.setEnabled(False)
        self.commit_button.clicked.connect(self.commit)
        layout.addWidget(self.commit_button)
        self.kind.currentIndexChanged.connect(self.invalidate)
        self.location.textChanged.connect(self.invalidate)
        self.version.textChanged.connect(self.invalidate)
        self.domain.currentIndexChanged.connect(self.update_preview)
        self.collection.currentIndexChanged.connect(self.choose_collection)

    def browse(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Custom STIX Bundle / Collection Index', str(Path.home()), 'JSON (*.json)')
        if path:
            self.kind.setCurrentIndex(1)
            self.location.setText(str(Path(path).resolve()))

    def invalidate(self, *_):
        self.result = None
        self.commit_button.setEnabled(False)
        self.preview.clear()
        self.domain.clear()

    def load(self):
        if self.worker and self.worker.isRunning():
            return
        location, version, kind = self.location.text().strip(), self.version.text().strip(), self.kind.currentIndex()
        if not location:
            self.report('Enter a URL or custom STIX file path.', 1, 1)
            return
        self.invalidate()
        for widget in (self.location, self.version, self.kind, self.load_button, self.collection):
            widget.setEnabled(False)
        self.report(f'Output cache directory: {(Path(self.root).resolve() / "custom")}', 0, 0)
        self.start_task(lambda notify: load_layer_url(self.root, location, notify) if kind == 0 else
                        load_custom(self.root, location, version, notify), self.loaded)

    def loaded(self, result):
        if 'entries' in result:
            self.collection.blockSignals(True)
            self.collection.clear()
            for entry in result['entries']:
                self.collection.addItem(entry['name'] + ' · v' + entry['version'], entry)
            self.collection.setCurrentIndex(-1)
            self.collection.blockSignals(False)
            self.collection.show()
            self.preview.setPlainText('Collection Index loaded. Choose a version, then press Load to fetch its Bundle. No collection URLs were loaded automatically.')
            return
        self.result = result
        self.collection.hide()
        self.domain.clear()
        if 'catalog' in result:
            catalog = result['catalog']
            for domain in DOMAIN_LABELS:
                if any(obj.get('type') == 'attack-pattern' for obj in catalog.objects_by_domain[domain].values()):
                    self.domain.addItem(DOMAIN_LABELS[domain], domain)
            self.update_preview()
        else:
            self.preview.setPlainText(f'Validated Navigator JSON\nCache file: {result["path"]}\nNext: choose layer, snapshot and selection policy in the import preview.')

    def update_preview(self, *_):
        if self.result and 'catalog' in self.result and self.domain.currentData():
            catalog = self.result['catalog'].for_domain(self.domain.currentData())
            self.preview.setPlainText(f'Custom dataset SHA-256: {catalog.dataset_id}\nSource: {catalog.custom_source}\nCache file: {self.result["path"]}\n'
                                      f'{DOMAIN_LABELS[catalog.domain]} v{catalog.version}\n{len(catalog.records)} techniques · {len(catalog.tactics)} tactics · {len(catalog.groups)} platforms\n'
                                      'This dataset is isolated from official snapshots and other custom datasets.')

    def choose_collection(self, *_):
        entry = self.collection.currentData()
        if entry:
            self.location.setText(entry['url'])
            self.version.setText(entry['version'])

    def task_finished(self):
        super().task_finished()
        for widget in (self.location, self.version, self.kind, self.load_button, self.collection):
            widget.setEnabled(True)
        self.commit_button.setEnabled(self.result is not None)

    def commit(self):
        if not self.result or (self.worker and self.worker.isRunning()):
            return
        result = self.result
        self.accept()
        if 'catalog' in result:
            from ttp_documents import TTPDocument
            catalog = result['catalog'].for_domain(self.domain.currentData())
            self.imported.emit(TTPDocument('Custom-' + DOMAIN_LABELS[catalog.domain], catalog))
        else:
            self.layer_ready.emit(result['path'])


class UpgradeDialog(IntegrationDialog):
    imported = QtCore.Signal(object)

    def __init__(self, root, document, documents, parent):
        super().__init__(parent)
        self.root, self.document = root, snapshot_document(document)
        self.discovery = cached_discovery(root, parent.operation_report)
        self.target_catalog = None
        self.preview_data = None
        self.controls = []
        self.result_document = None
        self.setWindowTitle('Review and migrate layer annotations')
        self.resize(1100, 720)
        layout = QtWidgets.QVBoxLayout(self)
        self.name = QtWidgets.QLineEdit(document.name[:100] + '-upgraded')
        layout.addWidget(self.name)
        row = QtWidgets.QHBoxLayout()
        self.target = QtWidgets.QComboBox()
        for version in sorted(local_versions(root), key=lambda v: tuple(map(int, v.split('.'))), reverse=True):
            self.target.addItem('Official ATT&CK v' + version, ('official', version))
        seen = set()
        for doc in documents:
            if doc.catalog.domain == document.catalog.domain and doc.catalog.dataset_id and catalog_identity(doc.catalog) not in seen:
                seen.add(catalog_identity(doc.catalog))
                self.target.addItem('Custom: ' + doc.name + ' · v' + doc.catalog.version, ('custom', doc.catalog))
        row.addWidget(self.target, 1)
        self.load_button = QtWidgets.QPushButton('Load target and compare')
        self.load_button.clicked.connect(self.load_target)
        row.addWidget(self.load_button)
        layout.addLayout(row)
        self.summary = QtWidgets.QLabel('Choose a cached official release or an open custom dataset in the same domain. Load other official releases from Version first.')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.pending_only = QtWidgets.QCheckBox('Show only rows requiring review')
        self.pending_only.toggled.connect(self.filter_rows)
        layout.addWidget(self.pending_only)
        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(['Source / scope', 'Change', 'Action', 'Target technique', 'Target tactic', 'Reviewed'])
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        self.change_details = QtWidgets.QPlainTextEdit()
        self.change_details.setReadOnly(True)
        self.change_details.setPlaceholderText('Select a source row to inspect field changes and its original annotation.')
        self.change_details.setMaximumHeight(150)
        self.table.currentCellChanged.connect(self.show_changes)
        layout.addWidget(self.change_details)
        review = QtWidgets.QPushButton('Mark visible decisions reviewed')
        review.clicked.connect(self.mark_reviewed)
        layout.addWidget(review)
        self.added = QtWidgets.QPlainTextEdit()
        self.added.setReadOnly(True)
        self.added.setMaximumHeight(85)
        layout.addWidget(self.added)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        self.create_button = QtWidgets.QPushButton('Create migrated layer')
        self.create_button.setEnabled(False)
        self.create_button.clicked.connect(self.create)
        layout.addWidget(self.create_button)
        self.target.currentIndexChanged.connect(self.invalidate)

    def invalidate(self, *_):
        self.target_catalog, self.preview_data = None, None
        self.table.setRowCount(0)
        self.change_details.clear()
        self.controls = []
        self.create_button.setEnabled(False)

    def load_target(self):
        if self.worker and self.worker.isRunning() or self.target.currentData() is None:
            return
        kind, value = self.target.currentData()
        self.invalidate()
        self.target.setEnabled(False)
        self.load_button.setEnabled(False)
        def task(notify):
            catalog = prepare_version(self.root, value, self.discovery, notify)[0] if kind == 'official' else value
            catalog = catalog.for_domain(self.document.catalog.domain)
            return catalog, upgrade_preview(self.document, catalog, notify)
        self.start_task(task, self.loaded)

    def loaded(self, result):
        self.target_catalog, self.preview_data = result
        catalog, preview = result
        self.table.setRowCount(len(preview['rows']))
        # A shared model avoids hundreds of repeated complete technique catalogs.
        from PySide6 import QtGui
        self.technique_model = QtGui.QStandardItemModel(self)
        ids = sorted(catalog.records, key=lambda key: external_id(catalog.records[key]))
        for key in ids:
            record = catalog.records[key]
            item = QtGui.QStandardItem(external_id(record) + '  ' + record['name'])
            item.setData(external_id(record), QtCore.Qt.ItemDataRole.UserRole)
            self.technique_model.appendRow(item)
        for index, entry in enumerate(preview['rows']):
            source = QtWidgets.QTableWidgetItem(entry['source_id'] + ' / ' + (entry['source_scope'] or 'All tactics'))
            import json
            source.setToolTip(json.dumps(entry['annotation'], ensure_ascii=False, indent=2))
            source.setFlags(source.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(index, 0, source)
            status = QtWidgets.QTableWidgetItem(entry['status'])
            status.setToolTip('Changed fields: ' + ', '.join(change['field'] for change in entry['changes']))
            status.setFlags(status.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(index, 1, status)
            action = QtWidgets.QComboBox()
            action.addItems(['Choose', 'Copy', 'Drop'])
            action.setCurrentText(entry['action'])
            technique = QtWidgets.QComboBox()
            technique.setModel(self.technique_model)
            technique.setEditable(True)
            technique.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
            technique.completer().setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
            technique.completer().setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
            technique.setCurrentIndex(technique.findData(entry['target_id']))
            scope = QtWidgets.QComboBox()
            reviewed = QtWidgets.QCheckBox()
            reviewed.setChecked(entry['reviewed'])
            for column, widget in enumerate((action, technique, scope, reviewed), 2):
                self.table.setCellWidget(index, column, widget)
            control = {'action': action, 'technique': technique, 'scope': scope, 'reviewed': reviewed}
            self.controls.append(control)
            self.populate_scopes(control, entry['target_scope'])
            technique.currentIndexChanged.connect(lambda number, c=control: self.target_changed(c))
            technique.editTextChanged.connect(lambda text, c=control: c['reviewed'].setChecked(False))
            scope.currentIndexChanged.connect(lambda number, check=reviewed: check.setChecked(False))
            action.currentIndexChanged.connect(lambda number, check=reviewed: check.setChecked(False))
            reviewed.toggled.connect(self.filter_rows)
        self.summary.setText(f"{len(preview['rows'])} source annotation rows · {len(preview['added'])} added target techniques. Hover the source ID for the full annotation. Confirm changed mappings or explicitly Drop rows. The original layer stays open.")
        self.added.setPlainText('Added target IDs (available in the new matrix; not automatically selected):\n' + ', '.join(preview['added']))
        self.filter_rows()
        if preview['rows']:
            self.table.setCurrentCell(0, 0)

    def show_changes(self, row, *_):
        if not self.preview_data or row < 0 or row >= len(self.preview_data['rows']):
            return
        import json
        entry = self.preview_data['rows'][row]
        self.change_details.setPlainText(json.dumps({'source': entry['source_id'], 'scope': entry['source_scope'],
            'status': entry['status'], 'suggested_target': entry['target_id'], 'field_changes': entry['changes'],
            'original_annotation': entry['annotation']}, ensure_ascii=False, indent=2))

    def technique_id(self, control):
        combo = control['technique']
        index = combo.findText(combo.currentText(), QtCore.Qt.MatchFlag.MatchExactly)
        return combo.itemData(index) if index >= 0 else None

    def populate_scopes(self, control, preferred):
        combo = control['scope']
        combo.blockSignals(True)
        combo.clear()
        combo.addItem('Choose tactic…', None)
        combo.addItem('All tactics', '')
        identity = self.technique_id(control)
        record = next((o for o in self.target_catalog.records.values() if external_id(o) == identity), None)
        if record:
            phases = tactic_phases(record, self.target_catalog.domain)
            for slug in self.target_catalog.tactic_order:
                if slug in phases:
                    combo.addItem(self.target_catalog.tactics[slug]['name'], slug)
        combo.setCurrentIndex(combo.findData(preferred) if preferred is not None else 0)
        if combo.currentIndex() < 0:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def target_changed(self, control):
        preferred = control['scope'].currentData()
        self.populate_scopes(control, preferred)
        control['reviewed'].setChecked(False)

    def filter_rows(self, *_):
        for index, control in enumerate(self.controls):
            self.table.setRowHidden(index, self.pending_only.isChecked() and control['reviewed'].isChecked())

    def mark_reviewed(self):
        for index, control in enumerate(self.controls):
            if not self.table.isRowHidden(index):
                control['reviewed'].setChecked(True)
        self.filter_rows()

    def task_finished(self):
        super().task_finished()
        self.target.setEnabled(True)
        self.load_button.setEnabled(True)
        self.table.setEnabled(True)
        self.create_button.setEnabled(self.preview_data is not None)

    def create(self):
        if not self.preview_data or self.worker and self.worker.isRunning():
            return
        decisions = [{'action': c['action'].currentText(), 'target_id': self.technique_id(c),
                      'target_scope': c['scope'].currentData(), 'reviewed': c['reviewed'].isChecked()} for c in self.controls]
        name = self.name.text()
        target = self.target_catalog
        self.create_button.setEnabled(False)
        self.table.setEnabled(False)
        self.target.setEnabled(False)
        self.load_button.setEnabled(False)
        self.start_task(lambda notify: migrate_layer(self.document, target, decisions, name, notify), self.created)

    def created(self, document):
        # Finish closing only after QThread has terminated.
        self.result_document = document
        QtCore.QTimer.singleShot(0, self.install_result)

    def install_result(self):
        if self.closing or self.result_document is None:
            return
        if self.worker and self.worker.isRunning():
            QtCore.QTimer.singleShot(25, self.install_result)
            return
        self.accept()
        self.imported.emit(self.result_document)
