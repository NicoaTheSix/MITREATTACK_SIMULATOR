"""Independent ATT&CK, ATLAS and CAR activity-rail switches. Flow: README.md."""
import json
from PySide6 import QtCore, QtWidgets
from attack_catalog import BROWSE_CATEGORIES

ATTACK_CATEGORIES={'TTP',*BROWSE_CATEGORIES}
ATLAS_CATEGORIES={'ATLAS TTP','ATLAS Mitigations'}
CAR_CATEGORIES={'CAR Analytics','CAR Data Model','CAR Sensors'}
FAMILIES={'attack':'ATT&CK','atlas':'ATLAS','car':'CAR'}
FAMILY_CATEGORIES={'attack':ATTACK_CATEGORIES,'atlas':ATLAS_CATEGORIES,'car':CAR_CATEGORIES}
LEGACY_SCOPES={'both':set(FAMILIES),'attack':{'attack'},'atlas':{'atlas'}}


class NavigationVisibilityGuard(QtCore.QObject):
    """Keep framework exclusions authoritative during later Qt show events."""
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner
        self.categories={}

    def watch(self,category,button):
        if button not in self.categories:
            self.categories[button]=category
            button.installEventFilter(self)

    def eventFilter(self,watched,event):
        if event.type() in (QtCore.QEvent.Type.Show,QtCore.QEvent.Type.ShowToParent):
            category=self.categories.get(watched)
            if category is not None and not self.owner.navigation_category_visible(category):
                watched.hide()
                return True
        return super().eventFilter(watched,event)


class NavigationScope:
    def init_navigation_scope(self):
        print('Input settings file: '+str(self.settings_path),flush=True)
        print('Output files: None (sidebar preference in memory)',flush=True)
        print('[Sidebar content 1/2] Reading framework visibility',flush=True)
        enabled=set(FAMILIES)
        if self.ui_settings.contains('navigation/families'):
            try:
                value=json.loads(self.ui_settings.value('navigation/families'))
                if not isinstance(value,list) or any(not isinstance(v,str) or v not in FAMILIES for v in value):
                    raise ValueError('Invalid sidebar groups')
                enabled=set(value)
            except (TypeError,ValueError):
                enabled=set(FAMILIES)
        else:
            value=self.ui_settings.value('navigation/frameworks','both')
            enabled=LEGACY_SCOPES.get(value,set(FAMILIES)) if isinstance(value,str) else set(FAMILIES)
        self.navigation_families={family:family in enabled for family in FAMILIES}
        print('[Sidebar content 2/2] '+', '.join(FAMILIES[f] for f in FAMILIES if f in enabled),flush=True)

    @property
    def navigation_scope(self):
        """Compatibility summary for older programmatic callers."""
        enabled={f for f,value in self.navigation_families.items() if value}
        return next((scope for scope,groups in LEGACY_SCOPES.items() if enabled==groups),'custom')

    def add_navigation_scope_menu(self,settings_menu):
        menu=settings_menu.addMenu('Sidebar content')
        self.navigation_family_actions={}
        self.navigation_scope_actions=self.navigation_family_actions
        for value,label in FAMILIES.items():
            action=menu.addAction(label.replace('&','&&')); action.setCheckable(True)
            action.setData(value)
            action.setChecked(self.navigation_families[value])
            action.toggled.connect(lambda checked,key=value:self.set_navigation_family(key,checked))
            self.navigation_family_actions[value]=action

    def navigation_category_visible(self,category):
        return all(self.navigation_families[family] for family,categories in FAMILY_CATEGORIES.items()
                   if category in categories)

    def apply_navigation_scope(self):
        if not hasattr(self,'navigation_visibility_guard'):
            self.navigation_visibility_guard=NavigationVisibilityGuard(self)
            self.navigation_hidden=QtWidgets.QWidget(self)
            self.navigation_hidden.hide()
        rail_layout=self.navigation_rail.layout()
        position=0
        for category,button in self.navigation_buttons.items():
            self.navigation_visibility_guard.watch(category,button)
            visible=self.navigation_category_visible(category)
            if visible:
                if button.parentWidget() is not self.navigation_rail:
                    button.setParent(self.navigation_rail)
                rail_layout.insertWidget(position,button)
                button.show()
                position+=1
            else:
                button.hide()
                rail_layout.removeWidget(button)
                button.setParent(self.navigation_hidden)
        if self.loaded_ok and not self.navigation_category_visible(self.active_category):
            # Switch the hidden library's explorer to the shared Workplace while
            # retaining the right-hand page and its document tab.
            page,index,document_index=self.workspace.currentWidget(),self.tabs.currentIndex(),self.document_tabs.currentIndex()
            sidebar_visible=not self.sidebar.isHidden()
            self.switch_category('Workplace')
            with QtCore.QSignalBlocker(self.tabs), QtCore.QSignalBlocker(self.document_tabs):
                self.tabs.setCurrentIndex(index); self.document_tabs.setCurrentIndex(document_index)
                self.workspace.setCurrentWidget(page)
                self.sidebar.setVisible(sidebar_visible)
            if page is getattr(self,'atlas_cases_page',None):
                self.show_atlas_cases_sidebar()
        for family,action in self.navigation_family_actions.items():
            with QtCore.QSignalBlocker(action): action.setChecked(self.navigation_families[family])

    def set_navigation_scope(self,value):
        """Map the old API to exact groups; the user menu uses independent switches."""
        if value not in LEGACY_SCOPES: return False
        return self.set_navigation_families(LEGACY_SCOPES[value])

    def set_navigation_family(self,family,enabled):
        if family not in FAMILIES or type(enabled) is not bool: return False
        groups={f for f,value in self.navigation_families.items() if value}
        if enabled: groups.add(family)
        else: groups.discard(family)
        return self.set_navigation_families(groups)

    def set_navigation_families(self,groups):
        if not isinstance(groups,(set,frozenset,list,tuple)) or any(not isinstance(f,str) or f not in FAMILIES for f in groups):
            return False
        self.operation_report('Input files: None (sidebar choice in memory)')
        self.operation_report('Output settings file: '+str(self.settings_path))
        self.operation_report('[Sidebar content 1/3] Validating visibility preference',0,3)
        self.navigation_families={family:family in groups for family in FAMILIES}
        self.apply_navigation_scope()
        self.operation_report('[Sidebar content 2/3] Updating navigation and saving preference',1,3)
        self.ui_settings.setValue('navigation/families',json.dumps([f for f in FAMILIES if self.navigation_families[f]]))
        self.ui_settings.remove('navigation/frameworks')
        self.ui_settings.sync()
        self.operation_report('[Sidebar content 3/3] '+('Saved' if self.ui_settings.status()==QtCore.QSettings.Status.NoError
            else 'Could not save; preference applies to this session'),3,3)
        return True
