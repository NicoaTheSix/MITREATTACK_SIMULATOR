"""CAR navigation and per-Workplace inclusion synchronization. Workflow: README.md."""
from PySide6 import QtCore, QtWidgets
from car_catalog import load_car
from car_documents import change_inclusion, included
from car_mapping import related_analytics, resolve_technique
from car_views import CarBrowser, REF, esc, link
from localization import tr


class CarWorkspace:
    def init_car_workspace(self):
        self.car_catalog = None
        self.car_browser = CarBrowser(self)
        self.workspace.addWidget(self.car_browser)
        self.car_sidebar = QtWidgets.QLabel('CAR Analytics / Data Model / Sensors')
        self.car_sidebar.setWordWrap(True); self.explorer_stack.addWidget(self.car_sidebar)
        self.car_selection_toggle = QtWidgets.QToolButton()
        self.car_selection_toggle.setCheckable(True); self.car_selection_toggle.setChecked(True)
        self.car_selection_toggle.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.car_selection_toggle.setText('CAR Analytics (0)'); self.car_selection_toggle.setArrowType(QtCore.Qt.ArrowType.DownArrow)
        self.car_selection_list = QtWidgets.QListWidget()
        self.car_selection_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.car_selection_list.setAccessibleName('Included CAR Analytics')
        self.car_selection_list.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.car_selection_list.customContextMenuRequested.connect(self.car_selected_menu)
        self.workplace_tree.itemClicked.connect(lambda item,*_:self.car_browser.open_analytic(item.data(0,REF))
            if isinstance(item.data(0,REF),str) and ':' in item.data(0,REF) else None)
        self.car_selection_toggle.toggled.connect(lambda value:self.toggle_selection_group(self.car_selection_toggle,self.car_selection_list,value))
        layout = self.selection_page.layout()
        location = layout.indexOf(self.atlas_selection_list)+1
        layout.insertWidget(location,self.car_selection_toggle); layout.insertWidget(location+1,self.car_selection_list)
        layout.setStretch(location+1,1)

    def set_car_catalog(self,catalog):
        self.car_catalog=catalog; self.car_browser.set_catalog(catalog)
        if self.current_document: self.refresh_car_workspace()

    def car_catalog_failed(self,error):
        self.car_browser.status.setText(tr('CAR snapshot unavailable — saved selections remain available.')+' '+str(error))
        if self.current_document: self.refresh_car_workspace()

    def switch_car_category(self,category):
        self.active_category=category; self.navigation_buttons[category].setChecked(True)
        self.sidebar.setVisible(True); self.explorer_stack.setCurrentWidget(self.car_sidebar)
        self.sidebar_title.setText(category)
        for widget in (self.ttp_search,self.search,self.ttp_search_fields_button,self.source_search_fields_button,
                       self.source_results_bar,self.matrix_button,self.atlas_search,self.atlas_open_button): widget.hide()
        self.car_browser.refresh(); self.car_browser.show_category(category)

    def change_car_inclusion(self,identities,include,owner=None):
        document=self.current_document
        if document is None or not identities: return
        self.operation_report('Input files: None; output files: None (CAR inclusion in current Workplace memory)',0,0)
        self.operation_report('[CAR inclusion 1/3] Resolving exact snapshot IDs and document owner',0,3)
        try:
            change_inclusion(document,self.car_catalog,identities,include,owner)
        except ValueError as error:
            self.operation_report('[CAR inclusion] '+str(error),1,1); return
        self.operation_report('[CAR inclusion 2/3] Inclusion updated; TTPs and annotations retained',1,3)
        self.update_document_labels()
        self.refresh_car_workspace(); self.schedule_session_checkpoint()
        self.operation_report('[CAR inclusion 3/3] Views and recovery state synchronized',3,3)

    def refresh_car_workspace(self):
        if not hasattr(self,'car_selection_list') or not self.current_document: return
        document=self.current_document; entries=included(document)
        old_owner=self.car_selection_list.property('selectionOwner')
        highlighted={i.data(REF) for i in self.car_selection_list.selectedItems()} if old_owner==document.document_id else set()
        self.car_selection_list.clear(); self.car_selection_list.setProperty('selectionOwner',document.document_id)
        for key,entry in sorted(entries.items()):
            resolved=self.car_catalog and entry['source']['dataset_sha256']==self.car_catalog.dataset_id and entry['id'] in self.car_catalog.analytics
            label=entry['id']+'  '+entry['title']+('' if resolved else ' · '+tr('Unresolved snapshot'))
            item=QtWidgets.QListWidgetItem(label); item.setData(REF,key); item.setToolTip(entry['source']['commit'])
            self.car_selection_list.addItem(item); item.setSelected(key in highlighted)
        self.car_selection_toggle.setText(f'CAR Analytics ({len(entries)})')
        attack_count=len(self.selected); atlas=self.atlas_document(); atlas_count=len(atlas.selected) if atlas else 0
        self.tabs.setTabText(self.selection_tab_index,f'Workspace Selections · TTPs {attack_count+atlas_count} · CAR {len(entries)}')
        self.selection_summary.setText(f'{document.name} · ATT&CK {attack_count} · ATLAS {atlas_count} · CAR {len(entries)}')
        # ATLAS refresh rebuilds the Workplace tree first; append an independent CAR branch.
        for index in reversed(range(self.workplace_tree.topLevelItemCount())):
            if self.workplace_tree.topLevelItem(index).data(0,REF)=='car-group': self.workplace_tree.takeTopLevelItem(index)
        root=QtWidgets.QTreeWidgetItem([f'CAR Analytics ({len(entries)})']); root.setData(0,REF,'car-group')
        self.workplace_tree.addTopLevelItem(root); root.setExpanded(True)
        for key,entry in sorted(entries.items()):
            item=QtWidgets.QTreeWidgetItem([entry['id']+'  '+entry['title']]); item.setData(0,REF,key); root.addChild(item)
        self.car_browser.refresh()

    def car_selected_menu(self,position):
        item=self.car_selection_list.itemAt(position)
        if item and not item.isSelected(): self.car_selection_list.clearSelection(); item.setSelected(True)
        keys={i.data(REF) for i in self.car_selection_list.selectedItems()}; owner=self.current_document.document_id
        menu=QtWidgets.QMenu(self.car_selection_list)
        view=menu.addAction('View Analytic information',lambda:self.car_browser.open_analytic(sorted(keys)[0]) if keys and self.current_document.document_id==owner else None)
        remove=menu.addAction('Remove selected Analytics',lambda:self.change_car_inclusion(keys,False,owner))
        view.setEnabled(bool(keys)); remove.setEnabled(bool(keys))
        self.show_workplace_menu(menu,self.car_selection_list.viewport().mapToGlobal(position))

    def open_car_link(self,url):
        if url.scheme()!='car': return False
        self.car_browser.navigate(url.toString()); return True

    def show_car_technique(self,identity):
        resolution=resolve_technique(self.current_document.catalog,identity)
        if resolution['key']:
            self.show_record(resolution['key'])
        else:
            import json
            body='<h1>'+esc(identity)+'</h1><pre>'+esc(json.dumps(resolution,indent=2,ensure_ascii=False))+'</pre>'
            body+='<p><a href="https://attack.mitre.org/techniques/'+esc(identity.replace('.','/'))+'/">'+esc(tr('Open official source'))+'</a></p>'
            self.car_browser.detail_ref=None; self.car_browser.render_detail(body)

    def related_car_html(self,identity):
        if not self.car_catalog: return ''
        matches=related_analytics(self.car_catalog,identity)
        return '<hr><h2>'+esc(tr('Related CAR Analytics'))+'</h2><p>'+link('list','',tr('Back to CAR results'))+'</p>'+''.join(
            '<p>'+esc(scope)+' · '+link('analytic',key,key+' '+self.car_catalog.analytics[key]['title'])+'</p>' for scope,key in matches)
