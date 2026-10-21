"""Final upgrade summary, local reason drafts and return-to-review actions. Workflow: README.md."""
from copy import deepcopy
from PySide6 import QtCore, QtWidgets
from upgrade_summary import REASON_LIMIT, validate_reasons


class UpgradeSummaryDialog(QtWidgets.QDialog):
    def __init__(self, owner, report):
        super().__init__(owner)
        self.report_data = deepcopy(report)
        self.reason_edits = deepcopy(owner.skip_reasons)
        self.result_action = None
        self.navigation = None
        self.setWindowTitle('Final upgrade summary')
        self.resize(1250, 850)
        layout = QtWidgets.QVBoxLayout(self)
        self.overview = QtWidgets.QLabel()
        self.overview.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.overview.setWordWrap(True)
        layout.addWidget(self.overview)
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.categories = QtWidgets.QTableWidget(0, 5)
        self.categories.setHorizontalHeaderLabels(['Category', 'Reviewed', 'Total', 'Skipped', 'Status'])
        self.categories.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.categories, 'Category summary')
        reason_page = QtWidgets.QWidget()
        reasons = QtWidgets.QVBoxLayout(reason_page)
        hint = QtWidgets.QLabel('Reasons are optional. Skipping an Added annotation does not cancel an incoming Copy mapping.')
        hint.setWordWrap(True)
        reasons.addWidget(hint)
        self.skips = QtWidgets.QTableWidget(0, 4)
        self.skips.setHorizontalHeaderLabels(['Category', 'Item', 'Action', 'Skip reason'])
        self.skips.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.skips.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.skips.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.skips.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        reasons.addWidget(self.skips, 1)
        self.reason_empty = QtWidgets.QLabel('No skipped source rows or Added annotations.')
        reasons.addWidget(self.reason_empty)
        self.reason_editor = QtWidgets.QPlainTextEdit()
        self.reason_editor.setPlaceholderText('Optional skip reason, including multiple lines (up to 4096 characters)…')
        self.reason_editor.setMaximumHeight(110)
        reasons.addWidget(self.reason_editor)
        self.apply_reason = QtWidgets.QPushButton('Apply reason to selected skipped items')
        self.apply_reason.clicked.connect(self.apply_selected_reasons)
        reasons.addWidget(self.apply_reason)
        self.tabs.addTab(reason_page, 'Skipped items and reasons')
        pending_page = QtWidgets.QWidget()
        pending = QtWidgets.QVBoxLayout(pending_page)
        self.unfinished = QtWidgets.QTableWidget(0, 3)
        self.unfinished.setHorizontalHeaderLabels(['Type', 'Item', 'Details'])
        self.unfinished.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.unfinished.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.unfinished.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        pending.addWidget(self.unfinished, 1)
        self.pending_empty = QtWidgets.QLabel('No unfinished checks. The migration is ready to submit.')
        pending.addWidget(self.pending_empty)
        self.goto = QtWidgets.QPushButton('Return to selected unfinished item')
        self.goto.clicked.connect(self.return_selected)
        pending.addWidget(self.goto)
        self.unfinished.cellDoubleClicked.connect(lambda *_: self.return_selected())
        self.tabs.addTab(pending_page, 'Unfinished items')
        self.error = QtWidgets.QLabel()
        self.error.setWordWrap(True)
        self.error.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        layout.addWidget(self.error)
        buttons = QtWidgets.QHBoxLayout()
        self.back = QtWidgets.QPushButton('Back to review (keep reasons)')
        self.back.clicked.connect(lambda: self.finish('return'))
        self.first = QtWidgets.QPushButton('Return to first unfinished item')
        self.first.clicked.connect(lambda: self.finish('return', self.report_data['issues'][0] if self.report_data['issues'] else None))
        self.submit = QtWidgets.QPushButton('Submit migration')
        self.submit.clicked.connect(lambda: self.finish('submit'))
        cancel = QtWidgets.QPushButton('Cancel')
        cancel.clicked.connect(self.reject)
        for button in (self.back, self.first, self.submit, cancel):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        for index, category in enumerate(report['categories']):
            self.categories.insertRow(index)
            values = [category['category'], category['reviewed'], category['total'], category['skipped'], category['state']]
            for column, value in enumerate(values):
                self.categories.setItem(index, column, self.readonly(value))
        for index, skip in enumerate(report['skips']):
            self.skips.insertRow(index)
            for column, value in enumerate((skip['category'], skip['identity'] + ('/' + skip['scope'] if skip['scope'] else ''), skip['kind'])):
                self.skips.setItem(index, column, self.readonly(value))
            self.skips.setItem(index, 3, QtWidgets.QTableWidgetItem(skip['reason']))
        kinds = {'technique': 'Technique review', 'mapping': 'Source mapping', 'conflict': 'Conflict resolution', 'name': 'Document name'}
        for index, issue in enumerate(report['issues']):
            self.unfinished.insertRow(index)
            values = [kinds.get(issue['kind'], issue['kind']), issue.get('identity') or issue.get('target_id', ''), issue['message']]
            for column, value in enumerate(values):
                self.unfinished.setItem(index, column, self.readonly(value))
        self.skips.itemChanged.connect(self.reason_changed)
        self.skips.currentCellChanged.connect(self.load_reason)
        self.reason_empty.setVisible(not report['skips'])
        self.pending_empty.setVisible(not report['issues'])
        self.goto.setEnabled(bool(report['issues']))
        self.first.setEnabled(bool(report['issues']))
        self.apply_reason.setEnabled(bool(report['skips']))
        if report['issues']:
            self.unfinished.setCurrentCell(0, 0)
        if report['skips']:
            self.skips.setCurrentCell(0, 0)
        from localization import language_manager
        language_manager().changed.connect(self.refresh_text)
        self.refresh_text()

    @staticmethod
    def readonly(value):
        item = QtWidgets.QTableWidgetItem(str(value))
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        return item

    def refresh_text(self, *_):
        from localization import tr
        report = self.report_data
        label = tr('Ready to submit') if report['can_submit'] else tr('Submission blocked')
        self.overview.setText(label + '\n' + tr('Source v{source} → target v{target} · {domain}').format(
            source=report['source']['version'], target=report['target']['version'], domain=report['target']['domain']) + '\n' +
            tr('Result document: {name} · source document: {source_name}').format(
                name=report['result_name'], source_name=report['source_name']) + '\n' +
            tr('{reviewed}/{total} techniques reviewed · {copy} Copy · {drop} Drop · {pending} unfinished checks').format(
                reviewed=report['reviewed'], total=report['total'], copy=report['copy_rows'], drop=report['drop_rows'], pending=len(report['issues'])) + '\n' +
            tr('Output rows: {rows} · selected techniques: {techniques} · selected occurrences: {occurrences} · resolved conflicts: {resolved}/{conflicts}').format(
                rows=report['output_rows'] if report['output_rows'] is not None else '—',
                techniques=report['selected_techniques'] if report['selected_techniques'] is not None else '—',
                occurrences=report['selected_occurrences'] if report['selected_occurrences'] is not None else '—',
                resolved=report['resolved_conflicts'] if report['resolved_conflicts'] is not None else '—',
                conflicts=report['conflicts'] if report['conflicts'] is not None else '—'))
        self.validate_local_reasons()

    def validate_local_reasons(self):
        try:
            validate_reasons(self.parent().preview_data, self.reason_edits)
        except ValueError as error:
            self.error.setText(str(error))
            self.submit.setEnabled(False)
            return False
        self.error.clear()
        self.submit.setEnabled(self.report_data['can_submit'])
        return True

    def reason_changed(self, cell):
        if cell.column() == 3:
            key = self.report_data['skips'][cell.row()]['key']
            self.reason_edits[key] = cell.text()
            self.validate_local_reasons()

    def load_reason(self, row, *_):
        if row >= 0:
            self.reason_editor.setPlainText(self.skips.item(row, 3).text())

    def apply_selected_reasons(self):
        value = self.reason_editor.toPlainText()
        if len(value) > REASON_LIMIT:
            self.error.setText('Each skip reason must be text of at most 4096 characters.')
            return
        self.parent().report('Input files: None; output files: None (skip reason drafts in memory)', 0, 0)
        self.parent().report('[Skip reasons 1/2] Validating selected reason drafts', 0, 2)
        for index in sorted({i.row() for i in self.skips.selectedIndexes()}):
            self.skips.item(index, 3).setText(value)
        self.parent().report('[Skip reasons 2/2] Local reasons updated; Cancel discards this summary draft', 2, 2)

    def return_selected(self):
        row = self.unfinished.currentRow()
        if row >= 0:
            self.finish('return', self.report_data['issues'][row])

    def finish(self, action, navigation=None):
        if not self.validate_local_reasons() or action == 'submit' and not self.report_data['can_submit']:
            return
        self.result_action, self.navigation = action, deepcopy(navigation)
        self.accept()
