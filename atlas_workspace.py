"""Independent ATLAS navigation and selection inside a Workplace. Flow: README.md."""
import html

from PySide6 import QtCore, QtGui, QtWidgets

from atlas_catalog import DOMAIN
from atlas_matrix import AtlasMatrix, KEY, TACTIC, populate, sync_checks
from attack_catalog import external_id, catalog_identity
from attack_matrix import matrix_columns
from navigator_dialogs import AnnotationDialog
from ttp_documents import TTPDocument, technique_comments
from ttp_selection import change_cells, phases


class AtlasWorkspace:
    def init_atlas_workspace(self):
        self.atlas_catalog = None
        self.atlas_sidebar_signature = None
        self.atlas_matrix = AtlasMatrix()
        self.atlas_detail_bar = QtWidgets.QWidget()
        detail_layout = QtWidgets.QHBoxLayout(self.atlas_detail_bar)
        for label, callback in [('Add ATLAS technique', lambda:self.choose_atlas_technique(self.atlas_detail_key, '', True)),
                                ('Remove ATLAS technique', lambda:self.choose_atlas_technique(self.atlas_detail_key, '', False)),
                                ('Edit ATLAS annotation…', lambda:self.edit_atlas_annotation(self.atlas_detail_key))]:
            button = QtWidgets.QPushButton(label)
            button.clicked.connect(callback)
            detail_layout.addWidget(button)
        detail_layout.addStretch()
        self.details_page.layout().insertWidget(1, self.atlas_detail_bar)
        self.atlas_detail_bar.hide()
        self.details.textChanged.connect(self.atlas_detail_bar.hide)
        self.atlas_source_context = None
        self.atlas_source_bar = QtWidgets.QWidget()
        source_layout = QtWidgets.QHBoxLayout(self.atlas_source_bar)
        self.atlas_add_all_button = QtWidgets.QPushButton('Add all ATLAS TTPs')
        self.atlas_add_all_button.setAccessibleName('Add all related ATLAS TTPs to current Workplace')
        self.atlas_add_all_button.clicked.connect(self.add_all_atlas_source_ttps)
        source_layout.addWidget(self.atlas_add_all_button)
        self.atlas_remove_all_button = QtWidgets.QPushButton('Remove all ATLAS TTPs')
        self.atlas_remove_all_button.setAccessibleName('Remove all related ATLAS TTPs from current Workplace')
        self.atlas_remove_all_button.clicked.connect(self.remove_all_atlas_source_ttps)
        source_layout.addWidget(self.atlas_remove_all_button)
        self.atlas_source_count = QtWidgets.QLabel()
        source_layout.addWidget(self.atlas_source_count)
        source_layout.addStretch()
        self.details_page.layout().insertWidget(1, self.atlas_source_bar)
        self.hide_atlas_source_actions()
        self.details.textChanged.connect(self.hide_atlas_source_actions)
        self.atlas_matrix.progress.connect(self.operation_report)
        self.atlas_matrix.selection_requested.connect(self.choose_atlas_technique)
        self.atlas_matrix.detail_requested.connect(self.show_atlas_record)
        self.atlas_matrix_tab_index = self.tabs.addTab(self.atlas_matrix, 'ATLAS Matrix')
        self.tabs.setTabEnabled(self.atlas_matrix_tab_index, False)
        self.tabs.tabBar().setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.tabBar().customContextMenuRequested.connect(self.matrix_tab_menu)

        self.atlas_sidebar = QtWidgets.QTreeWidget()
        self.atlas_sidebar.setHeaderHidden(True)
        self.atlas_sidebar.setIndentation(16)
        self.atlas_sidebar.setAccessibleName('ATLAS explorer')
        self.explorer_stack.addWidget(self.atlas_sidebar)
        self.atlas_sidebar.itemChanged.connect(lambda item, column:self.choose_atlas_technique(
            item.data(0, KEY), item.data(0, TACTIC), item.checkState(0) == QtCore.Qt.CheckState.Checked)
            if item.data(0, KEY) and item.flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable else None)
        self.atlas_sidebar.itemClicked.connect(lambda item, column:self.show_atlas_record(item.data(0, KEY))
            if item.data(0, KEY) else None)
        self.workplace_tree = QtWidgets.QTreeWidget()
        self.workplace_tree.setHeaderHidden(True)
        self.workplace_tree.setAccessibleName('Workplace selected techniques')
        self.workplace_tree.itemClicked.connect(self.show_workplace_item)
        self.explorer_stack.addWidget(self.workplace_tree)
        self.atlas_search = QtWidgets.QLineEdit()
        self.atlas_search.setPlaceholderText('Search ATLAS name or ID…')
        self.atlas_search.setClearButtonEnabled(True)
        self.atlas_search.hide()
        self.sidebar.layout().insertWidget(1, self.atlas_search)
        self.atlas_search.textChanged.connect(self.rebuild_atlas_sidebar)
        self.atlas_open_button = QtWidgets.QPushButton('Open ATLAS Matrix')
        self.atlas_open_button.clicked.connect(self.open_atlas_matrix)
        self.atlas_open_button.hide()
        self.sidebar.layout().insertWidget(2, self.atlas_open_button)

        layout = self.selection_page.layout()
        matrix_buttons = QtWidgets.QHBoxLayout()
        self.open_attack_matrix_button = QtWidgets.QToolButton()
        self.open_attack_matrix_button.setText('Open ATT&CK Matrix')
        self.open_attack_matrix_button.clicked.connect(self.open_matrix)
        self.open_atlas_matrix_button = QtWidgets.QToolButton()
        self.open_atlas_matrix_button.setText('Open ATLAS Matrix')
        self.open_atlas_matrix_button.clicked.connect(self.open_atlas_matrix)
        matrix_buttons.addWidget(self.open_attack_matrix_button)
        matrix_buttons.addWidget(self.open_atlas_matrix_button)
        matrix_buttons.addStretch()
        layout.insertLayout(1, matrix_buttons)
        self.attack_selection_toggle = QtWidgets.QToolButton()
        self.attack_selection_toggle.setCheckable(True)
        self.attack_selection_toggle.setChecked(True)
        self.attack_selection_toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.attack_selection_toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow)
        self.attack_selection_toggle.setText('ATT&CK (0)')
        layout.insertWidget(layout.indexOf(self.selection_list), self.attack_selection_toggle)
        self.atlas_selection_toggle = QtWidgets.QToolButton()
        self.atlas_selection_toggle.setText('ATLAS TTP (0)')
        self.atlas_selection_toggle.setCheckable(True)
        self.atlas_selection_toggle.setChecked(True)
        self.atlas_selection_toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.atlas_selection_toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow)
        self.atlas_selection_list = QtWidgets.QListWidget()
        self.atlas_selection_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.atlas_selection_list.setAccessibleName('Selected ATLAS techniques')
        self.atlas_selection_list.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.atlas_selection_list.customContextMenuRequested.connect(self.atlas_selected_menu)
        index = layout.indexOf(self.selection_list) + 1
        layout.insertWidget(index, self.atlas_selection_toggle)
        layout.insertWidget(index + 1, self.atlas_selection_list)
        layout.setStretch(layout.indexOf(self.selection_list), 1)
        layout.setStretch(layout.indexOf(self.atlas_selection_list), 1)
        for toggle, listing in ((self.attack_selection_toggle, self.selection_list),
                                (self.atlas_selection_toggle, self.atlas_selection_list)):
            toggle.toggled.connect(lambda checked, t=toggle, w=listing:self.toggle_selection_group(t,w,checked))
        self.selection_page.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.selection_page.customContextMenuRequested.connect(self.workplace_menu)
        self.selection_annotation_button.setText('Edit ATT&CK annotation…')
        self.selection_batch_button.setText('Batch edit included ATT&CK TTPs…')
        for button in self.selection_page.findChildren(QtWidgets.QPushButton):
            if button.text() == 'Clear selection':
                button.setText('Clear ATT&CK selection')

    @property
    def current_atlas_catalog(self):
        doc = self.current_document
        return doc.atlas_document.catalog if doc and doc.atlas_document else self.atlas_catalog

    def set_atlas_catalog(self, catalog):
        self.atlas_catalog = catalog
        self.tabs.setTabEnabled(self.atlas_matrix_tab_index, True)

    def atlas_document(self, create=False):
        document = self.current_document
        if not document:
            return None
        if create and document.atlas_document is None and self.atlas_catalog:
            document.atlas_document = TTPDocument('ATLAS', self.atlas_catalog)
        return document.atlas_document

    def toggle_selection_group(self, toggle, listing, checked):
        toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow if checked else QtCore.Qt.ArrowType.RightArrow)
        listing.setVisible(checked)
        self.schedule_session_checkpoint()

    def ensure_attack_matrix_tab(self, reveal=True):
        if reveal:
            self.tabs.setTabVisible(self.matrix_tab_index, True)

    def open_atlas_matrix(self):
        catalog = self.current_atlas_catalog
        if not self.loaded_ok or not catalog:
            return
        self.operation_report('Input files: None; output files: None (ATLAS matrix view in memory)')
        self.operation_report('[ATLAS view 1/2] Opening matrix; selection retained', 0, 2)
        self.tabs.blockSignals(True)
        self.tabs.setTabVisible(self.atlas_matrix_tab_index, True)
        self.atlas_matrix.set_document(catalog, self.atlas_document())
        self.show_document_page()
        self.tabs.setCurrentIndex(self.atlas_matrix_tab_index)
        self.tabs.blockSignals(False)
        self.operation_report('[ATLAS view 2/2] Ready', 2, 2)
        self.schedule_session_checkpoint()

    def close_matrix_view(self, framework):
        index = self.matrix_tab_index if framework == 'attack' else self.atlas_matrix_tab_index
        self.operation_report('Input files: None; output files: None (matrix visibility in memory)')
        self.operation_report('[Matrix view 1/2] Closing ' + framework.upper() + ' matrix', 0, 2)
        self.tabs.blockSignals(True)
        if self.tabs.currentIndex() == index:
            self.tabs.setCurrentIndex(self.selection_tab_index)
        self.tabs.setTabVisible(index, False)
        self.tabs.blockSignals(False)
        self.show_document_page()
        self.operation_report('[Matrix view 2/2] Closed; all selected techniques and annotations retained', 2, 2)
        self.schedule_session_checkpoint()

    def add_matrix_open_actions(self, menu):
        menu.addAction('Open ATT&CK Matrix', self.open_matrix)
        action = menu.addAction('Open ATLAS Matrix', self.open_atlas_matrix)
        action.setEnabled(bool(self.current_atlas_catalog))

    def matrix_tab_menu(self, position):
        index = self.tabs.tabBar().tabAt(position)
        menu = QtWidgets.QMenu(self.tabs)
        if index in (self.matrix_tab_index, self.atlas_matrix_tab_index):
            framework = 'attack' if index == self.matrix_tab_index else 'atlas'
            menu.addAction('Close Matrix', lambda:self.close_matrix_view(framework))
        else:
            self.add_matrix_open_actions(menu)
        self.show_workplace_menu(menu, self.tabs.tabBar().mapToGlobal(position))

    def show_workplace_menu(self, menu, position):
        self.workplace_context_menu = menu
        menu.aboutToHide.connect(menu.deleteLater)
        menu.popup(position)

    def workplace_menu(self, position):
        menu = QtWidgets.QMenu(self.selection_page)
        self.add_matrix_open_actions(menu)
        self.show_workplace_menu(menu, self.selection_page.mapToGlobal(position))

    def switch_atlas_category(self, category):
        self.active_category = category
        self.navigation_buttons[category].setChecked(True)
        self.sidebar.setVisible(True)
        for widget in (self.ttp_search, self.search, self.ttp_search_fields_button,
                       self.source_search_fields_button, self.source_results_bar, self.matrix_button):
            widget.hide()
        workplace = category == 'Workplace'
        self.atlas_search.setVisible(not workplace)
        self.atlas_open_button.setVisible(not workplace)
        self.sidebar_title.setText(category.upper())
        self.explorer_stack.setCurrentWidget(self.workplace_tree if workplace else self.atlas_sidebar)
        if workplace:
            self.show_document_page()
            self.tabs.setCurrentIndex(self.selection_tab_index)
        else:
            self.rebuild_atlas_sidebar()
            self.open_details_page(category + ' Details')
            self.details.setHtml('<h1>' + html.escape(category) + '</h1><p>Select an entry in the sidebar.</p>')
        self.refresh_atlas_workspace()
        self.schedule_session_checkpoint()

    def restore_attack_sidebar(self):
        self.atlas_search.hide()
        self.atlas_open_button.hide()

    def rebuild_atlas_sidebar(self, *_):
        catalog = self.current_atlas_catalog
        category = self.active_category
        if not catalog or not category.startswith('ATLAS'):
            return
        self.atlas_sidebar_signature = catalog_identity(catalog), category
        self.atlas_sidebar.blockSignals(True)
        self.atlas_sidebar.clear()
        query = self.atlas_search.text().strip().casefold()
        if category == 'ATLAS TTP':
            for slug, rows in matrix_columns(catalog):
                branch = QtWidgets.QTreeWidgetItem([external_id(catalog.tactics[slug]) + '  ' + catalog.tactics[slug]['name']])
                branch.setData(0, KEY, catalog.tactics[slug]['id'])
                branch.setFlags(branch.flags() & ~QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                temporary = QtWidgets.QTreeWidget()
                populate(temporary, catalog, slug, rows, query)
                while temporary.topLevelItemCount():
                    branch.addChild(temporary.takeTopLevelItem(0))
                temporary.deleteLater()
                if branch.childCount():
                    self.atlas_sidebar.addTopLevelItem(branch)
                    branch.setExpanded(bool(query))
        else:
            kind = 'course-of-action' if category == 'ATLAS Mitigations' else 'x-atlas-case-study'
            objects = catalog.objects_by_domain[DOMAIN]
            for obj in sorted(objects.values(), key=external_id):
                if obj.get('type') != kind:
                    continue
                label = external_id(obj) + '  ' + obj['name']
                if query and query not in (label + ' ' + obj.get('description', '')).casefold():
                    continue
                node = QtWidgets.QTreeWidgetItem([label])
                node.setData(0, KEY, obj['id'])
                node.setFlags(node.flags() & ~QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                self.atlas_sidebar.addTopLevelItem(node)
        self.atlas_sidebar.blockSignals(False)
        sync_checks(self.atlas_sidebar, self.atlas_document())

    def choose_atlas_technique(self, key, tactic, checked):
        if not self.loaded_ok or not self.current_atlas_catalog or key not in self.current_atlas_catalog.records:
            return
        doc = self.atlas_document(create=True)
        slugs = phases(doc.catalog, key) if doc.selection_preferences['across_tactics'] or not tactic else {tactic}
        self.operation_report('Input files: None; output files: None (ATLAS selection in memory)')
        self.operation_report('[ATLAS selection 1/2] Updating selected techniques', 0, 2)
        change_cells(doc, {(key, slug) for slug in slugs}, 'add' if checked else 'remove', expand=False)
        self.update_document_labels()
        self.operation_report('[ATLAS selection 2/2] Workplace updated; ATT&CK selection retained', 2, 2)

    def refresh_atlas_workspace(self):
        if not self.current_document:
            return
        doc, catalog = self.atlas_document(), self.current_atlas_catalog
        count = len(doc.selected) if doc else 0
        self.attack_selection_toggle.setText(f'ATT&CK ({len(self.selected)})')
        self.atlas_selection_toggle.setText(f'ATLAS TTP ({count})')
        previous = self.atlas_selection_list.currentItem()
        previous = previous.data(KEY) if previous else None
        highlighted = {item.data(KEY) for item in self.atlas_selection_list.selectedItems()}
        if self.atlas_selection_list.property('selectionOwner') != self.current_document.document_id:
            previous, highlighted = None, set()
        self.atlas_selection_list.setProperty('selectionOwner', self.current_document.document_id)
        self.atlas_selection_list.clear()
        if doc:
            for key in sorted(doc.selected, key=lambda k:external_id(doc.catalog.records[k])):
                obj = doc.catalog.records[key]
                comment, scoped = technique_comments(doc, key)
                item = QtWidgets.QListWidgetItem(f'{external_id(obj)}  {obj["name"]}' + ('\n    ' + comment if comment else ''))
                item.setData(KEY, key)
                item.setIcon(self.navigation_buttons['ATLAS TTP'].icon())
                self.atlas_selection_list.addItem(item)
                item.setSelected(key in highlighted)
                if key == previous:
                    self.atlas_selection_list.setCurrentItem(item, QtCore.QItemSelectionModel.SelectionFlag.NoUpdate)
        self.tabs.setTabText(self.selection_tab_index, f'Selected Techniques ({len(self.selected) + count})')
        self.selection_summary.setText(f'{self.current_document.name} · Workplace · ATT&CK {len(self.selected)} · ATLAS {count}')
        self.open_atlas_matrix_button.setEnabled(bool(catalog) and self.loaded_ok)
        self.tabs.setTabEnabled(self.atlas_matrix_tab_index, bool(catalog) and self.loaded_ok)
        if catalog:
            self.atlas_matrix.set_document(catalog, doc)
            if self.active_category.startswith('ATLAS'):
                signature = catalog_identity(catalog), self.active_category
                if signature != self.atlas_sidebar_signature:
                    self.rebuild_atlas_sidebar()
                sync_checks(self.atlas_sidebar, doc)
                self.summary.setText(f'ATLAS {catalog.version} · {self.atlas_sidebar.topLevelItemCount()} entries')
        self.workplace_tree.clear()
        for label, document, framework in [('ATT&CK', self.current_document, 'attack'), ('ATLAS TTP', doc, 'atlas')]:
            branch = QtWidgets.QTreeWidgetItem([f'{label} ({len(document.selected) if document else 0})'])
            self.workplace_tree.addTopLevelItem(branch)
            if document:
                for key in sorted(document.selected, key=lambda k:external_id(document.catalog.records[k])):
                    obj = document.catalog.records[key]
                    item = QtWidgets.QTreeWidgetItem([external_id(obj) + '  ' + obj['name']])
                    item.setData(0, KEY, key)
                    item.setData(0, TACTIC, framework)
                    branch.addChild(item)
            branch.setExpanded(True)
        if self.active_category == 'Workplace':
            self.summary.setText(f'ATT&CK {len(self.selected)} · ATLAS {count}')
        if hasattr(self, 'refresh_car_workspace'):
            self.refresh_car_workspace()

    def show_workplace_item(self, item, column):
        key = item.data(0, KEY)
        if key:
            if item.data(0, TACTIC) == 'atlas':
                self.show_atlas_record(key)
            else:
                self.show_record(key)

    def atlas_selected_menu(self, position):
        if not self.loaded_ok:
            return
        menu = QtWidgets.QMenu(self.atlas_selection_list)
        self.add_matrix_open_actions(menu)
        item = self.atlas_selection_list.itemAt(position)
        if item:
            self.atlas_selection_list.setCurrentItem(item, QtCore.QItemSelectionModel.SelectionFlag.NoUpdate
                if item.isSelected() else QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect)
            key = item.data(KEY)
            menu.addSeparator()
            menu.addAction('View TTP information', lambda:self.show_atlas_record(key))
            menu.addAction('Edit ATLAS annotation…', lambda:self.edit_atlas_annotation(key))
            menu.addAction('Remove ATLAS technique', lambda:self.choose_atlas_technique(key, '', False))
        keys = {row.data(KEY) for row in self.atlas_selection_list.selectedItems()}
        owner = self.atlas_document()
        remove = menu.addAction('Remove selected TTPs', lambda:self.remove_highlighted_ttps('atlas', keys, owner))
        remove.setEnabled(bool(keys))
        if self.atlas_document() and self.atlas_document().selected:
            menu.addAction('Clear ATLAS selection', self.clear_atlas_selection)
        self.show_workplace_menu(menu, self.atlas_selection_list.viewport().mapToGlobal(position))

    def clear_atlas_selection(self):
        doc = self.atlas_document()
        if doc:
            self.operation_report('Input files: None; output files: None (ATLAS selection in memory)')
            self.operation_report('[ATLAS selection 1/2] Clearing selected ATLAS techniques', 0, 2)
            doc.selected.clear()
            doc.selection_scopes.clear()
            self.update_document_labels()
            self.operation_report('[ATLAS selection 2/2] Cleared ATLAS selection; annotations retained', 2, 2)

    def edit_atlas_annotation(self, key):
        doc = self.atlas_document()
        if doc is None and self.current_atlas_catalog:
            doc = TTPDocument('ATLAS', self.current_atlas_catalog)
        if not doc or key not in doc.catalog.records:
            return
        self.operation_report('Input files: None; output files: None (ATLAS annotations in memory)')
        self.operation_report('[ATLAS annotation 1/2] Editing annotation', 0, 2)
        dialog = AnnotationDialog(doc, key, self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.current_document.atlas_document = doc
            doc.navigator_layer = dialog.result_layer
            self.choose_atlas_technique(key, dialog.scope.currentData() or '', dialog.include.isChecked())
            self.operation_report('[ATLAS annotation 2/2] Saved in Workplace', 2, 2)
        else:
            self.operation_report('[ATLAS annotation 2/2] Cancelled', 2, 2)

    def show_atlas_record(self, key):
        catalog = self.current_atlas_catalog
        if not catalog or key not in catalog.objects_by_domain[DOMAIN]:
            return
        obj = catalog.objects_by_domain[DOMAIN][key]
        native = obj.get('x_atlas_native', {})
        self.open_details_page('ATLAS Details')
        self.crumb.setText('ATLAS ' + catalog.version + ' / ' + external_id(obj))
        esc = lambda value:html.escape(str(value))
        parts = [f'<p>ATLAS {esc(catalog.version)} · {esc(external_id(obj))}</p>',
                 f'<h1>{esc(obj["name"])}</h1>', '<h2>Description</h2>',
                 '<p>' + esc(obj.get('description', '')).replace('\n', '<br>') + '</p>']
        for field in ('maturity', 'platforms', 'type', 'actor', 'target', 'date', 'date-granularity',
                      'lifecycle-phases', 'categories', 'created-date', 'modified-date'):
            if field in native:
                value = ', '.join(native[field]) if isinstance(native[field], list) else native[field]
                parts.append(f'<p><b>{esc(field)}</b>: {esc(value)}</p>')
        reference = native.get('attack-reference')
        if reference:
            parts.append(f'<p>Official ATT&CK reference: <a href="{esc(reference["url"])}">{esc(reference["id"])}</a></p>')
        for ref in obj.get('external_references', []):
            url = ref.get('url', '')
            if url.startswith(('https://', 'http://')):
                parts.append(f'<p><a href="{esc(url)}">{esc(ref.get("description") or ref.get("external_id") or url)}</a></p>')
        edges = obj.get('x_atlas_relationships', {})
        for kind, title in [('mitigates', 'Techniques addressed'), ('employs', 'Case study steps')]:
            if edges.get(kind):
                parts.append('<h2>' + title + '</h2>')
                for edge in sorted(edges[kind], key=lambda e:e.get('step-id', e['target'])):
                    target = edge['target']
                    parts.append(f'<p><b>{esc(edge.get("step-id", ""))}</b> <a href="atlas:{esc(target)}">{esc(target)}</a>'
                        + (f' · {esc(edge["tactic"])}' if edge.get('tactic') else '') + '<br>'
                        + esc(edge.get('description', '')).replace('\n', '<br>')
                        + ('<br>Leads to: ' + esc(', '.join(edge['leads-to'])) if edge.get('leads-to') else '') + '</p>')
        self.details.setHtml(''.join(parts))
        self.details.set_copy_content(obj['name'], obj.get('description', ''))
        if obj['type'] == 'attack-pattern':
            self.atlas_detail_key = key
            self.atlas_detail_bar.show()
        else:
            self.atlas_detail_bar.hide()
        if obj['type'] in ('course-of-action', 'x-atlas-case-study'):
            self.atlas_source_context = (catalog_identity(catalog), key)
            keys = self.atlas_source_techniques(catalog, key)
            self.atlas_source_count.setText(f'{len(keys)} related ATLAS TTPs')
            self.atlas_add_all_button.setEnabled(bool(keys) and self.loaded_ok)
            self.atlas_remove_all_button.setEnabled(bool(keys) and self.loaded_ok)
            self.atlas_source_bar.show()
        self.object_copy_bar.set_context(catalog, DOMAIN, key)

    def hide_atlas_source_actions(self):
        self.atlas_source_context = None
        self.atlas_source_bar.hide()

    @staticmethod
    def atlas_source_techniques(catalog, key):
        obj = catalog.objects_by_domain[DOMAIN].get(key, {})
        kind = {'course-of-action': 'mitigates', 'x-atlas-case-study': 'employs'}.get(obj.get('type'))
        if kind is None:
            return set()
        by_id = {external_id(record): identity for identity, record in catalog.records.items()}
        return {by_id[edge['target']] for edge in obj.get('x_atlas_relationships', {}).get(kind, [])
                if edge.get('source') == external_id(obj) and edge.get('relationship-type') == kind
                and edge.get('target') in by_id}

    def add_all_atlas_source_ttps(self):
        self.change_all_atlas_source_ttps('add')

    def remove_all_atlas_source_ttps(self):
        self.change_all_atlas_source_ttps('remove')

    def change_all_atlas_source_ttps(self, action):
        catalog = self.current_atlas_catalog
        if not self.loaded_ok or not catalog or not self.current_document or not self.atlas_source_context:
            return
        identity, key = self.atlas_source_context
        if catalog_identity(catalog) != identity:
            self.hide_atlas_source_actions()
            return
        self.operation_report('Input files: None (verified ATLAS relationships in memory); output files: None')
        self.operation_report('[ATLAS source 1/3] Resolving related techniques', 0, 3)
        keys = self.atlas_source_techniques(catalog, key)
        if not keys:
            self.operation_report('[ATLAS source 3/3] No related ATLAS TTPs; Workplace unchanged', 3, 3)
            return
        doc = self.atlas_document(create=action == 'add')
        if doc is None:
            self.operation_report('[ATLAS source 3/3] No selected ATLAS TTPs; Workplace unchanged', 3, 3)
            return
        if action == 'add':
            changed = len(keys - doc.selected)
            self.operation_report('[ATLAS source 2/3] Including related TTPs; repeated case steps deduplicated', 1, 3)
            doc.selected.update(keys)
        else:
            changed = len(keys & doc.selected)
            self.operation_report('[ATLAS source 2/3] Removing only related ATLAS selections; annotations retained', 1, 3)
            doc.selected.difference_update(keys)
        for technique in keys:
            doc.selection_scopes.pop(technique, None)
        self.update_document_labels()
        message = (f'Added {changed} TTPs; {len(keys)} related TTPs included' if action == 'add' else
                   f'Removed {changed} related ATLAS TTPs; other selections and all annotations retained')
        self.operation_report('[ATLAS source 3/3] ' + message, 3, 3)

    def open_atlas_link(self, url):
        if url.scheme() != 'atlas':
            return False
        key = next((key for key,obj in self.current_atlas_catalog.objects_by_domain[DOMAIN].items()
                    if external_id(obj) == url.path()), None)
        if key:
            self.show_atlas_record(key)
        return True
