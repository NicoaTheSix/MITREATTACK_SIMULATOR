"""In-import Bundle acquisition and explicit dataset replacement review. Flow: README.md."""
from copy import deepcopy
from pathlib import Path
import re

from PySide6 import QtCore, QtWidgets
from custom_data_import import inspect_source, accept_source, resolve_location
from navigator_dialogs import IntegrationDialog


class CustomDataDialog(IntegrationDialog):
    source_accepted = QtCore.Signal(object)

    def __init__(self, root, layer, version, policy, layer_path, parent, origin=''):
        super().__init__(parent)
        self.root, self.layer_path = Path(root).resolve(), Path(layer_path).resolve()
        self.layer, self.version, self.policy, self.origin = deepcopy(layer), version, policy, origin
        self.candidate = None
        self.local_location = None
        self.busy = False
        self.setWindowTitle('Resolve custom data source')
        self.resize(920, 720)
        layout = QtWidgets.QVBoxLayout(self)
        hint = QtWidgets.QLabel('Fetch the declared URL, choose a local Bundle or inspect a cached Bundle. '
            'Nothing is fetched automatically. Accepting a source only updates this import preview.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        info = QtWidgets.QLabel(f"{layer['name']} · {layer['domain']} v{version}\n"
            f"customDataURL: {layer.get('customDataURL', '')}\nSHA-256: {layer.get('x_ttp_studio_dataset', '') or '—'}")
        info.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        info.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        info.setWordWrap(True)
        layout.addWidget(info)
        self.location = QtWidgets.QLineEdit(layer.get('customDataURL', ''))
        self.location.setPlaceholderText('Bundle URL or local JSON path')
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.location, 1)
        self.browse_button = QtWidgets.QPushButton('Browse Bundle…')
        self.browse_button.clicked.connect(self.browse)
        row.addWidget(self.browse_button)
        self.load_button = QtWidgets.QPushButton('Fetch / Validate source')
        self.load_button.clicked.connect(self.load)
        row.addWidget(self.load_button)
        layout.addLayout(row)
        self.cache = QtWidgets.QComboBox()
        self.cache.addItem('Choose a cached Bundle…', '')
        expected = layer.get('x_ttp_studio_dataset', '')
        folder = self.root / 'custom'
        self.report(f'Input cache directory: {folder}', 0, 0)
        self.report('Output files: None (available cache paths only; contents validated on request)', 0, 0)
        paths = sorted((p for p in folder.glob('*.json') if re.fullmatch(r'[0-9a-f]{64}', p.stem)),
                       key=lambda p: (p.stem != expected, p.name))[:1000]
        for path in paths:
            self.cache.addItem(path.name, str(path.resolve()))
        self.cache.currentIndexChanged.connect(self.choose_cache)
        layout.addWidget(self.cache)
        self.collection = QtWidgets.QComboBox()
        self.collection.currentIndexChanged.connect(self.choose_collection)
        self.collection.hide()
        layout.addWidget(self.collection)
        self.preview = QtWidgets.QPlainTextEdit()
        self.preview.setReadOnly(True)
        layout.addWidget(self.preview, 1)
        self.changed = QtWidgets.QCheckBox('I approve replacing the recorded dataset with this changed Bundle')
        self.changed.hide()
        self.changed.toggled.connect(self.refresh)
        layout.addWidget(self.changed)
        layout.addWidget(self.status)
        layout.addWidget(self.progress)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.accept_button = buttons.addButton('Use verified Bundle', QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        self.accept_button.clicked.connect(self.commit)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.location.textChanged.connect(self.location_changed)
        from localization import language_manager
        language_manager().changed.connect(self.render_candidate)
        if not self.location.text() and expected and (folder / (expected + '.json')).exists():
            self.set_local_location(folder / (expected + '.json'))
        self.refresh()

    def refresh(self, *_):
        for widget in (self.location, self.browse_button, self.load_button, self.cache, self.collection, self.changed):
            widget.setEnabled(not self.busy and not self.closing)
        self.accept_button.setEnabled(not self.busy and not self.closing and self.candidate is not None
                                     and (not self.candidate['changed'] or self.changed.isChecked()))

    def invalidate(self, *_):
        self.candidate = None
        self.preview.clear()
        self.changed.setChecked(False)
        self.changed.hide()
        self.refresh()

    def location_changed(self, value):
        # The initial declared source keeps its remote-reference semantics.
        # An edited native absolute path is an explicit local alternative.
        value = value.strip()
        try:
            path = Path(value).expanduser()
        except (ValueError, OSError, RuntimeError):
            self.local_location = None
        else:
            self.local_location = path if path.is_absolute() and not value.startswith('//') else None
        self.invalidate()

    def set_local_location(self, path):
        local = Path(path).expanduser().resolve()
        self.location.setText(str(local))
        self.local_location = local

    def browse(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Choose custom Bundle', str(self.layer_path.parent), 'JSON (*.json)')
        if path:
            self.set_local_location(path)

    def choose_cache(self, *_):
        if self.cache.currentData():
            self.set_local_location(self.cache.currentData())

    def choose_collection(self, *_):
        entry = self.collection.currentData()
        if entry:
            self.location.setText(entry['url'])

    def load(self):
        if self.busy or self.closing:
            return
        try:
            # Resolve now so editing the input cannot accidentally retain approval.
            location = resolve_location(self.local_location or self.location.text(), self.layer_path, self.origin)
            if self.local_location is not None:
                location = Path(location)
        except (ValueError, OSError, RuntimeError) as error:
            self.report(str(error), 1, 1)
            return
        self.invalidate()
        self.collection.hide()
        self.busy = True
        self.refresh()
        self.start_task(lambda notify: inspect_source(self.root, self.layer, self.version, location,
                        self.layer_path, notify, self.origin, self.policy), self.loaded)

    def loaded(self, candidate):
        if self.closing:
            return
        if 'entries' in candidate:
            self.collection.blockSignals(True)
            self.collection.clear()
            for entry in candidate['entries']:
                self.collection.addItem(f"{entry['name']} · v{entry['version']}", entry)
            self.collection.setCurrentIndex(-1)
            self.collection.blockSignals(False)
            self.collection.show()
            self.render_candidate()
            return
        self.candidate = candidate
        self.changed.setVisible(candidate['changed'])
        self.changed.setChecked(False)
        self.render_candidate()
        if candidate['changed']:
            self.report('Source content differs from the recorded SHA-256. Approve replacement explicitly or choose the original Bundle.', 3, 5)

    def render_candidate(self, *_):
        from localization import tr
        c = self.candidate
        if c is None:
            if not self.collection.isHidden():
                self.preview.setPlainText(tr('Collection Index loaded. Choose a version, then press Fetch / Validate source. '
                                            'The Bundle must match the layer domain and recorded release.'))
            return
        self.preview.setPlainText(tr('Resolved source: {source}\nFinal source: {final}\nExpected SHA-256: {expected}\n'
            'Actual SHA-256: {actual}\nCache output: {cache}\nDomain: {domain}\nRelease: {version}\n'
            'Selected TTPs: {selected}\nUnresolved annotation rows: {unresolved}').format(
                source=c['transport']['source'], final=c['transport']['final'], expected=c['expected'] or '—',
                actual=c['digest'], cache=c['cache'], domain=c['catalog'].domain, version=c['catalog'].version,
                selected=len(c['preview']['selected']), unresolved=c['preview']['unresolved']))

    def task_finished(self):
        self.busy = False
        self.refresh()
        super().task_finished()

    def commit(self):
        if not self.accept_button.isEnabled() or self.busy or self.closing:
            return
        candidate, allowed = self.candidate, self.changed.isChecked()
        self.busy = True
        self.refresh()
        self.start_task(lambda notify: accept_source(self.root, candidate, notify, allowed), self.accepted_source)

    def accepted_source(self, result):
        if not self.closing:
            self.source_accepted.emit(result)
            self.accept()

    def reject(self):
        self.closing = True
        self.refresh()
        super().reject()
