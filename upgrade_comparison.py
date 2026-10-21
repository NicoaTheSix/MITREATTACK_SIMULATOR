"""Readable source/target review and row-bound target editor. Workflow: README.md."""
from copy import deepcopy
from PySide6 import QtCore, QtGui, QtWidgets
from attack_catalog import external_id, tactic_phases
from navigator_integration import document_layer
from ttp_documents import TTPDocument
from upgrade_content import content_html, version_page, checked_version_page, mapped_annotation, annotation_patch
from upgrade_mapping import decision_targets


class UpgradeComparison(QtWidgets.QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner, self.context = owner, None
        self.urls = ['', '']
        layout = QtWidgets.QVBoxLayout(self)
        split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.browsers, self.page_buttons, self.page_notes = [], [], []
        for index, title in enumerate(('Before upgrade', 'After upgrade')):
            pane = QtWidgets.QWidget()
            column = QtWidgets.QVBoxLayout(pane)
            column.addWidget(QtWidgets.QLabel(title))
            button = QtWidgets.QPushButton('Open version page…')
            button.clicked.connect(lambda checked=False, i=index: self.open_page(i))
            column.addWidget(button)
            note = QtWidgets.QLabel()
            note.setWordWrap(True)
            column.addWidget(note)
            browser = QtWidgets.QTextBrowser()
            browser.setOpenLinks(False)
            browser.setOpenExternalLinks(False)
            column.addWidget(browser, 1)
            self.browsers.append(browser)
            self.page_buttons.append(button)
            self.page_notes.append(note)
            split.addWidget(pane)
        layout.addWidget(split, 1)
        self.destination = QtWidgets.QComboBox()
        self.destination.setToolTip('Choose the mapped destination to inspect or edit.')
        self.destination.currentIndexChanged.connect(lambda *_: self.refresh())
        layout.addWidget(self.destination)
        self.edit = QtWidgets.QPushButton('Edit target annotation…')
        self.edit.clicked.connect(self.edit_target)
        layout.addWidget(self.edit)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        from localization import language_manager
        language_manager().changed.connect(lambda *_: self.refresh())
        self.clear()

    def clear(self):
        self.context, self.urls = None, ['', '']
        for browser, button, note in zip(self.browsers, self.page_buttons, self.page_notes):
            browser.clear()
            button.setEnabled(False)
            note.clear()
        self.edit.setEnabled(False)
        self.status.clear()
        self.destination.blockSignals(True)
        self.destination.clear()
        self.destination.blockSignals(False)
        self.destination.hide()

    def row_decision(self, index):
        return self.owner.capture_decisions()[index]

    def destinations(self, index):
        try:
            return decision_targets(self.row_decision(index), self.owner.target_catalog)
        except ValueError:
            return []

    def show_row(self, index):
        if self.context != ('row', index):
            self.destination.blockSignals(True)
            self.destination.setCurrentIndex(0)
            self.destination.blockSignals(False)
        self.context = ('row', index)
        self.refresh()

    def show_item(self, identity):
        self.context = ('item', identity)
        self.refresh()

    def refresh(self):
        if not self.context or not self.owner.preview_data:
            return
        from localization import tr
        before = self.owner.document.catalog
        after = self.owner.target_catalog
        preview = self.owner.preview_data
        mode, value = self.context
        rows, selection, target_rows, target_selection = [], set(), [], set()
        valid_edit = False
        if mode == 'row':
            if value >= len(preview['rows']):
                self.clear()
                return
            source = preview['rows'][value]
            identity = source['source_id']
            destinations = self.destinations(value)
            branch = self.destination.currentIndex()
            self.destination.blockSignals(True)
            self.destination.clear()
            for i, dest in enumerate(destinations):
                self.destination.addItem(dest['target_id'] + ' / ' + (dest['target_scope'] or tr('All tactics')), i)
            self.destination.setCurrentIndex(min(max(branch, 0), len(destinations) - 1))
            self.destination.blockSignals(False)
            self.destination.setVisible(len(destinations) > 1)
            decision = destinations[self.destination.currentIndex()] if destinations else self.row_decision(value)
            target_id = decision['target_id'] or ''
            rows = [source['annotation']]
            if source['selected']:
                selection = {source['source_scope'] or tr('All tactics')}
            target_record = next((o for o in after.records.values() if external_id(o) == target_id), {})
            scope = decision['target_scope']
            valid_edit = bool(destinations) and bool(target_record) and scope is not None and (
                not scope or scope in tactic_phases(target_record, after.domain))
            if valid_edit:
                target_rows = [mapped_annotation(source, decision)]
                if source['selected']:
                    target_selection.add(scope or tr('All tactics'))
        else:
            self.destination.hide()
            item = next((i for i in preview['items'] if i['id'] == value), None)
            if item is None:
                self.clear()
                return
            identity, target_id = value, item['target_id']
            mapped_ids = {dest['target_id'] for i in item['row_indices'] for dest in self.destinations(i)}
            if len(mapped_ids) == 1:
                target_id = next(iter(mapped_ids))
            rows = [preview['rows'][i]['annotation'] for i in item['row_indices']]
            for index in item['row_indices']:
                source = preview['rows'][index]
                if source['selected']:
                    selection.add(source['source_scope'] or tr('All tactics'))
                for decision in self.destinations(index):
                    if decision['target_id'] == target_id:
                        target_rows.append(mapped_annotation(source, decision))
                        if source['selected']:
                            target_selection.add(decision['target_scope'] or tr('All tactics'))
            draft = self.owner.review_panel.drafts.get(identity)
            if draft:
                target_rows.extend(deepcopy(draft.navigator_layer.get('techniques', [])))
                from ttp_selection import selected_cells
                target_selection.update(slug for _, slug in selected_cells(draft))
            valid_edit = any(external_id(o) == target_id for o in after.records.values())
        display_target = target_id or identity
        self.browsers[0].setHtml(content_html(before, identity, rows, selection=selection))
        self.browsers[1].setHtml(content_html(after, display_target, target_rows, selection=target_selection))
        self.edit.setEnabled(valid_edit)
        for index, (catalog, key) in enumerate(((before, identity), (after, display_target))):
            self.urls[index] = version_page(catalog, key)
            self.page_buttons[index].setEnabled(bool(self.urls[index]))
            self.page_buttons[index].setToolTip(self.urls[index])
            message = ('Custom dataset: no official version page.' if catalog.dataset_id or catalog.custom_source else
                       'Website archive v{major}; dataset v{version}. Patch versions may differ.' if self.urls[index] else
                       'No version page for this record. The complete cached content is shown below.')
            self.page_notes[index].setText(tr(message).format(major=catalog.version.split('.')[0], version=catalog.version))
        self.status.setText('Choose Copy and a valid target technique/tactic to edit its annotation.'
                            if mode == 'row' and not valid_edit else
                            'Target draft saved. Review this technique and mapping again.'
                            if mode == 'row' and value in self.owner.annotation_edits else '')

    def edit_target(self):
        if not self.context or not self.edit.isEnabled():
            return
        mode, value = self.context
        if mode == 'item':
            item = next(i for i in self.owner.preview_data['items'] if i['id'] == value)
            index = self.owner.review_panel.items.index(item)
            self.owner.review_panel.table.setCurrentCell(index, 0)
            self.owner.review_panel.edit_target()
            return
        from navigator_dialogs import AnnotationDialog
        self.owner.report('Input files: None; output files: None (target annotation draft in memory)', 0, 0)
        self.owner.report('[Upgrade edit 1/2] Preparing mapped target annotation', 0, 2)
        source = self.owner.preview_data['rows'][value]
        destinations = self.destinations(value)
        branch = max(0, self.destination.currentIndex())
        if branch >= len(destinations):
            return
        decision = destinations[branch]
        row = mapped_annotation(source, decision)
        catalog = self.owner.target_catalog
        key = next(k for k, o in catalog.records.items() if external_id(o) == decision['target_id'])
        draft = TTPDocument('Target annotation review', catalog)
        draft.navigator_layer = {**document_layer(draft), 'techniques': [row]}
        dialog = AnnotationDialog(draft, key, self)
        dialog.scope.setCurrentIndex(dialog.scope.findData(decision['target_scope']))
        dialog.scope.setEnabled(False)
        dialog.include.hide()
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            self.owner.report('[Upgrade edit 2/2] Cancelled; previous target draft preserved', 2, 2)
            return
        result = next((r for r in dialog.result_layer['techniques'] if r['techniqueID'] == decision['target_id']
                       and r.get('tactic', '') == decision['target_scope']), {'techniqueID': decision['target_id']})
        if value in self.owner.mapping_targets:
            self.owner.mapping_targets[value][branch]['annotation_patch'] = annotation_patch(result)
        else:
            self.owner.annotation_edits[value] = annotation_patch(result)
        self.owner.mapping_changed(self.owner.controls[value], keep_targets=True)
        self.owner.report('[Upgrade edit 2/2] Target draft saved; review the mapping again', 2, 2)
        self.status.setText('Target draft saved. Review this technique and mapping again.')
        self.refresh()

    def open_page(self, index):
        url = self.urls[index]
        if not url or self.owner.worker and self.owner.worker.isRunning():
            return
        self.owner.set_review_enabled(False)
        self.owner.start_task(lambda notify: checked_version_page(url, notify), self.open_verified)

    def open_verified(self, url):
        if self.owner.closing:
            return
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)):
            self.owner.report('The version page was verified, but no browser could open it.', 1, 1)
