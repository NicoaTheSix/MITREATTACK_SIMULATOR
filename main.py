"""VS Code-inspired ATT&CK desktop explorer. See README.md for workflow and paths."""
from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from attack_catalog import BROWSE_CATEGORIES, DOMAIN_LABELS, Catalog, external_id, load_catalog
from version_dialog import VersionDialog

ROLE_ID = int(QtCore.Qt.ItemDataRole.UserRole) + 1
ROLE_CONTEXT = ROLE_ID + 1
ROLE_SEARCH = ROLE_ID + 2

STYLE = """
QWidget { background: #1e1e1e; color: #d4d4d4; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow::separator, QSplitter::handle { background: #303030; width: 4px; height: 4px; }
QMenuBar, QMenu { background: #181818; } QMenuBar::item:selected, QMenu::item:selected { background: #37373d; }
QFrame#rail { background: #181818; border-right: 1px solid #303030; }
QWidget#sidebar, QWidget#sidebar QLabel { background: #252526; }
QLabel#section { color: #bbbbbb; font-size: 11px; font-weight: 600; padding: 12px 4px; }
QLabel#crumb { color: #999999; padding: 8px 14px; border-bottom: 1px solid #303030; }
QLabel#summary { color: #9da5b4; font-size: 11px; padding: 4px; }
QLineEdit { background: #3c3c3c; border: 1px solid #555555; padding: 7px; selection-background-color: #264f78; }
QLineEdit:focus { border-color: #007acc; }
QTreeView { background: #252526; border: none; outline: 0; }
QTreeView::item { height: 27px; } QTreeView::item:selected { background: #094771; color: #ffffff; }
QTreeView::item:hover { background: #2a2d2e; }
QTreeView::indicator { width: 13px; height: 13px; }
QTreeView::indicator:unchecked { border: 1px solid #858585; background: #252526; }
QTreeView::indicator:checked { border: 1px solid #3794ff; background: #007acc; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: #2d2d2d; color: #969696; padding: 10px 20px; border-right: 1px solid #181818; }
QTabBar::tab:selected { background: #1e1e1e; color: #ffffff; border-top: 2px solid #007acc; }
QTextBrowser { border: none; padding: 18px; selection-background-color: #264f78; }
QPlainTextEdit { border: none; font-family: 'Cascadia Code', 'Consolas'; font-size: 11px; background: #181818; padding: 8px; }
QListWidget { border: none; padding: 12px; } QListWidget::item { padding: 9px; }
QListWidget::item:selected { background: #094771; color: #ffffff; }
QPushButton, QToolButton { border: none; padding: 6px 9px; background: #333333; }
QPushButton:hover, QToolButton:hover { background: #444444; }
QToolButton:checked { color: #ffffff; border-left: 2px solid #007acc; background: #252526; }
QStatusBar, QStatusBar QLabel { background: #007acc; color: #ffffff; font-size: 11px; }
QProgressBar { border: none; background: #075b91; height: 7px; } QProgressBar::chunk { background: #a8dcff; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #424242; min-height: 22px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


class DetailBrowser(QtWidgets.QTextBrowser):
    """Native copy buttons follow their rich-text headings while the document scrolls."""
    copied = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.copy_content = {}
        self.copy_title_button = QtWidgets.QPushButton("Copy", self.viewport())
        self.copy_description_button = QtWidgets.QPushButton("Copy", self.viewport())
        self.copy_buttons = {"Title": self.copy_title_button, "Description": self.copy_description_button}
        self.copy_timers = {}
        for section, button in self.copy_buttons.items():
            button.setFixedSize(68, 26)
            button.setAccessibleName(f"Copy {section.lower()}")
            button.setToolTip(f"Copy only the {section.lower()} to the clipboard")
            button.hide()
            button.clicked.connect(lambda checked=False, name=section: self.copy_section(name))
            timer = QtCore.QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(1200)
            timer.timeout.connect(lambda target=button: target.setText("Copy"))
            self.copy_timers[section] = timer
        self.position_timer = QtCore.QTimer(self)
        self.position_timer.setSingleShot(True)
        self.position_timer.timeout.connect(self.position_copy_buttons)
        self.verticalScrollBar().valueChanged.connect(lambda: self.position_timer.start(0))
        self.horizontalScrollBar().valueChanged.connect(lambda: self.position_timer.start(0))
        self.document().contentsChanged.connect(lambda: self.position_timer.start(0))

    def setHtml(self, text):
        self.copy_content = {}
        for button in self.copy_buttons.values():
            button.hide()
        super().setHtml(text)

    def set_copy_content(self, title, description):
        self.copy_content = {"Title": title, "Description": description}
        for section, button in self.copy_buttons.items():
            self.copy_timers[section].stop()
            button.setText("Copy")
            button.setEnabled(bool(self.copy_content[section]))
        self.position_timer.start(0)

    def position_copy_buttons(self):
        for section, button in self.copy_buttons.items():
            needle = self.copy_content.get("Title", "") if section == "Title" else "Description"
            if not self.copy_content or not needle:
                button.hide()
                continue
            cursor = self.document().find(needle, 0, QtGui.QTextDocument.FindFlag.FindCaseSensitively)
            if cursor.isNull():
                button.hide()
                continue
            cursor.setPosition(cursor.selectionEnd())
            rect = self.cursorRect(cursor)
            x = min(rect.right() + 14, self.viewport().width() - button.width() - 16)
            y = rect.top() + max(0, (rect.height() - button.height()) // 2)
            visible = y >= 0 and y + button.height() <= self.viewport().height() and x > rect.right()
            button.move(x, y)
            button.setVisible(visible)
            button.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "position_timer"):
            self.position_timer.start(0)

    def copy_section(self, section):
        value = self.copy_content.get(section)
        if not value:
            return
        print(f"[Clipboard 1/2] Input files: None ({section} in memory); output files: None (system clipboard)", flush=True)
        QtWidgets.QApplication.clipboard().setText(value)
        print(f"[Clipboard 2/2] Complete: {section} copied", flush=True)
        self.copy_buttons[section].setText("Copied")
        self.copy_timers[section].start()
        self.copied.emit(section)

class CatalogLoader(QtCore.QThread):
    progress = QtCore.Signal(str, int, int)
    loaded = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, root: Path, parent=None, pointer_path=None):
        super().__init__(parent)
        self.root = root
        self.pointer_path = pointer_path or root / "latest.json"

    def report(self, message, current, total):
        if self.isInterruptionRequested():
            raise InterruptedError("Catalog loading cancelled")
        print(message + (f" ({current}/{total})" if total else ""), flush=True)
        self.progress.emit(message, current, total)

    def run(self):
        try:
            try:
                catalog = load_catalog(self.root, self.report, self.pointer_path)
            except InterruptedError:
                raise
            except Exception:
                if self.pointer_path.name != "active.json":
                    raise
                self.report("Saved version unavailable; loading latest.json instead", 0, 0)
                catalog = load_catalog(self.root, self.report)
            self.loaded.emit(catalog)
        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class MainWindow(QtWidgets.QMainWindow):
    ready = QtCore.Signal()

    def __init__(self, data_root: Path, pointer_path=None):
        super().__init__()
        self.data_root = data_root.resolve()
        self.version_dialog = None
        self.restore_category = "TTP"
        self.retained_selection = set()
        self.removed_selection_count = 0
        pointer_path = pointer_path or (self.data_root / "active.json" if (self.data_root / "active.json").exists() else self.data_root / "latest.json")
        self.setWindowTitle("MITRE ATT&CK Simulator")
        self.resize(1440, 920)
        self.setMinimumSize(900, 600)
        self.catalog: Catalog | None = None
        self.items_by_id = {}
        self.selected = set()
        self.syncing = False
        self.closing = False
        self.loaded_ok = False
        self.build_queue = []
        self.build_index = 0
        self.platform_items = {}
        self.active_category = "TTP"
        self.library_models = {}
        self.library_queue = []
        self.library_index = 0
        self.library_items = {}
        self.build_timer = QtCore.QTimer(self)
        self.build_timer.timeout.connect(self.build_batch)
        self.build_ui()
        self.loader = CatalogLoader(self.data_root, self, pointer_path)
        self.loader.progress.connect(self.report)
        self.loader.loaded.connect(self.begin_tree)
        self.loader.failed.connect(self.load_failed)
        self.loader.finished.connect(self.loader_finished)
        self.report(f"Input file: {pointer_path.resolve()}", 0, 0)
        self.report("Output files: None (selections stay in memory)", 0, 0)
        QtCore.QTimer.singleShot(0, self.loader.start)

    def build_ui(self):
        file_menu = self.menuBar().addMenu("File")
        quit_action = file_menu.addAction("Exit")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        view_menu = self.menuBar().addMenu("View")
        sidebar_action = view_menu.addAction("Toggle ATT&CK Explorer")
        sidebar_action.setShortcut("Ctrl+B")
        sidebar_action.triggered.connect(lambda: self.sidebar.setVisible(not self.sidebar.isVisible()))
        output_action = view_menu.addAction("Toggle Output")
        output_action.setShortcut("Ctrl+J")
        output_action.triggered.connect(lambda: self.output_panel.setVisible(not self.output_panel.isVisible()))
        search_action = view_menu.addAction("Search Techniques")
        search_action.setShortcut("Ctrl+F")
        search_action.triggered.connect(self.focus_search)

        self.version_action = self.menuBar().addAction("Version")
        self.version_action.setToolTip("Choose an official ATT&CK version")
        self.version_action.setEnabled(False)
        self.version_action.triggered.connect(self.open_versions)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        rail = QtWidgets.QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(140)
        rail_layout = QtWidgets.QVBoxLayout(rail)
        rail_layout.setContentsMargins(0, 8, 0, 0)
        rail_layout.setSpacing(4)
        self.navigation_group = QtWidgets.QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        self.navigation_buttons = {}
        for category in ("TTP", *BROWSE_CATEGORIES):
            button = QtWidgets.QToolButton()
            button.setText(category)
            button.setToolTip("ATT&CK techniques" if category == "TTP" else category)
            button.setCheckable(True)
            button.setEnabled(category == "TTP")
            button.setFixedSize(140, 46)
            button.setStyleSheet("QToolButton { text-align: left; padding-left: 16px; background: #181818; }"
                                "QToolButton:checked { color: #ffffff; background: #252526; border-left: 2px solid #007acc; }")
            self.navigation_group.addButton(button)
            self.navigation_buttons[category] = button
            button.clicked.connect(lambda checked=False, name=category: self.switch_category(name))
            rail_layout.addWidget(button)
        self.rail_button = self.navigation_buttons["TTP"]
        self.rail_button.setChecked(True)
        rail_layout.addStretch()
        layout.addWidget(rail)
        self.horizontal = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        layout.addWidget(self.horizontal)
        self.sidebar = QtWidgets.QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(270)
        side_layout = QtWidgets.QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(12, 0, 8, 8)
        self.sidebar_title = QtWidgets.QLabel("ATT&CK EXPLORER")
        self.sidebar_title.setObjectName("section")
        side_layout.addWidget(self.sidebar_title)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search technique name or ID…")
        self.search.setClearButtonEnabled(True)
        self.search.setEnabled(False)
        side_layout.addWidget(self.search)
        self.summary = QtWidgets.QLabel("Enterprise · Loading catalog…")
        self.summary.setObjectName("summary")
        side_layout.addWidget(self.summary)
        self.model = QtGui.QStandardItemModel(self)
        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterRole(ROLE_SEARCH)
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setRecursiveFilteringEnabled(True)
        self.proxy.setAutoAcceptChildRows(True)
        self.tree = QtWidgets.QTreeView()
        self.tree.setHeaderHidden(True)
        self.tree.setModel(self.proxy)
        self.tree.setUniformRowHeights(True)
        self.tree.setIndentation(16)
        self.tree.setAnimated(False)
        self.tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.selectionModel().currentChanged.connect(self.show_index)
        self.model.itemChanged.connect(self.check_changed)
        self.library_proxy = QtCore.QSortFilterProxyModel(self)
        self.library_proxy.setFilterRole(ROLE_SEARCH)
        self.library_proxy.setFilterCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.library_proxy.setRecursiveFilteringEnabled(True)
        self.library_proxy.setAutoAcceptChildRows(True)
        self.library_tree = QtWidgets.QTreeView()
        self.library_tree.setHeaderHidden(True)
        self.library_tree.setModel(self.library_proxy)
        self.library_tree.setUniformRowHeights(True)
        self.library_tree.setIndentation(16)
        self.library_tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.library_tree.selectionModel().currentChanged.connect(self.show_library_index)
        self.explorer_stack = QtWidgets.QStackedWidget()
        self.explorer_stack.addWidget(self.tree)
        self.explorer_stack.addWidget(self.library_tree)
        side_layout.addWidget(self.explorer_stack)
        collapse = QtWidgets.QPushButton("Collapse all")
        collapse.clicked.connect(lambda: (self.tree if self.active_category == "TTP" else self.library_tree).collapseAll())
        side_layout.addWidget(collapse)
        self.horizontal.addWidget(self.sidebar)
        self.search_timer = QtCore.QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search_timer.timeout.connect(self.apply_search)
        self.search.textChanged.connect(lambda: self.search_timer.start())

        self.vertical = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.horizontal.addWidget(self.vertical)
        editor = QtWidgets.QWidget()
        editor_layout = QtWidgets.QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        self.tabs = QtWidgets.QTabWidget()
        details = QtWidgets.QWidget()
        details_layout = QtWidgets.QVBoxLayout(details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        self.crumb = QtWidgets.QLabel("Enterprise  /  ATT&CK Explorer")
        self.crumb.setObjectName("crumb")
        details_layout.addWidget(self.crumb)
        self.details = DetailBrowser()
        self.details.copied.connect(lambda section: self.state.setText(f"Copied {section.lower()} to clipboard"))
        self.details.setOpenExternalLinks(False)
        self.details.setOpenLinks(False)
        self.details.anchorClicked.connect(self.open_detail_link)
        self.details.setHtml("<h1>ATT&CK Explorer</h1><p>Browse Platform → Tactic → Technique in the sidebar.</p>"
                             "<p>Select a technique to inspect its description. Check its box to add it to the selection.</p>"
                             "<p style='color:#999999'>Loading the local Enterprise catalog…</p>")
        details_layout.addWidget(self.details)
        self.tabs.addTab(details, "Technique Details")
        selection_page = QtWidgets.QWidget()
        selection_layout = QtWidgets.QVBoxLayout(selection_page)
        selection_layout.addWidget(QtWidgets.QLabel("Selected technique IDs · in memory"))
        self.selection_list = QtWidgets.QListWidget()
        self.selection_list.itemClicked.connect(self.show_selected)
        selection_layout.addWidget(self.selection_list)
        clear = QtWidgets.QPushButton("Clear selection")
        clear.clicked.connect(self.clear_selection)
        selection_layout.addWidget(clear)
        self.tabs.addTab(selection_page, "Selected Techniques (0)")
        editor_layout.addWidget(self.tabs)
        self.vertical.addWidget(editor)
        self.output_panel = QtWidgets.QWidget()
        output_layout = QtWidgets.QVBoxLayout(self.output_panel)
        output_layout.setContentsMargins(12, 0, 12, 0)
        label = QtWidgets.QLabel("OUTPUT  ·  Catalog loading")
        label.setObjectName("section")
        output_layout.addWidget(label)
        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(1000)
        output_layout.addWidget(self.output)
        self.vertical.addWidget(self.output_panel)
        self.horizontal.setSizes([420, 970])
        self.vertical.setSizes([660, 180])
        self.horizontal.setStretchFactor(1, 1)
        self.vertical.setStretchFactor(0, 1)
        self.setCentralWidget(central)
        self.state = QtWidgets.QLabel("Loading Enterprise ATT&CK")
        self.statusBar().addWidget(self.state, 1)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(140)
        self.statusBar().addPermanentWidget(self.progress_bar)
        self.version_label = QtWidgets.QLabel("Enterprise")
        self.statusBar().addPermanentWidget(self.version_label)

    @QtCore.Slot(str, int, int)
    def report(self, message, current=0, total=0):
        self.output.appendPlainText(message + (f" ({current}/{total})" if total else ""))
        self.state.setText(message)
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)

    def open_versions(self):
        if self.version_dialog and self.version_dialog.isVisible():
            self.version_dialog.raise_()
            return
        if self.version_dialog:
            self.version_dialog.deleteLater()
        self.version_dialog = VersionDialog(self.data_root, self.catalog.version if self.catalog else None, self)
        self.version_dialog.chosen.connect(self.apply_version)
        self.version_dialog.show()

    def apply_version(self, value):
        catalog, pointer = value
        self.version_action.setEnabled(False)
        self.search.setEnabled(False)
        for button in self.navigation_buttons.values():
            button.setEnabled(False)
        self.begin_tree(catalog)

    def focus_search(self):
        self.sidebar.setVisible(True)
        self.search.setFocus()

    def load_failed(self, message):
        self.version_action.setEnabled(True)
        self.report(f"Failed: {message}", 1, 1)
        print(f"Failed: {message}", flush=True)
        self.details.setHtml(f"<h2>Catalog could not be loaded</h2><p>{html.escape(message)}</p>"
                             "<p>Check data/attack/latest.json and the downloaded snapshot. See README.md.</p>")

    def begin_tree(self, catalog):
        if self.closing:
            return
        self.syncing = True
        self.restore_category = self.active_category
        self.retained_selection = self.selected.intersection(catalog.records)
        self.removed_selection_count = len(self.selected - self.retained_selection)
        self.selected = set()
        self.loaded_ok = False
        self.search_timer.stop()
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.proxy.setFilterFixedString("")
        self.library_proxy.setSourceModel(None)
        self.model.clear()
        for model in self.library_models.values():
            model.deleteLater()
        self.items_by_id = {}
        self.platform_items = {}
        self.library_models = {}
        self.library_items = {}
        self.build_queue = []
        self.library_queue = []
        self.build_index = self.library_index = 0
        self.active_category = "TTP"
        self.navigation_buttons["TTP"].setChecked(True)
        self.explorer_stack.setCurrentIndex(0)
        self.selection_list.clear()
        self.details.setHtml("<h1>Loading ATT&CK v" + html.escape(catalog.version) + "</h1><p>Building the selected version…</p>")
        self.catalog = catalog
        self.children_by_parent = {}
        for child, parent in catalog.parents.items():
            self.children_by_parent.setdefault(parent, []).append(child)
        self.syncing = True
        for category, kinds in BROWSE_CATEGORIES.items():
            model = QtGui.QStandardItemModel(self)
            self.library_models[category] = model
            self.library_items[category] = []
            for domain, domain_label in DOMAIN_LABELS.items():
                records = catalog.objects_by_domain[domain]
                found = [(kind, label, sorted((obj for obj in records.values() if obj.get("type") == kind),
                                              key=lambda obj: (external_id(obj), obj.get("name", "").casefold())))
                         for kind, label in kinds.items()]
                if not any(objects for _, _, objects in found):
                    continue
                domain_item = self.make_item(domain_label, context=(domain, "", ""))
                model.appendRow(domain_item)
                for kind, label, objects in found:
                    if not objects:
                        continue
                    group = domain_item
                    if len(kinds) > 1:
                        group = self.make_item(f"{label} ({len(objects)})", context=(domain, kind, ""))
                        domain_item.appendRow(group)
                    for start in range(0, len(objects), 100):
                        self.library_queue.append((category, domain, kind, group, objects[start:start + 100]))
        for platform, tactics in catalog.groups.items():
            platform_item = self.make_item(platform, context=(platform, "", ""))
            self.model.appendRow(platform_item)
            self.platform_items[platform] = platform_item
            for slug, ids in tactics.items():
                self.build_queue.append((platform, slug, ids))
        self.report("[4/4 Tree] Building Platform → Tactic → Technique", 0, len(self.build_queue))
        self.build_timer.start(0)

    def make_item(self, text, stix_id=None, context=None, selectable=True):
        item = QtGui.QStandardItem(text)
        item.setEditable(False)
        item.setData(text, ROLE_SEARCH)
        item.setData(context, ROLE_CONTEXT)
        if stix_id:
            item.setData(stix_id, ROLE_ID)
            if selectable:
                item.setCheckable(True)
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)
                self.items_by_id.setdefault(stix_id, []).append(item)
            item.setToolTip(text + ("" if selectable else "\nParent grouping only; not mapped to this platform/tactic"))
        return item

    def build_batch(self):
        if self.closing:
            self.build_timer.stop()
            return
        for _ in range(4):
            if self.build_index >= len(self.build_queue):
                self.build_library_batch()
                return
            platform, slug, ids = self.build_queue[self.build_index]
            tactic = self.catalog.tactics[slug]
            tactic_item = self.make_item(f"{external_id(tactic)}  {tactic['name']}", context=(platform, slug, ""))
            if tactic.get("_historical_phase"):
                tactic_item.setToolTip("Historical phase heading derived from this release; no official tactic ID in the bundle")
            self.platform_items[platform].appendRow(tactic_item)
            id_set = set(ids)
            parent_items = {}
            top_ids = sorted({self.catalog.parents.get(key, key) for key in ids},
                             key=lambda key: external_id(self.catalog.records[key]))
            for key in top_ids:
                record = self.catalog.records[key]
                item = self.make_item(f"{external_id(record)}  {record['name']}", key,
                                      (platform, slug, key), key in id_set)
                tactic_item.appendRow(item)
                parent_items[key] = item
                children = self.children_by_parent.get(key, [])
                if children:
                    mapped = sum(child in id_set for child in children)
                    item.setToolTip(item.toolTip() + f"\nSub-techniques in this branch: {mapped}/{len(children)}"
                                    "\nOther sub-techniques are listed under their mapped platforms/tactics.")
            for key in ids:
                parent = self.catalog.parents.get(key)
                if parent:
                    record = self.catalog.records[key]
                    parent_items[parent].appendRow(self.make_item(f"{external_id(record)}  {record['name']}",
                                                                  key, (platform, slug, key)))
            self.build_index += 1
        self.report("[4/4 Tree] Building explorer branches", self.build_index, len(self.build_queue))

    def build_library_batch(self):
        for _ in range(4):
            if self.library_index >= len(self.library_queue):
                self.finish_tree()
                return
            category, domain, kind, group, objects = self.library_queue[self.library_index]
            for obj in objects:
                key = obj["id"]
                label = f"{external_id(obj)}  {obj.get('name', key)}".strip()
                item = self.make_item(label, context=(domain, kind, key))
                item.setData(key, ROLE_ID)
                item.setToolTip(label)
                group.appendRow(item)
                self.library_items[category].append(item)
            self.library_index += 1
        self.report("[4/4 Library] Building navigation lists", self.library_index, len(self.library_queue))

    def finish_tree(self):
        self.build_timer.stop()
        self.syncing = False
        self.loaded_ok = True
        self.search.setEnabled(True)
        for button in self.navigation_buttons.values():
            button.setEnabled(True)
        self.summary.setText(f"Enterprise v{self.catalog.version} · {len(self.catalog.groups)} platforms")
        self.version_label.setText(f"ATT&CK v{self.catalog.version}  |  Enterprise")
        self.report("[4/4 Tree] Complete", 1, 1)
        print(f"[4/4 Tree] Complete: {len(self.items_by_id)} unique selectable technique IDs", flush=True)
        windows = self.platform_items.get("Windows", next(iter(self.platform_items.values())))
        index = self.proxy.mapFromSource(windows.index())
        self.tree.expand(index)
        for row in range(windows.rowCount()):
            tactic = windows.child(row)
            if tactic.data(ROLE_CONTEXT)[1] == "execution":
                self.tree.expand(self.proxy.mapFromSource(tactic.index()))
                if tactic.rowCount():
                    item = tactic.child(0)
                    self.tree.setCurrentIndex(self.proxy.mapFromSource(item.index()))
                break
        self.syncing = True
        self.selected = self.retained_selection.intersection(self.items_by_id)
        for key in self.selected:
            for item in self.items_by_id[key]:
                item.setCheckState(QtCore.Qt.CheckState.Checked)
        self.syncing = False
        self.refresh_selection()
        self.switch_category(self.restore_category)
        self.version_action.setText(f"Version (v{self.catalog.version})")
        self.version_action.setEnabled(True)
        if self.removed_selection_count:
            self.report(f"[Version 4/4 Switch] {self.removed_selection_count} selected techniques unavailable in this version were removed", 1, 1)
        self.report(f"[Version 4/4 Switch] Ready: v{self.catalog.version}; {len(self.selected)} selections retained", 1, 1)
        self.ready.emit()

    def switch_category(self, category):
        if not self.loaded_ok:
            return
        self.active_category = category
        self.navigation_buttons[category].setChecked(True)
        self.sidebar.setVisible(True)
        self.search_timer.stop()
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.proxy.setFilterFixedString("")
        self.library_proxy.setFilterFixedString("")
        self.tabs.setCurrentIndex(0)
        self.tabs.setTabText(0, "Technique Details" if category == "TTP" else f"{category} Details")
        if category == "TTP":
            self.explorer_stack.setCurrentIndex(0)
            self.sidebar_title.setText("ATT&CK EXPLORER")
            self.search.setPlaceholderText("Search technique name or ID…")
            self.summary.setText(f"Enterprise v{self.catalog.version} · {len(self.catalog.groups)} platforms")
            self.version_label.setText(f"ATT&CK v{self.catalog.version}  |  Enterprise")
            if self.tree.currentIndex().isValid():
                self.show_index(self.tree.currentIndex())
        else:
            self.library_proxy.setSourceModel(self.library_models[category])
            self.explorer_stack.setCurrentIndex(1)
            self.sidebar_title.setText(category.upper())
            self.search.setPlaceholderText(f"Search {category.lower()} name or ID…")
            count = len(self.library_items[category])
            self.summary.setText(f"ATT&CK v{self.catalog.version} · {count} entries across domains")
            self.version_label.setText(f"ATT&CK v{self.catalog.version}  |  {category}")
            self.crumb.setText(f"ATT&CK  /  {category}")
            self.details.setHtml(f"<h1>{html.escape(category)}</h1>"
                                 "<p>Expand a domain and select an entry in the sidebar.</p>"
                                 f"<p>{count} active entries in the local snapshot.</p>"
                                 + ("<p>Assets describe ICS devices and systems.</p>" if category == "Assets" else ""))
            self.library_tree.expandToDepth(0)
        self.state.setText(f"Ready  |  {category}  |  {len(self.selected)} techniques selected")

    def show_library_index(self, index, previous=None):
        if not index.isValid() or not self.catalog or self.active_category == "TTP":
            return
        item = self.library_proxy.sourceModel().itemFromIndex(self.library_proxy.mapToSource(index))
        domain, kind, key = item.data(ROLE_CONTEXT)
        self.crumb.setText(f"{DOMAIN_LABELS[domain]}  /  {self.active_category}  /  {external_id(self.catalog.objects_by_domain[domain][key]) if key else item.text()}")
        if not key:
            self.details.setHtml(f"<h1>{html.escape(item.text())}</h1><p>Expand this branch to browse its entries.</p>")
            return
        obj = self.catalog.objects_by_domain[domain][key]
        kind_label = BROWSE_CATEGORIES[self.active_category][kind]
        metadata = [("Domain", DOMAIN_LABELS[domain]), ("Type", kind_label)]
        for name, field in (("Platforms", "x_mitre_platforms"), ("Aliases", "aliases"),
                            ("Version", "x_mitre_version"), ("Created", "created"), ("Modified", "modified")):
            value = obj.get(field)
            if value:
                metadata.append((name, ", ".join(value) if isinstance(value, list) else str(value)))
        meta = "".join(f"<p><b>{name}</b> &nbsp; {html.escape(value)}</p>" for name, value in metadata)
        refs = [ref for ref in obj.get("external_references", []) if ref.get("source_name", "").startswith("mitre")]
        url = next((ref.get("url", "") for ref in refs if ref.get("url", "").startswith("https://attack.mitre.org/")), "")
        self.details.document().setDefaultStyleSheet("body {color:#d4d4d4;} h1 {font-size:26px;color:#ffffff;margin-right:90px;} "
                                                     "h2 {font-size:16px;color:#eeeeee;} a {color:#4daafc;}")
        self.details.setHtml(f"<p style='color:#4daafc'>{html.escape(external_id(obj))} · {html.escape(kind_label)}</p>"
                             f"<h1>{html.escape(obj.get('name', key))}</h1>{meta}<hr><h2>Description</h2>"
                             f"<p>{html.escape(obj.get('description') or 'No description in this local record.').replace(chr(10), '<br>')}</p>"
                             + (f"<p><a href='{html.escape(url, quote=True)}'>Open official ATT&CK reference ↗</a></p>" if url else ""))
        self.details.set_copy_content(obj.get("name", key), obj.get("description", ""))

    def apply_search(self):
        if self.active_category != "TTP":
            self.library_proxy.setFilterFixedString(self.search.text().strip())
            if self.search.text().strip():
                self.library_tree.expandAll()
            else:
                self.library_tree.collapseAll()
                self.library_tree.expandToDepth(0)
            return
        self.proxy.setFilterFixedString(self.search.text().strip())
        if self.search.text().strip():
            self.tree.expandAll()
        else:
            self.tree.collapseAll()
            if "Windows" in self.platform_items:
                self.tree.expand(self.proxy.mapFromSource(self.platform_items["Windows"].index()))

    def show_index(self, index, previous=None):
        if not index.isValid() or not self.catalog:
            return
        item = self.model.itemFromIndex(self.proxy.mapToSource(index))
        context = item.data(ROLE_CONTEXT)
        key = item.data(ROLE_ID)
        platform, slug, _ = context
        if key:
            self.show_record(key, platform, slug)
        else:
            self.crumb.setText("Enterprise  /  " + platform + ("  /  " + self.catalog.tactics[slug]["name"] if slug else ""))
            self.details.setHtml(f"<h1>{html.escape(item.text())}</h1>"
                                 "<p>Expand this branch to browse its mapped techniques.</p>")

    def show_record(self, key, platform="", slug=""):
        record = self.catalog.records[key]
        self.detail_context = (platform, slug)
        related = self.related_techniques_html(key, platform, slug)
        self.crumb.setText("  /  ".join(part for part in ("Enterprise", platform,
                           self.catalog.tactics[slug]["name"] if slug else "", external_id(record)) if part))
        phases = [self.catalog.tactics[phase["phase_name"]]["name"] for phase in record.get("kill_chain_phases", [])
                  if phase.get("kill_chain_name") == "mitre-attack" and phase["phase_name"] in self.catalog.tactics]
        refs = [ref for ref in record.get("external_references", []) if ref.get("source_name") == "mitre-attack"]
        url = next((ref.get("url", "") for ref in refs), "")
        self.details.document().setDefaultStyleSheet("body {color:#d4d4d4;} h1 {font-size:26px;color:#ffffff;margin-right:90px;} "
                                                     "h2 {font-size:16px;color:#eeeeee;} a {color:#4daafc;} p {line-height:1.5;}")
        self.details.setHtml(f"<p style='color:#4daafc'>{html.escape(external_id(record))} · "
                             f"{'Sub-technique' if record.get('x_mitre_is_subtechnique') else 'Technique'}</p>"
                             f"<h1>{html.escape(record['name'])}</h1>"
                             f"<p><b>Platforms</b> &nbsp; {html.escape(', '.join(record.get('x_mitre_platforms', [])))}</p>"
                             f"<p><b>Tactics</b> &nbsp; {html.escape(', '.join(phases))}</p>"
                             "<p style='color:#999999'>Catalog entry · behavior module not implemented</p>"
                             f"{related}<hr><h2>Description</h2>"
                             f"<p>{html.escape(record.get('description', '')).replace(chr(10), '<br>')}</p>"
                             f"<p><a href='{html.escape(url, quote=True)}'>Open official ATT&CK reference ↗</a></p>"
                             + self.procedure_examples_html(key))
        self.details.set_copy_content(record["name"], record.get("description", ""))

    def procedure_examples_html(self, key):
        examples = self.catalog.procedures_by_domain["enterprise-attack"].get(key, [])
        if not examples:
            return "<hr><h2>Procedure Examples (0)</h2><p>No active procedure examples in this local snapshot.</p>"
        rows = []
        for example in examples:
            target = f"library:enterprise-attack/{example['source_ref']}"
            reference_links = []
            for reference in example["references"]:
                url = reference.get("url", "")
                if url.startswith("https://"):
                    reference_links.append(f"<a href='{html.escape(url, quote=True)}'>"
                                           f"{html.escape(reference.get('source_name', 'Reference'))}</a>")
            description = html.escape(example["description"] or "No procedure description in this source relationship.").replace(chr(10), "<br>")
            rows.append(f"<tr><td valign='top'>{html.escape(example['source_id'])}</td>"
                        f"<td valign='top'><a href='{html.escape(target, quote=True)}'>{html.escape(example['source_name'])}</a></td>"
                        f"<td>{description}" + ("<br>" + " · ".join(reference_links) if reference_links else "") + "</td></tr>")
        return (f"<hr><h2>Procedure Examples ({len(examples)})</h2>"
                "<table cellspacing='0' cellpadding='6' border='1' width='100%'><tr>"
                "<th align='left'>ID</th><th align='left'>Name</th><th align='left'>Description</th></tr>"
                + "".join(rows) + "</table>")

    def related_techniques_html(self, key, platform, slug):
        parent = self.catalog.parents.get(key, key)
        children = sorted(self.children_by_parent.get(parent, []),
                          key=lambda child: external_id(self.catalog.records[child]))
        if not children:
            return ""
        record = self.catalog.records[parent]
        context_ids = set(self.catalog.groups.get(platform, {}).get(slug, []))
        parent_link = (f"<p><b>Parent technique</b> &nbsp; <a href='attack:{parent}'>"
                       f"{html.escape(external_id(record) + ' ' + record['name'])}</a></p>" if key != parent else "")
        scope = (f"<p style='color:#aaaaaa'>{sum(child in context_ids for child in children)} of {len(children)} "
                 f"active sub-techniques are mapped to {html.escape(platform)} / "
                 f"{html.escape(self.catalog.tactics[slug]['name'])}. "
                 "The table lists all platforms; the explorer branch shows its mapped entries.</p>"
                 if platform and slug else f"<p>{len(children)} active sub-techniques across all platforms.</p>")
        rows = []
        for child in children:
            obj = self.catalog.records[child]
            status = "In this branch" if child in context_ids else "Other platform/tactic"
            rows.append(f"<tr><td><a href='attack:{child}'>"
                        f"{html.escape(external_id(obj) + ' ' + obj['name'])}</a></td>"
                        f"<td>{html.escape(', '.join(obj.get('x_mitre_platforms', [])))}</td>"
                        + (f"<td>{status}</td>" if platform and slug else "") + "</tr>")
        return (parent_link + "<h2>Sub-techniques</h2>" + scope
                + "<table cellspacing='0' cellpadding='6' border='1'><tr><th align='left'>ID / Name</th>"
                "<th align='left'>Platforms</th>" + ("<th align='left'>Current branch</th>" if platform and slug else "")
                + "</tr>" + "".join(rows) + "</table>")

    def open_detail_link(self, url):
        if url.scheme() == "attack":
            if self.active_category != "TTP":
                self.switch_category("TTP")
            key = url.path()
            items = self.items_by_id.get(key, [])
            if not items:
                return
            platform, slug = getattr(self, "detail_context", ("", ""))
            item = next((item for item in items if item.data(ROLE_CONTEXT)[:2] == (platform, slug)), None)
            if item is None:
                item = next((item for item in items if item.data(ROLE_CONTEXT)[0] == platform), items[0])
            if self.search.text():
                self.search.clear()
                self.search_timer.stop()
                self.apply_search()
            index = self.proxy.mapFromSource(item.index())
            parent_index = index.parent()
            while parent_index.isValid():
                self.tree.expand(parent_index)
                parent_index = parent_index.parent()
            self.tree.setCurrentIndex(index)
            self.tree.scrollTo(index)
            platform, slug, _ = item.data(ROLE_CONTEXT)
            self.show_record(key, platform, slug)
            self.tabs.setCurrentIndex(0)
        elif url.scheme() == "library":
            domain, separator, key = url.path().partition("/")
            obj = self.catalog.objects_by_domain.get(domain, {}).get(key)
            if not separator or obj is None:
                return
            category = next((name for name, kinds in BROWSE_CATEGORIES.items() if obj.get("type") in kinds), None)
            if category is None:
                return
            self.switch_category(category)
            item = next((item for item in self.library_items[category]
                         if item.data(ROLE_CONTEXT)[0] == domain and item.data(ROLE_ID) == key), None)
            if item is not None:
                index = self.library_proxy.mapFromSource(item.index())
                parent_index = index.parent()
                while parent_index.isValid():
                    self.library_tree.expand(parent_index)
                    parent_index = parent_index.parent()
                self.library_tree.setCurrentIndex(index)
                self.library_tree.scrollTo(index)
                self.show_library_index(index)
        elif url.scheme() == "https":
            QtGui.QDesktopServices.openUrl(url)

    def check_changed(self, item):
        if self.syncing or not item.isCheckable():
            return
        key = item.data(ROLE_ID)
        checked = item.checkState() == QtCore.Qt.CheckState.Checked
        self.syncing = True
        for duplicate in self.items_by_id[key]:
            duplicate.setCheckState(item.checkState())
        self.syncing = False
        if checked:
            self.selected.add(key)
        else:
            self.selected.discard(key)
        self.refresh_selection()

    def refresh_selection(self):
        self.selection_list.clear()
        for key in sorted(self.selected, key=lambda key: external_id(self.catalog.records[key])):
            record = self.catalog.records[key]
            item = QtWidgets.QListWidgetItem(f"{external_id(record)}  {record['name']}")
            item.setData(ROLE_ID, key)
            self.selection_list.addItem(item)
        self.tabs.setTabText(1, f"Selected Techniques ({len(self.selected)})")
        self.state.setText(f"Ready  |  {len(self.selected)} selected")

    def show_selected(self, item):
        self.switch_category("TTP")
        self.show_record(item.data(ROLE_ID))
        self.tabs.setCurrentIndex(0)

    def clear_selection(self):
        self.syncing = True
        for key in self.selected:
            for item in self.items_by_id[key]:
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)
        self.selected.clear()
        self.syncing = False
        self.refresh_selection()

    def loader_finished(self):
        if self.closing:
            self.close()

    def closeEvent(self, event):
        self.build_timer.stop()
        if self.version_dialog and self.version_dialog.worker and self.version_dialog.worker.isRunning():
            self.closing = True
            self.version_dialog.worker.requestInterruption()
            self.version_dialog.worker.finished.connect(self.close, QtCore.Qt.ConnectionType.SingleShotConnection)
            event.ignore()
            return
        if self.loader.isRunning():
            self.closing = True
            self.loader.requestInterruption()
            event.ignore()
            return
        event.accept()


def smoke_test(window, screenshot):
    """Exercise real mappings, ID search, duplicate selection, and rendered detail content."""
    try:
        print("[Verification 1/4] Checking platform/tactic/technique mappings", flush=True)
        catalog = window.catalog
        assert set(window.items_by_id) == set(catalog.records)
        for key, items in window.items_by_id.items():
            for item in items:
                platform, slug, _ = item.data(ROLE_CONTEXT)
                assert key in catalog.groups[platform][slug]
        child_id = next(key for key in window.items_by_id if external_id(catalog.records[key]) == "T1059.001")
        child = window.items_by_id[child_id][0]
        assert child.parent().data(ROLE_ID) == catalog.parents[child_id]
        print("[Verification 2/4] Checking recursive ID search", flush=True)
        window.search.setText("T1059.001")
        window.search_timer.stop()
        window.apply_search()
        assert window.proxy.mapFromSource(child.index()).isValid()
        window.search.setText("nonexistent-technique-zzzz")
        window.search_timer.stop()
        window.apply_search()
        assert window.proxy.rowCount() == 0
        window.search.clear()
        window.search_timer.stop()
        window.apply_search()
        print("[Verification 3/4] Checking synchronized and independent selection", flush=True)
        child.setCheckState(QtCore.Qt.CheckState.Checked)
        assert window.selected == {child_id}
        assert all(item.checkState() == QtCore.Qt.CheckState.Checked for item in window.items_by_id[child_id])
        assert catalog.parents[child_id] not in window.selected
        window.clear_selection()
        assert not window.selected
        assert all(item.checkState() == QtCore.Qt.CheckState.Unchecked for item in window.items_by_id[child_id])
        print("[Verification 4/4] Checking technique detail rendering", flush=True)
        item = next(item for item in window.items_by_id[child_id] if item.data(ROLE_CONTEXT)[0] == "Windows")
        index = window.proxy.mapFromSource(item.index())
        parent = index.parent()
        while parent.isValid():
            window.tree.expand(parent)
            parent = parent.parent()
        window.tree.setCurrentIndex(index)
        window.tree.scrollTo(index)
        assert "PowerShell" in window.details.toPlainText()
        def finish():
            try:
                if screenshot:
                    screenshot.parent.mkdir(parents=True, exist_ok=True)
                    if not window.grab().save(str(screenshot)):
                        raise RuntimeError("Could not save screenshot")
                    print(f"[Preview] Saved: {screenshot}", flush=True)
                print("[Verification] PASS", flush=True)
                window.close()
                QtWidgets.QApplication.instance().exit(0)
            except Exception as error:
                print(f"[Verification] FAIL: {error}", flush=True)
                window.close()
                QtWidgets.QApplication.instance().exit(1)
        QtCore.QTimer.singleShot(250, finish)
    except Exception as error:
        print(f"[Verification] FAIL: {type(error).__name__}: {error}", flush=True)
        window.close()
        QtWidgets.QApplication.instance().exit(1)


def configure_application(app):
    """Use explicit colors for consistent text contrast on Windows and offscreen previews."""
    app.setStyle("Fusion")
    palette = QtGui.QPalette()
    colors = {
        QtGui.QPalette.ColorRole.Window: "#1e1e1e",
        QtGui.QPalette.ColorRole.WindowText: "#d4d4d4",
        QtGui.QPalette.ColorRole.Base: "#252526",
        QtGui.QPalette.ColorRole.AlternateBase: "#2d2d2d",
        QtGui.QPalette.ColorRole.Text: "#d4d4d4",
        QtGui.QPalette.ColorRole.Button: "#333333",
        QtGui.QPalette.ColorRole.ButtonText: "#d4d4d4",
        QtGui.QPalette.ColorRole.Highlight: "#094771",
        QtGui.QPalette.ColorRole.HighlightedText: "#ffffff",
        QtGui.QPalette.ColorRole.ToolTipBase: "#252526",
        QtGui.QPalette.ColorRole.ToolTipText: "#ffffff",
        QtGui.QPalette.ColorRole.Link: "#4daafc",
    }
    for role, color in colors.items():
        palette.setColor(role, QtGui.QColor(color))
    palette.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.Text, QtGui.QColor("#999999"))
    app.setPalette(palette)
    if app.platformName() == "offscreen":
        font_root = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf"):
            font_path = font_root / name
            if font_path.is_file():
                print(f"[Preview fonts] Input file: {font_path}", flush=True)
                if QtGui.QFontDatabase.addApplicationFont(str(font_path)) < 0:
                    print(f"[Preview fonts] Could not load {font_path}", flush=True)
        print("[Preview fonts] Complete", flush=True)
    app.setFont(QtGui.QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "data" / "attack")
    parser.add_argument("--smoke-test", action="store_true", help="Verify UI behavior and exit")
    parser.add_argument("--screenshot", type=Path, help="Save a preview during --smoke-test")
    args = parser.parse_args()
    if args.screenshot and not args.smoke_test:
        parser.error("--screenshot requires --smoke-test")
    root = args.data_dir.expanduser().resolve()
    screenshot = args.screenshot.expanduser().resolve() if args.screenshot else None
    print(f"Python executable: {Path(sys.executable).resolve()}", flush=True)
    startup_pointer = root / "active.json" if (root / "active.json").exists() else root / "latest.json"
    print(f"Input file: {startup_pointer}", flush=True)
    print(f"Output files: {screenshot if screenshot else 'None (in-memory UI)'}", flush=True)
    app = QtWidgets.QApplication(sys.argv[:1])
    configure_application(app)
    window = MainWindow(root)
    window.show()
    if args.smoke_test:
        window.ready.connect(lambda: smoke_test(window, screenshot))
        window.loader.failed.connect(lambda _: app.exit(1))
        QtCore.QTimer.singleShot(45000, lambda: (print("[Verification] Timed out", flush=True), window.close(), app.exit(1)))
    exit_code = app.exec()
    if window.loader.isRunning():
        window.loader.requestInterruption()
        window.loader.wait()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())






