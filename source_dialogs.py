"""Source previews and reviewed layer migration. Operation flow: README.md."""
from pathlib import Path
from PySide6 import QtCore, QtWidgets
from attack_catalog import DOMAIN_LABELS, external_id, tactic_phases, catalog_identity, domain_label
from attack_versions import cached_discovery, local_versions, prepare_version
from custom_sources import load_custom, load_layer_url
from layer_analysis import snapshot_document
from layer_upgrade import upgrade_preview, migrate_layer, migration_plan
from navigator_dialogs import IntegrationDialog


class SourceDialog(IntegrationDialog):
    imported = QtCore.Signal(object)
    layer_ready = QtCore.Signal(object)

    def __init__(self, root, version, parent):
        super().__init__(parent)
        self.root, self.result = root, None
        self.layer_origin = ''
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
            for domain in catalog.domain_labels:
                if any(obj.get('type') == 'attack-pattern' for obj in catalog.objects_by_domain[domain].values()):
                    self.domain.addItem(domain_label(domain, catalog), domain)
            self.update_preview()
        else:
            self.preview.setPlainText(f'Validated Navigator JSON\nCache file: {result["path"]}\nNext: choose layer, snapshot and selection policy in the import preview.')

    def update_preview(self, *_):
        if self.result and 'catalog' in self.result and self.domain.currentData():
            catalog = self.result['catalog'].for_domain(self.domain.currentData())
            self.preview.setPlainText(f'Custom dataset SHA-256: {catalog.dataset_id}\nSource: {catalog.custom_source}\nCache file: {self.result["path"]}\n'
                                      f'{domain_label(catalog.domain, catalog)} v{catalog.version}\n{len(catalog.records)} techniques · {len(catalog.tactics)} tactics · {len(catalog.groups)} platforms\n'
                                      f"Matrices: {', '.join(obj['name'] for obj in catalog.matrices_by_domain.get(catalog.domain, []))}\n"
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
            self.imported.emit(TTPDocument('Custom-' + DOMAIN_LABELS.get(catalog.domain, catalog.domain), catalog))
        else:
            self.layer_origin = result.get('origin', '')
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
        self.annotation_edits = {}
        self.mapping_targets = {}
        self.conflict_resolutions = []
        self.conflict_preview_pending = False
        self.conflict_plan_received = False
        self.skip_reasons = {}
        self.summary_preview_pending = False
        self.summary_plan_received = False
        self.result_document = None
        self.setWindowTitle('Review and migrate layer annotations')
        self.resize(1400, 1000)
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
        for column, width in ((0, 200), (1, 190), (4, 210), (5, 90)):
            self.table.setColumnWidth(column, width)
        from upgrade_review_dialog import UpgradeReviewPanel
        self.review_panel = UpgradeReviewPanel(self)
        self.review_tabs = QtWidgets.QTabWidget()
        self.review_tabs.addTab(self.review_panel, 'Technique review')
        self.review_tabs.addTab(self.table, 'Annotation mappings')
        self.review_panel.changed.connect(self.filter_mapping_rows)
        self.review_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.review_splitter.addWidget(self.review_tabs)
        layout.addWidget(self.review_splitter, 1)
        self.change_details = QtWidgets.QPlainTextEdit()
        self.change_details.setReadOnly(True)
        self.change_details.setPlaceholderText('Select a source row to inspect field changes and its original annotation.')
        self.table.currentCellChanged.connect(self.show_changes)
        from upgrade_comparison import UpgradeComparison
        self.comparison = UpgradeComparison(self)
        self.content_tabs = QtWidgets.QTabWidget()
        self.content_tabs.addTab(self.comparison, 'Content comparison')
        self.content_tabs.addTab(self.change_details, 'Raw differences')
        self.review_splitter.addWidget(self.content_tabs)
        self.review_splitter.setSizes([350, 500])
        self.review_tabs.currentChanged.connect(self.refresh_comparison)
        review = QtWidgets.QPushButton('Mark visible decisions reviewed')
        self.review_button = review
        review.clicked.connect(self.mark_reviewed)
        layout.addWidget(review)
        mapping_bar = QtWidgets.QHBoxLayout()
        self.targets_button = QtWidgets.QPushButton('Edit mapping targets…')
        self.targets_button.setToolTip('Select a source row in Annotation mappings before editing destinations.')
        self.targets_button.setEnabled(False)
        self.targets_button.clicked.connect(self.edit_mapping_targets)
        self.conflicts_button = QtWidgets.QPushButton('Review migration conflicts…')
        self.conflicts_button.clicked.connect(self.review_conflicts)
        mapping_bar.addWidget(self.targets_button)
        mapping_bar.addWidget(self.conflicts_button)
        layout.addLayout(mapping_bar)
        self.conflict_note = QtWidgets.QLabel('Conflict resolutions are validated again before creation.')
        self.conflict_note.setWordWrap(True)
        layout.addWidget(self.conflict_note)
        self.added = QtWidgets.QPlainTextEdit()
        self.added.setReadOnly(True)
        self.added.setMaximumHeight(85)
        self.added.hide()
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        self.create_button = QtWidgets.QPushButton('Review final summary…')
        self.create_button.setEnabled(False)
        self.create_button.clicked.connect(self.open_summary)
        layout.addWidget(self.create_button)
        self.target.currentIndexChanged.connect(self.invalidate)

    def invalidate(self, *_):
        self.target_catalog, self.preview_data = None, None
        self.table.setRowCount(0)
        self.change_details.clear()
        self.controls = []
        self.annotation_edits = {}
        self.mapping_targets = {}
        self.conflict_resolutions = []
        self.conflict_preview_pending = False
        self.conflict_plan_received = False
        self.skip_reasons = {}
        self.summary_preview_pending = False
        self.summary_plan_received = False
        self.review_panel.clear()
        self.comparison.clear()
        self.added.clear()
        self.conflict_note.setText('Conflict resolutions are validated again before creation.')
        self.targets_button.setEnabled(False)
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
        if self.closing:
            return
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
            technique.editTextChanged.connect(lambda text, c=control: self.mapping_changed(c))
            scope.currentIndexChanged.connect(lambda number, c=control: self.mapping_changed(c))
            action.currentIndexChanged.connect(lambda number, c=control: self.mapping_changed(c, keep_targets=True))
            reviewed.toggled.connect(lambda checked, c=control: self.mapping_review_changed(c, checked))
        self.summary.setText(f"{len(preview['rows'])} source annotation rows · {len(preview['added'])} added target techniques. Hover the source ID for the full annotation. Confirm changed mappings or explicitly Drop rows. The original layer stays open.")
        self.added.setPlainText('Added target IDs (available in the new matrix; not automatically selected):\n' + ', '.join(preview['added']))
        self.review_panel.load(preview)
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
        self.comparison.show_row(row)
        self.update_mapping_button()

    def update_mapping_button(self):
        busy = self.conflict_preview_pending or self.summary_preview_pending or bool(self.worker and self.worker.isRunning())
        self.targets_button.setEnabled(bool(self.preview_data) and self.review_tabs.currentIndex() == 1
                                       and self.table.currentRow() >= 0 and not busy and not self.closing)

    def refresh_comparison(self, *_):
        self.update_mapping_button()
        if not self.preview_data:
            return
        if self.review_tabs.currentIndex() == 1:
            self.show_changes(self.table.currentRow())
        else:
            row = self.review_panel.table.currentRow()
            if 0 <= row < len(self.review_panel.items):
                self.comparison.show_item(self.review_panel.items[row]['id'])

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
        self.mapping_changed(control)

    def mapping_changed(self, control, *, keep_targets=False):
        index = self.controls.index(control)
        if not keep_targets:
            old_targets = self.mapping_targets.pop(index, None)
            if old_targets and len(old_targets) == 1 and old_targets[0].get('annotation_patch'):
                self.annotation_edits[index] = {**self.annotation_edits.get(index, {}), **old_targets[0]['annotation_patch']}
            control['technique'].setEnabled(True)
            control['scope'].setEnabled(True)
        status = self.preview_data['rows'][index]['status']
        count = len(self.mapping_targets.get(index, []))
        self.table.item(index, 1).setText(status + (' · ' + str(count) + ' destinations' if count > 1 else ''))
        self.invalidate_conflicts()
        control['reviewed'].setChecked(False)
        self.review_panel.unreview(self.preview_data['rows'][index]['source_id'])
        self.comparison.refresh()

    def invalidate_conflicts(self):
        self.conflict_resolutions = []
        self.conflict_note.setText('Mapping or annotation changed. Review current conflicts again.')

    def capture_decisions(self):
        from copy import deepcopy
        decisions = [{'action': c['action'].currentText(), 'target_id': self.technique_id(c),
                      'target_scope': c['scope'].currentData(), 'reviewed': c['reviewed'].isChecked()} for c in self.controls]
        for index, patch in self.annotation_edits.items():
            decisions[index]['annotation_patch'] = deepcopy(patch)
        for index, targets in self.mapping_targets.items():
            decisions[index]['targets'] = deepcopy(targets)
        return decisions

    def edit_mapping_targets(self):
        from copy import deepcopy
        from upgrade_mapping_dialogs import MappingTargetsDialog
        index = self.table.currentRow()
        if not self.preview_data or index < 0 or self.conflict_preview_pending or self.summary_preview_pending or self.worker and self.worker.isRunning():
            return
        control = self.controls[index]
        targets = deepcopy(self.mapping_targets.get(index, [{'target_id': self.technique_id(control),
                                                          'target_scope': control['scope'].currentData()}]))
        self.report('Input files: None; output files: None (mapping destination draft in memory)', 0, 0)
        self.report('[Upgrade targets 1/2] Preparing explicit destination list', 0, 2)
        dialog = MappingTargetsDialog(self, targets)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            self.report('[Upgrade targets 2/2] Cancelled; previous destinations preserved', 2, 2)
            return
        targets = dialog.result_targets
        with QtCore.QSignalBlocker(control['technique']):
            control['technique'].setCurrentIndex(control['technique'].findData(targets[0]['target_id']))
        self.populate_scopes(control, targets[0]['target_scope'])
        with QtCore.QSignalBlocker(control['action']):
            control['action'].setCurrentText('Copy')
        self.mapping_targets[index] = deepcopy(targets)
        control['technique'].setEnabled(len(targets) == 1)
        control['scope'].setEnabled(len(targets) == 1)
        control['scope'].setToolTip('\n'.join(t['target_id'] + ' / ' + (t['target_scope'] or 'All tactics') for t in targets))
        self.mapping_changed(control, keep_targets=True)
        self.review_tabs.setCurrentIndex(1)
        self.comparison.show_row(index)
        self.report('[Upgrade targets 2/2] Destinations saved; review this source again', 2, 2)

    def review_conflicts(self, focus=None):
        if not self.preview_data or self.conflict_preview_pending or self.summary_preview_pending or self.worker and self.worker.isRunning():
            return
        from copy import deepcopy
        self.conflict_focus = deepcopy(focus) if isinstance(focus, dict) else None
        decisions, reviews, target = self.capture_decisions(), self.review_panel.decisions(), self.target_catalog
        self.conflict_preview_pending = True
        self.conflict_plan_received = False
        self.set_review_enabled(False)
        self.start_task(lambda notify: migration_plan(self.document, target, decisions, notify, reviews=reviews,
                                                     require_review=False), self.conflicts_ready)

    def conflicts_ready(self, plan):
        self.conflict_plan_received = True
        if self.closing:
            return
        if self.worker and self.worker.isRunning():
            QtCore.QTimer.singleShot(25, lambda: self.conflicts_ready(plan))
            return
        self.conflict_preview_pending = False
        self.set_review_enabled(True)
        from copy import deepcopy
        from upgrade_mapping_dialogs import ConflictResolutionDialog
        if not plan['conflicts']:
            self.conflict_resolutions = []
            self.conflict_note.setText('No conflicting fields in the current migration plan.')
            return
        self.report('Input files: None; output files: None (field conflict decisions in memory)', 0, 0)
        dialog = ConflictResolutionDialog(self, plan)
        if self.conflict_focus:
            index = next((i for i, conflict in enumerate(plan['conflicts']) if all(
                conflict[key] == self.conflict_focus.get(key) for key in ('target_id', 'target_scope', 'field'))), 0)
            dialog.table.setCurrentCell(index, 0)
            dialog.table.scrollToItem(dialog.table.item(index, 0))
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.conflict_resolutions = deepcopy(dialog.result_resolutions)
            self.conflict_note.setText('Current field conflicts resolved. All source and technique reviews are still required.')

    def mapping_review_changed(self, control, checked):
        if not checked:
            index = self.controls.index(control)
            self.review_panel.unreview(self.preview_data['rows'][index]['source_id'])
        self.filter_rows()

    def filter_rows(self, *_):
        self.review_panel.filter_rows()

    def filter_mapping_rows(self):
        allowed = {item['id'] for item in self.review_panel.items if self.review_panel.matches(item)}
        for index, control in enumerate(self.controls):
            self.table.setRowHidden(index, self.preview_data['rows'][index]['source_id'] not in allowed or
                                   (self.pending_only.isChecked() and control['reviewed'].isChecked()))

    def mark_reviewed(self):
        self.review_panel.mark_visible()
        self.filter_rows()

    def task_finished(self):
        if self.conflict_preview_pending and not self.conflict_plan_received:
            self.conflict_preview_pending = False
        if self.summary_preview_pending and not self.summary_plan_received:
            self.summary_preview_pending = False
        super().task_finished()
        self.set_review_enabled(not self.closing and not self.conflict_preview_pending and not self.summary_preview_pending)

    def set_review_enabled(self, enabled):
        for widget in (self.target, self.load_button, self.table, self.review_panel, self.pending_only,
                       self.name, self.comparison, self.review_button, self.targets_button, self.conflicts_button):
            widget.setEnabled(enabled)
        self.create_button.setEnabled(enabled and self.preview_data is not None)
        if enabled:
            self.update_mapping_button()

    def current_summary_token(self):
        from upgrade_summary import summary_token
        return summary_token(self.document, self.target_catalog, self.capture_decisions(), self.review_panel.decisions(),
                             self.conflict_resolutions, self.name.text())

    def open_summary(self):
        if not self.preview_data or self.closing or self.conflict_preview_pending or self.summary_preview_pending or self.worker and self.worker.isRunning():
            return
        from copy import deepcopy
        from upgrade_summary import build_summary
        decisions, reviews = self.capture_decisions(), self.review_panel.decisions()
        target, name = self.target_catalog, self.name.text()
        resolutions, reasons = deepcopy(self.conflict_resolutions), deepcopy(self.skip_reasons)
        self.summary_preview_pending, self.summary_plan_received = True, False
        self.set_review_enabled(False)
        self.start_task(lambda notify: build_summary(self.document, target, decisions, name, notify,
                        reviews=reviews, resolutions=resolutions, skip_reasons=reasons), self.summary_ready)

    def summary_ready(self, report):
        self.summary_plan_received = True
        if self.closing:
            return
        if self.worker and self.worker.isRunning():
            QtCore.QTimer.singleShot(25, lambda: self.summary_ready(report))
            return
        self.summary_preview_pending = False
        self.set_review_enabled(True)
        from upgrade_summary_dialog import UpgradeSummaryDialog
        from copy import deepcopy
        if report['input_token'] != self.current_summary_token():
            self.report('Upgrade inputs changed. Review the final summary again.', 0, 0)
            return
        dialog = UpgradeSummaryDialog(self, report)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted or self.closing:
            return
        if report['input_token'] != self.current_summary_token():
            self.report('Upgrade inputs changed. Review the final summary again.', 0, 0)
            return
        self.skip_reasons = deepcopy(dialog.reason_edits)
        if dialog.result_action == 'submit':
            self.create()
        elif dialog.navigation:
            self.return_to_unfinished(dialog.navigation)

    def return_to_unfinished(self, issue):
        self.pending_only.setChecked(False)
        self.review_panel.category.setCurrentIndex(0)
        self.review_panel.annotated_only.setChecked(False)
        self.filter_rows()
        if issue['kind'] == 'name':
            self.name.setFocus()
            self.name.selectAll()
        elif issue['kind'] == 'conflict':
            self.review_conflicts(issue)
        elif issue['kind'] == 'mapping':
            self.review_tabs.setCurrentIndex(1)
            row = issue.get('source_index', 0)
            if 0 <= row < self.table.rowCount():
                self.table.setCurrentCell(row, 0)
                self.table.scrollToItem(self.table.item(row, 0))
        else:
            self.review_tabs.setCurrentIndex(0)
            row = next((i for i, item in enumerate(self.review_panel.items) if item['id'] == issue.get('identity')), 0)
            if row < self.review_panel.table.rowCount():
                self.review_panel.table.setCurrentCell(row, 0)
                self.review_panel.table.scrollToItem(self.review_panel.table.item(row, 0))
        self.report('Returned to an unfinished upgrade item; source data is unchanged.', 1, 1)

    def create(self):
        if not self.preview_data or self.closing or self.conflict_preview_pending or self.summary_preview_pending or self.worker and self.worker.isRunning():
            return
        decisions = self.capture_decisions()
        name = self.name.text()
        target = self.target_catalog
        reviews = self.review_panel.decisions()
        from copy import deepcopy
        resolutions = deepcopy(self.conflict_resolutions)
        reasons = deepcopy(self.skip_reasons)
        self.set_review_enabled(False)
        self.start_task(lambda notify: migrate_layer(self.document, target, decisions, name, notify, reviews=reviews,
                                                    resolutions=resolutions, skip_reasons=reasons), self.created)

    def created(self, document):
        # Finish closing only after QThread has terminated.
        if self.closing:
            return
        self.result_document = document
        QtCore.QTimer.singleShot(0, self.install_result)

    def reject(self):
        # A close after worker completion must also cancel a queued installation.
        self.closing = True
        super().reject()

    def install_result(self):
        if self.closing or self.result_document is None:
            return
        if self.worker and self.worker.isRunning():
            QtCore.QTimer.singleShot(25, self.install_result)
            return
        self.accept()
        self.imported.emit(self.result_document)
