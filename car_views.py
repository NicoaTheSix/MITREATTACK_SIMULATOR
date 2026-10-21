"""Native CAR browser, stable sortable identities and internal reference pages. Workflow: README.md."""
from datetime import date
import html
import json
import re
from urllib.parse import quote, unquote
from PySide6 import QtCore, QtGui, QtWidgets
from attack_catalog import external_id
from car_mapping import resolve_technique
from car_documents import included
from localization import tr

REF = int(QtCore.Qt.ItemDataRole.UserRole) + 110
SORT = REF + 1
OWNER = REF + 2
SNAPSHOT = REF + 3
HEADERS = ['ID', 'Name', 'Submission Date', 'ATT&CK Techniques', 'Implementations', 'Applicable Platforms']


def esc(value):
    return html.escape(str(value))


def link(kind, key, label):
    return '<a href="car:' + kind + '/' + quote(key, safe='/') + '">' + esc(label) + '</a>'


def natural(identity):
    return tuple(int(v) for v in identity.split('-')[1:])


def row_values(analytic, catalog):
    parents = sorted({c['technique'] for c in analytic.get('coverage', [])})
    techniques = '; '.join(resolve_technique(catalog, v)['name'] + ' (' + v + ')' for v in parents)
    tools = ', '.join(sorted({v['type'].capitalize() for v in analytic.get('implementations', [])}, key=str.casefold))
    platforms = ', '.join(sorted(set(analytic.get('platforms', [])), key=str.casefold))
    raw_date = analytic.get('submission_date') or ''
    try:
        parsed = date.fromisoformat(str(raw_date).replace('/', '-'))
    except ValueError:
        parsed = None
    values = [analytic['id'], analytic.get('title', ''), str(raw_date), techniques, tools, platforms]
    keys = [natural(analytic['id']), analytic.get('title', '').casefold(), parsed.toordinal() if parsed else None,
            techniques.casefold() or None, tools.casefold() or None, platforms.casefold() or None]
    return values, keys


class AnalyticSort(QtCore.QSortFilterProxyModel):
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        self.setDynamicSortFilter(True)

    def lessThan(self, left, right):
        a, b = left.data(SORT), right.data(SORT)
        ascending = self.sortOrder() == QtCore.Qt.SortOrder.AscendingOrder
        if (a is None) != (b is None):
            return (a is not None) if ascending else (a is None)
        if a == b:
            ai, bi = natural(left.data(REF)), natural(right.data(REF))
            return ai < bi if ascending else ai > bi
        return a < b

    def filterAcceptsRow(self, row, parent):
        browser = self.browser
        identity = self.sourceModel().index(row, 1).data(REF)
        record = browser.car.analytics[identity]
        query = browser.search.text().casefold()
        return (query in (identity+' '+record['title']).casefold()
                and (not browser.platform.currentData() or browser.platform.currentData() in record.get('platforms', []))
                and (not browser.tool.currentData() or browser.tool.currentData() in [v['type'] for v in record.get('implementations', [])])
                and (not browser.only_included.isChecked() or browser.is_included(identity)))


class CarBrowser(QtWidgets.QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner, self.car, self.catalog, self.kind = owner, None, None, 'CAR Analytics'
        self.owner_id = None
        self.source_signature = None
        outer = QtWidgets.QVBoxLayout(self)
        self.status = QtWidgets.QLabel('CAR is loading…'); outer.addWidget(self.status)
        self.stack = QtWidgets.QStackedWidget(); outer.addWidget(self.stack, 1)
        analytics_page = QtWidgets.QWidget(); layout = QtWidgets.QVBoxLayout(analytics_page)
        bar = QtWidgets.QHBoxLayout()
        self.search = QtWidgets.QLineEdit(); self.search.setPlaceholderText('Search CAR name or ID…'); self.search.setClearButtonEnabled(True)
        self.platform = QtWidgets.QComboBox(); self.platform.addItem('All platforms', '')
        self.tool = QtWidgets.QComboBox(); self.tool.addItem('All tools', '')
        self.only_included = QtWidgets.QCheckBox('Only included Analytics')
        for widget in (self.search, self.platform, self.tool, self.only_included): bar.addWidget(widget)
        layout.addLayout(bar)
        self.tabs = QtWidgets.QTabWidget(); layout.addWidget(self.tabs, 1)
        self.table = QtWidgets.QTableView(); self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True); self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Interactive)
        self.model = QtGui.QStandardItemModel(0, 7, self)
        self.model.setHorizontalHeaderLabels(['Include', *HEADERS])
        self.proxy = AnalyticSort(self); self.proxy.setSourceModel(self.model); self.table.setModel(self.proxy)
        for column, width in enumerate((70, 160, 330, 140, 350, 200, 180)): self.table.setColumnWidth(column, width)
        self.table.sortByColumn(1, QtCore.Qt.SortOrder.AscendingOrder)
        self.model.itemChanged.connect(self.checked)
        self.table.doubleClicked.connect(lambda index:self.open_analytic(index.data(REF)))
        self.table.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.context_menu)
        self.tabs.addTab(self.table, 'Analytics')
        self.by_technique = QtWidgets.QTableWidget(0, 3)
        self.by_technique.setHorizontalHeaderLabels(['ATT&CK Technique', 'ATT&CK Sub-technique(s)', 'CAR Analytic(s)'])
        for col in range(3): self.by_technique.horizontalHeader().setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.by_technique, 'By ATT&CK Technique')
        actions = QtWidgets.QHBoxLayout()
        for label, callback in [('View Analytic information', self.open_highlighted),
                                ('Add highlighted Analytics to Workplace', lambda:self.change_highlighted(True)),
                                ('Remove highlighted Analytics from Workplace', lambda:self.change_highlighted(False))]:
            button = QtWidgets.QPushButton(label); button.clicked.connect(callback); actions.addWidget(button)
        layout.addLayout(actions)
        self.stack.addWidget(analytics_page)
        self.models = QtWidgets.QTreeWidget(); self.models.setHeaderLabels(['CAR Data Model', 'Description'])
        self.models.itemActivated.connect(lambda item,*_:self.navigate(item.data(0,REF)))
        self.models.itemClicked.connect(lambda item,*_:self.navigate(item.data(0,REF)))
        self.stack.addWidget(self.models)
        self.sensors = QtWidgets.QListWidget(); self.sensors.itemClicked.connect(lambda item:self.navigate(item.data(REF)))
        self.stack.addWidget(self.sensors)
        self.detail_page = QtWidgets.QWidget(); details = QtWidgets.QVBoxLayout(self.detail_page)
        bar = QtWidgets.QHBoxLayout(); back = QtWidgets.QPushButton('Back to CAR results'); back.clicked.connect(self.show_list); bar.addWidget(back)
        self.add = QtWidgets.QPushButton('Add Analytic to Workplace'); self.remove = QtWidgets.QPushButton('Remove Analytic from Workplace')
        self.add.clicked.connect(lambda:self.change_detail(True)); self.remove.clicked.connect(lambda:self.change_detail(False))
        bar.addWidget(self.add); bar.addWidget(self.remove); details.addLayout(bar)
        self.details = QtWidgets.QTextBrowser(); self.details.setOpenLinks(False); self.details.anchorClicked.connect(lambda url:self.navigate(url.toString()))
        details.addWidget(self.details, 1); self.stack.addWidget(self.detail_page)
        self.detail_ref = None
        self.search.textChanged.connect(self.refilter)
        self.platform.currentIndexChanged.connect(self.refilter); self.tool.currentIndexChanged.connect(self.refilter)
        self.only_included.toggled.connect(self.refilter)

    def set_catalog(self, car):
        if self.car and self.car.dataset_id==car.dataset_id:
            self.car=car
            return
        self.car = car
        self.models.clear(); self.sensors.clear(); self.source_signature=None
        self.platform.clear(); self.platform.addItem('All platforms','')
        self.tool.clear(); self.tool.addItem('All tools','')
        for value in sorted({v for a in car.analytics.values() for v in a.get('platforms', [])}): self.platform.addItem(value, value)
        for value in sorted({i['type'] for a in car.analytics.values() for i in a.get('implementations', [])}): self.tool.addItem(value.capitalize(), value)
        self.status.setText(f'CAR · {len(car.analytics)} Analytics · commit {car.source["commit"][:12]}')
        for key, model in sorted(car.models.items()):
            root = QtWidgets.QTreeWidgetItem([model.get('name', key), model.get('description', '')]); root.setData(0,REF,'car:model/'+key); self.models.addTopLevelItem(root)
            for field in ('actions', 'fields'):
                group = QtWidgets.QTreeWidgetItem([field.title()]); root.addChild(group)
                for entry in model[field]:
                    row = QtWidgets.QTreeWidgetItem([entry['name'], entry.get('description','')])
                    row.setData(0,REF,'car:model/'+key+'/'+(entry['name'] if field=='actions' else '/'+entry['name'])); group.addChild(row)
        self.models.resizeColumnToContents(0)
        for key, sensor in sorted(car.sensors.items()):
            item = QtWidgets.QListWidgetItem(str(sensor.get('sensor_name',key))+' '+str(sensor.get('sensor_version','')))
            item.setData(REF,'car:sensor/'+key); self.sensors.addItem(item)

    def refresh(self):
        document = self.owner.current_document
        if not document: return
        if self.owner_id is not None and self.owner_id != document.document_id:
            self.detail_ref = None
            self.table.clearSelection()
            if self.stack.currentWidget() is self.detail_page:
                self.show_list()
        self.owner_id, self.catalog = document.document_id, document.catalog
        if not self.car: return
        signature = self.car.dataset_id, document.catalog.domain, document.catalog.version, document.catalog.dataset_id
        if signature != self.source_signature:
            self.source_signature = signature
            self.model.blockSignals(True); self.model.removeRows(0,self.model.rowCount())
            for identity, record in sorted(self.car.analytics.items()):
                values, keys = row_values(record,self.catalog)
                check = QtGui.QStandardItem(); check.setCheckable(True)
                items = [check]+[QtGui.QStandardItem(value or '—') for value in values]
                for column,item in enumerate(items):
                    item.setData(identity,REF); item.setData(self.car.dataset_id,SNAPSHOT); item.setData(keys[column-1] if column else None,SORT)
                    item.setToolTip(values[column-1] if column else identity)
                self.model.appendRow(items)
            self.model.blockSignals(False)
            self.rebuild_groups()
        self.sync_checks()

    def is_included(self, identity):
        key = self.car.dataset_id+':'+identity
        return key in included(self.owner.current_document)

    def sync_checks(self):
        if not self.car or not self.owner.current_document: return
        self.model.blockSignals(True)
        for row in range(self.model.rowCount()):
            item = self.model.item(row,0); item.setData(self.owner.current_document.document_id,OWNER)
            item.setCheckState(QtCore.Qt.CheckState.Checked if self.is_included(item.data(REF)) else QtCore.Qt.CheckState.Unchecked)
        self.model.blockSignals(False); self.refilter()
        if self.detail_ref:
            self.add.setEnabled(not self.detail_ref in included(self.owner.current_document))
            self.remove.setEnabled(self.detail_ref in included(self.owner.current_document))

    def checked(self, item):
        if item.column()==0 and self.owner.current_document:
            self.owner.change_car_inclusion({item.data(SNAPSHOT)+':'+item.data(REF)},item.checkState()==QtCore.Qt.CheckState.Checked,item.data(OWNER))

    def refilter(self,*_):
        self.proxy.invalidateFilter()

    def highlighted(self):
        return {i.data(REF) for i in self.table.selectionModel().selectedRows()}

    def change_highlighted(self, include):
        if self.highlighted(): self.owner.change_car_inclusion(self.highlighted(),include,self.owner_id)

    def open_highlighted(self):
        ids = sorted(self.highlighted())
        if ids: self.open_analytic(ids[0])

    def context_menu(self, position):
        index = self.table.indexAt(position)
        if index.isValid() and not self.table.selectionModel().isRowSelected(index.row(),QtCore.QModelIndex()):
            self.table.selectRow(index.row())
        identities, owner = {self.car.dataset_id+':'+v for v in self.highlighted()}, self.owner_id
        menu = QtWidgets.QMenu(self)
        menu.addAction('View Analytic information',lambda:self.open_analytic(sorted(identities)[0]) if identities and self.owner.current_document.document_id==owner else None)
        menu.addAction('Add highlighted Analytics to Workplace',lambda:self.owner.change_car_inclusion(identities,True,owner))
        menu.addAction('Remove highlighted Analytics from Workplace',lambda:self.owner.change_car_inclusion(identities,False,owner))
        self.owner.show_workplace_menu(menu,self.table.viewport().mapToGlobal(position))

    def label(self, identity):
        record = resolve_technique(self.catalog,identity)
        return identity+' '+record['name']+' ['+record['status']+']'

    def rich_cell(self,text):
        label = QtWidgets.QLabel(text); label.setWordWrap(True); label.setOpenExternalLinks(False)
        label.linkActivated.connect(self.navigate); label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        return label

    def rebuild_groups(self):
        self.by_technique.setRowCount(len(self.car.groups))
        for row,((parent,scope), ids) in enumerate(sorted(self.car.groups.items())):
            values = [link('technique',parent,self.label(parent)),link('technique',scope,self.label(scope)) if scope else esc('N/A — technique only'),
                      '<br>'.join(link('analytic',key,key+' '+self.car.analytics[key]['title']) for key in ids)]
            for column,value in enumerate(values): self.by_technique.setCellWidget(row,column,self.rich_cell(value))
            self.by_technique.setRowHeight(row,max(55,len(ids)*42))

    def show_category(self,category):
        self.kind=category; self.show_list()

    def show_list(self):
        self.stack.setCurrentIndex({'CAR Analytics':0,'CAR Data Model':1,'CAR Sensors':2}[self.kind])
        self.owner.workspace.setCurrentWidget(self)

    def change_detail(self,include):
        if self.detail_ref: self.owner.change_car_inclusion({self.detail_ref},include,self.owner_id)

    def open_analytic(self,identity):
        if not identity or not self.owner.current_document: return
        entries = self.owner.current_document.car_workspace.get('entries',{})
        if ':' not in identity and not self.car: return
        key = identity if ':' in identity else self.car.dataset_id+':'+identity
        saved = entries.get(key)
        exact = self.car is not None and key.startswith(self.car.dataset_id+':') and key.split(':')[-1] in self.car.analytics
        record = self.car.analytics.get(key.split(':')[-1]) if exact else None
        record = record or (saved or {}).get('record',{})
        if not record: return
        self.detail_ref=key; self.owner_id=self.owner.current_document.document_id
        rows=[]
        for cov in record.get('coverage',[]):
            parent=cov['technique']; scopes=cov.get('subtechniques',[])
            rows.append('<p>'+link('technique',parent,self.label(parent))+': '+
                        (', '.join(link('technique',v,self.label(v)) for v in scopes) if scopes else
                         esc('No listed sub-techniques' if 'subtechniques' in cov else 'N/A — technique only'))+
                        '<br>'+esc(json.dumps(cov,ensure_ascii=False))+'</p>')
        refs=record.get('data_model_references',[])
        rows.append('<h2>'+esc(tr('CAR Data Model'))+'</h2>'+('<br>'.join(link('model',r,r) for r in refs) or esc(tr('Not provided'))))
        candidates=self.car.candidates(record) if exact else {}
        rows.append('<h2>'+esc(tr('Sensor candidates — partial field intersections, not validation'))+'</h2>'+ '<br>'.join(
            link('sensor',k,k)+': '+esc(', '.join(v)) for k,v in candidates.items()))
        if not refs:
            rows.append('<p>'+esc(tr('Unknown — data requirements not provided'))+'</p>')
        elif not candidates:
            rows.append('<p>'+esc(tr('No candidate in this snapshot'))+'</p>')
        rows.append('<h2>'+esc(tr('Implementations'))+'</h2>')
        for number,implementation in enumerate(record.get('implementations',[]),1):
            rows.append('<h3>'+esc(str(number)+' · '+implementation['type'])+'</h3><pre>'+esc(json.dumps(implementation,indent=2,ensure_ascii=False))+'</pre>')
            for url in re.findall(r'https?://[^\s\)<>\"\]]+',json.dumps(implementation,ensure_ascii=False)):
                rows.append('<p><a href="'+esc(url.rstrip('.,'))+'">'+esc(tr('Open implementation reference'))+'</a></p>')
        source=self.car.source if exact else saved['source']
        body='<h1>'+esc(record.get('id','')+' '+record.get('title',''))+'</h1><p>'+esc(tr('Resolved snapshot') if exact else tr('Unresolved snapshot — saved analytic retained'))+'</p>'
        body+='<p>'+esc(source['commit'])+'</p><p>'+esc(record.get('submission_date',tr('Not provided')))+'</p>'
        body+='<h2>'+esc(tr('Description'))+'</h2><p>'+esc(record.get('description','')).replace('\n','<br>')+'</p>'
        body+='<h2>'+esc(tr('Native coverage'))+'</h2>'+''.join(rows)
        body+='<h2>'+esc(tr('Complete native record — tests are reference text only'))+'</h2><pre>'+esc(json.dumps(record,indent=2,ensure_ascii=False))+'</pre>'
        self.render_detail(body,True)

    def render_detail(self,body,analytic=False):
        self.add.setVisible(analytic); self.remove.setVisible(analytic)
        self.details.setHtml(body); self.stack.setCurrentWidget(self.detail_page)
        self.owner.workspace.setCurrentWidget(self); self.sync_checks()

    def navigate(self,target):
        text=unquote(target); url=QtCore.QUrl(text)
        if url.scheme() in ('http','https'):
            if url.host() and not url.userInfo(): QtGui.QDesktopServices.openUrl(url)
            return
        if not text.startswith('car:'): return
        kind,_,key=text[4:].partition('/')
        if kind=='list': self.show_list()
        elif kind=='analytic': self.open_analytic(key)
        elif kind=='technique': self.owner.show_car_technique(key)
        elif kind=='model': self.show_model(key)
        elif kind=='sensor': self.show_sensor(key)

    def show_model(self,reference):
        if not self.car: return
        parts=reference.split('/'); key=parts[0]; model=self.car.models.get(key)
        if not model: return
        action=parts[1] if len(parts)>1 else ''; field=parts[2] if len(parts)>2 else ''
        refs=[r for r in self.car.references if len(r.split('/'))==3 and r.split('/')[0]==key and (not action or r.split('/')[1]==action)
              and (not field or r.split('/')[-1]==field)]
        analytic_ids=sorted({a for r in refs for a in self.car.references[r]})
        body='<h1>'+esc(reference)+'</h1><p>'+esc(model.get('description',''))+'</p>'
        for category in ('actions','fields'):
            body+='<h2>'+esc(category.title())+'</h2>'
            for entry in model[category]:
                route=key+'/'+entry['name'] if category=='actions' else key+'//'+entry['name']
                body+='<p>'+link('model',route,entry['name'])+' '+esc(entry.get('description',''))+'</p>'
        body+='<h2>'+esc(tr('Exact referencing Analytics'))+'</h2>'+'<br>'.join(link('analytic',a,a+' '+self.car.analytics[a]['title']) for a in analytic_ids)
        body+='<pre>'+esc(json.dumps(model,indent=2,ensure_ascii=False))+'</pre>'
        self.detail_ref=None; self.render_detail(body)

    def show_sensor(self,key):
        if not self.car: return
        record=self.car.sensors.get(key)
        if not record: return
        fields=self.car.sensor_fields[key]
        body='<h1>'+esc(record.get('sensor_name',key)+' '+str(record.get('sensor_version','')))+'</h1><p>'+esc(record.get('sensor_description',''))+'</p>'
        body+='<h2>'+esc(tr('Native mappings and notes'))+'</h2>'
        for mapping in record['mappings']:
            body+='<p>'+esc(mapping['object']+'/'+mapping['action'])+'<br>'+esc(mapping.get('notes',''))+'<br>'+', '.join(
                link('model',mapping['object']+'/'+mapping['action']+'/'+f,f) for f in mapping['fields'])+'</p>'
        body+='<h2>'+esc(tr('Sensor candidates — partial field intersections, not validation'))+'</h2>'
        for identity,analytic in sorted(self.car.analytics.items()):
            intersection=sorted(fields & set(analytic.get('data_model_references',[])))
            if intersection: body+='<p>'+link('analytic',identity,identity+' '+analytic['title'])+'<br>'+esc(', '.join(intersection))+'</p>'
        body+='<pre>'+esc(json.dumps(record,indent=2,ensure_ascii=False))+'</pre>'
        self.detail_ref=None; self.render_detail(body)
