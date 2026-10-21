"""Platform-filtered ATT&CK matrix with expandable families. Workflow: README.md."""
from __future__ import annotations

import html
from PySide6 import QtCore, QtGui, QtWidgets

from attack_catalog import external_id, DOMAIN_LABELS, supports_navigator, tactic_phases, domain_label
from navigator_visuals import LayerAppearance, OverlayAppearance, display_color
from navigator_fields import presentation, sorted_families, web_url
from matrix_presentations import FamilyView
from ttp_search import matches as search_matches, DEFAULT_SEARCH_FIELDS
from ttp_selection import is_selected
from matrix_display import display_label, labels, header_color, marker_colors
from navigator_visuals import foreground_color
from matrix_expansion import expanded_family
from ttp_sources import SOURCE_KINDS, source_choices, resolve_sources, source_cells
from source_preview import SourceResultHover, draw_source_preview

MATRIX_ID = int(QtCore.Qt.ItemDataRole.UserRole) + 1
MATRIX_SLUG = MATRIX_ID + 1
MATRIX_STYLE = MATRIX_SLUG + 1
MATRIX_TOOLTIP = MATRIX_STYLE + 1
MATRIX_CHILDREN = MATRIX_TOOLTIP + 1
ALL_PLATFORMS = "All Platforms"
SOURCE_SEARCH = MATRIX_CHILDREN + 1


class SourceCompleter(QtWidgets.QCompleter):
    def splitPath(self, path):
        return [path.strip()]

    def pathFromIndex(self, index):
        # Search a separate role while completing only the short identity label.
        return index.data(QtCore.Qt.ItemDataRole.DisplayRole) or ''


def matrix_columns(catalog, platform=ALL_PLATFORMS):
    """Project the catalog's exact mappings, retaining structural parents without selecting them."""
    if isinstance(platform, (list, tuple, set)):
        if set(platform) - catalog.groups.keys():
            raise ValueError('Platform is absent from this ATT&CK version')
        scopes = [catalog.groups[p] for p in platform]
    elif platform != ALL_PLATFORMS and platform not in catalog.groups:
        raise ValueError("Platform is absent from this ATT&CK version")
    else:
        scopes = catalog.groups.values() if platform == ALL_PLATFORMS else [catalog.groups[platform]]
    scoped = {slug: set() for slug in catalog.tactic_order}
    for tactics in scopes:
        for slug, keys in tactics.items():
            scoped[slug].update(keys)
    sort_key = lambda key: (catalog.records[key]['name'].casefold(), external_id(catalog.records[key]))
    columns = []
    for slug in catalog.tactic_order:
        keys = scoped[slug]
        families = {}
        for key in keys:
            parent = catalog.parents.get(key, key)
            families.setdefault(parent, []).extend([key] if parent != key else [])
        rows = [{"key": key, "selectable": key in keys, "children": sorted(families[key], key=sort_key)}
                for key in sorted(families, key=sort_key)]
        if rows:
            columns.append((slug, rows))
    return columns


class MatrixDelegate(QtWidgets.QStyledItemDelegate):
    """Wrap long technique names within a narrow matrix column."""
    def sizeHint(self, option, index):
        depth = 1 if index.parent().isValid() else 0
        width = max(70, self.parent().viewport().width() - 52 - depth * 14)
        rect = option.fontMetrics.boundingRect(QtCore.QRect(0, 0, width, 1000),
                                               QtCore.Qt.TextFlag.TextWordWrap, str(index.data() or ""))
        return QtCore.QSize(width, max(34, rect.height() + 12))

    def paint(self, painter, option, index):
        wrapped = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(wrapped, index)
        wrapped.features |= QtWidgets.QStyleOptionViewItem.ViewItemFeature.WrapText
        wrapped.textElideMode = QtCore.Qt.TextElideMode.ElideNone
        wrapped.displayAlignment = QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        appearance = index.data(MATRIX_STYLE) or {}
        if not appearance.get("background") and appearance.get('enabled', True):
            super().paint(painter, wrapped, index)
            self.paint_source_preview(painter,wrapped.rect,index)
            self.paint_markers(painter,wrapped.rect,appearance)
            return
        # Draw the annotation fill explicitly: stylesheet item colors would
        # otherwise replace BackgroundRole, especially for the selected row.
        painter.save()
        painter.fillRect(wrapped.rect, QtGui.QColor(appearance["background"] or '#222526'))
        selected = bool(wrapped.state & QtWidgets.QStyle.StateFlag.State_Selected)
        painter.setPen(QtGui.QPen(QtGui.QColor(appearance["foreground"] if selected else '#41484d'), 2 if selected else 1))
        painter.drawRect(wrapped.rect.adjusted(0, 0, -1, -1))
        widget = wrapped.widget or self.parent()
        style = widget.style()
        if wrapped.features & QtWidgets.QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator:
            checkbox = QtWidgets.QStyleOptionButton()
            checkbox.rect = style.subElementRect(QtWidgets.QStyle.SubElement.SE_ItemViewItemCheckIndicator, wrapped, widget)
            checkbox.state = QtWidgets.QStyle.StateFlag.State_Enabled | (
                QtWidgets.QStyle.StateFlag.State_On if wrapped.checkState == QtCore.Qt.CheckState.Checked
                else QtWidgets.QStyle.StateFlag.State_Off)
            style.drawControl(QtWidgets.QStyle.ControlElement.CE_CheckBox, checkbox, painter, widget)
        text_rect = style.subElementRect(QtWidgets.QStyle.SubElement.SE_ItemViewItemText, wrapped, widget).adjusted(3, 0, -3, 0)
        painter.setPen(QtGui.QColor(appearance["foreground"]))
        painter.setFont(wrapped.font)
        painter.drawText(text_rect, QtCore.Qt.TextFlag.TextWordWrap | QtCore.Qt.AlignmentFlag.AlignLeft
                         | QtCore.Qt.AlignmentFlag.AlignVCenter, wrapped.text)
        painter.restore()
        self.paint_source_preview(painter,wrapped.rect,index)
        self.paint_markers(painter,wrapped.rect,appearance)

    def paint_source_preview(self,painter,rect,index):
        tree = self.parent()
        children = []
        if not tree.isExpanded(index):
            children = [tree.model().index(i,0,index) for i in range(tree.model().rowCount(index))]
        keys = [child.data(MATRIX_ID) for child in children if not tree.isRowHidden(child.row(),index)]
        kind = tree.owner.source_preview_kind(index.data(MATRIX_ID),index.data(MATRIX_SLUG),keys,tree.isExpanded(index))
        draw_source_preview(painter,rect,kind)

    @staticmethod
    def paint_markers(painter,rect,appearance):
        painter.save()
        for number,color in enumerate(marker_colors(appearance)):
            painter.setPen(QtGui.QPen(QtGui.QColor(color),2))
            y=rect.bottom()-3-number*3
            painter.drawLine(rect.left()+4,y,rect.right()-4,y)
        painter.restore()


class TechniqueTree(QtWidgets.QTreeWidget):
    """Retain additive checkbox clicks; labels use Navigator modifier gestures."""
    def __init__(self, owner, slug):
        super().__init__()
        self.owner, self.slug = owner, slug
        self.gesture_press = False

    def mousePressEvent(self, event):
        self.gesture_press = False
        item = self.itemAt(event.position().toPoint())
        if event.button() == QtCore.Qt.MouseButton.LeftButton and item and item.flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable:
            rect = self.visualItemRect(item)
            # The branch arrow lies to the left of the item's visual rect.
            if event.position().x() >= rect.left():
                option = QtWidgets.QStyleOptionViewItem()
                option.initFrom(self)
                option.rect = rect
                self.itemDelegate().initStyleOption(option,self.indexFromItem(item))
                indicator = self.style().subElementRect(QtWidgets.QStyle.SubElement.SE_ItemViewItemCheckIndicator,option,self)
                modified = self.owner.selection_modifiers(event.modifiers())
                if modified or not indicator.contains(event.position().toPoint()):
                    self.setCurrentItem(item)
                    self.gesture_press = True
                    self.owner.request_mouse_selection(item.data(0,MATRIX_ID),self.slug,event.modifiers())
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.gesture_press:
            self.gesture_press = False
            event.accept()
            return
        super().mouseReleaseEvent(event)


class AttackMatrix(QtWidgets.QWidget):
    selection_requested = QtCore.Signal(str, bool)
    scoped_selection_requested = QtCore.Signal(str, str, bool)
    mouse_selection_requested = QtCore.Signal(str, str, str)
    family_expansion_requested = QtCore.Signal(str, str, bool, object)
    detail_requested = QtCore.Signal(str, str)
    progress = QtCore.Signal(str, int, int)
    ready = QtCore.Signal()
    layer_requested = QtCore.Signal(str)
    overlay_requested = QtCore.Signal(bool)
    new_layer_requested = QtCore.Signal()
    duplicate_layer_requested = QtCore.Signal()
    layer_settings_requested = QtCore.Signal()
    color_selected_requested = QtCore.Signal()
    clear_selected_color_requested = QtCore.Signal()
    score_selected_requested = QtCore.Signal()
    annotation_requested = QtCore.Signal(str, str)
    cell_color_requested = QtCore.Signal(str, str)
    cell_clear_color_requested = QtCore.Signal(str, str)
    source_requested = QtCore.Signal(str, str)
    source_operation_requested = QtCore.Signal(str, str, str)
    source_batch_requested = QtCore.Signal(object, object, str)
    source_detail_requested = QtCore.Signal(str, str)
    presentation_requested = QtCore.Signal(str, int, object)
    display_requested = QtCore.Signal(object)
    bulk_selection_requested = QtCore.Signal(str, str, str)
    batch_edit_requested = QtCore.Signal(bool)
    enabled_requested = QtCore.Signal(object)
    cell_enabled_requested = QtCore.Signal(str, str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.catalog = None
        self.selected = set()
        self.selection_scopes = {}
        self.search_fields = list(DEFAULT_SEARCH_FIELDS)
        self.columns = []
        self.items_by_id = {}
        self.queue = []
        self.build_index = 0
        self.building = False
        self.expansion_mode = None
        self.expansion_syncing = False
        self.expansion_document_id = None
        self.restore_expansion = False
        self.syncing = False
        self.appearance = LayerAppearance()
        self.source_preview_cells = frozenset()
        self.source_preview_context = None
        self.source_catalog = None
        self.source_entries = {}
        self.selected_platforms = None
        self.presentation_syncing = False
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 8)
        layers = QtWidgets.QHBoxLayout()
        layers.addWidget(QtWidgets.QLabel("Layer"))
        self.layer_selector = QtWidgets.QComboBox()
        self.layer_selector.setMinimumWidth(150)
        self.layer_selector.currentIndexChanged.connect(lambda index: self.layer_requested.emit(self.layer_selector.itemData(index) or ''))
        layers.addWidget(self.layer_selector, 1)
        self.show_all_layers = QtWidgets.QCheckBox("Show all layers")
        self.show_all_layers.setToolTip("Overlay all open layers matching the active domain and ATT&CK version. Overlaps use equal-weight RGB mixing.")
        self.show_all_layers.toggled.connect(self.overlay_requested.emit)
        layers.addWidget(self.show_all_layers)
        for name, text, signal in (("new_layer_button", "New layer", self.new_layer_requested),
                                  ("duplicate_layer_button", "Duplicate", self.duplicate_layer_requested),
                                  ("layer_settings_button", "Layer settings…", self.layer_settings_requested)):
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(lambda checked=False, target=signal: target.emit())
            setattr(self, name, button)
            layers.addWidget(button)
        layout.addLayout(layers)
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.addWidget(QtWidgets.QLabel("Platform"))
        self.platform = QtWidgets.QComboBox()
        self.platform.setMinimumWidth(140)
        self.platform.currentTextChanged.connect(self.single_platform_changed)
        toolbar.addWidget(self.platform)
        self.platforms_button = QtWidgets.QPushButton('Multiple…')
        self.platforms_button.clicked.connect(self.choose_platforms)
        toolbar.addWidget(self.platforms_button)
        self.view_layout = QtWidgets.QComboBox()
        self.view_layout.addItems(['Flat', 'Side', 'Mini'])
        self.view_layout.currentTextChanged.connect(self.presentation_changed)
        toolbar.addWidget(self.view_layout)
        self.sorting = QtWidgets.QComboBox()
        self.sorting.addItems(['Name ↑', 'Name ↓', 'Score ↑', 'Score ↓'])
        self.sorting.currentIndexChanged.connect(self.presentation_changed)
        toolbar.addWidget(self.sorting)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText("Search matrix by technique name or ID…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_items)
        toolbar.addWidget(self.search, 1)
        self.expand_button = QtWidgets.QPushButton("Expand all")
        self.expand_button.clicked.connect(lambda: self.set_expanded(True))
        toolbar.addWidget(self.expand_button)
        self.collapse_button = QtWidgets.QPushButton("Collapse all")
        self.collapse_button.clicked.connect(lambda: self.set_expanded(False))
        toolbar.addWidget(self.collapse_button)
        layout.addLayout(toolbar)
        display_bar=QtWidgets.QHBoxLayout()
        self.show_names=QtWidgets.QCheckBox('Show names')
        self.show_ids=QtWidgets.QCheckBox('Show IDs')
        self.show_tactic_background=QtWidgets.QCheckBox('Tactic background')
        for control in (self.show_names,self.show_ids,self.show_tactic_background):
            display_bar.addWidget(control)
        self.tactic_color_button=QtWidgets.QPushButton('Header color…')
        display_bar.addWidget(self.tactic_color_button)
        self.expand_annotated_button=QtWidgets.QPushButton('Expand annotated')
        self.expand_annotated_button.setToolTip('Expand families containing annotated children; siblings remain visible. Selection is unchanged.')
        self.expand_annotated_button.clicked.connect(self.expand_annotated)
        display_bar.addWidget(self.expand_annotated_button)
        self.expansion_mode_picker = QtWidgets.QComboBox()
        for title, value in [('Per-technique · saved', None), ('Collapse all · saved', 'none'),
                             ('Expand all · saved', 'all'), ('Annotated · saved', 'annotated')]:
            self.expansion_mode_picker.addItem(title, value)
        self.expansion_mode_picker.setToolTip('Expansion policy saved with the layer. Search may temporarily open matching families.')
        self.expansion_mode_picker.activated.connect(lambda index:self.choose_expansion(self.expansion_mode_picker.itemData(index)))
        display_bar.addWidget(self.expansion_mode_picker)
        display_bar.addStretch()
        layout.addLayout(display_bar)
        self.show_names.toggled.connect(lambda value:self.request_display({'showName':value}))
        self.show_ids.toggled.connect(lambda value:self.request_display({'showID':value}))
        self.show_tactic_background.toggled.connect(lambda value:self.request_display({'showTacticRowBackground':value}))
        self.tactic_color_button.clicked.connect(self.choose_tactic_color)
        sources = QtWidgets.QHBoxLayout()
        sources.addWidget(QtWidgets.QLabel("TTPs from"))
        self.source_kind = QtWidgets.QComboBox()
        self.source_kind.addItems(list(SOURCE_KINDS))
        self.source_kind.currentTextChanged.connect(self.populate_sources)
        sources.addWidget(self.source_kind)
        self.source_picker = QtWidgets.QComboBox()
        self.source_picker.setEditable(True)
        self.source_picker.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.source_picker.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.source_picker.setMinimumContentsLength(20)
        self.source_picker.setMaxVisibleItems(15)
        self.source_picker.lineEdit().setClearButtonEnabled(True)
        self.source_completer = SourceCompleter(self.source_picker.model(), self.source_picker)
        self.source_completer.setCompletionRole(SOURCE_SEARCH)
        self.source_completer.setCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)
        self.source_completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)
        self.source_completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
        self.source_picker.setCompleter(self.source_completer)
        self.source_hover_filters = [SourceResultHover(view,self.preview_source_index,self.clear_source_preview)
                                     for view in (self.source_picker.view(),self.source_completer.popup())]
        self.source_picker.editTextChanged.connect(lambda *_:self.clear_source_preview())
        self.source_completer.activated[str].connect(self.choose_source_completion)
        self.source_picker.editTextChanged.connect(self.update_source_state)
        sources.addWidget(self.source_picker, 1)
        self.add_source_button = QtWidgets.QPushButton("Add techniques")
        self.add_source_button.clicked.connect(self.add_source)
        sources.addWidget(self.add_source_button)
        self.remove_source_button = QtWidgets.QPushButton('Remove techniques')
        self.remove_source_button.clicked.connect(lambda: self.add_source('remove'))
        sources.addWidget(self.remove_source_button)
        self.source_details_button = QtWidgets.QPushButton('View source')
        self.source_details_button.clicked.connect(self.view_source_details)
        sources.addWidget(self.source_details_button)
        layout.addLayout(sources)
        results = QtWidgets.QHBoxLayout()
        self.source_results_summary = QtWidgets.QLabel()
        self.source_results_summary.setWordWrap(True)
        results.addWidget(self.source_results_summary,1)
        self.add_source_results_button = QtWidgets.QPushButton('Add all results')
        self.remove_source_results_button = QtWidgets.QPushButton('Remove all results')
        self.add_source_results_button.clicked.connect(lambda:self.change_source_results('add'))
        self.remove_source_results_button.clicked.connect(lambda:self.change_source_results('remove'))
        results.addWidget(self.add_source_results_button)
        results.addWidget(self.remove_source_results_button)
        layout.addLayout(results)
        self.populate_sources()
        colors = QtWidgets.QHBoxLayout()
        for name, text, signal in (("color_button", "Color selected…", self.color_selected_requested),
                                  ("clear_color_button", "Clear selected colors", self.clear_selected_color_requested),
                                  ("score_button", "Score selected…", self.score_selected_requested)):
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(lambda checked=False, target=signal: target.emit())
            setattr(self, name, button)
            colors.addWidget(button)
        colors.addStretch()
        self.show_colors = QtWidgets.QCheckBox("Show layer colors")
        self.show_colors.setChecked(True)
        self.show_colors.toggled.connect(self.apply_appearance)
        colors.addWidget(self.show_colors)
        layout.addLayout(colors)
        batch = QtWidgets.QHBoxLayout()
        batch.addWidget(QtWidgets.QLabel('Selection scope'))
        self.selection_scope = QtWidgets.QComboBox()
        self.selection_scope.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.selection_scope.setMinimumContentsLength(18)
        self.selection_scope.addItem('Platform scope · includes hidden', 'platform')
        self.selection_scope.addItem('Search matches · excludes hidden', 'search')
        self.selection_scope.addItem('Visible / expanded cells', 'visible')
        batch.addWidget(self.selection_scope)
        self.selection_tactic = QtWidgets.QComboBox()
        self.selection_tactic.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.selection_tactic.setMinimumContentsLength(12)
        self.selection_tactic.addItem('All tactics', '')
        batch.addWidget(self.selection_tactic)
        self.bulk_select_button = QtWidgets.QToolButton()
        self.bulk_select_button.setText('Select…')
        self.bulk_select_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QtWidgets.QMenu(self.bulk_select_button)
        for label, action in [('Select all in scope', 'add'), ('Select only this scope', 'replace'),
                              ('Deselect scope', 'remove'), ('Invert scope', 'invert'),
                              ('Select annotated only', 'annotated'), ('Select unannotated only', 'unannotated')]:
            menu.addAction(label, lambda checked=False, op=action: self.bulk_selection_requested.emit(
                op, self.selection_scope.currentData(), self.selection_tactic.currentData() or ''))
        self.bulk_select_button.setMenu(menu)
        batch.addWidget(self.bulk_select_button)
        self.batch_edit_button = QtWidgets.QPushButton('Batch edit selected…')
        self.batch_edit_button.clicked.connect(lambda: self.batch_edit_requested.emit(False))
        batch.addWidget(self.batch_edit_button)
        self.state_button = QtWidgets.QToolButton()
        self.state_button.setText('State…')
        self.state_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        state_menu = QtWidgets.QMenu(self.state_button)
        for label, value in [('Enable selected', True), ('Disable selected', False), ('Toggle selected states', 'toggle')]:
            state_menu.addAction(label, lambda checked=False, state=value: self.enabled_requested.emit(state))
        state_menu.addSeparator()
        state_menu.addAction('Clear all selected annotations…', lambda: self.batch_edit_requested.emit(True))
        self.state_button.setMenu(state_menu)
        batch.addWidget(self.state_button)
        batch.addStretch()
        layout.addLayout(batch)
        self.summary = QtWidgets.QLabel("Open the matrix after the local catalog loads.")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.overlay_info = QtWidgets.QLabel()
        self.overlay_info.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.overlay_info.setWordWrap(True)
        self.overlay_info.setStyleSheet('color:#9da5b4;font-size:11px;')
        self.overlay_info.hide()
        layout.addWidget(self.overlay_info)
        self.legend = QtWidgets.QLabel()
        self.legend.setWordWrap(True)
        self.legend.setTextFormat(QtCore.Qt.TextFormat.RichText)
        layout.addWidget(self.legend)
        self.empty = QtWidgets.QLabel("No matching techniques. Clear the search or change platform.")
        self.empty.hide()
        layout.addWidget(self.empty)
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.content = QtWidgets.QWidget()
        self.column_layout = QtWidgets.QHBoxLayout(self.content)
        self.column_layout.setContentsMargins(0, 0, 0, 0)
        self.column_layout.setSpacing(8)
        self.column_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, 1)
        hint = QtWidgets.QLabel("Expand with the arrow · Check to include · Double-click for details · Right-click to edit color/annotation\n"
                               "Source hover: cyan outline = related technique; dashed outline = related collapsed child")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.build_column)

    def invalidate(self):
        self.clear_source_preview()
        self.source_picker.hidePopup()
        self.source_completer.popup().hide()
        self.timer.stop()
        self.catalog = None
        self.update_source_state()
        self.building = False
        self.syncing = True
        while self.column_layout.count():
            widget = self.column_layout.takeAt(0).widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        self.columns = []
        self.items_by_id = {}
        self.queue = []
        self.syncing = False
        self.empty.hide()
        self.summary.setText("Loading the document's ATT&CK catalog…")

    def set_catalog(self, catalog, selected):
        if self.catalog is catalog:
            self.update_selection(selected)
            return
        previous_platform = self.platform.currentText()
        self.invalidate()
        self.catalog = catalog
        if self.source_catalog is not catalog:
            self.source_catalog = catalog
            self.populate_sources()
        self.selected = set(selected)
        self.platform.blockSignals(True)
        self.platform.clear()
        self.platform.addItems([ALL_PLATFORMS, *catalog.groups])
        self.platform.setCurrentText(previous_platform if previous_platform in catalog.groups else ALL_PLATFORMS)
        self.platform.blockSignals(False)
        self.selection_tactic.blockSignals(True)
        self.selection_tactic.clear()
        self.selection_tactic.addItem('All tactics', '')
        for slug in catalog.tactic_order:
            self.selection_tactic.addItem(catalog.tactics[slug]['name'], slug)
        self.selection_tactic.blockSignals(False)
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.rebuild()

    def rebuild(self, *_):
        if self.catalog is None:
            return
        catalog, selected = self.catalog, set(self.selected)
        self.invalidate()
        self.catalog, self.selected = catalog, selected
        self.progress.emit("[Matrix 1/3 Scope] Input files: None; output files: None (verified catalog in memory)", 0, 0)
        self.queue = [(slug, sorted_families(catalog, slug, rows, self.appearance, self.sorting.currentIndex()))
                      for slug, rows in matrix_columns(catalog, self.platform_scope())]
        self.build_index = 0
        self.building = True
        self.bulk_select_button.setEnabled(False)
        self.batch_edit_button.setEnabled(False)
        self.state_button.setEnabled(False)
        self.progress.emit("[Matrix 1/3 Scope] Platform/tactic families resolved", 1, 1)
        self.timer.start(0)

    def make_item(self, key, slug, selectable, children=0):
        record = self.catalog.records[key]
        name = display_label(external_id(record),record['name'],self.display_layer())
        name += f" ({children})" if children and name else ''
        item = QtWidgets.QTreeWidgetItem([name])
        item.setData(0, MATRIX_ID, key)
        item.setData(0, MATRIX_SLUG, slug)
        item.setData(0,MATRIX_CHILDREN,children)
        item.setToolTip(0, f"{external_id(record)}  {record['name']}"
                          + (f"\n{children} sub-techniques in this platform/tactic" if children else "")
                          + ("" if selectable else "\nGrouping only; parent is not mapped to this platform/tactic"))
        item.setData(0, MATRIX_TOOLTIP, item.toolTip(0))
        flags = QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
        if selectable:
            flags |= QtCore.Qt.ItemFlag.ItemIsUserCheckable
            item.setCheckState(0, QtCore.Qt.CheckState.Checked if self.cell_selected(key, slug) else QtCore.Qt.CheckState.Unchecked)
            self.items_by_id.setdefault(key, []).append(item)
        item.setFlags(flags)
        self.apply_item_appearance(item)
        return item

    def build_column(self):
        if self.catalog is None:
            self.timer.stop()
            return
        if self.build_index >= len(self.queue):
            self.timer.stop()
            self.building = False
            self.update_source_state()
            self.filter_items()
            self.update_selection(self.selected)
            self.progress.emit("[Matrix 3/3 Ready] Matrix columns complete", 1, 1)
            self.ready.emit()
            return
        slug, families = self.queue[self.build_index]
        frame = QtWidgets.QWidget()
        mode = self.view_layout.currentText().lower()
        frame.setFixedWidth(365 if mode == 'side' else 225 if mode == 'mini' else 190)
        column = QtWidgets.QVBoxLayout(frame)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(5)
        title = QtWidgets.QLabel(self.catalog.tactics[slug]['name'])
        title.setWordWrap(True)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(44)
        title.setStyleSheet("color:#6caedf;font-weight:600;font-size:13px;")
        title.setToolTip(external_id(self.catalog.tactics[slug]) or "Historical phase heading")
        title.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        title.customContextMenuRequested.connect(lambda pos, label=title, tactic=slug: self.tactic_menu(label, tactic, pos))
        self.apply_header(title,slug)
        column.addWidget(title)
        count = QtWidgets.QLabel(f"{len(families)} techniques")
        count.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        count.setStyleSheet("font-size:11px;color:#bbbbbb;")
        column.addWidget(count)
        if mode != 'flat':
            view = FamilyView(self, slug, families, mode == 'mini')
            scroller = QtWidgets.QScrollArea()
            scroller.setWidgetResizable(True)
            scroller.setWidget(view)
            column.addWidget(scroller, 1)
            self.columns.append({'slug': slug, 'frame': frame, 'view': view, 'title':title, 'count': count, 'total': len(families)})
            self.column_layout.addWidget(frame)
            self.build_index += 1
            self.filter_items()
            self.progress.emit('[Matrix 2/3 Columns] Building ' + mode + ' tactic columns', self.build_index, len(self.queue))
            return
        tree = TechniqueTree(self,slug)
        tree.setExpandsOnDoubleClick(False)
        tree.setHeaderHidden(True)
        tree.setColumnCount(1)
        tree.setIndentation(14)
        tree.setWordWrap(True)
        tree.setUniformRowHeights(False)
        tree.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        tree.setItemDelegate(MatrixDelegate(tree))
        tree.setStyleSheet("QTreeWidget {background:#222526;border:none;} "
                           "QTreeWidget::item {border:1px solid #41484d;color:#6caedf;padding:3px 1px;} "
                           "QTreeWidget::item:selected {background:#094771;color:#ffffff;}")
        self.syncing = True
        for family in families:
            root = self.make_item(family['key'], slug, family['selectable'], len(family['children']))
            tree.addTopLevelItem(root)
            for child in family['children']:
                root.addChild(self.make_item(child, slug, True))
            if (root.data(0, MATRIX_STYLE) or {}).get("showSubtechniques"):
                root.setExpanded(True)
        self.syncing = False
        tree.itemChanged.connect(self.item_changed)
        tree.itemExpanded.connect(lambda item:self.manual_expansion(item.data(0,MATRIX_ID),slug,True))
        tree.itemCollapsed.connect(lambda item:self.manual_expansion(item.data(0,MATRIX_ID),slug,False))
        tree.itemActivated.connect(lambda item, column, tactic=slug: self.detail_requested.emit(item.data(0, MATRIX_ID), tactic))
        tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(lambda position, view=tree: self.open_cell_menu(view, position))
        column.addWidget(tree, 1)
        self.columns.append({"slug": slug, "frame": frame, "tree": tree, 'title':title, "count": count, "total": len(families)})
        self.column_layout.addWidget(frame)
        self.build_index += 1
        self.filter_items()
        self.progress.emit("[Matrix 2/3 Columns] Building expandable tactic columns", self.build_index, len(self.queue))

    def item_changed(self, item, _column):
        if self.syncing or not item.flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable:
            return
        self.request_selection(item.data(0, MATRIX_ID), item.data(0, MATRIX_SLUG), item.checkState(0) == QtCore.Qt.CheckState.Checked)

    def request_selection(self, key, slug, checked):
        self.selection_requested.emit(key, checked)
        self.scoped_selection_requested.emit(key, slug, checked)

    @staticmethod
    def selection_modifiers(modifiers):
        return bool(modifiers & (QtCore.Qt.KeyboardModifier.ControlModifier | QtCore.Qt.KeyboardModifier.MetaModifier |
                                 QtCore.Qt.KeyboardModifier.ShiftModifier))

    def request_mouse_selection(self, key, slug, modifiers):
        if not self.building:
            action = ('remove' if self.cell_selected(key,slug) else 'add') if self.selection_modifiers(modifiers) else 'replace'
            self.mouse_selection_requested.emit(key,slug,action)

    def manual_expansion(self, key, slug, expanded):
        if self.building or self.syncing or self.expansion_syncing or self.presentation_syncing or not self.catalog:
            return
        # Ignore native expansion signals for leaves.
        if not any(parent==key and slug in tactic_phases(self.catalog.records[child],self.catalog.domain)
                   for child,parent in self.catalog.parents.items()):
            return
        observed = {}
        if not self.search.text().strip():
            opened = self.expansion_snapshot()
            for column in self.columns:
                if 'view' in column:
                    roots = [family['root'].key for family in column['view'].families if family['children']]
                else:
                    tree = column['tree']
                    roots = [tree.topLevelItem(i).data(0,MATRIX_ID) for i in range(tree.topLevelItemCount()) if tree.topLevelItem(i).childCount()]
                observed.update({(root,column['slug']):(root,column['slug']) in opened for root in roots})
        self.family_expansion_requested.emit(key,slug,expanded,observed)

    def cell_selected(self, key, slug):
        return is_selected(self.selected, self.selection_scopes, key, slug)

    def update_selection(self, selected, scopes=None):
        self.selected = set(selected)
        if scopes is not None:
            self.selection_scopes = {key:list(value) for key, value in scopes.items()}
        for column in self.columns:
            if 'view' in column:
                column['view'].refresh()
        self.syncing = True
        for key, items in self.items_by_id.items():
            for item in items:
                item.setCheckState(0, QtCore.Qt.CheckState.Checked if self.cell_selected(key, item.data(0, MATRIX_SLUG)) else QtCore.Qt.CheckState.Unchecked)
        self.syncing = False
        if self.catalog:
            scope = ', '.join(self.selected_platforms) if self.selected_platforms is not None else self.platform.currentText()
            source = f' · Custom {self.catalog.dataset_id[:8]}' if self.catalog.dataset_id else ''
            self.summary.setText(f"{domain_label(self.catalog.domain, self.catalog)} v{self.catalog.version}{source} · {scope or 'No platforms'} · {len(self.selected)} selected TTPs")
        editable = bool(self.catalog) and supports_navigator(self.catalog) and bool(self.selected)
        self.color_button.setEnabled(editable)
        self.clear_color_button.setEnabled(editable)
        self.score_button.setEnabled(editable)
        self.batch_edit_button.setEnabled(editable and not self.building)
        self.state_button.setEnabled(editable and not self.building)
        self.bulk_select_button.setEnabled(bool(self.catalog) and not self.building)

    def update_layers(self, documents, current):
        identity = current.document_id if current else None
        if identity != self.expansion_document_id:
            self.clear_source_preview()
            self.source_picker.hidePopup()
            self.source_completer.popup().hide()
            self.expansion_document_id = identity
            self.restore_expansion = True
        if current:
            self.selection_scopes = {key:list(value) for key, value in current.selection_scopes.items()}
            self.search_fields = list(current.search_fields)
        self.layer_selector.blockSignals(True)
        self.layer_selector.clear()
        for document in documents:
            source = ' · Custom' if document.catalog.dataset_id else ''
            self.layer_selector.addItem(f"{document.name} · {domain_label(document.catalog.domain, document.catalog)} v{document.catalog.version}{source}", document.document_id)
        self.layer_selector.setCurrentIndex(next((index for index, document in enumerate(documents) if document is current), -1))
        self.layer_selector.blockSignals(False)
        supported = bool(current) and supports_navigator(current.catalog)
        self.new_layer_button.setEnabled(supported)
        self.duplicate_layer_button.setEnabled(supported)
        self.layer_settings_button.setEnabled(supported)
        self.show_all_layers.setEnabled(supported)

    def set_layer(self, layer, catalog=None):
        previous = self.score_signature()
        self.appearance = LayerAppearance(layer, catalog or self.catalog)
        self.load_presentation(layer)
        if self.catalog and self.sorting.currentIndex() >= 2 and previous != self.score_signature():
            self.rebuild()
        self.overlay_info.hide()
        self.apply_appearance()

    def set_overlay(self, layers, active_layer, total, scope, target, catalog=None):
        previous = self.score_signature()
        self.appearance = OverlayAppearance(layers, active_layer, catalog or self.catalog)
        self.load_presentation(active_layer)
        if self.catalog and self.sorting.currentIndex() >= 2 and previous != self.score_signature():
            self.rebuild()
        excluded = total - len(layers)
        text = f"All layers: {len(layers)}/{total} matching {scope} · Editing: {target}. Overlaps use equal RGB mixing."
        if excluded:
            text += f" {excluded} other-domain/version layer(s) excluded."
        if self.appearance.legend_truncated:
            text += " Legend shortened; hover a technique for its source layers."
        self.overlay_info.setText(text)
        self.overlay_info.show()
        self.apply_appearance()

    def apply_item_appearance(self, item):
        key, slug = item.data(0, MATRIX_ID), item.data(0, MATRIX_SLUG)
        appearance = self.appearance.cell(external_id(self.catalog.records[key]), slug)
        record=self.catalog.records[key]
        text=display_label(external_id(record),record['name'],self.display_layer())
        children=[item.child(i).data(0,MATRIX_ID) for i in range(item.childCount())]
        count=item.data(0,MATRIX_CHILDREN) or item.childCount()
        item.setText(0,self.family_label(key,slug,children,item.isExpanded(),count))
        tooltip = item.data(0, MATRIX_TOOLTIP)
        if children:
            annotated = sum(bool(self.appearance.cell(external_id(self.catalog.records[child]),slug).get('annotated')) for child in children)
            tooltip += f'\n{annotated} annotated / {len(children)} sub-techniques in this platform/tactic'
        tooltip += '\nIncluded in this tactic: ' + str(self.cell_selected(key, slug))
        if appearance["score"] is not None:
            tooltip += f"\nScore: {appearance['score']}"
        if appearance.get('aggregateScore') is not None:
            tooltip += f"\nAggregate score: {appearance['aggregateScore']:g}"
        if appearance["comment"]:
            tooltip += f"\nComment: {appearance['comment']}"
        for abstract,content in appearance.get('sourceNotes',[]):
            tooltip+='\nSource STIX Note'+(': '+abstract if abstract else '')+'\n'+content
        for source in appearance.get('annotationSources',[]):
            tooltip+='\nOverlay annotation: '+source['name']+'\n'+source['text']
        for entry in appearance.get('metadata', []):
            if 'name' in entry and entry['name'] != 'TTP Selection Studio selected':
                tooltip += f"\n{entry['name']}: {entry['value']}"
        for entry in appearance.get('links', []):
            if 'label' in entry:
                tooltip += f"\n{entry['label']}: {entry['url']}"
        if not appearance.get('activeEnabled', appearance['enabled']):
            tooltip += "\nDisabled in the active layer; export inclusion is independent"
        elif not appearance['enabled']:
            tooltip += "\nDisabled in this layer"
        sources = appearance.get('sources', [])
        if sources:
            tooltip += f"\nOverlay: {len(sources)} layer(s) · displayed color {appearance['background']}"
            for source in sources:
                tooltip += f"\n{source['name']}: {source['color']}"
                if source['score'] is not None:
                    tooltip += f" · score {source['score']}"
                if source.get('aggregateScore') is not None:
                    tooltip += f" · aggregate {source['aggregateScore']:g}"
                if source['comment']:
                    tooltip += f" · {source['comment']}"
        item.setToolTip(0, tooltip)
        if not self.show_colors.isChecked():
            appearance["background"], appearance["foreground"] = '', '' if appearance['enabled'] else '#999999'
        item.setData(0, MATRIX_STYLE, appearance)
        item.setBackground(0, QtGui.QBrush(QtGui.QColor(appearance["background"])) if appearance["background"] else QtGui.QBrush())
        item.setForeground(0, QtGui.QBrush(QtGui.QColor(appearance["foreground"])) if appearance["foreground"] else QtGui.QBrush())

    def apply_appearance(self, *_):
        previous = self.syncing
        self.syncing = True
        for column in self.columns:
            if 'title' in column:
                self.apply_header(column['title'],column['slug'])
            if 'view' in column:
                column['view'].refresh()
                continue
            tree = column["tree"]
            for number in range(tree.topLevelItemCount()):
                root = tree.topLevelItem(number)
                self.apply_item_appearance(root)
                for child in range(root.childCount()):
                    self.apply_item_appearance(root.child(child))
            tree.viewport().update()
        self.syncing = previous
        pieces = []
        gradient = self.appearance.gradient
        swatch = lambda color: f"<span style='color:{display_color(color)}'>■</span>"
        if any('score' in row for row in self.appearance.rows.values()):
            pieces.append(f"Score {gradient['minValue']}: " + ' → '.join(swatch(color) for color in gradient['colors']) + f" : {gradient['maxValue']}")
        pieces.extend(swatch(entry['color']) + ' ' + html.escape(entry['label']) for entry in self.appearance.layer.get('legendItems', []))
        self.legend.setText(' &nbsp; | &nbsp; '.join(pieces))
        from navigator_preferences import display_preferences
        self.legend.setVisible(bool(pieces) and self.show_colors.isChecked() and display_preferences(self.display_layer())['legend_visible'])
        self.filter_items()

    def family_label(self, key, slug, children, expanded, total=None):
        record = self.catalog.records[key]
        text = display_label(external_id(record),record['name'],self.display_layer())
        count = len(children) if total is None else total
        annotated = sum(bool(self.appearance.cell(external_id(self.catalog.records[child]),slug).get('annotated')) for child in children)
        return text + (f' [{annotated} annotated]' if text and annotated and not expanded else '') + (f' ({count})' if text and count else '')

    def open_cell_menu(self, tree, position):
        item = tree.itemAt(position)
        if item is None or not supports_navigator(self.catalog) or not item.flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable:
            return
        key, slug = item.data(0, MATRIX_ID), item.data(0, MATRIX_SLUG)
        self.technique_menu(key, slug, tree, tree.viewport().mapToGlobal(position))

    def technique_menu(self, key, slug, widget, position):
        if not supports_navigator(self.catalog):
            return
        menu = QtWidgets.QMenu(widget)
        menu.addAction('View technique details', lambda: self.detail_requested.emit(key, slug))
        for text,action in [('Select this technique','add'),('Deselect this technique','remove'),
                            ('Select only this technique','replace')]:
            menu.addAction(text,lambda checked=False,action=action:self.mouse_selection_requested.emit(key,slug,action))
        menu.addAction('Invert this technique', lambda:self.mouse_selection_requested.emit(key,slug,'remove' if self.cell_selected(key,slug) else 'add'))
        menu.addAction('Select this tactic',lambda:self.bulk_selection_requested.emit('add','platform',slug))
        menu.addAction('Deselect this tactic',lambda:self.bulk_selection_requested.emit('remove','platform',slug))
        selections = menu.addMenu('Matrix selection')
        for text,action in [('Select all','add'),('Deselect all','remove'),('Invert selection','invert'),
                            ('Select annotated','annotated'),('Select unannotated','unannotated')]:
            selections.addAction(text,lambda checked=False,action=action:self.bulk_selection_requested.emit(action,'platform',''))
        for text,obj in [('Open technique reference',self.catalog.records[key]),('Open tactic reference',self.catalog.tactics.get(slug,{}))]:
            for ref in obj.get('external_references',[]):
                if ref.get('source_name') in ('mitre-attack','mitre-mobile-attack','mitre-ics-attack') and ref.get('url'):
                    try: url=web_url(ref['url'])
                    except ValueError: continue
                    menu.addAction(text,lambda checked=False,url=url:self.open_context_url(url))
                    break
        from context_templates import CONTEXT_KEY, resolve_context
        entries = self.display_layer().get(CONTEXT_KEY,[])
        if entries:
            custom = menu.addMenu('Custom actions')
            for entry in entries:
                try: url = resolve_context(entry,self.catalog,key,slug)
                except ValueError: continue
                action = custom.addAction(entry['label'])
                action.setEnabled(bool(url))
                action.setToolTip(url or 'Required parent/sub-technique or tactic data is unavailable.')
                if url: action.triggered.connect(lambda checked=False,url=url:self.open_context_url(url))
        menu.addSeparator()
        menu.addAction("Set technique color…", lambda: self.cell_color_requested.emit(key, slug))
        menu.addAction("Clear technique color", lambda: self.cell_clear_color_requested.emit(key, slug))
        menu.addAction("Edit technique annotation…", lambda: self.annotation_requested.emit(key, slug))
        menu.addSeparator()
        menu.addAction('Enable technique', lambda: self.cell_enabled_requested.emit(key, '', True))
        menu.addAction('Disable technique', lambda: self.cell_enabled_requested.emit(key, '', False))
        menu.addAction('Toggle technique states', lambda: self.cell_enabled_requested.emit(key, '', 'toggle'))
        menu.addAction('Enable in this tactic', lambda: self.cell_enabled_requested.emit(key, slug, True))
        menu.addAction('Disable in this tactic', lambda: self.cell_enabled_requested.emit(key, slug, False))
        for entry in self.appearance.cell(external_id(self.catalog.records[key]), slug).get('links', []):
            if entry.get('divider'):
                menu.addSeparator()
            elif 'url' in entry:
                try:
                    web_url(entry['url'])
                except ValueError:
                    continue
                menu.addAction('Open: ' + entry['label'], lambda checked=False, url=entry['url']:
                               QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)))
        self.cell_menu = menu
        menu.aboutToHide.connect(menu.deleteLater)
        menu.popup(position)

    def open_context_url(self,url):
        web_url(url)
        self.progress.emit('Input files: None; output files: None (opening a user-selected reference URL)',0,0)
        self.progress.emit('[Reference 1/2] Opening URL in the system browser',0,2)
        opened = QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
        self.progress.emit('[Reference 2/2] '+('Opened' if opened else 'Could not open the system browser'),2,2)

    def populate_sources(self, *_):
        """List active source objects from this layer's exact domain/version."""
        self.clear_source_preview()
        catalog = self.source_catalog
        kind = self.source_kind.currentText()
        self.source_entries = {}
        self.source_search_index = {}
        self.source_picker.blockSignals(True)
        self.source_picker.clear()
        fields = getattr(self,'source_search_fields',['name','id','description'])
        self.source_picker.lineEdit().setPlaceholderText(f"Search {kind.lower()} · {', '.join(fields)}…")
        if catalog is not None:
            self.progress.emit("[Source Picker 1/2] Input files: None; output files: None (verified catalog in memory)", 0, 2)
            choices = source_choices(catalog,kind,fields)
            for row in choices:
                self.source_entries[row['label']] = row['key']
                self.source_search_index[row['key']] = row['search'].casefold()
                self.source_picker.addItem(row['label'], row['key'])
                self.source_picker.setItemData(self.source_picker.count()-1, row['search'], SOURCE_SEARCH)
                self.source_picker.setItemData(self.source_picker.count()-1, row['label']+'\n'+row['description'], QtCore.Qt.ItemDataRole.ToolTipRole)
            self.progress.emit(f"[Source Picker 2/2] {kind}: {len(choices)} entries in {domain_label(catalog.domain, catalog)} v{catalog.version}", 2, 2)
        self.source_picker.setCurrentIndex(-1)
        self.source_picker.setEditText('')
        self.source_picker.setEnabled(bool(self.source_entries))
        self.source_picker.blockSignals(False)
        self.update_source_state()

    def choose_source_completion(self, text):
        index = self.source_picker.findText(text, QtCore.Qt.MatchFlag.MatchExactly)
        if index >= 0:
            self.source_picker.setCurrentIndex(index)
            self.source_picker.setEditText(text)

    def source_selection(self):
        # Editable combo currentData can still describe the previous item after
        # typing. Only an exact displayed entry can trigger a bulk selection.
        key = self.source_entries.get(self.source_picker.currentText())
        catalog = self.catalog
        if not key or catalog is None or catalog is not self.source_catalog:
            return None, set()
        return key, resolve_sources(catalog,{key})

    def update_source_state(self, *_):
        key, keys = self.source_selection()
        self.add_source_button.setEnabled(bool(key and keys) and not self.building)
        self.add_source_button.setText(f"Add techniques ({len(keys)})" if key else "Add techniques")
        self.remove_source_button.setEnabled(bool(key and keys) and not self.building)
        self.remove_source_button.setText(f"Remove techniques ({len(keys)})" if key else "Remove techniques")
        self.add_source_button.setToolTip("Adds exact direct/explicit-path techniques to the active layer; keeps existing selections."
                                         if keys else "Choose an entry with active technique relationships in this domain/version.")
        self.source_details_button.setEnabled(bool(key) and not self.building)
        results = self.source_result_keys()
        cells = source_cells(self.catalog,results) if self.catalog else set()
        target_count = len({key for key,slug in cells})
        self.source_results_summary.setText(f'Results: {len(results)} sources · {target_count} mapped TTPs · {len(cells)} tactic occurrences')
        self.source_results_summary.setToolTip('Union of the current source kind/query. Blank query means all entries. '
            'Counts are direct/explicit-path mappings before family/visibility preferences. Add/Remove applies immediately and preserves annotations.')
        for button in (self.add_source_results_button,self.remove_source_results_button):
            button.setEnabled(bool(cells) and not self.building)

    def source_result_keys(self):
        if not self.catalog or self.catalog is not self.source_catalog: return set()
        query = self.source_picker.currentText().strip().casefold()
        chosen = self.source_entries.get(self.source_picker.currentText())
        if chosen: return {chosen}
        return {key for key,text in self.source_search_index.items() if not query or query in text}

    def change_source_results(self,action):
        if not self.building and self.catalog:
            keys = self.source_result_keys()
            if keys: self.source_batch_requested.emit(self.catalog,keys,action)

    def view_source_details(self):
        key,_ = self.source_selection()
        if key and not self.building: self.source_detail_requested.emit(self.catalog.domain,key)

    def add_source(self, action='add'):
        action = 'add' if isinstance(action, bool) else action
        key, keys = self.source_selection()
        if key and keys and not self.building:
            if action == 'add':
                self.source_requested.emit(self.catalog.domain, key)
            self.source_operation_requested.emit(self.catalog.domain, key, action)

    def record_matches(self, key, query):
        return search_matches(self.catalog, key, query, self.search_fields)

    def preview_source_index(self,index,owner):
        key = index.data(QtCore.Qt.ItemDataRole.UserRole)
        return self.preview_source(self.source_catalog,key,owner)

    def preview_source(self,catalog,key,owner):
        if not catalog or catalog is not self.catalog or self.building or not self.isVisible():
            self.clear_source_preview()
            return False
        context = (id(catalog),key,owner)
        if context == self.source_preview_context: return True
        self.progress.emit('Input files: None; output files: None (temporary source preview in memory)',0,0)
        self.progress.emit('[Source Preview 1/2] Resolving exact mapped technique/tactic occurrences',0,2)
        try:
            cells = frozenset(source_cells(catalog,{key}) & self.scope_cells('platform'))
        except (ValueError,TypeError):
            self.clear_source_preview()
            self.progress.emit('[Source Preview 2/2] No supported source in the active dataset',2,2)
            return False
        self.source_preview_context = context
        self.source_preview_cells = cells
        self.repaint_source_preview()
        self.progress.emit(f'[Source Preview 2/2] {len(cells)} platform-mapped occurrences; preview only, document unchanged',2,2)
        return True

    def clear_source_preview(self,owner=None):
        if owner is not None and self.source_preview_context and self.source_preview_context[2] is not owner: return
        if not self.source_preview_context and not self.source_preview_cells: return
        self.source_preview_context = None
        self.source_preview_cells = frozenset()
        self.repaint_source_preview()
        self.progress.emit('Input files: None; output files: None (restoring source preview)',0,0)
        self.progress.emit('[Source Preview] Restored; selection, annotation colors and expansion unchanged',1,1)

    def repaint_source_preview(self):
        for column in self.columns:
            if 'tree' in column: column['tree'].viewport().update()
            else:
                for family in column['view'].families:
                    for cell in [family['root'],*family['children']]: cell.update()

    def source_preview_kind(self,key,slug,children=(),expanded=True):
        if (key,slug) in self.source_preview_cells: return 'direct'
        if not expanded and any((child,slug) in self.source_preview_cells for child in children): return 'family'
        return ''

    def hideEvent(self,event):
        self.clear_source_preview()
        super().hideEvent(event)

    def matches(self, item, query):
        record = self.catalog.records[item.data(0, MATRIX_ID)]
        return self.record_matches(record['id'], query)

    def filter_items(self, *_):
        previous, self.expansion_syncing = self.expansion_syncing, True
        try: self._filter_items()
        finally: self.expansion_syncing = previous

    def _filter_items(self):
        if self.catalog is None:
            return
        self.clear_source_preview()
        self.apply_expansion_mode()
        query = self.search.text().strip().casefold()
        shown = 0
        for column in self.columns:
            if 'view' in column:
                count = column['view'].filter(query)
                column['count'].setText(f'{count} techniques')
                column['frame'].setVisible(count > 0)
                shown += count
                continue
            tree, count = column['tree'], 0
            for number in range(tree.topLevelItemCount()):
                root = tree.topLevelItem(number)
                root_matches = self.matches(root, query)
                child_matches = False
                for child_number in range(root.childCount()):
                    child = root.child(child_number)
                    match = self.matches(child, query)
                    child_matches |= match
                    visible_child = (root_matches or match) and not (child.data(0, MATRIX_STYLE) or {}).get('hidden')
                    child.setHidden(not visible_child)
                child_matches = any(not root.child(child).isHidden() for child in range(root.childCount()))
                visible = (root_matches and not (root.data(0, MATRIX_STYLE) or {}).get('hidden')) or child_matches
                root.setHidden(not visible)
                count += int(visible)
                if query and child_matches:
                    root.setExpanded(True)
                root.setText(0,self.family_label(root.data(0,MATRIX_ID),column['slug'],
                    [root.child(i).data(0,MATRIX_ID) for i in range(root.childCount())],root.isExpanded()))
            column['count'].setText(f"{count}/{column['total']} techniques" if query else f"{count} techniques")
            column['frame'].setVisible(count > 0)
            shown += count
        self.empty.setVisible(not shown and not self.building)

    def expansion_snapshot(self):
        """Capture actual per-tactic UI expansion without changing stored layer annotations."""
        expanded=set()
        for column in self.columns:
            slug=column['slug']
            if 'view' in column:
                for family in column['view'].families:
                    if family['toggle'].isChecked():
                        expanded.add((family['root'].key,slug))
            else:
                tree=column['tree']
                for index in range(tree.topLevelItemCount()):
                    item=tree.topLevelItem(index)
                    if item.isExpanded():
                        expanded.add((item.data(0,MATRIX_ID),slug))
        return expanded

    def display_layer(self):
        return getattr(self.appearance,'active',self.appearance).layer

    def apply_header(self,title,slug):
        obj=self.catalog.tactics[slug]
        mini=self.view_layout.currentText()=='Mini'
        title.setText(display_label(external_id(obj),obj['name'],self.display_layer(),mini))
        background=header_color(self.display_layer(),mini)
        foreground=foreground_color(background) if background else '#6caedf'
        title.setStyleSheet('font-weight:600;font-size:13px;color:'+foreground+';background:'+
                           (background or '#000000' if mini else background or 'transparent')+';')
        title.setToolTip((external_id(obj)+'  '+obj['name']).strip())

    def request_display(self,fields):
        if not self.presentation_syncing and self.catalog:
            self.display_requested.emit(fields)

    def choose_tactic_color(self):
        color=QtWidgets.QColorDialog.getColor(QtGui.QColor(self.display_layer().get('tacticRowBackground','#dddddd')),self,'Tactic header color')
        if color.isValid():
            self.request_display({'tacticRowBackground':color.name(),'showTacticRowBackground':True})

    def expand_annotated(self):
        self.choose_expansion('annotated')

    def choose_expansion(self, mode):
        if not self.catalog or self.building: return
        self.progress.emit('Input files: None; output files: None (layer expansion policy in memory)',0,0)
        self.progress.emit('[Expansion 1/2] Resolving the saved expansion policy',0,2)
        self.expansion_mode = mode
        layout = self.display_layer().setdefault('layout',{})
        if mode is None: layout.pop('expandedSubtechniques',None)
        else: layout['expandedSubtechniques'] = mode
        self.apply_expansion_mode(force_legacy=mode is None)
        self.request_display({'expandedSubtechniques':mode})
        self.progress.emit('[Expansion 2/2] Policy applied; selection unchanged',2,2)

    def apply_expansion_mode(self, force_legacy=False):
        previous, self.expansion_syncing = self.expansion_syncing, True
        try: self._apply_expansion_mode()
        finally: self.expansion_syncing = previous

    def _apply_expansion_mode(self):
        if not self.catalog: return
        mini = self.view_layout.currentText() == 'Mini'
        for column in self.columns:
            slug=column['slug']
            if 'view' in column:
                for family in column['view'].families:
                    family['toggle'].setChecked(expanded_family(self.appearance,self.catalog,family['root'].key,slug,
                                                               [child.key for child in family['children']],mini))
            else:
                tree=column['tree']
                for index in range(tree.topLevelItemCount()):
                    root=tree.topLevelItem(index)
                    root.setExpanded(expanded_family(self.appearance,self.catalog,root.data(0,MATRIX_ID),slug,
                                                    [root.child(i).data(0,MATRIX_ID) for i in range(root.childCount())]))

    def set_expanded(self, expanded):
        self.choose_expansion('all' if expanded else 'none')

    def platform_scope(self):
        return [p for p in self.selected_platforms if p in self.catalog.groups] if self.selected_platforms is not None else (self.platform.currentText() or ALL_PLATFORMS)

    def score_signature(self):
        source = getattr(self.appearance, 'active', self.appearance)
        return ([(key, row.get('score'), row.get('enabled')) for key, row in source.rows.items()],
                {key:source.layer.get('layout',{}).get(key) for key in ('showAggregateScores','countUnscored','aggregateFunction')})

    def single_platform_changed(self, text):
        if self.presentation_syncing:
            return
        self.selected_platforms = None if text == ALL_PLATFORMS else [text]
        self.presentation_changed()

    def presentation_changed(self, *_):
        if self.presentation_syncing or not self.catalog:
            return
        self.presentation_requested.emit(self.view_layout.currentText().lower(), self.sorting.currentIndex(), self.selected_platforms)
        self.rebuild()

    def load_presentation(self, layer):
        mode, sorting, platforms = presentation(layer)
        platforms = None if platforms is None else list(platforms)
        old = (self.view_layout.currentText().lower(), self.sorting.currentIndex(), self.selected_platforms)
        self.presentation_syncing = True
        previous_expansion = self.expansion_mode
        self.expansion_mode = layer.get('layout',{}).get('expandedSubtechniques')
        if previous_expansion != self.expansion_mode or self.restore_expansion:
            self.apply_expansion_mode(force_legacy=True)
            self.restore_expansion = False
        self.expansion_mode_picker.setCurrentIndex(max(0,self.expansion_mode_picker.findData(self.expansion_mode)))
        show_id,show_name=labels(layer)
        self.show_names.setChecked(show_name)
        self.show_ids.setChecked(show_id)
        self.show_tactic_background.setChecked(layer.get('showTacticRowBackground',False))
        for control in (self.show_names,self.show_ids,self.show_tactic_background,self.tactic_color_button):
            control.setEnabled(mode!='mini')
        self.view_layout.setCurrentText(mode.title())
        self.sorting.setCurrentIndex(sorting)
        self.selected_platforms = platforms
        self.platform.blockSignals(True)
        self.platform.setCurrentText(platforms[0] if platforms and len(platforms) == 1 else ALL_PLATFORMS)
        self.platform.blockSignals(False)
        self.platforms_button.setText(f'Platforms ({len(platforms)})…' if platforms is not None else 'Multiple…')
        self.presentation_syncing = False
        if self.catalog and old != (mode, sorting, platforms):
            # Keep unknown imported platform filters in JSON; only supported platforms project.
            self.rebuild()

    def choose_platforms(self):
        if not self.catalog:
            return
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle('Platforms · match any selected platform')
        layout = QtWidgets.QVBoxLayout(dialog)
        listing = QtWidgets.QListWidget()
        listing.setMinimumSize(280, 260)
        chosen = self.selected_platforms if self.selected_platforms is not None else self.catalog.groups
        for platform in self.catalog.groups:
            item = QtWidgets.QListWidgetItem(platform, listing)
            item.setCheckState(QtCore.Qt.CheckState.Checked if platform in chosen else QtCore.Qt.CheckState.Unchecked)
        layout.addWidget(listing)
        row = QtWidgets.QHBoxLayout()
        for text, state in [('Select all', QtCore.Qt.CheckState.Checked), ('Clear', QtCore.Qt.CheckState.Unchecked)]:
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(lambda checked=False, value=state: [listing.item(i).setCheckState(value) for i in range(listing.count())])
            row.addWidget(button)
        layout.addLayout(row)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.selected_platforms = [listing.item(i).text() for i in range(listing.count()) if listing.item(i).checkState() == QtCore.Qt.CheckState.Checked]
            self.presentation_changed()

    def tactic_menu(self, label, slug, position):
        menu = QtWidgets.QMenu(label)
        for text, operation in [('Select all techniques in this tactic', 'add'),
                                ('Deselect this tactic', 'remove'), ('Invert this tactic', 'invert')]:
            menu.addAction(text, lambda checked=False, op=operation: self.bulk_selection_requested.emit(op, 'platform', slug))
        self.tactic_context_menu = menu
        menu.aboutToHide.connect(menu.deleteLater)
        menu.popup(label.mapToGlobal(position))

    def scope_keys(self, scope='platform', tactic=''):
        if not self.catalog or self.building:
            return set()
        if scope not in ('platform', 'search', 'visible'):
            raise ValueError('Unknown selection scope.')
        if scope == 'visible':
            keys = set()
            for column in self.columns:
                if (tactic and column['slug'] != tactic) or column['frame'].isHidden():
                    continue
                if 'view' in column:
                    for family in column['view'].families:
                        if family['frame'].isHidden():
                            continue
                        cells = [family['root']] + (family['children'] if family['toggle'].isChecked() else [])
                        keys.update(cell.key for cell in cells if cell.selectable and not cell.isHidden() and not cell.projection['hidden'])
                else:
                    tree = column['tree']
                    for index in range(tree.topLevelItemCount()):
                        root = tree.topLevelItem(index)
                        if root.isHidden():
                            continue
                        cells = [root] + ([root.child(i) for i in range(root.childCount())] if root.isExpanded() else [])
                        keys.update(item.data(0, MATRIX_ID) for item in cells if not item.isHidden()
                                    and item.flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable
                                    and not (item.data(0, MATRIX_STYLE) or {}).get('hidden'))
            return keys
        query = self.search.text().strip().casefold()
        result = set()
        for slug, families in matrix_columns(self.catalog, self.platform_scope()):
            if tactic and tactic != slug:
                continue
            for family in families:
                for key in ([family['key']] if family['selectable'] else []) + family['children']:
                    record = self.catalog.records[key]
                    if scope == 'search' and (not self.record_matches(key, query)
                                              or self.appearance.cell(external_id(record), slug)['hidden']):
                        continue
                    result.add(key)
        return result

    def scope_cells(self, scope='platform', tactic=''):
        return {(key, slug) for slug in self.catalog.tactic_order if not tactic or tactic == slug
                for key in self.scope_keys(scope, slug)} if self.catalog else set()
