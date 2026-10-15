"""VS Code-inspired ATT&CK desktop explorer. See README.md for workflow and paths."""
from __future__ import annotations

import argparse
import html
from copy import deepcopy
import math
import os
from pathlib import Path
import subprocess
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from attack_catalog import BROWSE_CATEGORIES, DOMAIN_LABELS, Catalog, external_id, load_catalog, tactic_phases, catalog_identity, supports_navigator
from version_dialog import VersionDialog
from ttp_documents import TTPDocument, export_document_json, export_document_csv, validate_document_name, technique_comments, technique_states
from attack_matrix import AttackMatrix
from windows_taskbar import set_window_taskbar_properties
from navigator_integration import export_layer, document_layer, export_layers, update_technique_fields, validate_layer
from navigator_dialogs import ImportLayerDialog, AnnotationDialog, LayerSettingsDialog, SelectionCompareDialog, VersionCompareDialog
from navigator_visuals import DEFAULT_GRADIENT
from layer_analysis_dialogs import FormulaDialog, MatrixExportDialog
from navigator_fields import set_presentation
from source_dialogs import SourceDialog, UpgradeDialog
from batch_dialogs import BatchEditDialog
from ttp_operations import batch_patch, annotated_keys, apply_selection, rows_by_scope

ROLE_ID = int(QtCore.Qt.ItemDataRole.UserRole) + 1
ROLE_CONTEXT = ROLE_ID + 1
ROLE_SEARCH = ROLE_ID + 2
APP_USER_MODEL_ID = "TTPSelectionStudio.Desktop"
NAVIGATION_ICON_FILES = {
    "TTP": "ttp-selection-studio-icon-pixel.png",
    "Mitigations": "navigation/mitigations.png",
    "Assets": "navigation/assets.png",
    "Detections": "navigation/detections.png",
    "Groups": "navigation/groups.png",
    "Software": "navigation/software.png",
    "Campaigns": "navigation/campaigns.png",
}

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


def load_navigation_icons():
    """Read category artwork once per window and preserve pixel edges at UI sizes."""
    asset_root = Path(__file__).resolve().parent / "assets"
    paths = {category: (asset_root / name).resolve()
             for category, name in NAVIGATION_ICON_FILES.items()}
    for path in paths.values():
        print(f"[Navigation icons 1/3] Input file: {path}", flush=True)
    print("[Navigation icons 1/3] Output files: None (button icons in memory)", flush=True)
    icons = {}
    for index, (category, path) in enumerate(paths.items(), 1):
        print(f"[Navigation icons 2/3] Loading {category} ({index}/{len(paths)})", flush=True)
        pixmap = QtGui.QPixmap(str(path))
        if pixmap.isNull():
            print(f"[Navigation icons 2/3] Could not load {path}; keeping the text label", flush=True)
            continue
        icon = QtGui.QIcon()
        for size in (32, 64, 96):
            icon.addPixmap(pixmap.scaled(size, size, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                        QtCore.Qt.TransformationMode.FastTransformation))
        icons[category] = icon
    print(f"[Navigation icons 3/3] Complete: {len(icons)}/{len(paths)} icons ready", flush=True)
    return icons


class MainWindow(QtWidgets.QMainWindow):
    ready = QtCore.Signal()

    def __init__(self, data_root: Path, pointer_path=None, settings_path=None):
        super().__init__()
        self.data_root = data_root.resolve()
        self.settings_path = (Path(settings_path) if settings_path is not None else
                              Path(__file__).resolve().parent / "data" / "ui-settings.ini").resolve()
        self.ui_settings, self.navigation_labels_visible = self.load_ui_settings()
        self.version_dialog = None
        self.integration_dialog = None
        self.documents = []
        self.active_document_index = -1
        self.document_counter = 0
        self.restore_matrix_view = False
        self.restore_details_view = True
        self.restoring_workspace = False
        self.details_title = "Technique Details"
        self.restore_category = "TTP"
        self.retained_selection = set()
        self.removed_selection_count = 0
        pointer_path = pointer_path or (self.data_root / "active.json" if (self.data_root / "active.json").exists() else self.data_root / "latest.json")
        self.setWindowTitle("TTP Selection Studio")
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
        self.configure_native_taskbar()
        QtCore.QTimer.singleShot(0, self.loader.start)

    def configure_native_taskbar(self):
        if sys.platform != "win32" or QtWidgets.QApplication.instance().platformName() != "windows":
            return
        icon_path = Path(__file__).resolve().parent / "assets" / "ttp-selection-studio-icon-pixel.ico"
        python_path = Path(sys.executable).resolve()
        pythonw_path = python_path.with_name("pythonw.exe")
        if pythonw_path.is_file():
            python_path = pythonw_path
        command = subprocess.list2cmdline([str(python_path), "-B", str(Path(__file__).resolve()),
                                          "--data-dir", str(self.data_root)])
        try:
            set_window_taskbar_properties(int(self.winId()), APP_USER_MODEL_ID, icon_path,
                                          command, self.operation_report)
        except (OSError, AttributeError) as error:
            self.operation_report(f"[Taskbar window 3/3] Could not configure taskbar icon: {error}")

    def load_ui_settings(self):
        print(f"[UI settings 1/2] Input file: {self.settings_path}", flush=True)
        print("[UI settings 1/2] Output files: None (reading preferences)", flush=True)
        settings = QtCore.QSettings(str(self.settings_path), QtCore.QSettings.Format.IniFormat)
        try:
            visible = settings.value("navigation/show_labels", True, type=bool)
            if settings.status() != QtCore.QSettings.Status.NoError:
                raise ValueError(f"Settings status: {settings.status().name}")
        except (TypeError, ValueError) as error:
            print(f"[UI settings 2/2] Could not read preference: {error}; showing labels", flush=True)
            visible = True
        else:
            print(f"[UI settings 2/2] Complete: navigation labels {'shown' if visible else 'hidden'}", flush=True)
        return settings, visible

    def set_navigation_labels_visible(self, visible):
        self.operation_report("[UI settings 1/3] Input files: None (menu preference in memory)", 0, 3)
        self.operation_report(f"[UI settings 1/3] Output file: {self.settings_path}", 0, 3)
        self.navigation_labels_visible = visible
        self.apply_navigation_label_layout()
        self.operation_report("[UI settings 2/3] Navigation layout updated; saving preference", 1, 3)
        self.ui_settings.setValue("navigation/show_labels", visible)
        self.ui_settings.sync()
        if self.ui_settings.status() != QtCore.QSettings.Status.NoError:
            self.operation_report("[UI settings 3/3] Preference could not be saved; layout applies to this session", 3, 3)
        else:
            self.operation_report(f"[UI settings 3/3] Complete: navigation labels {'shown' if visible else 'hidden'}", 3, 3)

    def apply_navigation_label_layout(self):
        width, height = (112, 68) if self.navigation_labels_visible else (56, 48)
        if any(button.icon().isNull() for button in self.navigation_buttons.values()):
            width = max(width, 112)
        style = (QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon if self.navigation_labels_visible
                 else QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.navigation_rail.setFixedWidth(width)
        for button in self.navigation_buttons.values():
            # Keep text and accessible names even when Qt paints only the icon.
            # Missing artwork must retain a visible category label.
            button.setToolButtonStyle(style if not button.icon().isNull() else
                                      QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setFixedSize(width, height)

    def build_ui(self):
        file_menu = self.menuBar().addMenu("File")
        self.new_action = file_menu.addAction("New File")
        self.new_action.setShortcut(QtGui.QKeySequence.StandardKey.New)
        self.new_action.setEnabled(False)
        self.new_action.triggered.connect(self.new_document)
        self.export_action = file_menu.addAction("Export…")
        self.export_action.setShortcut("Ctrl+Shift+E")
        self.export_action.setEnabled(False)
        self.export_action.triggered.connect(lambda: self.export_current_document())
        self.export_csv_action = file_menu.addAction("Export CSV…")
        self.export_csv_action.setEnabled(False)
        self.export_csv_action.triggered.connect(lambda: self.export_current_document(file_format="csv"))
        self.import_layer_action = file_menu.addAction("Import Navigator Layer…")
        self.import_layer_action.setShortcut("Ctrl+O")
        self.import_layer_action.setEnabled(False)
        self.import_layer_action.triggered.connect(lambda: self.import_navigator_layer())
        self.load_source_action = file_menu.addAction('Load layer URL / custom STIX…')
        self.load_source_action.setEnabled(False)
        self.load_source_action.triggered.connect(self.open_source_dialog)
        self.export_layer_action = file_menu.addAction("Export Navigator Layer…")
        self.export_layer_action.setEnabled(False)
        self.export_layer_action.triggered.connect(lambda: self.export_current_document(file_format="navigator"))
        file_menu.addSeparator()
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
        self.details_action = view_menu.addAction("Technique Details")
        self.details_action.setEnabled(False)
        self.details_action.triggered.connect(lambda: self.open_details_page())

        self.version_action = self.menuBar().addAction("Version")
        self.version_action.setToolTip("Choose an official ATT&CK version")
        self.version_action.setEnabled(False)
        self.version_action.triggered.connect(self.open_versions)

        navigator_menu = self.menuBar().addMenu("Navigator")
        self.new_layer_action = navigator_menu.addAction("New layer")
        self.new_layer_action.triggered.connect(self.new_navigator_layer)
        self.duplicate_layer_action = navigator_menu.addAction("Duplicate active layer")
        self.duplicate_layer_action.triggered.connect(self.duplicate_navigator_layer)
        self.layer_settings_action = navigator_menu.addAction("Layer settings…")
        self.layer_settings_action.triggered.connect(self.edit_layer_settings)
        self.export_all_layers_action = navigator_menu.addAction("Export all open layers…")
        self.export_all_layers_action.triggered.connect(lambda: self.export_all_layers())
        self.layer_actions = (self.new_layer_action, self.duplicate_layer_action, self.layer_settings_action, self.export_all_layers_action)
        self.formula_action = navigator_menu.addAction('Create layer from score formula…')
        self.formula_action.triggered.connect(self.open_formula_dialog)
        self.matrix_svg_action = navigator_menu.addAction('Export matrix SVG…')
        self.matrix_svg_action.triggered.connect(lambda: self.export_matrix_view('svg'))
        self.matrix_excel_action = navigator_menu.addAction('Export matrix Excel…')
        self.matrix_excel_action.triggered.connect(lambda: self.export_matrix_view('xlsx'))
        self.layer_actions += (self.formula_action, self.matrix_svg_action, self.matrix_excel_action)
        self.upgrade_layer_action = navigator_menu.addAction('Review and upgrade layer…')
        self.upgrade_layer_action.triggered.connect(self.open_upgrade_dialog)
        self.layer_actions += (self.upgrade_layer_action,)
        self.batch_edit_action = navigator_menu.addAction('Batch edit selected TTPs…')
        self.batch_edit_action.triggered.connect(lambda: self.edit_ttp_batch())
        self.clear_annotations_action = navigator_menu.addAction('Clear selected annotations…')
        self.clear_annotations_action.triggered.connect(lambda: self.edit_ttp_batch(clear=True))
        self.enable_selected_action = navigator_menu.addAction('Enable selected TTPs')
        self.enable_selected_action.triggered.connect(lambda: self.set_technique_states(set(self.selected), True))
        self.disable_selected_action = navigator_menu.addAction('Disable selected TTPs')
        self.disable_selected_action.triggered.connect(lambda: self.set_technique_states(set(self.selected), False))
        selection_tools = navigator_menu.addAction('Batch selection tools')
        selection_tools.triggered.connect(self.open_matrix)
        self.batch_actions = (self.batch_edit_action, self.clear_annotations_action, self.enable_selected_action, self.disable_selected_action)
        self.layer_actions += self.batch_actions
        for action in self.layer_actions:
            action.setEnabled(False)
        navigator_menu.addSeparator()
        self.compare_selections_action = navigator_menu.addAction("Compare open TTP documents…")
        self.compare_selections_action.triggered.connect(self.open_selection_comparison)
        self.compare_versions_action = navigator_menu.addAction("Compare ATT&CK versions…")
        self.compare_versions_action.triggered.connect(self.open_version_comparison)
        self.compare_selections_action.setEnabled(False)
        self.compare_versions_action.setEnabled(False)
        open_navigator_action = navigator_menu.addAction("Open ATT&CK Navigator website")
        open_navigator_action.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(
            QtCore.QUrl("https://mitre-attack.github.io/attack-navigator/")))

        settings_menu = self.menuBar().addMenu("Settings")
        self.show_navigation_labels_action = settings_menu.addAction("Show navigation labels")
        self.show_navigation_labels_action.setCheckable(True)
        self.show_navigation_labels_action.setChecked(self.navigation_labels_visible)
        self.show_navigation_labels_action.toggled.connect(self.set_navigation_labels_visible)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        rail = QtWidgets.QFrame()
        self.navigation_rail = rail
        rail.setObjectName("rail")
        rail_layout = QtWidgets.QVBoxLayout(rail)
        rail_layout.setContentsMargins(0, 8, 0, 0)
        rail_layout.setSpacing(4)
        self.navigation_group = QtWidgets.QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        self.navigation_buttons = {}
        navigation_icons = load_navigation_icons()
        for category in ("TTP", *BROWSE_CATEGORIES):
            button = QtWidgets.QToolButton()
            button.setText(category)
            button.setAccessibleName(category)
            button.setIconSize(QtCore.QSize(32, 32))
            if category in navigation_icons:
                button.setIcon(navigation_icons[category])
            button.setToolTip("TTP — ATT&CK techniques" if category == "TTP" else category)
            button.setCheckable(True)
            button.setEnabled(category == "TTP")
            button.setStyleSheet("QToolButton { padding: 6px 9px; background: #181818; border-left: 2px solid transparent; }"
                                "QToolButton:hover { background: #2a2d2e; }"
                                "QToolButton:checked { color: #ffffff; background: #252526; border-left: 2px solid #007acc; }")
            self.navigation_group.addButton(button)
            self.navigation_buttons[category] = button
            button.clicked.connect(lambda checked=False, name=category: self.switch_category(name))
            rail_layout.addWidget(button)
        self.rail_button = self.navigation_buttons["TTP"]
        self.rail_button.setChecked(True)
        self.apply_navigation_label_layout()
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
        self.ttp_search = QtWidgets.QLineEdit()
        self.ttp_search.setPlaceholderText("Search TTP name or ID…")
        self.ttp_search.setAccessibleName("Search TTPs")
        self.ttp_search.setToolTip("Search the document's ATT&CK domain by technique name or ID")
        self.ttp_search.setClearButtonEnabled(True)
        self.ttp_search.setEnabled(False)
        side_layout.addWidget(self.ttp_search)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search technique name or ID…")
        self.search.setClearButtonEnabled(True)
        self.search.setEnabled(False)
        self.search.hide()  # The dedicated TTP field handles the TTP category.
        side_layout.addWidget(self.search)
        self.summary = QtWidgets.QLabel("Enterprise · Loading catalog…")
        self.summary.setObjectName("summary")
        side_layout.addWidget(self.summary)
        self.matrix_button = QtWidgets.QPushButton("Open ATT&CK Matrix")
        self.matrix_button.setEnabled(False)
        self.matrix_button.clicked.connect(self.open_matrix)
        side_layout.addWidget(self.matrix_button)
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
        self.tree.clicked.connect(self.show_index)
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
        self.library_tree.clicked.connect(self.show_library_index)
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
        self.ttp_search_timer = QtCore.QTimer(self)
        self.ttp_search_timer.setSingleShot(True)
        self.ttp_search_timer.setInterval(180)
        self.ttp_search_timer.timeout.connect(self.apply_ttp_search)
        self.ttp_search.textChanged.connect(lambda: self.ttp_search_timer.start())
        self.ttp_search.returnPressed.connect(self.apply_ttp_search)

        self.vertical = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.horizontal.addWidget(self.vertical)
        editor = QtWidgets.QWidget()
        editor_layout = QtWidgets.QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)
        self.document_tabs = QtWidgets.QTabBar()
        self.document_tabs.setAccessibleName("Workspace files and details")
        self.document_tabs.setExpanding(False)
        self.document_tabs.setUsesScrollButtons(True)
        self.document_tabs.setElideMode(QtCore.Qt.TextElideMode.ElideRight)
        self.document_tabs.setEnabled(False)
        self.document_tabs.currentChanged.connect(self.workspace_tab_changed)
        self.document_tabs.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.document_tabs.customContextMenuRequested.connect(self.show_document_context_menu)
        self.document_context_menu = None
        editor_layout.addWidget(self.document_tabs)
        self.workspace = QtWidgets.QStackedWidget()
        self.tabs = QtWidgets.QTabWidget()
        self.details_page = QtWidgets.QWidget()
        details_layout = QtWidgets.QVBoxLayout(self.details_page)
        details_layout.setContentsMargins(0, 0, 0, 0)
        self.crumb = QtWidgets.QLabel("Enterprise  /  ATT&CK Explorer")
        self.crumb.setObjectName("crumb")
        details_layout.addWidget(self.crumb)
        self.bulk_source_context = None
        self.bulk_action_bar = QtWidgets.QWidget()
        bulk_layout = QtWidgets.QHBoxLayout(self.bulk_action_bar)
        bulk_layout.setContentsMargins(18, 4, 18, 4)
        self.bulk_add_button = QtWidgets.QPushButton("Add all TTPs")
        self.bulk_add_button.setAccessibleName("Add all source TTPs to active document")
        self.bulk_add_button.clicked.connect(self.add_current_source_ttps)
        bulk_layout.addWidget(self.bulk_add_button)
        self.annotation_context = None
        self.annotation_button = QtWidgets.QPushButton("Edit Navigator annotation…")
        self.annotation_button.clicked.connect(self.edit_navigator_annotation)
        self.annotation_button.hide()
        bulk_layout.addWidget(self.annotation_button)
        bulk_layout.addStretch()
        self.bulk_action_bar.hide()
        details_layout.addWidget(self.bulk_action_bar)
        self.details = DetailBrowser()
        self.details.textChanged.connect(self.hide_bulk_action)
        self.details.copied.connect(lambda section: self.state.setText(f"Copied {section.lower()} to clipboard"))
        self.details.setOpenExternalLinks(False)
        self.details.setOpenLinks(False)
        self.details.anchorClicked.connect(self.open_detail_link)
        self.details.setHtml("<h1>ATT&CK Explorer</h1><p>Browse Platform → Tactic → Technique in the sidebar.</p>"
                             "<p>Select a technique to inspect its description. Check its box to add it to the selection.</p>"
                             "<p style='color:#999999'>Loading the local Enterprise catalog…</p>")
        details_layout.addWidget(self.details)
        selection_page = QtWidgets.QWidget()
        selection_layout = QtWidgets.QVBoxLayout(selection_page)
        self.selection_summary = QtWidgets.QLabel("Selected TTPs · active document")
        selection_layout.addWidget(self.selection_summary)
        self.selection_export_button = QtWidgets.QPushButton("Export JSON / CSV…")
        self.selection_export_button.setEnabled(False)
        self.selection_export_button.clicked.connect(lambda: self.export_current_document())
        selection_layout.addWidget(self.selection_export_button)
        self.selection_list = QtWidgets.QListWidget()
        self.selection_list.itemClicked.connect(self.show_selected)
        self.selection_list.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.selection_list.customContextMenuRequested.connect(self.show_selected_context_menu)
        selection_layout.addWidget(self.selection_list)
        self.selection_annotation_button = QtWidgets.QPushButton("Edit TTP annotation…")
        self.selection_annotation_button.setEnabled(False)
        self.selection_annotation_button.clicked.connect(lambda: self.edit_selected_annotation())
        self.selection_list.currentItemChanged.connect(
            lambda item, previous: self.selection_annotation_button.setEnabled(bool(item) and self.loaded_ok))
        selection_layout.addWidget(self.selection_annotation_button)
        clear = QtWidgets.QPushButton("Clear selection")
        clear.clicked.connect(self.clear_selection)
        selection_layout.addWidget(clear)
        batch_row = QtWidgets.QHBoxLayout()
        self.selection_batch_button = QtWidgets.QPushButton('Batch edit included TTPs…')
        self.selection_batch_button.clicked.connect(lambda: self.edit_ttp_batch())
        batch_row.addWidget(self.selection_batch_button)
        self.selection_state_button = QtWidgets.QToolButton()
        self.selection_state_button.setText('Enabled state…')
        self.selection_state_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        state_menu = QtWidgets.QMenu(self.selection_state_button)
        for label, state in [('Enable included TTPs', True), ('Disable included TTPs', False), ('Toggle included states', 'toggle')]:
            state_menu.addAction(label, lambda checked=False, value=state: self.set_technique_states(set(self.selected), value))
        state_menu.addAction('Clear all included annotations…', lambda: self.edit_ttp_batch(clear=True))
        self.selection_state_button.setMenu(state_menu)
        batch_row.addWidget(self.selection_state_button)
        selection_layout.addLayout(batch_row)
        self.selection_tab_index = self.tabs.addTab(selection_page, "Selected Techniques (0)")
        self.matrix_view = AttackMatrix()
        self.matrix_view.progress.connect(self.operation_report)
        self.matrix_view.selection_requested.connect(self.select_matrix_ttp)
        self.matrix_view.detail_requested.connect(self.show_matrix_detail)
        self.matrix_view.layer_requested.connect(self.select_navigator_layer)
        self.matrix_view.overlay_requested.connect(self.toggle_all_layers)
        self.matrix_view.new_layer_requested.connect(self.new_navigator_layer)
        self.matrix_view.duplicate_layer_requested.connect(self.duplicate_navigator_layer)
        self.matrix_view.layer_settings_requested.connect(self.edit_layer_settings)
        self.matrix_view.color_selected_requested.connect(lambda: self.choose_technique_color(set(self.selected)))
        self.matrix_view.clear_selected_color_requested.connect(lambda: self.apply_technique_fields(set(self.selected), {'color': ''}, include=False))
        self.matrix_view.score_selected_requested.connect(self.score_selected_techniques)
        self.matrix_view.annotation_requested.connect(lambda key, slug: self.edit_navigator_annotation(key, '', True))
        self.matrix_view.cell_color_requested.connect(lambda key, slug: self.choose_technique_color({key}))
        self.matrix_view.cell_clear_color_requested.connect(lambda key, slug: self.apply_technique_fields({key}, {'color': ''}, include=False))
        self.matrix_view.source_requested.connect(self.add_source_ttps)
        self.matrix_view.presentation_requested.connect(self.change_matrix_presentation)
        self.matrix_view.bulk_selection_requested.connect(self.select_ttp_batch)
        self.matrix_view.batch_edit_requested.connect(lambda clear: self.edit_ttp_batch(clear=clear))
        self.matrix_view.enabled_requested.connect(lambda value: self.set_technique_states(set(self.selected), value))
        self.matrix_view.cell_enabled_requested.connect(lambda key, slug, value: self.set_technique_states({key}, value, slug or None))
        self.matrix_tab_index = self.tabs.addTab(self.matrix_view, "ATT&CK Matrix")
        self.tabs.setTabEnabled(self.matrix_tab_index, False)
        self.tabs.currentChanged.connect(self.editor_tab_changed)
        self.workspace.addWidget(self.tabs)
        self.workspace.addWidget(self.details_page)
        editor_layout.addWidget(self.workspace)
        self.ensure_details_tab()
        self.workspace.setCurrentWidget(self.details_page)
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

    @property
    def current_document(self):
        if 0 <= self.active_document_index < len(self.documents):
            return self.documents[self.active_document_index]
        return None

    def operation_report(self, message, current=0, total=0):
        print(message + (f" ({current}/{total})" if total else ""), flush=True)
        self.report(message, current, total)

    def editor_tab_changed(self, index):
        if index == self.matrix_tab_index and self.loaded_ok and self.workspace.currentWidget() is self.tabs:
            self.open_matrix()

    @property
    def details_tab_index(self):
        return next((index for index in range(self.document_tabs.count())
                     if self.document_tabs.tabData(index) == "__details__"), -1)

    def ensure_details_tab(self):
        index = self.details_tab_index
        if index >= 0:
            return index
        self.document_tabs.blockSignals(True)
        index = self.document_tabs.addTab(self.details_title)
        self.document_tabs.setTabData(index, "__details__")
        self.document_tabs.setTabToolTip(index, "Reference details for the active document · close without changing its TTPs")
        close = QtWidgets.QToolButton(self.document_tabs)
        close.setText("×")
        close.setAccessibleName("Close details page")
        close.setToolTip("Close details page")
        close.setAutoRaise(True)
        close.setFixedSize(22, 22)
        close.setStyleSheet("QToolButton {padding:0; background:transparent;} QToolButton:hover {background:#444444;}")
        close.clicked.connect(self.close_details_page)
        self.document_tabs.setTabButton(index, QtWidgets.QTabBar.ButtonPosition.RightSide, close)
        self.document_tabs.blockSignals(False)
        return index

    def set_details_title(self, title):
        self.details_title = title
        if self.details_tab_index >= 0:
            self.document_tabs.setTabText(self.details_tab_index, title)

    def workspace_tab_changed(self, index):
        if self.document_tabs.tabData(index) == "__details__":
            self.workspace.setCurrentWidget(self.details_page)
        else:
            self.activate_document(index)

    def show_document_page(self):
        self.workspace.setCurrentWidget(self.tabs)
        if self.current_document:
            self.document_tabs.blockSignals(True)
            self.document_tabs.setCurrentIndex(self.active_document_index)
            self.document_tabs.blockSignals(False)

    def open_details_page(self, title=None):
        if title is not None:
            self.set_details_title(title)
        if self.restoring_workspace:
            return
        reopening = self.details_tab_index < 0
        if reopening:
            self.operation_report("Input files: None; output files: None (reference page in memory)")
            self.operation_report("[Details 1/2] Reopening reference page", 0, 2)
        index = self.ensure_details_tab()
        self.document_tabs.setCurrentIndex(index)
        self.workspace.setCurrentWidget(self.details_page)
        if reopening:
            self.operation_report("[Details 2/2] Ready; active document selections preserved", 2, 2)

    def close_details_page(self):
        index = self.details_tab_index
        if index < 0:
            return
        self.operation_report("Input files: None; output files: None (closing reference page)")
        self.operation_report("[Details 1/2] Closing reference tab", 0, 2)
        was_visible = self.workspace.currentWidget() is self.details_page
        self.document_tabs.blockSignals(True)
        self.document_tabs.removeTab(index)
        self.document_tabs.blockSignals(False)
        if was_visible:
            self.show_document_page()
        self.operation_report("[Details 2/2] Closed; document and selected TTPs preserved", 2, 2)

    def open_matrix(self):
        if not self.loaded_ok:
            return
        if self.active_category != "TTP":
            self.switch_category("TTP")
        self.matrix_view.set_catalog(self.catalog, self.selected)
        self.refresh_layer_appearance()
        self.show_document_page()
        self.tabs.setCurrentIndex(self.matrix_tab_index)

    def select_matrix_ttp(self, key, checked):
        if not self.loaded_ok or key not in self.items_by_id:
            return
        item = self.items_by_id[key][0]
        item.setCheckState(QtCore.Qt.CheckState.Checked if checked else QtCore.Qt.CheckState.Unchecked)

    def show_matrix_detail(self, key, slug):
        if not self.loaded_ok or key not in self.items_by_id:
            return
        platform = self.matrix_view.platform.currentText()
        candidates = self.items_by_id[key]
        item = next((item for item in candidates if item.data(ROLE_CONTEXT)[1] == slug
                     and item.data(ROLE_CONTEXT)[0] == platform),
                    next((item for item in candidates if item.data(ROLE_CONTEXT)[1] == slug), candidates[0]))
        actual_platform, actual_slug, _ = item.data(ROLE_CONTEXT)
        self.show_record(key, actual_platform, actual_slug)

    def append_document(self, catalog):
        self.document_counter += 1
        document = TTPDocument(f"Untitled-{self.document_counter}", catalog.for_domain("enterprise-attack"))
        self.documents.append(document)
        self.document_tabs.blockSignals(True)
        index = self.document_tabs.insertTab(len(self.documents) - 1, document.name)
        self.document_tabs.setTabData(index, document.document_id)
        self.document_tabs.blockSignals(False)
        return len(self.documents) - 1

    def sync_active_document(self):
        document = self.current_document
        if document and self.catalog and self.loaded_ok:
            document.set_catalog(self.catalog)
            document.selected = set(self.selected)
        self.update_document_labels()

    def update_document_labels(self):
        for number, document in enumerate(self.documents):
            self.document_tabs.setTabText(number, document.name + (" *" if document.dirty else ""))
            self.document_tabs.setTabToolTip(number, f"{document.name}\n{DOMAIN_LABELS[document.catalog.domain]} · ATT&CK v{document.catalog.version}\n"
                                                + (str(document.export_path) if document.export_path else "Not exported"))
        document = self.current_document
        if document:
            self.setWindowTitle(document.name + (" *" if document.dirty else "") + " — TTP Selection Studio")
            self.selection_summary.setText(f"{document.name} · {DOMAIN_LABELS[document.catalog.domain]} · ATT&CK v{document.catalog.version} · {len(document.selected)} selected TTPs")
        self.matrix_view.update_layers(self.documents, document)
        for number, candidate in enumerate(self.documents):
            if candidate.catalog.dataset_id:
                self.document_tabs.setTabToolTip(number, self.document_tabs.tabToolTip(number) +
                                                '\nCustom dataset SHA-256: ' + candidate.catalog.dataset_id)
        supported = self.loaded_ok and bool(document) and supports_navigator(document.catalog)
        for action in self.layer_actions:
            action.setEnabled(supported)
        for action in self.batch_actions:
            action.setEnabled(supported and bool(self.selected))
        self.selection_batch_button.setEnabled(supported and bool(self.selected))
        self.selection_state_button.setEnabled(supported and bool(self.selected))
        if self.matrix_view.show_all_layers.isChecked():
            self.refresh_layer_appearance()

    def refresh_layer_appearance(self, report_overlay=False):
        document = self.current_document
        supported = document and supports_navigator(document.catalog)
        active_layer = document_layer(document, validate=False) if supported else {}
        if supported and self.matrix_view.show_all_layers.isChecked():
            compatible = [candidate for candidate in self.documents
                          if catalog_identity(candidate.catalog) == catalog_identity(document.catalog)]
            layers = []
            for number, candidate in enumerate(compatible, 1):
                if report_overlay:
                    self.operation_report('[Overlay 2/3] Reading compatible layer colors', number - 1, len(compatible))
                layers.append((candidate.name, document_layer(candidate, validate=False)))
            scope = f"{DOMAIN_LABELS[document.catalog.domain]} v{document.catalog.version}"
            self.matrix_view.set_overlay(layers, active_layer, len(self.documents), scope, document.name, document.catalog)
        else:
            if report_overlay:
                self.operation_report('[Overlay 2/3] Restoring active layer colors', 2, 3)
            self.matrix_view.set_layer(active_layer, document.catalog if document else None)

    def toggle_all_layers(self, enabled):
        if not self.loaded_ok:
            return
        self.operation_report('Input files: None; output files: None (read-only layer color projection)')
        self.operation_report('[Overlay 1/3] Resolving compatible layers' if enabled else '[Overlay 1/3] Leaving all-layer view', 0, 3)
        self.sync_active_document()
        self.refresh_layer_appearance(report_overlay=True)
        self.operation_report('[Overlay 3/3] Ready; source selections and annotations preserved', 3, 3)

    def select_navigator_layer(self, document_id):
        if not self.loaded_ok:
            return
        index = self.document_index(document_id)
        if index < 0:
            return
        self.layer_matrix_pending = True
        self.activate_document(index)
        if self.loaded_ok:
            self.layer_matrix_pending = False
            self.open_matrix()

    def new_navigator_layer(self):
        if not self.loaded_ok or not supports_navigator(self.catalog):
            return
        self.operation_report("Input files: None; output files: None (new layer in memory)")
        self.operation_report("[Layer 1/2] Creating an Enterprise layer", 0, 2)
        self.new_document()
        document = self.current_document
        document.navigator_layer = {'name': document.name, 'domain': document.catalog.domain,
                                    'versions': {'attack': document.catalog.version, 'navigator': '5.2.0', 'layer': '4.5'},
                                    'techniques': [], 'gradient': deepcopy(DEFAULT_GRADIENT),
                                    'legendItems': [], 'selectSubtechniquesWithParent': False}
        self.update_document_labels()
        if self.loaded_ok:
            self.open_matrix()
        else:
            self.layer_matrix_pending = True
        self.operation_report("[Layer 2/2] Created; change domain with the filename context menu", 2, 2)

    def open_formula_dialog(self):
        if not self.loaded_ok or not supports_navigator(self.catalog):
            return
        self.sync_active_document()
        self.operation_report('Input files: None; output files: None (formula source snapshots in memory)')
        self.show_integration_dialog(FormulaDialog(self.documents, self.current_document, self))

    def export_matrix_view(self, kind, target=None):
        if not self.loaded_ok or not supports_navigator(self.catalog):
            return None
        if self.integration_dialog and self.integration_dialog.isVisible():
            self.integration_dialog.raise_()
            return None
        self.sync_active_document()
        self.open_matrix()
        if target is None:
            target, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Export matrix ' + kind.upper(),
                str(Path.home() / (self.current_document.name + '.' + kind)),
                'SVG images (*.svg)' if kind == 'svg' else 'Excel workbooks (*.xlsx)')
        if not target:
            self.operation_report('[Matrix Export] Cancelled; no output files written', 1, 1)
            return None
        matrix = self.matrix_view
        options = {'platform': matrix.platform_scope(), 'query': matrix.search.text(),
                   'colors': matrix.show_colors.isChecked(),
                   'sources': list(self.documents) if matrix.show_all_layers.isChecked() else None}
        self.operation_report('Input files: None (matrix/layer snapshots in memory)')
        self.operation_report(f'Output file: {Path(target).expanduser().resolve()}')
        dialog = MatrixExportDialog(self.current_document, target, kind, options, self)
        self.show_integration_dialog(dialog)
        return dialog

    def duplicate_navigator_layer(self):
        if not self.loaded_ok or not supports_navigator(self.catalog):
            return
        self.sync_active_document()
        source = self.current_document
        self.operation_report("Input files: None; output files: None (copying active layer in memory)")
        self.operation_report("[Layer Copy 1/2] Copying selections, annotations and archives", 0, 2)
        base = source.name[:100] + '-copy'
        name = base
        number = 2
        while any(document.name.casefold() == name.casefold() for document in self.documents):
            name = base + '-' + str(number)
            number += 1
        layer = document_layer(source)
        layer['name'] = name
        document = TTPDocument(name, source.catalog, selected=set(source.selected), navigator_layer=layer,
                               navigator_import_selected=set(source.navigator_import_selected),
                               navigator_snapshots=deepcopy(source.navigator_snapshots),
                               domain_snapshots=deepcopy(source.domain_snapshots),
                               migration_archives=deepcopy(source.migration_archives))
        self.install_imported_document(document)
        if self.loaded_ok:
            self.open_matrix()
        else:
            self.layer_matrix_pending = True
        self.operation_report(f"[Layer Copy 2/2] Created {name} with independent data", 2, 2)

    def edit_layer_settings(self):
        if not self.loaded_ok or not supports_navigator(self.catalog):
            return
        self.sync_active_document()
        self.operation_report("Input files: None; output files: None (layer settings in memory)")
        self.operation_report("[Layer Settings 1/2] Editing description, gradient and legend", 0, 2)
        dialog = LayerSettingsDialog(self.current_document, self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            self.operation_report("[Layer Settings] Cancelled; document preserved", 1, 1)
            return
        self.current_document.navigator_layer = dialog.result_layer
        self.current_document.name = dialog.result_layer['name']
        self.refresh_selection()
        self.operation_report("[Layer Settings 2/2] Saved; native matrix colors updated", 2, 2)

    def choose_technique_color(self, keys, tactic=None):
        if not self.loaded_ok or not keys:
            return
        self.operation_report("Input files: None; output files: None (technique colors in memory)")
        self.operation_report("[Color 1/2] Choosing a technique color", 0, 2)
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor('#007acc'), self, 'Technique color')
        if not color.isValid():
            self.operation_report("[Color] Cancelled; document preserved", 1, 1)
            return
        self.apply_technique_fields(keys, {'color': color.name()}, tactic)

    def score_selected_techniques(self):
        if not self.loaded_ok or not self.selected:
            return
        self.operation_report("Input files: None; output files: None (technique scores in memory)")
        self.operation_report("[Score 1/2] Editing selected technique scores", 0, 2)
        text, accepted = QtWidgets.QInputDialog.getText(self, 'Score selected techniques', 'Finite score (blank to clear). Explicit colors override the gradient:')
        if not accepted:
            self.operation_report("[Score] Cancelled; document preserved", 1, 1)
            return
        try:
            score = float(text) if text.strip() else None
            if score is not None and not math.isfinite(score):
                raise ValueError('Score must be finite.')
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, 'Invalid score', str(error))
            self.operation_report(f"[Score] Failed: {error}", 1, 1)
            return
        self.apply_technique_fields(set(self.selected), {'score': score})

    def apply_technique_fields(self, keys, fields, tactic=None, include=True):
        if not self.loaded_ok or not keys:
            return False
        self.sync_active_document()
        self.operation_report("Input files: None; output files: None (active layer in memory)")
        self.operation_report("[Layer Color/Score 1/3] Validating technique annotations", 0, 3)
        try:
            changed = update_technique_fields(self.current_document, keys, fields, tactic)
        except Exception as error:
            self.operation_report(f"[Layer Color/Score] Failed: {error}", 1, 1)
            QtWidgets.QMessageBox.warning(self, 'Invalid annotation', str(error))
            return False
        self.operation_report("[Layer Color/Score 2/3] Updating selected technique rows", 1, 3)
        clearing_only = all(value is None or (name == 'color' and value == '') for name, value in fields.items())
        if clearing_only and not changed:
            self.operation_report("[Layer Color/Score 3/3] Nothing to clear; layer and selection unchanged", 3, 3)
            return True
        if include:
            self.syncing = True
            for key in keys:
                self.selected.add(key)
                for item in self.items_by_id[key]:
                    item.setCheckState(QtCore.Qt.CheckState.Checked)
            self.syncing = False
        self.refresh_selection()
        self.operation_report("[Layer Color/Score 3/3] Ready; native colors and exports synchronized", 3, 3)
        return True

    def set_technique_states(self, keys, value, tactic=None):
        if not self.loaded_ok or not keys or not supports_navigator(self.catalog):
            return False
        self.sync_active_document()
        try:
            result = batch_patch(self.current_document, keys, {'enabled': value}, tactic, self.operation_report)
        except Exception as error:
            self.operation_report(f'[State] Failed: {error}', 1, 1)
            return False
        self.refresh_selection()
        return result['changed']

    def select_ttp_batch(self, action, scope='platform', tactic=''):
        matrix = self.matrix_view
        if not self.loaded_ok or matrix.catalog is not self.catalog or matrix.building:
            return False
        self.operation_report('Input files: None; output files: None (selection in memory)')
        self.operation_report('[Batch Selection 1/3] Resolving platform/search/tactic scope', 0, 3)
        try:
            keys = matrix.scope_keys(scope, tactic)
            annotations = annotated_keys(self.current_document, keys, tactic or None)
            selected = apply_selection(self.selected, keys, action, annotations)
        except ValueError as error:
            self.operation_report(f'[Batch Selection] Failed: {error}', 1, 1)
            return False
        self.operation_report('[Batch Selection 2/3] Synchronizing inclusion checkboxes', 1, 3)
        changed = self.selected ^ selected
        self.syncing = True
        try:
            for key in changed:
                state = QtCore.Qt.CheckState.Checked if key in selected else QtCore.Qt.CheckState.Unchecked
                for item in self.items_by_id.get(key, []):
                    item.setCheckState(state)
            self.selected = selected
        finally:
            self.syncing = False
        self.refresh_selection()
        self.operation_report(f'[Batch Selection 3/3] {len(keys)} in scope; {len(selected)} included TTPs; states unchanged', 3, 3)
        return True

    def edit_ttp_batch(self, clear=False):
        if not self.loaded_ok or not self.selected or not supports_navigator(self.catalog):
            return
        if self.integration_dialog and self.integration_dialog.isVisible():
            self.integration_dialog.raise_()
            return
        self.sync_active_document()
        document = self.current_document
        self.operation_report('Input files: None; output files: None (batch editing draft in memory)')
        dialog = BatchEditDialog(document, set(self.selected), self, clear=clear)
        self.show_integration_dialog(dialog)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            self.operation_report('[Batch Edit] Cancelled; original document preserved', 1, 1)
            return
        if self.current_document is not document or not dialog.result_data:
            self.operation_report('[Batch Edit] Active document changed; draft was not applied', 1, 1)
            return
        if dialog.result_data['changed']:
            document.navigator_layer = dialog.result_layer
        self.refresh_selection()
        self.operation_report('[Batch Edit] Applied; inclusion checkboxes preserved', 3, 3)

    def export_all_layers(self, target=None):
        if not self.loaded_ok:
            return None
        self.sync_active_document()
        if target is None:
            target, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Export all open Navigator layers', str(Path.home() / 'layers.navigator.json'), 'JSON files (*.json)')
        if not target:
            self.operation_report('[Layers Export] Cancelled; no output files written', 1, 1)
            return None
        try:
            return export_layers(self.documents, target, self.operation_report)
        except Exception as error:
            self.operation_report(f'[Layers Export] Failed: {error}', 1, 1)
            QtWidgets.QMessageBox.critical(self, 'Layer export failed', str(error))
            return None

    def new_document(self):
        if not self.loaded_ok:
            return
        self.operation_report("[New File 1/2] Input files: None; output files: None (document in memory)", 0, 2)
        self.sync_active_document()
        index = self.append_document(getattr(self, 'official_catalog', self.catalog) if self.catalog.dataset_id else self.catalog)
        self.document_tabs.blockSignals(True)
        self.document_tabs.setCurrentIndex(index)
        self.document_tabs.blockSignals(False)
        self.activate_document(index)
        self.operation_report(f"[New File 2/2] Created {self.current_document.name}", 2, 2)

    def document_index(self, document_id):
        return next((index for index, document in enumerate(self.documents)
                     if document.document_id == document_id), -1)

    def show_document_context_menu(self, position):
        if not self.loaded_ok:
            return
        index = self.document_tabs.tabAt(position)
        if index < 0:
            return
        if self.document_context_menu:
            self.document_context_menu.close()
            self.document_context_menu.deleteLater()
        menu = QtWidgets.QMenu(self.document_tabs)
        self.document_context_menu = menu
        if self.document_tabs.tabData(index) == "__details__":
            menu.addAction("Close Details", self.close_details_page)
            menu.popup(self.document_tabs.mapToGlobal(position))
            return
        document_id = self.documents[index].document_id
        close_action = menu.addAction("Close File")
        close_action.triggered.connect(lambda: self.close_document(self.document_index(document_id)))
        rename_action = menu.addAction("Rename…")
        rename_action.triggered.connect(lambda: self.rename_document(self.document_index(document_id)))
        domain_menu = menu.addMenu("ATT&CK Domain")
        domain_group = QtGui.QActionGroup(domain_menu)
        domain_group.setExclusive(True)
        document = self.documents[index]
        for domain, label in DOMAIN_LABELS.items():
            action = domain_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(domain == document.catalog.domain)
            available = any(obj.get("type") == "attack-pattern"
                            for obj in document.catalog.objects_by_domain[domain].values())
            action.setEnabled(available)
            if not available:
                action.setText(f"{label} (unavailable in v{document.catalog.version})")
            domain_group.addAction(action)
            action.triggered.connect(lambda checked=False, value=domain: self.change_document_domain(
                self.document_index(document_id), value))
        self.document_context_menu = menu
        menu.popup(self.document_tabs.mapToGlobal(position))

    def change_document_domain(self, index, domain):
        if not self.loaded_ok or not 0 <= index < len(self.documents):
            return False
        self.sync_active_document()
        document = self.documents[index]
        if document.catalog.domain == domain:
            return True
        self.operation_report("Input files: None (verified catalog in memory); output files: None")
        self.operation_report(f"[Domain 1/3] Resolving {DOMAIN_LABELS.get(domain, domain)}", 0, 3)
        try:
            catalog = document.catalog.for_domain(domain)
        except ValueError as error:
            self.operation_report(f"[Domain] Failed: {error}", 1, 1)
            return False
        document.set_catalog(catalog)
        self.operation_report("[Domain 2/3] Restored this domain's selections and annotations", 2, 3)
        if index == self.active_document_index:
            self.pending_domain_report = True
            self.selected = set(document.selected)
            self.operation_report("[Domain 3/3] Building the domain tree and matrix", 2, 3)
            self.apply_version((catalog, None))
        else:
            self.update_document_labels()
            self.operation_report(f"[Domain 3/3] {document.name}: {DOMAIN_LABELS[domain]}", 3, 3)
        return True

    def rename_document(self, index):
        if not self.loaded_ok or not 0 <= index < len(self.documents):
            return False
        self.sync_active_document()
        document = self.documents[index]
        text = document.name
        while True:
            text, accepted = QtWidgets.QInputDialog.getText(self, "Rename file", "New document name:", text=text)
            if not accepted:
                return False
            try:
                name = validate_document_name(text)
            except ValueError as error:
                QtWidgets.QMessageBox.warning(self, "Invalid filename", str(error))
                continue
            break
        self.operation_report("[Rename 1/2] Input files: None; output files: None (document in memory)", 0, 2)
        previous = document.name
        document.name = name
        self.update_document_labels()
        self.operation_report(f"[Rename 2/2] {previous} → {name}", 2, 2)
        return True

    def close_document(self, index):
        if not self.loaded_ok or not 0 <= index < len(self.documents):
            return False
        self.sync_active_document()
        document = self.documents[index]
        if document.dirty:
            answer = QtWidgets.QMessageBox.question(
                self, "Close file", f'Export changes to "{document.name}" before closing?',
                QtWidgets.QMessageBox.StandardButton.Save | QtWidgets.QMessageBox.StandardButton.Discard
                | QtWidgets.QMessageBox.StandardButton.Cancel, QtWidgets.QMessageBox.StandardButton.Cancel)
            if answer == QtWidgets.QMessageBox.StandardButton.Cancel:
                return False
            if answer == QtWidgets.QMessageBox.StandardButton.Save and self.export_document_at_index(index) is None:
                return False
            if answer == QtWidgets.QMessageBox.StandardButton.Save and document.dirty:
                self.operation_report("[Close File] Kept open: export Studio JSON to preserve all document annotations.", 1, 1)
                return False
        self.operation_report("[Close File 1/2] Input files: None; output files: None (closing in-memory document)", 0, 2)
        previous_active = self.active_document_index
        keep_details = self.workspace.currentWidget() is self.details_page
        self.document_tabs.blockSignals(True)
        self.documents.pop(index)
        self.document_tabs.removeTab(index)
        if index != previous_active:
            self.active_document_index = previous_active - int(index < previous_active)
            self.document_tabs.setCurrentIndex(self.details_tab_index if keep_details else self.active_document_index)
            self.document_tabs.blockSignals(False)
            self.update_document_labels()
        else:
            self.active_document_index = -1
            self.selected = set()
            next_index = min(index, len(self.documents) - 1)
            self.document_tabs.setCurrentIndex(next_index)
            self.document_tabs.blockSignals(False)
            if self.documents:
                self.activate_document(next_index)
            else:
                self.new_document()
        self.operation_report(f"[Close File 2/2] Closed {document.name}", 2, 2)
        return True

    def activate_document(self, index):
        if not self.loaded_ok or index < 0 or index >= len(self.documents):
            return
        self.workspace.setCurrentWidget(self.tabs)
        self.document_tabs.blockSignals(True)
        self.document_tabs.setCurrentIndex(index)
        self.document_tabs.blockSignals(False)
        if index == self.active_document_index:
            return
        self.sync_active_document()
        self.active_document_index = index
        document = self.current_document
        self.selected = set(document.selected)
        self.operation_report(f"[Document 1/2] Input files: None; output files: None; activating {document.name}", 0, 2)
        if document.catalog is not self.catalog:
            # Each file retains the snapshot used for its selections. Rebuild from
            # its verified in-memory catalog without network requests or pointer writes.
            self.apply_version((document.catalog, None))
            return
        self.syncing = True
        for key, items in self.items_by_id.items():
            checked = QtCore.Qt.CheckState.Checked if key in self.selected else QtCore.Qt.CheckState.Unchecked
            for item in items:
                item.setCheckState(checked)
        self.syncing = False
        self.refresh_selection()
        self.operation_report(f"[Document 2/2] Ready: {document.name}; {len(self.selected)} selected TTPs", 2, 2)

    def export_current_document(self, target=None, file_format=None):
        return self.export_document_at_index(self.active_document_index, target, file_format)

    def export_document_at_index(self, index, target=None, file_format=None):
        if not self.loaded_ok or not 0 <= index < len(self.documents):
            return None
        self.sync_active_document()
        document = self.documents[index]
        if target is None:
            folder = document.export_path.parent if document.export_path else Path.home()
            default_format = file_format or document.export_format or ("csv" if document.export_path and document.export_path.suffix.casefold() == ".csv" else "json")
            initial = folder / (document.name + "." + default_format)
            filters = ("CSV files (*.csv)" if file_format == "csv" else "Navigator Layer files (*.json)"
                       if file_format == "navigator" else "JSON files (*.json);;CSV files (*.csv);;Navigator Layer files (*.json)")
            default_filter = ("CSV files (*.csv)" if default_format == "csv" else "Navigator Layer files (*.json)"
                              if default_format == "navigator" else "JSON files (*.json)")
            if default_format == "navigator":
                initial = folder / (document.name + ("" if document.name.endswith(".navigator") else ".navigator") + ".json")
            filename, chosen_filter = QtWidgets.QFileDialog.getSaveFileName(self, "Export selected TTPs", str(initial), filters, default_filter)
            if not filename:
                self.operation_report("[Export] Cancelled; no output files written", 1, 1)
                return None
            target = Path(filename)
            if file_format is None:
                file_format = ("navigator" if chosen_filter.startswith("Navigator") else "csv"
                               if chosen_filter.startswith("CSV") or (not chosen_filter and target.suffix.casefold() == ".csv") else "json")
        file_format = file_format or ("csv" if Path(target).suffix.casefold() == ".csv" else "json")
        try:
            exporter = export_layer if file_format == "navigator" else export_document_csv if file_format == "csv" else export_document_json
            path = exporter(document, Path(target), self.operation_report)
        except Exception as error:
            self.operation_report(f"[Export] Failed: {type(error).__name__}: {error}", 1, 1)
            QtWidgets.QMessageBox.critical(self, "Export failed", str(error))
            return None
        self.update_document_labels()
        return path

    def show_integration_dialog(self, dialog):
        if self.integration_dialog and self.integration_dialog.isVisible():
            self.integration_dialog.raise_()
            dialog.deleteLater()
            return
        if self.integration_dialog:
            self.integration_dialog.deleteLater()
        self.integration_dialog = dialog
        dialog.show()

    def import_navigator_layer(self, path=None):
        if not self.loaded_ok:
            return
        if self.integration_dialog and self.integration_dialog.isVisible():
            self.integration_dialog.raise_()
            return
        if path is None:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Navigator Layer", str(Path.home()), "Navigator Layer files (*.json)")
        if not path:
            self.operation_report("[Navigator Import] Cancelled; no output files written", 1, 1)
            return
        dialog = ImportLayerDialog(self.data_root, path, self.catalog, self)
        dialog.imported.connect(self.install_imported_document)
        self.show_integration_dialog(dialog)

    def install_imported_document(self, document):
        self.sync_active_document()
        self.documents.append(document)
        self.document_tabs.blockSignals(True)
        index = self.document_tabs.insertTab(len(self.documents) - 1, document.name)
        self.document_tabs.setTabData(index, document.document_id)
        self.document_tabs.setCurrentIndex(index)
        self.document_tabs.blockSignals(False)
        self.activate_document(index)

    def open_source_dialog(self):
        if not self.loaded_ok:
            return
        dialog = SourceDialog(self.data_root, self.catalog.version, self)
        dialog.imported.connect(self.install_imported_document)
        dialog.layer_ready.connect(lambda path: QtCore.QTimer.singleShot(0, lambda: self.import_navigator_layer(path)))
        self.show_integration_dialog(dialog)

    def open_upgrade_dialog(self):
        if not self.loaded_ok or not supports_navigator(self.catalog):
            return
        self.sync_active_document()
        dialog = UpgradeDialog(self.data_root, self.current_document, self.documents, self)
        dialog.imported.connect(self.install_imported_document)
        self.show_integration_dialog(dialog)

    def change_matrix_presentation(self, layout, sorting, platforms):
        if not self.loaded_ok or not supports_navigator(self.catalog):
            return
        self.operation_report('Input files: None; output files: None (layer presentation in memory)')
        self.operation_report('[Presentation 1/2] Saving layout, sorting and platform filters', 1, 2)
        try:
            set_presentation(self.current_document, layout, sorting, platforms)
        except ValueError as error:
            self.operation_report(f'[Presentation] Failed: {error}', 1, 1)
            return
        self.update_document_labels()
        self.refresh_layer_appearance()
        self.operation_report('[Presentation 2/2] Saved to the active layer', 2, 2)

    def open_selection_comparison(self):
        if self.loaded_ok:
            self.sync_active_document()
            self.show_integration_dialog(SelectionCompareDialog(list(self.documents), self))

    def open_version_comparison(self):
        if self.catalog and self.catalog.dataset_id:
            self.operation_report('Custom dataset: use Navigator → Review and upgrade layer to compare and migrate to an open custom dataset.', 1, 1)
            return
        if self.loaded_ok:
            self.sync_active_document()
            self.show_integration_dialog(VersionCompareDialog(self.data_root, self.current_document, self))

    def edit_navigator_annotation(self, key=None, tactic=None, return_matrix=False, return_selection=False):
        key = key if isinstance(key, str) else self.annotation_context
        if not self.loaded_ok or not key or not self.current_document:
            return
        self.sync_active_document()
        self.operation_report("Input files: None; output files: None (document annotations in memory)")
        self.operation_report("[Annotation 1/2] Editing technique annotation", 0, 2)
        dialog = AnnotationDialog(self.current_document, key, self)
        if tactic is not None:
            dialog.scope.setCurrentIndex(dialog.scope.findData(tactic))
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            self.operation_report("[Annotation 2/2] Cancelled; document unchanged", 2, 2)
            return
        self.current_document.navigator_layer = dialog.result_layer
        item = self.items_by_id[key][0]
        item.setCheckState(QtCore.Qt.CheckState.Checked if dialog.include.isChecked() else QtCore.Qt.CheckState.Unchecked)
        self.refresh_selection()
        if return_matrix:
            self.open_matrix()
        elif return_selection:
            self.show_document_page()
            self.tabs.setCurrentIndex(self.selection_tab_index)
        else:
            self.show_record(key, *getattr(self, "detail_context", ("", "")))
        self.operation_report("[Annotation 2/2] Saved in active document", 2, 2)

    def open_versions(self):
        if self.catalog and self.catalog.dataset_id:
            self.operation_report('Custom dataset: use File → Load layer URL / custom STIX to open another dataset, or Navigator → Review and upgrade layer to migrate annotations.', 1, 1)
            return
        if self.version_dialog and self.version_dialog.isVisible():
            self.version_dialog.raise_()
            return
        if self.version_dialog:
            self.version_dialog.deleteLater()
        self.version_dialog = VersionDialog(self.data_root, self.catalog.version if self.catalog else None, self,
                                            domain=self.catalog.domain if self.catalog else "enterprise-attack")
        self.version_dialog.chosen.connect(self.apply_version)
        self.version_dialog.show()

    def apply_version(self, value):
        catalog, pointer = value
        if pointer is not None and self.current_document:
            try:
                catalog = catalog.for_domain(self.current_document.catalog.domain)
            except ValueError as error:
                self.operation_report(f"[Version] Failed: {error}", 1, 1)
                return
        self.version_action.setEnabled(False)
        self.new_action.setEnabled(False)
        self.export_action.setEnabled(False)
        self.export_csv_action.setEnabled(False)
        self.load_source_action.setEnabled(False)
        for action in (self.import_layer_action, self.export_layer_action, self.compare_selections_action, self.compare_versions_action):
            action.setEnabled(False)
        for action in self.layer_actions:
            action.setEnabled(False)
        self.selection_export_button.setEnabled(False)
        self.document_tabs.setEnabled(False)
        self.details_action.setEnabled(False)
        self.search.setEnabled(False)
        self.ttp_search.setEnabled(False)
        for button in self.navigation_buttons.values():
            button.setEnabled(False)
        self.begin_tree(catalog)

    def focus_search(self):
        self.sidebar.setVisible(True)
        (self.ttp_search if self.active_category == "TTP" else self.search).setFocus()

    def load_failed(self, message):
        self.restoring_workspace = False
        self.open_details_page("Technique Details")
        self.version_action.setEnabled(True)
        self.report(f"Failed: {message}", 1, 1)
        print(f"Failed: {message}", flush=True)
        self.details.setHtml(f"<h2>Catalog could not be loaded</h2><p>{html.escape(message)}</p>"
                             "<p>Check data/attack/latest.json and the downloaded snapshot. See README.md.</p>")

    def begin_tree(self, catalog):
        if not catalog.dataset_id:
            self.official_catalog = catalog
        if self.closing:
            return
        self.restore_details_view = self.workspace.currentWidget() is self.details_page
        self.restore_matrix_view = self.workspace.currentWidget() is self.tabs and self.tabs.currentIndex() == self.matrix_tab_index
        self.restoring_workspace = True
        self.matrix_button.setEnabled(False)
        self.tabs.setTabEnabled(self.matrix_tab_index, False)
        self.matrix_view.invalidate()
        self.syncing = True
        self.restore_category = self.active_category
        self.retained_selection = self.selected.intersection(catalog.records)
        self.removed_selection_count = len(self.selected - self.retained_selection)
        self.selected = set()
        self.loaded_ok = False
        self.search_timer.stop()
        self.ttp_search_timer.stop()
        self.ttp_search.setEnabled(False)
        self.ttp_search.blockSignals(True)
        self.ttp_search.clear()
        self.ttp_search.blockSignals(False)
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
        self.ttp_search.setEnabled(True)
        for button in self.navigation_buttons.values():
            button.setEnabled(True)
        self.summary.setText(f"{DOMAIN_LABELS[self.catalog.domain]} v{self.catalog.version} · {len(self.catalog.groups)} platforms")
        self.version_label.setText(f"ATT&CK v{self.catalog.version}  |  {DOMAIN_LABELS[self.catalog.domain]}")
        self.report("[4/4 Tree] Complete", 1, 1)
        print(f"[4/4 Tree] Complete: {len(self.items_by_id)} unique selectable technique IDs", flush=True)
        windows = self.platform_items.get("Windows", next(iter(self.platform_items.values()), None))
        if windows is None:
            self.load_failed("No mapped platforms/tactics in the selected domain")
            return
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
        if not self.documents:
            self.active_document_index = self.append_document(self.catalog)
            self.document_tabs.blockSignals(True)
            self.document_tabs.setCurrentIndex(self.active_document_index)
            self.document_tabs.blockSignals(False)
        self.new_action.setEnabled(True)
        self.export_action.setEnabled(True)
        self.export_csv_action.setEnabled(True)
        self.load_source_action.setEnabled(True)
        for action in (self.import_layer_action, self.export_layer_action, self.compare_selections_action, self.compare_versions_action):
            action.setEnabled(True)
        self.selection_export_button.setEnabled(True)
        self.document_tabs.setEnabled(True)
        self.details_action.setEnabled(True)
        self.matrix_button.setEnabled(True)
        self.tabs.setTabEnabled(self.matrix_tab_index, True)
        self.refresh_selection()
        self.switch_category(self.restore_category)
        self.restoring_workspace = False
        if self.restore_matrix_view:
            self.open_matrix()
        elif self.restore_details_view:
            self.open_details_page()
        else:
            self.show_document_page()
        self.version_action.setText(f"Version (v{self.catalog.version})")
        self.version_action.setEnabled(True)
        if self.removed_selection_count:
            self.report(f"[Version 4/4 Switch] {self.removed_selection_count} selected techniques unavailable in this version were removed", 1, 1)
        self.report(f"[Version 4/4 Switch] Ready: v{self.catalog.version}; {len(self.selected)} selections retained", 1, 1)
        if getattr(self, "pending_domain_report", False):
            self.pending_domain_report = False
            self.operation_report(f"[Domain 3/3] Ready: {DOMAIN_LABELS[self.catalog.domain]} · {len(self.selected)} selected TTPs", 3, 3)
        if getattr(self, 'layer_matrix_pending', False):
            self.layer_matrix_pending = False
            self.open_matrix()
        self.ready.emit()

    def switch_category(self, category):
        if not self.loaded_ok:
            return
        self.active_category = category
        self.matrix_button.setVisible(category == "TTP")
        self.navigation_buttons[category].setChecked(True)
        self.sidebar.setVisible(True)
        self.search_timer.stop()
        self.ttp_search_timer.stop()
        self.ttp_search.blockSignals(True)
        self.ttp_search.clear()
        self.ttp_search.blockSignals(False)
        self.ttp_search.setVisible(category == "TTP")
        self.search.setVisible(category != "TTP")
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.proxy.setFilterFixedString("")
        self.library_proxy.setFilterFixedString("")
        self.open_details_page("Technique Details" if category == "TTP" else f"{category} Details")
        if category == "TTP":
            self.explorer_stack.setCurrentIndex(0)
            self.sidebar_title.setText("ATT&CK EXPLORER")
            self.search.setPlaceholderText("Search technique name or ID…")
            self.summary.setText(f"{DOMAIN_LABELS[self.catalog.domain]} v{self.catalog.version} · {len(self.catalog.groups)} platforms")
            self.version_label.setText(f"ATT&CK v{self.catalog.version}  |  {DOMAIN_LABELS[self.catalog.domain]}")
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
        self.open_details_page(f"{self.active_category} Details")
        domain, kind, key = item.data(ROLE_CONTEXT)
        self.crumb.setText(f"{DOMAIN_LABELS[domain]}  /  {self.active_category}  /  {external_id(self.catalog.objects_by_domain[domain][key]) if key else item.text()}")
        if not key:
            self.details.setHtml(f"<h1>{html.escape(item.text())}</h1><p>Expand this branch to browse its entries.</p>")
            return
        obj = self.catalog.objects_by_domain[domain][key]
        self.library_detail_context = (domain, key)
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
                             + (f"<p><a href='{html.escape(url, quote=True)}'>Open official ATT&CK reference ↗</a></p>" if url else "")
                             + self.source_techniques_html(domain, key))
        self.details.set_copy_content(obj.get("name", key), obj.get("description", ""))
        self.configure_bulk_action(domain, key)

    def hide_bulk_action(self):
        self.bulk_source_context = None
        self.annotation_context = None
        self.annotation_button.hide()
        self.bulk_action_bar.hide()

    def configure_bulk_action(self, domain, key):
        obj = self.catalog.objects_by_domain[domain][key]
        if obj.get("type") not in {"intrusion-set", "malware", "tool", "campaign"}:
            return
        keys = {row["target_ref"] for row in self.catalog.techniques_by_source[domain].get(key, [])}
        self.bulk_source_context = (domain, key)
        self.bulk_add_button.show()
        self.annotation_button.hide()
        self.bulk_add_button.setText(f"Add all TTPs ({len(keys)})")
        self.bulk_add_button.setEnabled(self.loaded_ok and domain == self.catalog.domain and bool(keys))
        self.bulk_add_button.setToolTip(
            f"Change this document's ATT&CK Domain to {DOMAIN_LABELS[domain]} to add these TTPs." if domain != self.catalog.domain else
            "Add the entry's directly related techniques to the active document; existing selections are kept."
            if keys else "No active related TTPs in this snapshot.")
        self.bulk_action_bar.show()

    def add_current_source_ttps(self):
        if self.bulk_source_context:
            self.add_source_ttps(*self.bulk_source_context)

    def add_source_ttps(self, domain, key):
        if not self.loaded_ok or not self.current_document:
            return
        obj = self.catalog.objects_by_domain.get(domain, {}).get(key, {})
        if domain != self.catalog.domain or obj.get("type") not in {"intrusion-set", "malware", "tool", "campaign"}:
            return
        self.operation_report("Input files: None (source relationships and active document in memory)")
        self.operation_report("Output files: None (selection only; use Export to write JSON/CSV)")
        self.operation_report(f"[Add all TTPs 1/3] Resolving {external_id(obj)} in v{self.catalog.version}", 0, 1)
        keys = {row["target_ref"] for row in self.catalog.techniques_by_source[domain].get(key, [])}
        selectable = keys.intersection(self.items_by_id)
        added = selectable - self.selected
        self.operation_report("[Add all TTPs 2/3] Updating checkboxes", 0, len(added))
        self.syncing = True
        try:
            for number, target in enumerate(sorted(added), 1):
                for item in self.items_by_id[target]:
                    item.setCheckState(QtCore.Qt.CheckState.Checked)
                if number % 100 == 0:
                    self.operation_report("[Add all TTPs 2/3] Updating checkboxes", number, len(added))
            self.selected.update(added)
        finally:
            self.syncing = False
        self.refresh_selection()
        self.operation_report(f"[Add all TTPs 3/3] Added {len(added)}; already selected {len(selectable - added)}; "
                              f"unavailable {len(keys - selectable)}; total {len(self.selected)}", 1, 1)

    def source_techniques_html(self, domain, key):
        obj = self.catalog.objects_by_domain[domain][key]
        headings = {"course-of-action": "Techniques Addressed by Mitigation",
                    "malware": "Techniques Used by Software", "tool": "Techniques Used by Software",
                    "campaign": "Techniques Used by Campaign", "intrusion-set": "Techniques Used by Group"}
        if obj.get("type") not in headings:
            return ""
        entries = self.catalog.techniques_by_source[domain].get(key, [])
        self.operation_report("Input files: None (related TTPs from the verified in-memory catalog)")
        self.operation_report("Output files: None (detail page only)")
        self.operation_report(f"[Related TTPs 1/2] Rendering {external_id(obj)} relationships", 0, len(entries))
        rows = []
        for number, entry in enumerate(entries, 1):
            target = self.catalog.objects_by_domain[domain][entry["target_ref"]]
            link = f"technique:{domain}/{target['id']}"
            parent = self.catalog.objects_by_domain[domain].get(self.catalog.parents_by_domain[domain].get(target["id"]))
            parent_html = (f"<br><span style='color:#aaaaaa'>Parent: {html.escape(external_id(parent))} "
                           f"{html.escape(parent['name'])}</span>" if parent else "")
            use = html.escape(entry["description"] or "No use description in this source relationship.").replace(chr(10), "<br>")
            refs = [f"<a href='{html.escape(ref['url'], quote=True)}'>{html.escape(ref.get('source_name', 'Reference'))}</a>"
                    for ref in entry["references"] if ref.get("url", "").startswith("https://")]
            rows.append(f"<tr><td valign='top'>{DOMAIN_LABELS[domain]}</td>"
                        f"<td valign='top'><a href='{link}'>{html.escape(external_id(target))}</a></td>"
                        f"<td valign='top'><a href='{link}'>{html.escape(target['name'])}</a>{parent_html}</td>"
                        f"<td>{use}" + ("<br>" + " · ".join(refs) if refs else "") + "</td></tr>")
            if number % 200 == 0:
                self.operation_report("[Related TTPs 1/2] Rendering rows", number, len(entries))
        self.operation_report(f"[Related TTPs 2/2] Ready: {len(entries)} relationships", 1, 1)
        heading = f"<hr><a name='related-ttps'></a><h2>{headings[obj['type']]} ({len(entries)})</h2>"
        if not rows:
            return heading + "<p>No active related techniques in this domain/version snapshot.</p>"
        return (heading + "<table cellspacing='0' cellpadding='6' border='1' width='100%'><tr>"
                "<th align='left'>Domain</th><th align='left'>ID</th><th align='left'>Name</th>"
                "<th align='left'>Use</th></tr>" + "".join(rows) + "</table>")

    def apply_ttp_search(self):
        self.ttp_search_timer.stop()
        if not self.loaded_ok or self.active_category != "TTP":
            return
        # Trim only the filter value, never the editable text: a paused trailing
        # space must survive so the user can continue typing the next word.
        query = self.ttp_search.text()
        self.search_timer.stop()
        self.search.blockSignals(True)
        self.search.setText(query)
        self.search.blockSignals(False)
        self.operation_report(f"Input files: None (TTP search uses the in-memory {DOMAIN_LABELS[self.catalog.domain]} catalog)")
        self.operation_report("Output files: None (sidebar filtering only)")
        self.operation_report("[TTP Search 1/2] Filtering technique names and IDs", 0, 1)
        self.apply_search()
        self.operation_report("[TTP Search 2/2] Ready" + (f": {query}" if query else ": all TTPs"), 1, 1)

    def apply_search(self):
        if self.active_category != "TTP":
            self.library_proxy.setFilterFixedString(self.search.text().strip())
            if self.search.text().strip():
                self.library_tree.expandAll()
            else:
                self.library_tree.collapseAll()
                self.library_tree.expandToDepth(0)
            return
        if self.ttp_search.text() != self.search.text():
            self.ttp_search.blockSignals(True)
            self.ttp_search.setText(self.search.text())
            self.ttp_search.blockSignals(False)
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
        self.open_details_page("Technique Details")
        item = self.model.itemFromIndex(self.proxy.mapToSource(index))
        context = item.data(ROLE_CONTEXT)
        key = item.data(ROLE_ID)
        platform, slug, _ = context
        if key:
            self.show_record(key, platform, slug)
        else:
            self.crumb.setText(DOMAIN_LABELS[self.catalog.domain] + "  /  " + platform + ("  /  " + self.catalog.tactics[slug]["name"] if slug else ""))
            self.details.setHtml(f"<h1>{html.escape(item.text())}</h1>"
                                 "<p>Expand this branch to browse its mapped techniques.</p>")

    def show_record(self, key, platform="", slug=""):
        self.open_details_page("Technique Details")
        record = self.catalog.records[key]
        parent_key = self.catalog.parents.get(key)
        parent = self.catalog.records.get(parent_key)
        parent_html = (f"<p><b>Parent technique</b> &nbsp; {html.escape(external_id(parent))} "
                       f"{html.escape(parent['name'])}</p>" if parent else "")
        self.detail_context = (platform, slug)
        related = self.related_techniques_html(key, platform, slug)
        self.crumb.setText("  /  ".join(part for part in (DOMAIN_LABELS[self.catalog.domain], platform,
                           self.catalog.tactics[slug]["name"] if slug else "", external_id(record)) if part))
        phases = [self.catalog.tactics[slug]["name"] for slug in self.catalog.tactic_order
                  if slug in tactic_phases(record, self.catalog.domain)]
        refs = [ref for ref in record.get("external_references", []) if ref.get("source_name") in {"mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"}]
        url = next((ref.get("url", "") for ref in refs), "")
        self.details.document().setDefaultStyleSheet("body {color:#d4d4d4;} h1 {font-size:26px;color:#ffffff;margin-right:90px;} "
                                                     "h2 {font-size:16px;color:#eeeeee;} a {color:#4daafc;} p {line-height:1.5;}")
        self.details.setHtml(f"<p style='color:#4daafc'>{html.escape(external_id(record))} · "
                             f"{'Sub-technique' if record.get('x_mitre_is_subtechnique') else 'Technique'}</p>"
                             f"<h1>{html.escape(record['name'])}</h1>"
                             f"{parent_html}"
                             f"<p><b>Platforms</b> &nbsp; {html.escape(', '.join(record.get('x_mitre_platforms', [])))}</p>"
                             f"<p><b>Tactics</b> &nbsp; {html.escape(', '.join(phases))}</p>"
                             "<p style='color:#999999'>Catalog entry · select this TTP to include it in the active document</p>"
                             f"{related}<hr><h2>Description</h2>"
                             f"<p>{html.escape(record.get('description', '')).replace(chr(10), '<br>')}</p>"
                             f"<p><a href='{html.escape(url, quote=True)}'>Open official ATT&CK reference ↗</a></p>"
                             + self.procedure_examples_html(key, self.catalog.domain))
        self.details.set_copy_content(record["name"], record.get("description", ""))
        self.annotation_context = key
        self.bulk_add_button.hide()
        self.annotation_button.show()
        self.bulk_action_bar.show()

    def procedure_examples_html(self, key, domain="enterprise-attack"):
        examples = self.catalog.procedures_by_domain[domain].get(key, [])
        if not examples:
            return "<hr><h2>Procedure Examples (0)</h2><p>No active procedure examples in this local snapshot.</p>"
        rows = []
        for example in examples:
            target = f"library:{domain}/{example['source_ref']}"
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
        if url.scheme() == "technique":
            domain, separator, key = url.path().partition("/")
            obj = self.catalog.objects_by_domain.get(domain, {}).get(key)
            if not separator or obj is None or obj.get("type") != "attack-pattern":
                return
            if domain == self.catalog.domain:
                self.open_detail_link(QtCore.QUrl(f"attack:{key}"))
            else:
                self.show_domain_technique(domain, key)
        elif url.scheme() == "attack":
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

    def show_domain_technique(self, domain, key):
        """Inspect a library link belonging to a different domain from this file."""
        obj = self.catalog.objects_by_domain[domain][key]
        parent = self.catalog.objects_by_domain[domain].get(self.catalog.parents_by_domain[domain].get(key))
        self.crumb.setText(f"{DOMAIN_LABELS[domain]}  /  Techniques  /  {external_id(obj)}")
        self.open_details_page(f"{DOMAIN_LABELS[domain]} Technique Details")
        parent_html = (f"<p><b>Parent technique</b> <a href='technique:{domain}/{parent['id']}'>"
                       f"{html.escape(external_id(parent) + ' ' + parent['name'])}</a></p>" if parent else "")
        source_domain, source_key = getattr(self, "library_detail_context", ("", ""))
        back = (f"<p><a href='library:{source_domain}/{source_key}'>Back to source entry</a></p>"
                if source_domain == domain else "")
        self.details.setHtml(f"<p style='color:#4daafc'>{html.escape(external_id(obj))} · {DOMAIN_LABELS[domain]}</p>"
                             f"<h1>{html.escape(obj['name'])}</h1>{back}{parent_html}"
                             f"<p><b>Platforms</b> {html.escape(', '.join(obj.get('x_mitre_platforms', [])))}</p>"
                             f"<p>To select this TTP, change this document's ATT&CK Domain to {DOMAIN_LABELS[domain]}.</p>"
                             "<hr><h2>Description</h2>"
                             f"<p>{html.escape(obj.get('description', '')).replace(chr(10), '<br>')}</p>"
                             + self.procedure_examples_html(key, domain))
        self.details.set_copy_content(obj["name"], obj.get("description", ""))

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
        self.sync_active_document()
        state_rows = rows_by_scope(self.current_document)
        previous_syncing = self.syncing
        self.syncing = True
        for key, items in self.items_by_id.items():
            attack_id = external_id(self.catalog.records[key])
            for item in items:
                context = item.data(ROLE_CONTEXT)
                slug = context[1] if context else ''
                enabled = state_rows.get((attack_id, slug), state_rows.get((attack_id, ''), {})).get('enabled', True)
                item.setForeground(QtGui.QBrush() if enabled else QtGui.QBrush(QtGui.QColor('#858585')))
        self.syncing = previous_syncing
        self.matrix_view.update_selection(self.selected)
        self.refresh_layer_appearance()
        previous = self.selection_list.currentItem()
        previous_key = previous.data(ROLE_ID) if previous else None
        self.selection_list.clear()
        for key in sorted(self.selected, key=lambda key: external_id(self.catalog.records[key])):
            record = self.catalog.records[key]
            label = f"{external_id(record)}  {record['name']}"
            enabled, tactic_states = technique_states(self.current_document, key, state_rows)
            values = {entry['enabled'] for entry in tactic_states} or {enabled}
            label += '  [' + ('Mixed tactic states' if len(values) > 1 else 'Enabled' if True in values else 'Disabled') + ']'
            parent_key = self.catalog.parents.get(key)
            if parent_key:
                parent = self.catalog.records[parent_key]
                label += f"\n    Parent: {external_id(parent)}  {parent['name']}"
            comment, scoped = technique_comments(self.current_document, key)
            if comment:
                preview = ' '.join(comment.split())
                label += '\n    Comment: ' + (preview[:140] + '…' if len(preview) > 140 else preview)
            if scoped:
                label += f"\n    Tactic comments: {len(scoped)}"
            item = QtWidgets.QListWidgetItem(label)
            item.setData(ROLE_ID, key)
            item.setToolTip('\n\n'.join(([comment] if comment else []) +
                            [f"{entry['tactic']}: {entry['comment']}" for entry in scoped]))
            self.selection_list.addItem(item)
            if key == previous_key:
                self.selection_list.setCurrentItem(item)
        if self.selection_list.count() and self.selection_list.currentItem() is None:
            self.selection_list.setCurrentRow(0)
        self.tabs.setTabText(self.selection_tab_index, f"Selected Techniques ({len(self.selected)})")
        self.state.setText(f"Ready  |  {self.current_document.name if self.current_document else 'TTP'}  |  {len(self.selected)} selected")

    def show_selected(self, item):
        self.switch_category("TTP")
        self.show_record(item.data(ROLE_ID))

    def show_selected_context_menu(self, position):
        item = self.selection_list.itemAt(position)
        if not self.loaded_ok or item is None:
            return
        self.selection_list.setCurrentItem(item)
        key = item.data(ROLE_ID)
        menu = QtWidgets.QMenu(self.selection_list)
        menu.addAction("Edit TTP annotation…", lambda: self.edit_selected_annotation(key))
        self.selected_context_menu = menu
        menu.aboutToHide.connect(menu.deleteLater)
        menu.popup(self.selection_list.viewport().mapToGlobal(position))

    def edit_selected_annotation(self, key=None):
        item = self.selection_list.currentItem()
        key = key if isinstance(key, str) else item.data(ROLE_ID) if item else None
        if not self.loaded_ok or key not in self.selected:
            return
        self.show_document_page()
        self.tabs.setCurrentIndex(self.selection_tab_index)
        self.edit_navigator_annotation(key, '', return_selection=True)

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
        self.search_timer.stop()
        self.ttp_search_timer.stop()
        self.matrix_view.timer.stop()
        self.build_timer.stop()
        if self.integration_dialog and getattr(self.integration_dialog, "worker", None) and self.integration_dialog.worker.isRunning():
            self.closing = True
            self.integration_dialog.reject()
            self.integration_dialog.worker.finished.connect(self.close, QtCore.Qt.ConnectionType.SingleShotConnection)
            event.ignore()
            return
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


def configure_windows_taskbar():
    """Give Windows a project identity before Qt creates any native windows."""
    if sys.platform != "win32":
        return
    print("[Windows taskbar 1/2] Input files: None (application identity in memory)", flush=True)
    print("[Windows taskbar 1/2] Output files: None (current process identity)", flush=True)
    try:
        import ctypes

        set_app_id = ctypes.WinDLL("shell32").SetCurrentProcessExplicitAppUserModelID
        set_app_id.argtypes = [ctypes.c_wchar_p]
        set_app_id.restype = ctypes.c_long
        result = set_app_id(APP_USER_MODEL_ID)
        if result < 0:
            raise OSError(f"HRESULT 0x{result & 0xffffffff:08X}")
        print(f"[Windows taskbar 2/2] Complete: {APP_USER_MODEL_ID}", flush=True)
    except (OSError, AttributeError) as error:
        print(f"[Windows taskbar 2/2] Could not set application identity: {error}", flush=True)


def configure_application(app):
    """Use explicit colors for consistent text contrast on Windows and offscreen previews."""
    icon_path = Path(__file__).resolve().parent / "assets" / "ttp-selection-studio-icon-pixel.png"
    print(f"[Application icon 1/2] Input file: {icon_path}", flush=True)
    print("[Application icon 1/2] Output files: None (application/window icon in memory)", flush=True)
    icon_pixmap = QtGui.QPixmap(str(icon_path))
    if icon_pixmap.isNull():
        print("[Application icon 2/2] Could not load icon; using the system default", flush=True)
    else:
        app.setWindowIcon(QtGui.QIcon(icon_pixmap))
        print("[Application icon 2/2] Complete: pixel icon applied to application and windows", flush=True)
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
        for name in ("segoeui.ttf", "segoeuib.ttf", "consola.ttf", "msjh.ttc", "msjhbd.ttc"):
            font_path = font_root / name
            if font_path.is_file():
                print(f"[Preview fonts] Input file: {font_path}", flush=True)
                if QtGui.QFontDatabase.addApplicationFont(str(font_path)) < 0:
                    print(f"[Preview fonts] Could not load {font_path}", flush=True)
        print("[Preview fonts] Complete", flush=True)
    font = QtGui.QFont("Segoe UI", 10)
    if app.platformName() == "offscreen":
        font.setFamilies(["Segoe UI", "Microsoft JhengHei"])
    app.setFont(font)
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
    configure_windows_taskbar()
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






