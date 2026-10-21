"""Default-on framework choices for explicit file IO. Workflow: README.md."""
from pathlib import Path
from PySide6 import QtWidgets

from framework_io import FrameworkSelection, selection


class FrameworkOptionsDialog(QtWidgets.QDialog):
    def __init__(self, mode, path, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Read frameworks' if mode == 'read' else 'Write frameworks')
        self.resize(500, 220)
        layout = QtWidgets.QVBoxLayout(self)
        path_label = QtWidgets.QLabel(str(Path(path).expanduser().resolve()))
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        layout.addWidget(QtWidgets.QLabel('Choose frameworks to read:' if mode == 'read' else 'Choose frameworks to write:'))
        self.attack = QtWidgets.QCheckBox('ATT&CK')
        self.atlas = QtWidgets.QCheckBox('ATLAS')
        self.car = QtWidgets.QCheckBox('Include CAR Analytics')
        for box in (self.attack, self.atlas, self.car):
            box.setChecked(True)
            layout.addWidget(box)
        hint = QtWidgets.QLabel('Unselected frameworks stay in the current Workplace. A partial output does not mark the complete Workplace as saved.'
            if mode != 'read' else 'Only checked frameworks are read into a new Workplace. Existing documents stay unchanged.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        note = QtWidgets.QLabel('Navigator and matrix Excel contain only TTPs. Use Studio JSON for complete CAR selections; CSV identifies CAR rows separately.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok |
                                                 QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        for box in (self.attack, self.atlas, self.car):
            box.toggled.connect(self.sync_choices)

    def sync_choices(self):
        self.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(self.attack.isChecked() or self.atlas.isChecked() or self.car.isChecked())

    def choices(self):
        return selection((self.attack.isChecked(), self.atlas.isChecked(), self.car.isChecked()))


def choose_frameworks(parent, mode, path):
    parent.operation_report(f'Input file: {Path(path).resolve()}' if mode == 'read' else 'Input files: None (Workplace in memory)')
    parent.operation_report('Output files: None (read options)' if mode == 'read' else f'Output file: {Path(path).resolve()}')
    parent.operation_report('[Framework IO 1/2] Choosing ATT&CK / ATLAS / CAR', 0, 2)
    dialog = FrameworkOptionsDialog(mode, path, parent)
    accepted = dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted
    result = dialog.choices() if accepted else None
    dialog.deleteLater()
    parent.operation_report('[Framework IO 2/2] ' + (f'ATT&CK={result.attack}; ATLAS={result.atlas}; CAR={result.car}'
        if result is not None else 'Cancelled; no files or selections changed'), 2, 2)
    return result
