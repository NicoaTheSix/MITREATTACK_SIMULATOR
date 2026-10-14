"""Platform-filtered ATT&CK matrix with expandable families. Workflow: README.md."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from attack_catalog import external_id, DOMAIN_LABELS

MATRIX_ID = int(QtCore.Qt.ItemDataRole.UserRole) + 1
MATRIX_SLUG = MATRIX_ID + 1
ALL_PLATFORMS = "All Platforms"


def matrix_columns(catalog, platform=ALL_PLATFORMS):
    """Project the catalog's exact mappings, retaining structural parents without selecting them."""
    if platform != ALL_PLATFORMS and platform not in catalog.groups:
        raise ValueError("Platform is absent from this ATT&CK version")
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
        super().paint(painter, wrapped, index)


class AttackMatrix(QtWidgets.QWidget):
    selection_requested = QtCore.Signal(str, bool)
    detail_requested = QtCore.Signal(str, str)
    progress = QtCore.Signal(str, int, int)
    ready = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.catalog = None
        self.selected = set()
        self.columns = []
        self.items_by_id = {}
        self.queue = []
        self.build_index = 0
        self.building = False
        self.syncing = False
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 8)
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.addWidget(QtWidgets.QLabel("Platform"))
        self.platform = QtWidgets.QComboBox()
        self.platform.setMinimumWidth(140)
        self.platform.currentTextChanged.connect(self.rebuild)
        toolbar.addWidget(self.platform)
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
        self.summary = QtWidgets.QLabel("Open the matrix after the local catalog loads.")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
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
        hint = QtWidgets.QLabel("Expand a technique with its arrow · Check a box to select · Double-click a name for details")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.build_column)

    def invalidate(self):
        self.timer.stop()
        self.catalog = None
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
        self.selected = set(selected)
        self.platform.blockSignals(True)
        self.platform.clear()
        self.platform.addItems([ALL_PLATFORMS, *catalog.groups])
        self.platform.setCurrentText(previous_platform if previous_platform in catalog.groups else ALL_PLATFORMS)
        self.platform.blockSignals(False)
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
        self.queue = matrix_columns(catalog, self.platform.currentText() or ALL_PLATFORMS)
        self.build_index = 0
        self.building = True
        self.progress.emit("[Matrix 1/3 Scope] Platform/tactic families resolved", 1, 1)
        self.timer.start(0)

    def make_item(self, key, slug, selectable, children=0):
        record = self.catalog.records[key]
        name = record['name'] + (f" ({children})" if children else "")
        item = QtWidgets.QTreeWidgetItem([name])
        item.setData(0, MATRIX_ID, key)
        item.setData(0, MATRIX_SLUG, slug)
        item.setToolTip(0, f"{external_id(record)}  {record['name']}"
                          + (f"\n{children} sub-techniques in this platform/tactic" if children else "")
                          + ("" if selectable else "\nGrouping only; parent is not mapped to this platform/tactic"))
        flags = QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
        if selectable:
            flags |= QtCore.Qt.ItemFlag.ItemIsUserCheckable
            item.setCheckState(0, QtCore.Qt.CheckState.Checked if key in self.selected else QtCore.Qt.CheckState.Unchecked)
            self.items_by_id.setdefault(key, []).append(item)
        item.setFlags(flags)
        return item

    def build_column(self):
        if self.catalog is None:
            self.timer.stop()
            return
        if self.build_index >= len(self.queue):
            self.timer.stop()
            self.building = False
            self.filter_items()
            self.update_selection(self.selected)
            self.progress.emit("[Matrix 3/3 Ready] Matrix columns complete", 1, 1)
            self.ready.emit()
            return
        slug, families = self.queue[self.build_index]
        frame = QtWidgets.QWidget()
        frame.setFixedWidth(190)
        column = QtWidgets.QVBoxLayout(frame)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(5)
        title = QtWidgets.QLabel(self.catalog.tactics[slug]['name'])
        title.setWordWrap(True)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(44)
        title.setStyleSheet("color:#6caedf;font-weight:600;font-size:13px;")
        title.setToolTip(external_id(self.catalog.tactics[slug]) or "Historical phase heading")
        column.addWidget(title)
        count = QtWidgets.QLabel(f"{len(families)} techniques")
        count.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        count.setStyleSheet("font-size:11px;color:#bbbbbb;")
        column.addWidget(count)
        tree = QtWidgets.QTreeWidget()
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
        self.syncing = False
        tree.itemChanged.connect(self.item_changed)
        tree.itemActivated.connect(lambda item, column, tactic=slug: self.detail_requested.emit(item.data(0, MATRIX_ID), tactic))
        column.addWidget(tree, 1)
        self.columns.append({"slug": slug, "frame": frame, "tree": tree, "count": count, "total": len(families)})
        self.column_layout.addWidget(frame)
        self.build_index += 1
        self.filter_items()
        self.progress.emit("[Matrix 2/3 Columns] Building expandable tactic columns", self.build_index, len(self.queue))

    def item_changed(self, item, _column):
        if self.syncing or not item.flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable:
            return
        self.selection_requested.emit(item.data(0, MATRIX_ID), item.checkState(0) == QtCore.Qt.CheckState.Checked)

    def update_selection(self, selected):
        self.selected = set(selected)
        self.syncing = True
        for key, items in self.items_by_id.items():
            state = QtCore.Qt.CheckState.Checked if key in self.selected else QtCore.Qt.CheckState.Unchecked
            for item in items:
                item.setCheckState(0, state)
        self.syncing = False
        if self.catalog:
            self.summary.setText(f"{DOMAIN_LABELS[self.catalog.domain]} v{self.catalog.version} · {self.platform.currentText()} · {len(self.selected)} selected TTPs")

    def matches(self, item, query):
        record = self.catalog.records[item.data(0, MATRIX_ID)]
        return query in (external_id(record) + ' ' + record['name']).casefold()

    def filter_items(self, *_):
        if self.catalog is None:
            return
        query = self.search.text().strip().casefold()
        shown = 0
        for column in self.columns:
            tree, count = column['tree'], 0
            for number in range(tree.topLevelItemCount()):
                root = tree.topLevelItem(number)
                root_matches = self.matches(root, query)
                child_matches = False
                for child_number in range(root.childCount()):
                    child = root.child(child_number)
                    match = self.matches(child, query)
                    child_matches |= match
                    child.setHidden(not (root_matches or match))
                visible = root_matches or child_matches
                root.setHidden(not visible)
                count += int(visible)
                if query and child_matches:
                    root.setExpanded(True)
            column['count'].setText(f"{count}/{column['total']} techniques" if query else f"{count} techniques")
            column['frame'].setVisible(count > 0)
            shown += count
        self.empty.setVisible(not shown and not self.building)

    def set_expanded(self, expanded):
        for column in self.columns:
            if expanded:
                column['tree'].expandAll()
            else:
                column['tree'].collapseAll()
