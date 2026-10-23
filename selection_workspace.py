"""Native selection preferences, extended TTP search and source batches. Flow: README.md."""
from PySide6 import QtCore, QtGui, QtWidgets
from attack_catalog import tactic_phases, external_id
from ttp_search import SEARCH_FIELDS, matches, search_index, source_search_text
from navigator_preferences import SOURCE_FIELDS, SOURCE_KEY, source_fields
from ttp_selection import selected_cells, expand_cells, change_cells, is_selected
from ttp_operations import is_annotated, effective_row
from ttp_sources import SOURCE_TYPES, source_cells
from source_preview import SourceResultHover


class SelectionWorkspace:
    def remove_highlighted_ttps(self, framework, keys, owner):
        """Remove exact highlighted IDs; family/visibility preferences do not widen the set."""
        if not self.loaded_ok or framework not in ('attack', 'atlas'):
            return
        target = self.current_document if framework == 'attack' else self.atlas_document()
        if target is None or target is not owner:
            return
        self.operation_report('Input files: None; output files: None (highlighted TTP selections in memory)')
        self.operation_report('[Remove selected 1/3] Resolving highlighted ' + framework.upper() + ' TTPs', 0, 3)
        keys = set(keys) & target.selected
        self.operation_report('[Remove selected 2/3] Cancelling inclusion; all annotations retained', 1, 3)
        target.selected.difference_update(keys)
        for key in keys:
            target.selection_scopes.pop(key, None)
        if framework == 'attack':
            self.selected = set(target.selected)
            self.refresh_selection()
        else:
            self.update_document_labels()
        self.operation_report(f'[Remove selected 3/3] Removed {len(keys)} TTPs; other selections and annotations retained', 3, 3)

    def init_selection_tools(self, role_id, role_context, role_search):
        self.selection_roles = role_id, role_context, role_search
        self.selection_pref_actions = {}
        pref_menu = QtWidgets.QMenu('Selection behavior', self)
        for key, text in [('across_tactics','Select techniques across tactics'), ('with_family','Select parent, children and siblings together'),
                          ('visible_only','Select visible techniques only')]:
            action = pref_menu.addAction(text)
            action.setCheckable(True)
            action.toggled.connect(lambda value, field=key:self.change_selection_preference(field,value))
            self.selection_pref_actions[key] = action
        self.selection_pref_button = QtWidgets.QToolButton()
        self.selection_pref_button.setText('Selection behavior…')
        self.selection_pref_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.selection_pref_button.setMenu(pref_menu)
        self.navigator_menu.addMenu(pref_menu)
        self.search_field_actions = {}
        search_menu = QtWidgets.QMenu('Search fields', self)
        labels = {'name':'Name', 'id':'ATT&CK ID', 'description':'Description', 'data_sources':'Data Sources / Components / Log Sources',
                  'detection_strategies':'Detection Strategy · Name / ID / Description'}
        for field in SEARCH_FIELDS:
            action = search_menu.addAction(labels[field])
            action.setCheckable(True)
            action.toggled.connect(lambda checked, field=field:self.change_search_field(field,checked))
            self.search_field_actions[field] = action
        self.ttp_search_fields_button = QtWidgets.QToolButton()
        self.ttp_search_fields_button.setText('TTP search fields…')
        self.ttp_search_fields_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.ttp_search_fields_button.setMenu(search_menu)
        sidebar_layout = self.ttp_search.parentWidget().layout()
        sidebar_layout.insertWidget(sidebar_layout.indexOf(self.ttp_search)+1, self.ttp_search_fields_button)
        self.matrix_search_fields_button = QtWidgets.QToolButton()
        self.matrix_search_fields_button.setText('Search fields…')
        self.matrix_search_fields_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.matrix_search_fields_button.setMenu(search_menu)
        tools = QtWidgets.QHBoxLayout()
        tools.addWidget(self.selection_pref_button)
        tools.addWidget(self.matrix_search_fields_button)
        self.source_field_actions = {}
        source_menu = QtWidgets.QMenu('Source search fields', self)
        for field in SOURCE_FIELDS:
            action = source_menu.addAction(labels[field])
            action.setCheckable(True)
            action.toggled.connect(lambda checked, field=field:self.change_source_search_field(field, checked))
            self.source_field_actions[field] = action
        self.source_search_fields_button = QtWidgets.QToolButton()
        self.source_search_fields_button.setText('Source search fields…')
        self.source_search_fields_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.source_search_fields_button.setMenu(source_menu)
        sidebar_layout.insertWidget(sidebar_layout.indexOf(self.search)+1, self.source_search_fields_button)
        self.source_search_fields_button.hide()
        self.source_results_bar = QtWidgets.QWidget()
        result_layout = QtWidgets.QVBoxLayout(self.source_results_bar)
        result_layout.setContentsMargins(0,0,0,0)
        self.source_results_summary = QtWidgets.QLabel()
        self.source_results_summary.setWordWrap(True)
        result_layout.addWidget(self.source_results_summary)
        self.source_matrix_button = QtWidgets.QPushButton('Show matrix preview')
        self.source_matrix_button.setToolTip('Keep the source sidebar open; hover its results to preview the matrix without selecting TTPs.')
        self.source_matrix_button.clicked.connect(self.show_source_matrix)
        result_layout.addWidget(self.source_matrix_button)
        result_buttons = QtWidgets.QHBoxLayout()
        self.add_library_results_button = QtWidgets.QPushButton('Add all results')
        self.remove_library_results_button = QtWidgets.QPushButton('Remove all results')
        self.add_library_results_button.clicked.connect(lambda:self.change_library_results('add'))
        self.remove_library_results_button.clicked.connect(lambda:self.change_library_results('remove'))
        result_buttons.addWidget(self.add_library_results_button)
        result_buttons.addWidget(self.remove_library_results_button)
        result_layout.addLayout(result_buttons)
        sidebar_layout.insertWidget(sidebar_layout.indexOf(self.source_search_fields_button)+1,self.source_results_bar)
        self.source_results_bar.hide()
        self.library_source_hover = SourceResultHover(self.library_tree,self.preview_library_source,self.matrix_view.clear_source_preview)
        self.search.textChanged.connect(lambda *_:self.matrix_view.clear_source_preview())
        self.matrix_source_fields_button = QtWidgets.QToolButton()
        self.matrix_source_fields_button.setText('Source search fields…')
        self.matrix_source_fields_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.matrix_source_fields_button.setMenu(source_menu)
        tools.addWidget(self.matrix_source_fields_button)
        tools.addStretch()
        self.matrix_view.controls_layout.insertLayout(4, tools)
        self.sync_selection_tools()

    def sync_selection_tools(self):
        if not hasattr(self,'selection_pref_actions'):
            return
        document = self.current_document
        for field, action in self.selection_pref_actions.items():
            action.blockSignals(True)
            action.setChecked(bool(document and document.selection_preferences.get(field,False)))
            action.setEnabled(bool(document) and self.loaded_ok)
            action.blockSignals(False)
        for field, action in self.search_field_actions.items():
            action.blockSignals(True)
            action.setChecked(bool(document and field in document.search_fields))
            action.setEnabled(bool(document) and self.loaded_ok)
            action.blockSignals(False)
        self.selection_pref_button.setEnabled(bool(document) and self.loaded_ok)
        self.ttp_search_fields_button.setEnabled(bool(document) and self.loaded_ok)
        self.matrix_search_fields_button.setEnabled(bool(document) and self.loaded_ok)
        if document:
            hint = 'Literal, case-insensitive search in: ' + ', '.join(document.search_fields)
            self.ttp_search.setToolTip(hint)
            self.matrix_view.search.setToolTip(hint)
        fields = source_fields(document.navigator_layer if document else {})
        for field, action in self.source_field_actions.items():
            action.blockSignals(True)
            action.setChecked(field in fields)
            action.setEnabled(bool(document) and self.loaded_ok)
            action.blockSignals(False)
        self.source_search_fields_button.setEnabled(bool(document) and self.loaded_ok)
        self.matrix_source_fields_button.setEnabled(bool(document) and self.loaded_ok)
        if document:
            self.refresh_source_search_roles(fields)
        self.refresh_source_result_tools()

    def library_result_keys(self):
        if not self.loaded_ok or not self.catalog or self.active_category == 'TTP': return set()
        _,context_role,search_role = self.selection_roles
        query = self.search.text().strip().casefold()
        return {item.data(context_role)[2] for item in self.library_items.get(self.active_category,[])
                if item.data(context_role)[0] == self.catalog.domain and item.data(context_role)[1] in SOURCE_TYPES
                and (not query or query in (item.data(search_role) or '').casefold())}

    def refresh_source_result_tools(self):
        keys = self.library_result_keys()
        cells = source_cells(self.catalog,keys) if self.catalog else set()
        domain = self.catalog.domain if self.catalog else 'No catalog'
        self.source_results_summary.setText(f'{domain}: {len(keys)} matching sources · {len({key for key,slug in cells})} mapped TTPs · {len(cells)} tactic occurrences')
        self.source_results_summary.setToolTip('Supported source entries matching the selected search fields in the active document domain. '
            'Other domains and Analytics are excluded. Blank query means all supported entries in this category. '
            'Counts precede family/visibility preferences. Add/Remove applies immediately, preserving annotations.')
        for button in (self.add_library_results_button,self.remove_library_results_button):
            button.setEnabled(bool(cells) and self.loaded_ok)
        self.source_matrix_button.setEnabled(self.loaded_ok and bool(self.current_document))

    def preview_library_source(self,index,owner):
        context = index.data(self.selection_roles[1])
        if (not self.loaded_ok or self.active_category=='TTP' or not context or context[0]!=self.catalog.domain or
                context[1] not in SOURCE_TYPES or not context[2] or context[2] not in self.library_result_keys()):
            self.matrix_view.clear_source_preview()
            return False
        return self.matrix_view.preview_source(self.catalog,context[2],owner)

    def show_source_matrix(self):
        if not self.loaded_ok or not self.current_document: return
        self.operation_report('Input files: None; output files: None (source sidebar / matrix view in memory)')
        self.operation_report('[Source Matrix 1/2] Opening matrix while retaining the source category/query',0,2)
        blocked = self.tabs.blockSignals(True)
        try:
            self.matrix_view.set_catalog(self.catalog,self.selected)
            self.refresh_layer_appearance()
            self.show_document_page()
            self.tabs.setCurrentIndex(self.matrix_tab_index)
        finally:
            self.tabs.blockSignals(blocked)
        self.schedule_session_checkpoint()
        self.operation_report('[Source Matrix 2/2] Opened; hover source results once matrix columns are ready',2,2)

    def change_library_results(self,action):
        return self.change_sources_ttps(self.catalog,self.library_result_keys(),action)

    def refresh_source_search_roles(self, fields):
        signature = (id(self.catalog), tuple(fields))
        if getattr(self,'source_role_signature',None) == signature: return
        _, role_context, role_search = self.selection_roles
        previous, self.syncing = self.syncing, True
        try:
            for items in self.library_items.values():
                for item in items:
                    domain, _, key = item.data(role_context)
                    obj = self.catalog.objects_by_domain.get(domain,{}).get(key,{})
                    item.setData(source_search_text(obj,fields=fields),role_search)
            self.matrix_view.source_search_fields = list(fields)
            self.matrix_view.populate_sources()
            self.source_role_signature = signature
        finally:
            self.syncing = previous
        self.search.setToolTip('Literal source search in: '+', '.join(fields)+'; spaces supported.')
        if self.active_category != 'TTP':
            self.search.setPlaceholderText(f"Search {self.active_category.lower()} · {', '.join(fields)}…")

    def change_source_search_field(self, field, checked):
        if not self.loaded_ok or not self.current_document: return
        fields = set(source_fields(self.current_document.navigator_layer))
        fields.add(field) if checked else fields.discard(field)
        if not fields:
            self.sync_selection_tools()
            self.operation_report('[Source Search] Keep at least one field enabled',1,1)
            return
        self.operation_report('Input files: None; output files: None (per-layer source search preference in memory)')
        self.operation_report('[Source Search 1/2] Rebuilding source search fields',0,2)
        ordered = [f for f in SOURCE_FIELDS if f in fields]
        self.current_document.navigator_layer[SOURCE_KEY] = ordered
        self.refresh_source_search_roles(ordered)
        self.apply_search()
        self.update_document_labels()
        self.schedule_session_checkpoint()
        self.operation_report('[Source Search 2/2] Ready; source choices and TTP annotations preserved',2,2)

    def change_selection_preference(self, field, value):
        if not self.loaded_ok or not self.current_document:
            return
        self.operation_report('Input files: None; output files: None (document preference in memory)')
        self.operation_report('[Selection Preference 1/2] Updating future selection behavior',0,2)
        self.current_document.selection_preferences[field] = value
        self.update_document_labels()
        self.schedule_session_checkpoint()
        self.operation_report('[Selection Preference 2/2] Ready; existing choices and annotations unchanged',2,2)

    def change_search_field(self, field, checked):
        if not self.loaded_ok or not self.current_document:
            return
        fields = set(self.current_document.search_fields)
        fields.add(field) if checked else fields.discard(field)
        if not fields:
            self.sync_selection_tools()
            self.operation_report('[TTP Search] Keep at least one search field enabled',1,1)
            return
        self.operation_report('Input files: None; output files: None (search fields in memory)')
        self.operation_report('[Search Fields 1/2] Updating literal search index projection',0,2)
        self.current_document.search_fields = [f for f in SEARCH_FIELDS if f in fields]
        self.matrix_view.search_fields = list(self.current_document.search_fields)
        self.refresh_search_roles(force=True)
        self.apply_ttp_search()
        self.matrix_view.filter_items()
        self.update_document_labels()
        self.operation_report('[Search Fields 2/2] Ready; selections and annotations unchanged',2,2)

    def refresh_search_roles(self, force=False):
        if not self.catalog or not self.current_document:
            return
        signature = (id(self.catalog),tuple(self.current_document.search_fields))
        if not force and getattr(self,'search_role_signature',None)==signature:
            return
        index = search_index(self.catalog, self.operation_report)
        ROLE_ID, _, ROLE_SEARCH = self.selection_roles
        previous, self.syncing = self.syncing, True
        def walk(parent):
            for i in range(parent.rowCount()):
                item = parent.child(i)
                key = item.data(ROLE_ID)
                text = '\n'.join(index[key].get(f,'') for f in self.current_document.search_fields) if key in index else ''
                item.setData(text,ROLE_SEARCH)
                walk(item)
        walk(self.model.invisibleRootItem())
        self.syncing = previous
        self.search_role_signature = signature

    def visible_selection_cells(self, surface='matrix'):
        """Logical visible rows, including rows outside the scrolled viewport."""
        if surface == 'sidebar':
            result = set()
            _, role_context, _ = self.selection_roles
            def walk(parent=QtCore.QModelIndex()):
                for row in range(self.proxy.rowCount(parent)):
                    index = self.proxy.index(row, 0, parent)
                    item = self.model.itemFromIndex(self.proxy.mapToSource(index))
                    context = item.data(role_context)
                    if item.isCheckable() and context:
                        result.add((context[2], context[1]))
                    if self.tree.isExpanded(index):
                        walk(index)
            walk()
            return result
        matrix = self.matrix_view
        return matrix.scope_cells('visible') if matrix.catalog is self.catalog and not matrix.building else set()

    def commit_selection_cells(self, cells, action, annotated=(), expand=True, surface='matrix'):
        document = self.current_document
        document.selected = set(self.selected)
        visible = self.visible_selection_cells(surface) if document.selection_preferences.get('visible_only',False) else None
        changed = change_cells(document,cells,action,annotated,expand,visible)
        self.selected = set(document.selected)
        previous, self.syncing = self.syncing, True
        _, ROLE_CONTEXT, _ = self.selection_roles
        for key, items in self.items_by_id.items():
            for item in items:
                slug = (item.data(ROLE_CONTEXT) or ('',''))[1]
                state = QtCore.Qt.CheckState.Checked if is_selected(self.selected,document.selection_scopes,key,slug) else QtCore.Qt.CheckState.Unchecked
                item.setCheckState(state)
        self.syncing = previous
        self.refresh_selection()
        return changed

    def choose_technique_occurrence(self, key, checked, tactic=None, surface='matrix'):
        if not self.loaded_ok or key not in self.catalog.records:
            return False
        slugs = [tactic] if tactic else tactic_phases(self.catalog.records[key],self.catalog.domain) & self.catalog.tactics.keys()
        self.operation_report('Input files: None; output files: None (selected TTP occurrences in memory)')
        self.operation_report('[Select TTP 1/2] Resolving tactic/family preferences',0,2)
        result = self.commit_selection_cells({(key,slug) for slug in slugs},'add' if checked else 'remove',surface=surface)
        self.operation_report('[Select TTP 2/2] Ready; enabled states and annotations preserved',2,2)
        return result

    def select_mouse_occurrence(self, key, tactic, action):
        if not self.loaded_ok or key not in self.catalog.records or action not in ('replace','add','remove'):
            return False
        self.operation_report('Input files: None; output files: None (mouse selection in memory)')
        self.operation_report('[Mouse Selection 1/2] Applying gesture and family/tactic/visibility preferences',0,2)
        changed = self.commit_selection_cells({(key,tactic)},action)
        self.operation_report('[Mouse Selection 2/2] Ready; annotation and enabled state preserved',2,2)
        return changed

    def change_source_ttps(self, domain, key, action='add'):
        if not self.catalog or domain != self.catalog.domain: return False
        return self.change_sources_ttps(self.catalog,{key},action)

    def change_sources_ttps(self, catalog, source_keys, action='add'):
        if not self.loaded_ok or catalog is not self.catalog or action not in ('add','remove'): return False
        self.operation_report('Input files: None (exact active catalog relationships); output files: None')
        self.operation_report('[Source Selection 1/3] Resolving source result union and explicit mapping paths',0,3)
        try:
            source_keys = set(source_keys)
            cells = source_cells(catalog,source_keys)
        except (ValueError,TypeError) as error:
            self.operation_report('[Source Selection] Cancelled: '+str(error),1,1)
            return False
        if not cells:
            self.operation_report('[Source Selection 3/3] No mapped results; document preserved',3,3)
            return False
        self.operation_report('[Source Selection 2/3] Applying deduplicated targets and selection preferences',1,3)
        before = selected_cells(self.current_document)
        changed = self.commit_selection_cells(cells,action)
        delta = len(before ^ selected_cells(self.current_document))
        self.operation_report(f'[Source Selection 3/3] {len(source_keys)} sources; {len({key for key,slug in cells})} mapped TTPs; '
                              f'{delta} tactic occurrences changed; {len(self.selected)} included TTPs; annotations unchanged',3,3)
        return changed
