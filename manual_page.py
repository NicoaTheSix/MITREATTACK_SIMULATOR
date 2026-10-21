"""Read-only manual workspace with heading outline and feature links. Flow: README.md."""
from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown import Markdown
from PySide6 import QtCore, QtGui, QtWidgets
from localization import language, translate_html

ROOT = Path(__file__).resolve().parent
MANUAL_ROOT = ROOT / 'manual'
HOME = MANUAL_ROOT / 'in_app_manual_en.md'
MANUAL_TAB = '__manual__'


def manual_home():
    return MANUAL_ROOT / ('in_app_manual+_zh.md' if language() == 'zh_TW' else 'in_app_manual_en.md')


def manual_index():
    return MANUAL_ROOT / ('in_app_index+_zh.md' if language() == 'zh_TW' else 'in_app_index_en.md')


class ManualPage(QtWidgets.QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.current_path = manual_home()
        layout = QtWidgets.QVBoxLayout(self)
        toolbar = QtWidgets.QHBoxLayout()
        home = QtWidgets.QPushButton('Manual home')
        index = QtWidgets.QPushButton('All operating guides')
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText('Search this manual page… (Enter for next match)')
        self.search.setClearButtonEnabled(True)
        toolbar.addWidget(home)
        toolbar.addWidget(index)
        toolbar.addWidget(self.search, 1)
        layout.addLayout(toolbar)
        splitter = QtWidgets.QSplitter()
        self.outline = QtWidgets.QTreeWidget()
        self.outline.setHeaderLabel('Outline and sections')
        self.outline.setMinimumWidth(210)
        self.outline.setAccessibleName('Manual outline and sections')
        self.browser = QtWidgets.QTextBrowser()
        self.browser.setAccessibleName('Operating manual')
        self.browser.setOpenLinks(False)
        self.browser.setOpenExternalLinks(False)
        splitter.addWidget(self.outline)
        splitter.addWidget(self.browser)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 850])
        layout.addWidget(splitter, 1)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        home.clicked.connect(lambda: self.load_page(manual_home()))
        index.clicked.connect(lambda: self.load_page(manual_index()))
        self.search.returnPressed.connect(self.find_next)
        self.outline.itemClicked.connect(self.jump_to_heading)
        self.browser.anchorClicked.connect(self.follow_link)
        self.features = {
            'open-file': (window.open_studio_action, window.open_studio_document),
            'batch-edit': (window.batch_edit_action, window.edit_ttp_batch),
            'matrix': (window.matrix_button, window.open_matrix),
            'search': (None, self.open_search),
            'selected': (None, self.open_selection),
            'versions': (window.version_action, window.open_versions),
            'layer-settings': (window.layer_settings_action, window.edit_layer_settings),
            'formula': (window.formula_action, window.open_formula_dialog),
            'compare': (window.compare_selections_action, window.open_selection_comparison),
            'compare-versions': (window.compare_versions_action, window.open_version_comparison),
            'import-layer': (window.import_layer_action, window.import_navigator_layer),
            'sources': (window.load_source_action, window.open_source_dialog),
            'upgrade': (window.upgrade_layer_action, window.open_upgrade_dialog),
            'export-svg': (window.matrix_svg_action, lambda: window.export_matrix_view('svg')),
            'export-excel': (window.matrix_excel_action, lambda: window.export_matrix_view('xlsx')),
        }
        self.load_page(manual_home())

    def retranslate_manual(self):
        path = self.current_path
        if path.name.startswith('in_app_manual'):
            path = manual_home()
        elif path.name.startswith('in_app_index') or path == MANUAL_ROOT / 'README.md':
            path = manual_index()
        elif path == ROOT / 'README.md':
            path = MANUAL_ROOT / ('installation+_zh.md' if language() == 'zh_TW' else 'installation_en.md')
        elif language() == 'zh_TW' and path.name.endswith('_en.md'):
            counterpart = path.with_name(path.name[:-6] + '+_zh.md')
            if counterpart.exists():
                path = counterpart
        elif language() == 'en' and path.name.endswith('+_zh.md'):
            counterpart = path.with_name(path.name[:-7] + '_en.md')
            if counterpart.exists():
                path = counterpart
        self.load_page(path)

    def jump_to_heading(self, item, column=0):
        self.window.operation_report('Input files: None; output files: None (manual heading in memory)')
        self.window.operation_report('[Manual outline 1/2] Resolving heading', 0, 2)
        self.browser.scrollToAnchor(item.data(0, QtCore.Qt.ItemDataRole.UserRole))
        self.window.operation_report('[Manual outline 2/2] Ready: ' + item.text(0), 2, 2)

    def load_page(self, path, anchor=''):
        path = Path(path).resolve()
        notify = self.window.operation_report
        notify(f'Input file: {path}')
        notify('Output files: None (read-only manual workspace)')
        notify('[Manual 1/3] Reading local guide', 0, 3)
        try:
            if (not path.is_relative_to(MANUAL_ROOT) and path != ROOT / 'README.md') or path.suffix.lower() != '.md':
                raise ValueError('This link is outside the operating manual')
            if path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError('Manual page exceeds the size limit')
            text = path.read_text(encoding='utf-8-sig')
            notify('[Manual 2/3] Rendering guide and heading outline', 1, 3)
            renderer = Markdown(extensions=['tables', 'fenced_code', 'toc'])
            body = renderer.convert(text)
            if language() == 'zh_TW' and path.name.endswith('+_zh.md'):
                body = translate_html(body)
        except (OSError, ValueError) as error:
            self.status.setText('Could not open manual: ' + str(error))
            notify('[Manual 3/3] Failed: ' + str(error), 3, 3)
            return False
        self.current_path = path
        self.browser.document().setBaseUrl(QtCore.QUrl.fromLocalFile(str(path.parent) + '/'))
        self.browser.setHtml(body)
        self.outline.clear()

        def add_headings(tokens, parent):
            for token in tokens:
                item = QtWidgets.QTreeWidgetItem([html.unescape(re.sub('<[^>]+>', '', token['name']))])
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, token['id'])
                parent.addChild(item)
                add_headings(token['children'], item)

        add_headings(renderer.toc_tokens, self.outline.invisibleRootItem())
        self.outline.expandAll()
        if anchor:
            self.browser.scrollToAnchor(anchor)
        self.status.setText('Reading: ' + path.name + ' · Click the outline for a section or a feature link to open its control.')
        notify('[Manual 3/3] Ready: ' + path.name, 3, 3)
        return True

    def find_next(self):
        query = self.search.text()
        if not query:
            return
        self.window.operation_report('Input files: None; output files: None (search rendered manual text)')
        self.window.operation_report('[Manual search 1/2] Finding text', 0, 2)
        found = self.browser.find(query)
        if not found:
            self.browser.moveCursor(QtGui.QTextCursor.MoveOperation.Start)
            found = self.browser.find(query)
        self.status.setText(('Found: ' if found else 'No match on this page: ') + query)
        self.window.operation_report('[Manual search 2/2] ' + ('Match selected' if found else 'No match'), 2, 2)

    def open_search(self):
        self.window.switch_category('TTP')
        self.window.focus_search()

    def open_selection(self):
        self.window.show_document_page()
        self.window.tabs.setCurrentIndex(self.window.selection_tab_index)

    def follow_link(self, url):
        parts = urlsplit(url.toString())
        if parts.scheme == 'studio':
            self.window.operation_report('Input files: None (explicit manual feature link); output files: None')
            self.window.operation_report('[Manual feature 1/2] Resolving ' + parts.netloc, 0, 2)
            feature = self.features.get(parts.netloc)
            if parts.netloc in ('versions', 'compare-versions') and self.window.catalog and self.window.catalog.dataset_id:
                self.status.setText('For custom datasets, use URL / custom STIX or reviewed layer upgrade instead of the official version picker.')
                self.window.operation_report('[Manual feature 2/2] Official release feature unavailable for a custom dataset', 2, 2)
                return
            if not feature or not self.window.loaded_ok or (feature[0] is not None and not feature[0].isEnabled()):
                self.status.setText('This feature is unavailable. Finish loading a supported document and retry.')
                self.window.operation_report('[Manual feature 2/2] Unavailable for the current workspace', 2, 2)
                return
            self.window.operation_report('[Manual feature 2/2] Opening ' + parts.netloc, 2, 2)
            feature[1]()
        elif parts.scheme in ('http', 'https') and parts.netloc and not url.userInfo():
            self.window.operation_report('Input URL: ' + url.toString())
            self.window.operation_report('Output files: None (open browser from explicit manual link)')
            self.window.operation_report('[Manual link 1/2] Opening website', 1, 2)
            opened = QtGui.QDesktopServices.openUrl(url)
            self.window.operation_report('[Manual link 2/2] ' + ('Complete' if opened else 'Could not open browser'), 2, 2)
            if not opened:
                self.status.setText('Could not open browser. Copy this URL: ' + url.toString())
        elif (parts.scheme == 'file' and not parts.netloc) or (not parts.scheme and not parts.netloc):
            path = (Path(url.toLocalFile()) if parts.scheme == 'file' else
                    self.current_path.parent / unquote(parts.path) if parts.path else self.current_path)
            if path.resolve() == MANUAL_ROOT / 'README.md':
                path = manual_index()
            elif path.resolve() == ROOT / 'README.md':
                path = MANUAL_ROOT / ('installation+_zh.md' if language() == 'zh_TW' else 'installation_en.md')
            self.load_page(path, unquote(parts.fragment))
        else:
            self.status.setText('Unsupported manual link: ' + url.toString())


class ManualWorkspace:
    @property
    def manual_tab_index(self):
        return next((index for index in range(self.document_tabs.count())
                     if self.document_tabs.tabData(index) == MANUAL_TAB), -1)

    def open_manual(self):
        self.operation_report(f'Input file: {manual_home()}')
        self.operation_report('Output files: None (manual tab; current TTP document retained)')
        self.operation_report('[Manual tab 1/2] Opening operating manual', 0, 2)
        if getattr(self, 'manual_page', None) is None:
            self.manual_page = ManualPage(self)
            self.workspace.addWidget(self.manual_page)
        index = self.manual_tab_index
        if index < 0:
            previous = self.document_tabs.blockSignals(True)
            index = self.document_tabs.addTab('Manual')
            self.document_tabs.setTabData(index, MANUAL_TAB)
            self.document_tabs.setTabToolTip(index, 'Manual · outline, guides and feature shortcuts')
            close = QtWidgets.QToolButton(self.document_tabs)
            close.setText('×')
            close.setAccessibleName('Close manual')
            close.setToolTip('Close manual')
            close.setAutoRaise(True)
            close.setFixedSize(22, 22)
            close.clicked.connect(self.close_manual)
            self.document_tabs.setTabButton(index, QtWidgets.QTabBar.ButtonPosition.RightSide, close)
            self.document_tabs.blockSignals(previous)
        previous = self.document_tabs.blockSignals(True)
        self.document_tabs.setCurrentIndex(index)
        self.document_tabs.blockSignals(previous)
        self.workspace.setCurrentWidget(self.manual_page)
        self.restore_manual_view = True
        self.operation_report('[Manual tab 2/2] Ready', 2, 2)

    def close_manual(self):
        index = self.manual_tab_index
        if index < 0:
            return
        self.operation_report('Input files: None; output files: None (close manual tab)')
        self.operation_report('[Manual tab 1/2] Closing manual', 0, 2)
        visible = self.workspace.currentWidget() is self.manual_page
        previous = self.document_tabs.blockSignals(True)
        self.document_tabs.removeTab(index)
        self.document_tabs.blockSignals(previous)
        self.restore_manual_view = False
        if visible:
            self.show_document_page()
        self.operation_report('[Manual tab 2/2] Closed', 2, 2)
