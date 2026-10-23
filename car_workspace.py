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
        self.car_sidebar = QtWidgets.QWidget()
        sidebar_layout=QtWidgets.QVBoxLayout(self.car_sidebar)
        sidebar_layout.setContentsMargins(0,0,0,0)
        self.car_sidebar_search=QtWidgets.QLineEdit()
        self.car_sidebar_search.setPlaceholderText('Search CAR name or ID…')
        self.car_sidebar_search.setClearButtonEnabled(True)
        sidebar_layout.addWidget(self.car_sidebar_search)
        self.car_sidebar_list=QtWidgets.QTreeWidget()
        self.car_sidebar_list.setHeaderHidden(True)
        self.car_sidebar_list.setAccessibleName('CAR sidebar entries')
        sidebar_layout.addWidget(self.car_sidebar_list,1)
        self.car_sidebar_list.currentItemChanged.connect(self.select_car_sidebar_entry)
        self.car_sidebar_list.itemClicked.connect(self.open_car_sidebar_entry)
        self.car_sidebar_list.itemActivated.connect(self.open_car_sidebar_entry)
        self.car_sidebar_search.textChanged.connect(self.filter_car_sidebar)
        self.explorer_stack.addWidget(self.car_sidebar)
        self.car_sidebar_kind='CAR Analytics'
        self.car_sidebar_signature=None
        self.pending_car_entry=None
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
        car_actions=QtWidgets.QHBoxLayout()
        self.open_car_browser_button=QtWidgets.QPushButton('Open CAR Browser')
        self.open_car_browser_button.clicked.connect(self.open_car_browser)
        car_actions.addWidget(self.open_car_browser_button)
        self.car_sidebar_choice=QtWidgets.QLabel('CAR Analytics / Data Model / Sensors')
        self.car_sidebar_choice.setWordWrap(True)
        self.car_sidebar_choice.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        car_actions.addWidget(self.car_sidebar_choice,1)
        layout.insertLayout(3,car_actions)

    def set_car_catalog(self,catalog):
        self.car_catalog=catalog; self.car_browser.set_catalog(catalog)
        self.populate_car_sidebar()
        if self.current_document: self.refresh_car_workspace()

    def car_catalog_failed(self,error):
        self.car_browser.status.setText(tr('CAR snapshot unavailable — saved selections remain available.')+' '+str(error))
        if self.current_document: self.refresh_car_workspace()

    def switch_car_category(self,category):
        self.operation_report('Input files: None; output files: None (CAR sidebar in memory)',0,0)
        self.operation_report('[CAR sidebar 1/2] Updating the source list',0,2)
        self.active_category=category; self.navigation_buttons[category].setChecked(True)
        self.sidebar.setVisible(True); self.explorer_stack.setCurrentWidget(self.car_sidebar)
        self.sidebar_title.setText(tr(category))
        self.navigation_scroll.ensureWidgetVisible(self.navigation_buttons[category])
        for widget in (self.ttp_search,self.search,self.ttp_search_fields_button,self.source_search_fields_button,
                       self.source_results_bar,self.matrix_button,self.atlas_search,self.atlas_open_button): widget.hide()
        self.car_sidebar_kind=category
        self.populate_car_sidebar()
        self.summary.setText(self.car_browser.status.text())
        self.operation_report('[CAR sidebar 2/2] Ready; click an entry to open its details',2,2)
        self.schedule_session_checkpoint()

    def populate_car_sidebar(self):
        car=self.car_catalog
        signature=(car.dataset_id if car else None,self.car_sidebar_kind)
        if signature==self.car_sidebar_signature: return
        self.car_sidebar_signature=signature
        self.pending_car_entry=None
        self.car_sidebar_choice.setText(self.car_sidebar_kind)
        with QtCore.QSignalBlocker(self.car_sidebar_list):
            self.car_sidebar_list.clear()
            if car:
                if self.car_sidebar_kind=='CAR Analytics':
                    rows=[(key,key+'  '+record['title'],'car:analytic/'+key) for key,record in sorted(car.analytics.items())]
                elif self.car_sidebar_kind=='CAR Data Model':
                    rows=[(key,record.get('name',key),'car:model/'+key) for key,record in sorted(car.models.items())]
                else:
                    rows=[(key,str(record.get('sensor_name',key))+' '+str(record.get('sensor_version','')),'car:sensor/'+key) for key,record in sorted(car.sensors.items())]
                for key,label,reference in rows:
                    item=QtWidgets.QTreeWidgetItem([label]);item.setData(0,REF,reference)
                    item.setToolTip(0,label);self.car_sidebar_list.addTopLevelItem(item)
        self.filter_car_sidebar()

    def filter_car_sidebar(self,*_):
        query=self.car_sidebar_search.text().casefold()
        for index in range(self.car_sidebar_list.topLevelItemCount()):
            item=self.car_sidebar_list.topLevelItem(index)
            item.setHidden(query not in item.text(0).casefold())

    def select_car_sidebar_entry(self,item,previous):
        if not item or not self.car_catalog or not self.current_document: return
        self.pending_car_entry=(self.current_document.document_id,self.car_catalog.dataset_id,item.data(0,REF))
        self.car_sidebar_choice.setText(item.text(0))

    def open_car_sidebar_entry(self,item,column=0):
        if not self.loaded_ok or not item or not item.data(0,REF): return
        self.select_car_sidebar_entry(item,None)
        if self.pending_car_entry:
            self.open_car_browser()

    def open_car_browser(self):
        if not self.loaded_ok: return
        self.operation_report('Input files: None; output files: None (CAR browser in memory)',0,0)
        self.operation_report('[CAR browser 1/2] Opening the selected CAR reference',0,2)
        self.show_document_page()
        self.car_browser.refresh()
        choice=self.pending_car_entry
        valid_choice=choice and self.car_catalog and choice[:2]==(self.current_document.document_id,self.car_catalog.dataset_id)
        if valid_choice or self.car_browser.kind!=self.car_sidebar_kind:
            self.car_browser.show_category(self.car_sidebar_kind)
        else:
            self.reveal_car_browser()
        if valid_choice:
            self.car_browser.navigate(choice[2])
        self.operation_report('[CAR browser 2/2] Ready; Workplace content retained',2,2)

    @property
    def car_browser_tab_index(self):
        return next((i for i in range(self.document_tabs.count())
                     if self.document_tabs.tabData(i)=='__car_browser__'),-1)

    def ensure_car_browser_tab(self):
        index=self.car_browser_tab_index
        if index>=0: return index
        with QtCore.QSignalBlocker(self.document_tabs):
            index=self.document_tabs.addTab('CAR Browser')
            self.document_tabs.setTabData(index,'__car_browser__')
            self.document_tabs.setTabIcon(index,self.navigation_icons['CAR Analytics'])
            close=QtWidgets.QToolButton(self.document_tabs)
            close.setText('×');close.setAccessibleName('Close CAR Browser');close.setToolTip('Close CAR Browser')
            close.setAutoRaise(True);close.setFixedSize(22,22)
            close.clicked.connect(self.close_car_browser)
            self.document_tabs.setTabButton(index,QtWidgets.QTabBar.ButtonPosition.RightSide,close)
        return index

    def reveal_car_browser(self):
        if not self.loaded_ok: return
        reopening=self.car_browser_tab_index<0
        if reopening:
            self.operation_report('Input files: None; output files: None (CAR reference tab in memory)')
            self.operation_report('[CAR tab 1/2] Opening independent reference tab',0,2)
        self.car_browser.refresh()
        with QtCore.QSignalBlocker(self.document_tabs):
            self.document_tabs.setCurrentIndex(self.ensure_car_browser_tab())
        self.workspace.setCurrentWidget(self.car_browser)
        self.schedule_session_checkpoint()
        if reopening:self.operation_report('[CAR tab 2/2] Ready; document content retained',2,2)

    def close_car_browser(self):
        index=self.car_browser_tab_index
        if index<0: return
        self.operation_report('Input files: None; output files: None (CAR reference tab in memory)')
        self.operation_report('[CAR tab 1/2] Closing reference tab',0,2)
        active=self.workspace.currentWidget() is self.car_browser
        with QtCore.QSignalBlocker(self.document_tabs):self.document_tabs.removeTab(index)
        if active:self.show_document_page()
        self.schedule_session_checkpoint()
        self.operation_report('[CAR tab 2/2] Closed; browser state and document content retained',2,2)

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
        if self.pending_car_entry and (self.pending_car_entry[0]!=self.current_document.document_id or
                not self.car_catalog or self.pending_car_entry[1]!=self.car_catalog.dataset_id):
            self.pending_car_entry=None
            self.car_sidebar_choice.setText(self.car_sidebar_kind)
            self.car_sidebar_list.clearSelection()
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
