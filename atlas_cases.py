"""Searchable ATLAS case studies in an upper reference tab. Flow: README.md."""
from PySide6 import QtCore, QtWidgets
from attack_catalog import catalog_identity, external_id
from atlas_catalog import DOMAIN
from stix_clipboard import ObjectCopyBar

CASE_KEY=int(QtCore.Qt.ItemDataRole.UserRole)+170


class AtlasCasesPage(QtWidgets.QWidget):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner; self.signature=None; self.key=None; self.context=None; self.owner_id=None
        outer=QtWidgets.QVBoxLayout(self)
        browser=QtWidgets.QWidget(); left=QtWidgets.QVBoxLayout(browser); left.setContentsMargins(0,0,0,0)
        self.sidebar=browser
        self.search=QtWidgets.QLineEdit(); self.search.setPlaceholderText('Search ATLAS case studies by name, ID or description…')
        self.search.setMaxLength(10000)
        self.search.setClearButtonEnabled(True); left.addWidget(self.search)
        self.count=QtWidgets.QLabel(); left.addWidget(self.count)
        self.listing=QtWidgets.QTreeWidget(); self.listing.setHeaderHidden(True)
        self.listing.setAccessibleName('ATLAS case studies list'); left.addWidget(self.listing,1)
        owner.explorer_stack.addWidget(browser)
        content=QtWidgets.QWidget(); details=QtWidgets.QVBoxLayout(content); details.setContentsMargins(0,0,0,0)
        actions=QtWidgets.QHBoxLayout()
        self.add=QtWidgets.QPushButton('Add all ATLAS TTPs'); self.remove=QtWidgets.QPushButton('Remove all ATLAS TTPs')
        self.related=QtWidgets.QLabel()
        for widget in (self.add,self.remove,self.related): actions.addWidget(widget)
        actions.addStretch(); details.addLayout(actions)
        self.copy_bar=ObjectCopyBar(owner.operation_report,self); details.addWidget(self.copy_bar)
        self.details=type(owner.details)(); details.addWidget(self.details,1)
        self.details.document().setDefaultStyleSheet('body { color:#d4d4d4; } h1,h2 { color:#eeeeee; } a { color:#4daafc; }')
        self.details.setOpenExternalLinks(False); self.details.setOpenLinks(False)
        self.details.anchorClicked.connect(owner.open_detail_link)
        self.details.copied.connect(lambda section:owner.state.setText('Copied '+section.lower()+' to clipboard'))
        outer.addWidget(content)
        self.search.textChanged.connect(self.refilter)
        self.listing.itemClicked.connect(lambda item,*_:self.show_record(item.data(0,CASE_KEY)))
        self.add.clicked.connect(lambda:self.change_ttps('add'))
        self.remove.clicked.connect(lambda:self.change_ttps('remove'))
        self.clear_detail()

    def clear_detail(self):
        self.key=None; self.context=None; self.copy_bar.clear_context()
        self.add.setEnabled(False); self.remove.setEnabled(False); self.related.clear()
        self.details.setHtml('<h1>ATLAS Case Studies</h1><p>Select a case study to inspect its details.</p>')

    def refresh(self):
        catalog=self.owner.current_atlas_catalog
        self.owner_id=self.owner.current_document.document_id if self.owner.current_document else None
        signature=catalog_identity(catalog) if catalog else None
        if signature!=self.signature:
            self.signature=signature; key=self.key
            self.listing.clear()
            if catalog:
                for identity,obj in sorted(catalog.objects_by_domain[DOMAIN].items(),key=lambda pair:external_id(pair[1])):
                    if obj.get('type')=='x-atlas-case-study':
                        item=QtWidgets.QTreeWidgetItem([external_id(obj)+'  '+obj['name']]); item.setData(0,CASE_KEY,identity)
                        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                        item.setToolTip(0,item.text(0)); self.listing.addTopLevelItem(item)
            if key and catalog and key in catalog.objects_by_domain[DOMAIN]: self.show_record(key)
            else: self.clear_detail()
        self.refilter()

    def refilter(self,*_):
        catalog=self.owner.current_atlas_catalog; query=self.search.text().casefold(); count=0
        for row in range(self.listing.topLevelItemCount()):
            item=self.listing.topLevelItem(row); obj=catalog.objects_by_domain[DOMAIN][item.data(0,CASE_KEY)]
            visible=query in (item.text(0)+' '+obj.get('description','')).casefold()
            item.setHidden(not visible); count+=visible
        self.count.setText(f'{count} / {self.listing.topLevelItemCount()} case studies')

    def show_record(self,key):
        catalog=self.owner.current_atlas_catalog
        obj=catalog.objects_by_domain[DOMAIN].get(key,{}) if catalog else {}
        if obj.get('type')!='x-atlas-case-study': return
        self.key=key; self.context=(catalog_identity(catalog),key)
        self.owner_id=self.owner.current_document.document_id
        self.details.setHtml(self.owner.atlas_record_html(catalog,obj))
        self.details.set_copy_content(obj['name'],obj.get('description',''))
        self.copy_bar.set_context(catalog,DOMAIN,key)
        keys=self.owner.atlas_source_techniques(catalog,key)
        self.related.setText(f'{len(keys)} related ATLAS TTPs')
        self.add.setEnabled(bool(keys) and self.owner.loaded_ok); self.remove.setEnabled(bool(keys) and self.owner.loaded_ok)
        for row in range(self.listing.topLevelItemCount()):
            item=self.listing.topLevelItem(row)
            if item.data(0,CASE_KEY)==key:
                self.listing.setCurrentItem(item); break

    def change_ttps(self,action):
        if self.context:
            if not self.owner.current_atlas_catalog or self.context[0]!=catalog_identity(self.owner.current_atlas_catalog):
                self.owner.operation_report('Input files: None; output files: None (stale case-study source in memory)')
                self.owner.operation_report('[ATLAS cases] Source changed; no selections were modified',1,1)
                self.clear_detail(); return
            self.owner.change_all_atlas_source_ttps(action,self.context,self.owner_id)
