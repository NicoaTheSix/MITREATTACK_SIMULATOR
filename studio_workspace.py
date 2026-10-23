"""Native Save/Open/Exit and checkpoint orchestration. Operation flow: README.md."""
from pathlib import Path

from PySide6 import QtCore, QtWidgets
from layer_analysis import snapshot_document
from navigator_dialogs import IntegrationWorker
from studio_dialogs import StudioTaskDialog
from studio_files import open_studio, save_studio, read_session, write_session, session_payload, session_checksum
from localization import tr
from framework_dialog import choose_frameworks
from framework_io import selection, FrameworkSelection
from app_identity import APP_NAME


class StudioWorkspace:
    def init_studio_workspace(self, session_path):
        self.session_path = Path(session_path).expanduser().resolve() if session_path is not None else None
        self.session_initialized = False
        self.session_startup_done = False
        self.session_signature = None
        self.session_worker = None
        self.session_stopping = False
        self.session_lock = None
        self.pending_session_view = None
        self.pending_session_notice = None
        self.session_timer = QtCore.QTimer(self)
        self.session_timer.setSingleShot(True)
        self.session_timer.setInterval(1500)
        self.session_timer.timeout.connect(self.checkpoint_session)
        if self.session_path:
            self.operation_report('Input files: None (recovery ownership check)', 0, 0)
            self.operation_report(f'Output session file: {self.session_path}', 0, 0)
            self.operation_report(f'Output lock file: {self.session_path}.lock', 0, 0)
            try:
                self.session_path.parent.mkdir(parents=True, exist_ok=True)
                lock = QtCore.QLockFile(str(self.session_path) + '.lock')
                if not lock.tryLock(0):
                    raise OSError('Another application instance owns this recovery file.')
                self.session_lock = lock
            except OSError as error:
                self.operation_report(f'[Session] Recovery disabled: {error}; manual Save remains available.', 1, 1)
                self.session_path = None

    def add_studio_actions(self, file_menu):
        self.open_studio_action = file_menu.addAction('Open Studio JSON…')
        self.open_studio_action.setShortcut('Ctrl+O')
        self.open_studio_action.triggered.connect(lambda: self.open_studio_document())
        self.save_action = file_menu.addAction('Save')
        self.save_action.setShortcut('Ctrl+S')
        self.save_action.triggered.connect(lambda: self.save_studio_document())
        self.save_as_action = file_menu.addAction('Save As…')
        self.save_as_action.setShortcut('Ctrl+Shift+S')
        self.save_as_action.triggered.connect(lambda: self.save_studio_document(save_as=True))
        self.recover_session_action = file_menu.addAction('Restore last session…')
        self.recover_session_action.triggered.connect(lambda: self.restore_studio_session())
        self.new_session_action = file_menu.addAction('Start new recovery session…')
        self.new_session_action.triggered.connect(self.start_new_recovery)
        self.studio_actions = (self.open_studio_action, self.save_action, self.save_as_action,
                               self.recover_session_action, self.new_session_action)
        for action in self.studio_actions:
            action.setEnabled(False)

    def studio_task(self, title, task):
        if self.integration_dialog and self.integration_dialog.isVisible():
            self.integration_dialog.raise_()
            return None
        dialog = StudioTaskDialog(title, task, self)
        self.show_integration_dialog(dialog)
        accepted = dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted
        if dialog.failure_message:
            QtWidgets.QMessageBox.critical(self, title + ' failed', dialog.failure_message)
        return dialog.result_value if accepted else None

    def open_studio_document(self, path=None, *, frameworks=None):
        if not self.loaded_ok:
            return None
        interactive = path is None and frameworks is None
        if path is None:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Studio JSON', str(Path.home()), 'Studio JSON (*.json)')
        if not path:
            self.operation_report('[Studio Open] Cancelled; workspace unchanged', 1, 1)
            return None
        path = Path(path).expanduser().resolve()
        frameworks = choose_frameworks(self, 'read', path) if interactive else selection(frameworks)
        if frameworks is None:
            return None
        existing = next((i for i, doc in enumerate(self.documents) if doc.save_path == path), None)
        if existing is not None and frameworks == FrameworkSelection():
            self.activate_document(existing)
            self.operation_report('[Studio Open] File is already open; activated existing tab', 1, 1)
            return self.documents[existing]
        document = self.studio_task('Open Studio JSON', lambda notify: open_studio(self.data_root, path, notify, frameworks, self.catalog))
        if document is None:
            return None
        if any(doc.document_id == document.document_id for doc in self.documents):
            QtWidgets.QMessageBox.warning(self, 'Document already open',
                'Another file with this document UUID is already open. Close that tab first, or use Duplicate active layer.')
            return None
        return document if self.install_imported_document(document) else None

    def save_studio_document(self, save_as=False, target=None, index=None, *, frameworks=None):
        if not self.loaded_ok:
            return None
        interactive = target is None and frameworks is None
        index = self.active_document_index if index is None else index
        if not 0 <= index < len(self.documents):
            return None
        self.sync_active_document()
        document = self.documents[index]
        if target is None and not save_as:
            target = document.save_path
        if target is None:
            folder = document.save_path.parent if document.save_path else Path.home()
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Studio JSON',
                str(folder / (document.name + '.json')), 'Studio JSON (*.json)')
            if not filename:
                self.operation_report('[Studio Save] Cancelled; document and files unchanged', 1, 1)
                return None
            target, save_as = Path(filename), True
        target = Path(target).expanduser().resolve()
        if target.suffix.casefold() != '.json':
            target = target.with_name(target.name + '.json')
        if self.session_path and target == self.session_path:
            QtWidgets.QMessageBox.warning(self, 'Recovery file reserved', 'Choose a different filename; this path belongs to automatic workspace recovery.')
            return None
        if any(doc is not document and doc.save_path == target for doc in self.documents):
            QtWidgets.QMessageBox.warning(self, 'File already open', 'Choose a different filename; another open tab owns this save path.')
            return None
        frameworks = choose_frameworks(self, 'write', target) if interactive else selection(frameworks)
        if frameworks is None:
            return None
        source = snapshot_document(document)
        result = self.studio_task('Save Studio JSON', lambda notify: save_studio(source, target, notify, save_as, frameworks))
        if result is None:
            return None
        # Parent-window edits are blocked while this immutable draft is being written.
        document.name = result.name
        document.save_path, document.saved_fingerprint = result.save_path, result.saved_fingerprint
        document.saved_file_sha256 = result.saved_file_sha256
        self.update_document_labels()
        return result.save_path

    def allow_studio_output(self, target, owner=None):
        target = Path(target).expanduser().resolve()
        if self.session_path and target == self.session_path:
            QtWidgets.QMessageBox.warning(self, 'Recovery file reserved', 'Choose a different filename; this path belongs to workspace recovery.')
            return False
        if any(doc is not owner and doc.save_path == target for doc in self.documents):
            QtWidgets.QMessageBox.warning(self, 'File already open', 'Choose a different filename; another open document owns this Studio save path.')
            return False
        return True

    def confirm_studio_changes(self, documents, title):
        dirty = [doc for doc in documents if doc.dirty]
        if not dirty:
            return 'clean'
        names = '\n'.join('• ' + doc.name for doc in dirty[:20])
        if len(dirty) > 20:
            names += f'\n… and {len(dirty) - 20} more'
        answer = QtWidgets.QMessageBox.question(self, title,
            'Save complete Studio JSON before continuing?\n\n' + names +
            '\n\nSave saves each listed document. Discard drops these changes from recovery. Cancel keeps everything open.',
            QtWidgets.QMessageBox.StandardButton.Save | QtWidgets.QMessageBox.StandardButton.Discard |
            QtWidgets.QMessageBox.StandardButton.Cancel, QtWidgets.QMessageBox.StandardButton.Cancel)
        if answer == QtWidgets.QMessageBox.StandardButton.Cancel:
            return 'cancel'
        if answer == QtWidgets.QMessageBox.StandardButton.Discard:
            return 'discard'
        for document in dirty:
            index = self.documents.index(document)
            if self.save_studio_document(index=index) is None or document.dirty:
                return 'cancel'
        return 'saved'

    def studio_view(self):
        page = ('details' if self.workspace.currentWidget() is self.details_page else
                'cases' if self.workspace.currentWidget() is self.atlas_cases_page else
                'car' if self.workspace.currentWidget() is self.car_browser else
                'matrix' if self.tabs.currentIndex() in (self.matrix_tab_index, self.atlas_matrix_tab_index) else 'selected')
        return {'page': page, 'details_open': self.details_tab_index >= 0,
                'category': self.active_category, 'overlay': self.matrix_view.show_all_layers.isChecked(),
                'show_colors': self.matrix_view.show_colors.isChecked(),
                'matrix_framework': 'atlas' if self.tabs.currentIndex() == self.atlas_matrix_tab_index else 'attack',
                'attack_matrix_open': self.tabs.isTabVisible(self.matrix_tab_index),
                'atlas_matrix_open': self.tabs.isTabVisible(self.atlas_matrix_tab_index),
                'atlas_cases_open':self.atlas_cases_tab_index>=0,
                'car_browser_open':self.car_browser_tab_index>=0,
                'car_browser_kind':self.car_browser.kind,
                'matrix_controls_expanded':self.matrix_view.controls_toggle.isChecked(),
                'atlas_case_key':self.atlas_cases_page.key,
                'atlas_cases_query':self.atlas_cases_page.search.text(),
                'attack_expanded': self.attack_selection_toggle.isChecked(),
                'atlas_expanded': self.atlas_selection_toggle.isChecked(),
                'car_expanded':self.car_selection_toggle.isChecked()}

    def workspace_signature(self):
        values = [(doc.document_id, doc.content_token(), doc.dirty, str(doc.save_path), doc.saved_fingerprint,
                   doc.saved_file_sha256) for doc in self.documents]
        return session_checksum({'documents': values, 'active': self.active_document_index, 'view': self.studio_view()})

    def schedule_session_checkpoint(self):
        if getattr(self, 'session_path', None) and self.session_initialized and not self.session_stopping and self.loaded_ok:
            self.session_timer.start()

    def checkpoint_session(self):
        if not self.session_path or not self.session_initialized or self.session_stopping or not self.loaded_ok:
            return
        if self.session_worker and self.session_worker.isRunning():
            self.session_timer.start()
            return
        signature = self.workspace_signature()
        if signature == self.session_signature:
            return
        try:
            payload = session_payload(self.documents, self.active_document_index, self.studio_view())
        except Exception as error:
            self.operation_report(f'[Session] Checkpoint failed; use manual Save: {error}', 1, 1)
            return
        if self.session_worker:
            self.session_worker.deleteLater()
        self.session_worker = IntegrationWorker(lambda notify: write_session(payload, self.session_path, notify), self)
        self.session_worker.progress.connect(self.operation_report)
        self.session_worker.completed.connect(lambda _: setattr(self, 'session_signature', signature))
        self.session_worker.failed.connect(lambda error: self.operation_report('[Session] Checkpoint failed; previous checkpoint retained: ' + error, 1, 1))
        self.session_worker.start()

    def finish_studio_startup(self):
        for action in self.studio_actions:
            action.setEnabled(self.loaded_ok)
        self.recover_session_action.setEnabled(bool(self.session_path))
        self.new_session_action.setEnabled(bool(self.session_path))
        if self.pending_session_view is not None:
            view, self.pending_session_view = self.pending_session_view, None
            self.matrix_view.show_all_layers.setChecked(bool(view.get('overlay', False)))
            self.matrix_view.show_colors.setChecked(bool(view.get('show_colors', True)))
            self.matrix_view.set_controls_expanded(view.get('matrix_controls_expanded', True))
            if view.get('car_browser_open',False) or view.get('page')=='car':
                self.ensure_car_browser_tab()
            else:
                self.close_car_browser()
            self.car_browser.kind=view.get('car_browser_kind','CAR Analytics')
            self.car_browser.show_list(reveal=False)
            if view.get('atlas_cases_open',True) or view.get('page')=='cases':
                self.ensure_atlas_cases_tab()
            else:
                self.close_atlas_cases()
            self.switch_category(view.get('category') if view.get('category') in self.navigation_buttons else 'TTP')
            if not view.get('details_open', True):
                self.close_details_page()
            self.atlas_cases_page.search.setText(view.get('atlas_cases_query',''))
            self.atlas_cases_page.refresh()
            if view.get('atlas_case_key'):
                self.atlas_cases_page.show_record(view['atlas_case_key'])
            if view.get('page')=='car':
                self.reveal_car_browser()
            elif view.get('page')=='cases' or view.get('category')=='ATLAS Case Studies':
                self.open_atlas_cases(view.get('atlas_case_key'))
            elif view.get('page') == 'matrix':
                if view.get('matrix_framework') == 'atlas':
                    self.open_atlas_matrix()
                else:
                    self.open_matrix()
            elif view.get('page') == 'details':
                self.open_details_page()
            else:
                self.show_document_page()
                self.tabs.setCurrentIndex(self.selection_tab_index)
            self.tabs.blockSignals(True)
            self.tabs.setTabVisible(self.matrix_tab_index, view.get('attack_matrix_open', True))
            self.tabs.setTabVisible(self.atlas_matrix_tab_index, view.get('atlas_matrix_open', True))
            self.tabs.blockSignals(False)
            self.attack_selection_toggle.setChecked(view.get('attack_expanded', True))
            self.atlas_selection_toggle.setChecked(view.get('atlas_expanded', True))
            self.car_selection_toggle.setChecked(view.get('car_expanded',True))
        if self.pending_session_notice is not None:
            if self.matrix_view.building:
                self.matrix_view.ready.connect(self.report_session_restore_complete,
                    QtCore.Qt.ConnectionType.SingleShotConnection)
            else:
                self.report_session_restore_complete()
        if not self.session_startup_done:
            self.session_startup_done = True
            if self.session_path and self.session_path.exists():
                QtCore.QTimer.singleShot(0, lambda: self.restore_studio_session(startup=True))
            else:
                self.session_initialized = True
        self.schedule_session_checkpoint()

    @QtCore.Slot()
    def report_session_restore_complete(self):
        if self.pending_session_notice is None:
            return
        automatic, count, unsaved = self.pending_session_notice
        self.pending_session_notice = None
        self.output_panel.show()
        message = ('[Session Restore 3/3] Automatically restored the previous session: {tabs} tabs '
                   '({unsaved} with unsaved changes). Checkpoint: {path}' if automatic else
                   '[Session Restore 3/3] Restored the selected session: {tabs} tabs '
                   '({unsaved} with unsaved changes). Checkpoint: {path}')
        self.operation_report(tr(message).format(tabs=count, unsaved=unsaved, path=self.session_path), 3, 3)

    def restore_studio_session(self, startup=False):
        if not self.session_path or not self.loaded_ok:
            return False
        self.session_timer.stop()
        self.session_initialized = False
        if self.session_worker and self.session_worker.isRunning():
            self.session_worker.wait()
        if not self.session_path.exists():
            self.operation_report('[Session] No recovery checkpoint exists yet', 1, 1)
            self.session_initialized = True
            self.schedule_session_checkpoint()
            return False
        self.operation_report(f'Input file: {self.session_path}', 0, 0)
        self.operation_report('Output files: None (workspace restoration in memory)', 0, 0)
        if startup:
            self.operation_report(tr('[Session Restore 1/3] Automatically validating the previous session'), 0, 3)
        result = self.studio_task('Restore last session', lambda notify: read_session(self.data_root, self.session_path, notify))
        if result is None:
            self.operation_report('[Session] Recovery cancelled/failed; checkpoint retained. Retry Restore last session or explicitly Start new recovery session.', 1, 1)
            return False
        if not result['documents']:
            self.operation_report(tr('[Session] The previous checkpoint has no tabs; starting an empty workspace.'), 1, 1)
            self.session_initialized = True
            self.schedule_session_checkpoint()
            return False
        if not startup:
            answer = QtWidgets.QMessageBox.question(self, 'Restore last session',
                f"Restore {len(result['documents'])} tabs, including unsaved drafts?\n"
                'Yes restores them. No keeps the current workspace and starts a new checkpoint. Cancel retains the previous checkpoint.',
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No |
                QtWidgets.QMessageBox.StandardButton.Cancel, QtWidgets.QMessageBox.StandardButton.Yes)
            if answer == QtWidgets.QMessageBox.StandardButton.Cancel:
                return False
            if answer == QtWidgets.QMessageBox.StandardButton.No:
                self.session_initialized = True
                self.schedule_session_checkpoint()
                return False
            if self.confirm_studio_changes(self.documents, 'Replace current workspace') == 'cancel':
                return False
        self.operation_report(tr('[Session Restore 2/3] Installing validated tabs and restoring the workspace view'), 1, 3)
        self.close_details_page()
        self.document_tabs.blockSignals(True)
        while self.document_tabs.count():
            self.document_tabs.removeTab(0)
        self.documents = result['documents']
        for index, doc in enumerate(self.documents):
            self.document_tabs.addTab(doc.name)
            self.document_tabs.setTabData(index, doc.document_id)
        self.active_document_index = result['active_index']
        self.document_tabs.setCurrentIndex(self.active_document_index)
        self.document_tabs.blockSignals(False)
        self.document_counter = max(self.document_counter, len(self.documents))
        self.selected = set(self.current_document.selected)
        self.pending_session_view = result['view']
        self.pending_session_notice = (startup, len(self.documents), sum(doc.dirty for doc in self.documents))
        self.session_initialized, self.session_signature = True, None
        self.operation_report('[Session] Installing all validated tabs; original checkpoint retained until the next successful checkpoint', 1, 1)
        self.apply_version((self.current_document.catalog, None))
        return True

    def start_new_recovery(self):
        if not self.session_path:
            return
        answer = QtWidgets.QMessageBox.question(self, 'Start new recovery session',
            'Replace the previous recovery checkpoint with the currently open workspace? Existing Studio JSON files are unaffected.',
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No)
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            self.session_initialized, self.session_signature = True, None
            self.schedule_session_checkpoint()

    def finish_studio_exit(self):
        self.sync_active_document()
        decision = self.confirm_studio_changes(self.documents, 'Exit ' + APP_NAME)
        if decision == 'cancel':
            return False
        self.session_timer.stop()
        self.session_stopping = True
        if self.session_worker and self.session_worker.isRunning():
            self.session_worker.wait()
        if self.session_path and self.session_initialized:
            try:
                # Discard invalidates the entire recovery workspace, so rejected drafts never resurface.
                documents = [] if decision == 'discard' else self.documents
                payload = session_payload(documents, self.active_document_index, self.studio_view(), clean_exit=True)
                write_session(payload, self.session_path, self.operation_report)
            except Exception as error:
                self.session_stopping = False
                QtWidgets.QMessageBox.critical(self, 'Recovery checkpoint failed',
                    str(error) + '\nThe application remains open; save your documents and retry.')
                return False
        if self.session_lock:
            self.session_lock.unlock()
        return True
