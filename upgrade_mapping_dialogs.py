"""Atomic destination-list and field conflict editors. Workflow: README.md."""
from copy import deepcopy
import json
from PySide6 import QtCore, QtWidgets
from attack_catalog import external_id, tactic_phases
from upgrade_mapping import decision_targets, resolved_layer, canonical


class MappingTargetsDialog(QtWidgets.QDialog):
    def __init__(self, owner, targets):
        super().__init__(owner)
        self.owner, self.controls, self.result_targets = owner, [], None
        self.setWindowTitle('Edit mapping targets')
        self.resize(960, 560)
        layout = QtWidgets.QVBoxLayout(self)
        hint = QtWidgets.QLabel('Add explicit technique/tactic destinations. All tactics cannot overlap individual tactics for the same technique.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QtWidgets.QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['Target technique', 'Target tactic'])
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1, 260)
        layout.addWidget(self.table, 1)
        bar = QtWidgets.QHBoxLayout()
        self.add_button = QtWidgets.QPushButton('Add destination')
        self.remove_button = QtWidgets.QPushButton('Remove destination')
        self.add_button.clicked.connect(lambda: self.add_target({}))
        self.remove_button.clicked.connect(self.remove_target)
        bar.addWidget(self.add_button)
        bar.addWidget(self.remove_button)
        layout.addLayout(bar)
        self.error = QtWidgets.QLabel()
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for target in targets:
            self.add_target(target)

    def add_target(self, target):
        if len(self.controls) >= 100:
            self.error.setText('A source row supports at most 100 destinations.')
            return
        index = self.table.rowCount()
        self.table.insertRow(index)
        technique = QtWidgets.QComboBox()
        technique.setModel(self.owner.technique_model)
        technique.setEditable(True)
        technique.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        technique.completer().setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        technique.completer().setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        technique.setCurrentIndex(technique.findData(target.get('target_id')))
        scope = QtWidgets.QComboBox()
        control = {'technique': technique, 'scope': scope, 'patch': deepcopy(target.get('annotation_patch', {}))}
        self.controls.append(control)
        self.table.setCellWidget(index, 0, technique)
        self.table.setCellWidget(index, 1, scope)
        self.populate(control, target.get('target_scope'))
        technique.currentIndexChanged.connect(lambda *_: self.populate(control, control['scope'].currentData()))
        technique.editTextChanged.connect(lambda *_: self.populate(control, control['scope'].currentData()))

    def populate(self, control, preferred):
        combo = control['scope']
        combo.blockSignals(True)
        combo.clear()
        combo.addItem('Choose tactic…', None)
        combo.addItem('All tactics', '')
        identity = self.owner.technique_id(control)
        record = next((o for o in self.owner.target_catalog.records.values() if external_id(o) == identity), {})
        phases = tactic_phases(record, self.owner.target_catalog.domain)
        for slug in self.owner.target_catalog.tactic_order:
            if slug in phases:
                combo.addItem(self.owner.target_catalog.tactics[slug]['name'], slug)
        combo.setCurrentIndex(combo.findData(preferred) if preferred is not None else 0)
        if combo.currentIndex() < 0:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def remove_target(self):
        index = self.table.currentRow()
        if index >= 0:
            self.controls.pop(index)
            self.table.removeRow(index)

    def save(self):
        targets = [{'target_id': self.owner.technique_id(c), 'target_scope': c['scope'].currentData(),
                    **({'annotation_patch': c['patch']} if c['patch'] else {})} for c in self.controls]
        try:
            decision_targets({'action': 'Copy', 'targets': targets}, self.owner.target_catalog)
        except ValueError as error:
            self.error.setText(str(error))
            return
        self.result_targets = deepcopy(targets)
        self.accept()


class ConflictResolutionDialog(QtWidgets.QDialog):
    def __init__(self, owner, plan):
        super().__init__(owner)
        self.plan, self.controls, self.result_resolutions = plan, [], None
        self.setWindowTitle('Resolve migration conflicts')
        self.resize(1300, 760)
        layout = QtWidgets.QVBoxLayout(self)
        hint = QtWidgets.QLabel('Review each conflicting field. Compatible comments, links and metadata are merged without duplicates.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QtWidgets.QTableWidget(len(plan['conflicts']), 5)
        self.table.setHorizontalHeaderLabels(['Target / field', 'Candidate values', 'Conflict resolution', 'Custom JSON value', 'Reviewed'])
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 210)
        self.table.setColumnWidth(2, 270)
        self.table.setColumnWidth(4, 90)
        layout.addWidget(self.table, 1)
        for index, conflict in enumerate(plan['conflicts']):
            label = conflict['target_id'] + '/' + (conflict['target_scope'] or 'All tactics') + '\n' + conflict['field']
            cell = QtWidgets.QTableWidgetItem(label)
            cell.setFlags(cell.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(index, 0, cell)
            candidates = QtWidgets.QPlainTextEdit()
            candidates.setReadOnly(True)
            candidates.setPlainText('\n'.join(c['label'] + ': ' + canonical(c['value']) for c in conflict['candidates']))
            self.table.setCellWidget(index, 1, candidates)
            choice = QtWidgets.QComboBox()
            choice.addItem('Choose resolution…', None)
            for candidate in conflict['candidates']:
                choice.addItem(candidate['label'] + ' · ' + canonical(candidate['value']), 'candidate|' + candidate['origin'])
            choice.addItem('Custom JSON value', 'custom')
            choice.addItem('Clear field', 'clear')
            value = QtWidgets.QPlainTextEdit()
            value.setPlaceholderText('JSON: 7.5, true, "#abcdef", null…')
            value.setEnabled(False)
            reviewed = QtWidgets.QCheckBox()
            control = {'conflict': conflict, 'choice': choice, 'value': value, 'reviewed': reviewed}
            self.controls.append(control)
            self.table.setCellWidget(index, 2, choice)
            self.table.setCellWidget(index, 3, value)
            self.table.setCellWidget(index, 4, reviewed)
            self.table.setRowHeight(index, 115)
            choice.currentIndexChanged.connect(lambda *_, c=control: self.changed(c))
            value.textChanged.connect(lambda c=control: self.changed_value(c))
            old = next((r for r in owner.conflict_resolutions if all(r.get(k) == conflict[k]
                        for k in ('target_id', 'target_scope', 'field', 'fingerprint'))), None)
            if old:
                data = 'candidate|' + old.get('origin', '') if old['action'] == 'candidate' else old['action']
                choice.setCurrentIndex(choice.findData(data))
                if old['action'] == 'custom':
                    value.setPlainText(json.dumps(old['value'], ensure_ascii=False))
                reviewed.setChecked(old.get('reviewed') is True)
        self.error = QtWidgets.QLabel()
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 2)
        layout.addWidget(self.progress)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def changed(self, control):
        data = control['choice'].currentData()
        control['value'].setEnabled(data == 'custom')
        control['reviewed'].setChecked(False)
        if hasattr(self, 'error'):
            self.error.clear()

    def changed_value(self, control):
        control['reviewed'].setChecked(False)
        if hasattr(self, 'error'):
            self.error.clear()

    def save(self):
        decisions = []
        self.error.clear()
        try:
            for control in self.controls:
                conflict, data = control['conflict'], control['choice'].currentData()
                if not data or not control['reviewed'].isChecked():
                    raise ValueError('Choose and review every conflict resolution.')
                action, _, origin = data.partition('|')
                decision = {key: conflict[key] for key in ('target_id', 'target_scope', 'field', 'fingerprint')}
                decision.update(action=action, reviewed=True)
                if action == 'candidate':
                    decision['origin'] = origin
                elif action == 'custom':
                    decision['value'] = json.loads(control['value'].toPlainText())
                    canonical(decision['value'])
                decisions.append(decision)
            self.progress.setValue(1)
            self.parent().report('[Upgrade conflicts 1/2] Validating reviewed field resolutions', 1, 2)
            resolved_layer(self.plan, decisions)
        except (ValueError, TypeError) as error:
            self.error.setText(str(error))
            return
        self.progress.setValue(2)
        self.parent().report('[Upgrade conflicts 2/2] Field resolutions validated', 2, 2)
        self.result_resolutions = decisions
        self.accept()
