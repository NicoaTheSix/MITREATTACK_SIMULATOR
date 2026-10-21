"""Review immutable JSON annotation export options. Workflow: README.md."""
from pathlib import Path
from PySide6 import QtCore, QtWidgets
from localization import tr


class JSONAnnotationExportDialog(QtWidgets.QDialog):
    def __init__(self, plans, target, parent=None):
        super().__init__(parent)
        self.plans = tuple(plans)
        self.setWindowTitle('Navigator JSON annotation export')
        self.resize(800, 590)
        layout = QtWidgets.QVBoxLayout(self)
        path = QtWidgets.QLabel(tr('Output file: {path}').format(path=Path(target).expanduser().resolve()))
        path.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        path.setWordWrap(True)
        layout.addWidget(path)
        self.visible_only = QtWidgets.QCheckBox('Export annotations on visible techniques only')
        self.visible_only.setChecked(False)
        layout.addWidget(self.visible_only)
        hint = QtWidgets.QLabel('Default: preserve all annotations. Visibility uses platform filters, search, '
            'Hide disabled and expanded sub-techniques; scrolling and hover outlines do not count. '
            'The active layer uses the current matrix view. Other layers use their own saved settings without search or overlays.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        table = QtWidgets.QTableWidget(len(plans), 3)
        table.setHorizontalHeaderLabels(['Layer', 'Hidden modified cells', 'Distinct technique IDs'])
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        for number, plan in enumerate(plans):
            for column, text in enumerate((plan.layer['name'], len(plan.hidden_modified), plan.hidden_techniques)):
                table.setItem(number, column, QtWidgets.QTableWidgetItem(str(text)))
        self.layers_table = table
        layout.addWidget(table)
        self.warning = QtWidgets.QLabel()
        self.warning.setWordWrap(True)
        layout.addWidget(self.warning)
        self.details = QtWidgets.QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlainText('\n'.join(plan.layer['name'] + ' · ' + row['techniqueID'] + ' · '
            + (row.get('tactic') or tr('Unknown / unmapped scope'))
            for plan in plans for row in plan.hidden_modified))
        layout.addWidget(self.details)
        note = QtWidgets.QLabel('Visible-only export removes hidden technique annotations, including enabled state and custom row fields. '
            'Studio inclusion markers remain, so hidden selected techniques may have identity-only rows. '
            'Layer properties and selection scopes remain complete. Use Studio Save / Save As for the complete editable document. '
            'The source layer, selections and unsaved state are unchanged; this option is not saved.')
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QtWidgets.QDialogButtonBox()
        self.export_button = buttons.addButton('Export JSON', QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.visible_only.toggled.connect(self.update_warning)
        self.update_warning()

    def update_warning(self):
        count = sum(len(plan.hidden_modified) for plan in self.plans)
        message = ('{count} hidden modified annotation cells will be omitted from this export.' if self.visible_only.isChecked()
                   else '{count} hidden modified annotation cells will be preserved (default).')
        self.warning.setText(tr(message).format(count=count))
