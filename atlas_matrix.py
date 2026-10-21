"""ATLAS matrix and tactic tree, backed by the shared catalog. Flow: README.md."""
from PySide6 import QtCore, QtWidgets

from attack_catalog import external_id
from attack_matrix import matrix_columns, ALL_PLATFORMS
from ttp_selection import is_selected

KEY = int(QtCore.Qt.ItemDataRole.UserRole) + 40
TACTIC = KEY + 1


class AtlasTechniqueDelegate(QtWidgets.QStyledItemDelegate):
    """Wrap ATLAS labels without depending on ATT&CK source-preview widgets."""
    def sizeHint(self, option, index):
        depth = 1 if index.parent().isValid() else 0
        width = max(70, self.parent().viewport().width() - 52 - depth * 16)
        rect = option.fontMetrics.boundingRect(QtCore.QRect(0, 0, width, 1000),
            QtCore.Qt.TextFlag.TextWordWrap, str(index.data() or ''))
        return QtCore.QSize(width, max(34, rect.height() + 12))

    def paint(self, painter, option, index):
        wrapped = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(wrapped, index)
        wrapped.features |= QtWidgets.QStyleOptionViewItem.ViewItemFeature.WrapText
        wrapped.textElideMode = QtCore.Qt.TextElideMode.ElideNone
        wrapped.displayAlignment = QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        super().paint(painter, wrapped, index)


def populate(tree, catalog, slug, rows, query=''):
    """Keep matching children under their real parent; no inferred relationships."""
    def item(key, selectable=True):
        obj = catalog.records[key]
        node = QtWidgets.QTreeWidgetItem([f'{external_id(obj)}  {obj["name"]}'])
        node.setData(0, KEY, key)
        node.setData(0, TACTIC, slug)
        node.setToolTip(0, obj.get('description', ''))
        if selectable:
            node.setFlags(node.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            node.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
        else:
            node.setFlags(node.flags() & ~QtCore.Qt.ItemFlag.ItemIsUserCheckable)
        return node
    nodes = []
    query = query.casefold().strip()
    def matches(key):
        obj = catalog.records[key]
        return not query or query in (external_id(obj) + ' ' + obj['name']).casefold()
    for family in rows:
        parent_matches = matches(family['key'])
        children = [key for key in family['children'] if parent_matches or matches(key)]
        if not parent_matches and not children:
            continue
        parent = item(family['key'], family['selectable'])
        for key in children:
            parent.addChild(item(key))
        parent.setExpanded(bool(query))
        nodes.append(parent)
    tree.addTopLevelItems(nodes)


def sync_checks(tree, document):
    blocked = tree.blockSignals(True)
    iterator = QtWidgets.QTreeWidgetItemIterator(tree)
    while iterator.value():
        item = iterator.value()
        key, slug = item.data(0, KEY), item.data(0, TACTIC)
        if key and item.flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable:
            chosen = document and is_selected(document.selected, document.selection_scopes, key, slug)
            item.setCheckState(0, QtCore.Qt.CheckState.Checked if chosen else QtCore.Qt.CheckState.Unchecked)
        iterator += 1
    tree.blockSignals(blocked)


class AtlasMatrix(QtWidgets.QWidget):
    selection_requested = QtCore.Signal(str, str, bool)
    detail_requested = QtCore.Signal(str)
    progress = QtCore.Signal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.catalog = None
        self.document = None
        self.columns = []
        layout = QtWidgets.QVBoxLayout(self)
        bar = QtWidgets.QHBoxLayout()
        self.platform = QtWidgets.QComboBox()
        self.platform.setAccessibleName('ATLAS platform filter')
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText('Search ATLAS technique name or ID…')
        self.search.setClearButtonEnabled(True)
        bar.addWidget(self.platform)
        bar.addWidget(self.search, 1)
        layout.addLayout(bar)
        self.summary = QtWidgets.QLabel('ATLAS')
        layout.addWidget(self.summary)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        self.content = QtWidgets.QWidget()
        self.row = QtWidgets.QHBoxLayout(self.content)
        self.row.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.content)
        layout.addWidget(scroll, 1)
        self.platform.currentIndexChanged.connect(self.rebuild)
        self.search.textChanged.connect(self.rebuild)

    def set_document(self, catalog, document):
        changed = self.catalog is not catalog
        self.catalog, self.document = catalog, document
        if changed:
            self.platform.blockSignals(True)
            self.platform.clear()
            self.platform.addItems([ALL_PLATFORMS, *catalog.groups])
            self.platform.blockSignals(False)
            self.rebuild()
        else:
            self.update_selection(document)

    def rebuild(self, *_):
        if not self.catalog:
            return
        self.progress.emit('Input files: None; output files: None (verified ATLAS catalog in memory)', 0, 0)
        columns = matrix_columns(self.catalog, self.platform.currentText() or ALL_PLATFORMS)
        self.progress.emit('[ATLAS matrix 1/2] Building tactic columns', 0, len(columns))
        while self.row.count():
            entry = self.row.takeAt(0)
            if entry.widget():
                entry.widget().deleteLater()
        self.columns = []
        for index, (slug, rows) in enumerate(columns, 1):
            tree = QtWidgets.QTreeWidget()
            tree.setHeaderLabel(self.catalog.tactics[slug]['name'])
            tree.setMinimumWidth(255)
            tree.setIndentation(16)
            tree.setWordWrap(True)
            tree.setUniformRowHeights(False)
            tree.setItemDelegate(AtlasTechniqueDelegate(tree))
            tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
            tree.setAccessibleName('ATLAS tactic: ' + self.catalog.tactics[slug]['name'])
            populate(tree, self.catalog, slug, rows, self.search.text())
            if tree.topLevelItemCount() == 0:
                tree.deleteLater()
                continue
            tree.itemChanged.connect(self.changed)
            tree.itemDoubleClicked.connect(lambda item, column: self.detail_requested.emit(item.data(0, KEY)))
            self.columns.append(tree)
            self.row.addWidget(tree)
            self.progress.emit('[ATLAS matrix 1/2] Building tactic columns', index, len(columns))
        self.update_selection(self.document)
        self.progress.emit('[ATLAS matrix 2/2] Ready; double-click a technique for details', 2, 2)

    def changed(self, item, column):
        key, slug = item.data(0, KEY), item.data(0, TACTIC)
        if key:
            self.selection_requested.emit(key, slug, item.checkState(0) == QtCore.Qt.CheckState.Checked)

    def update_selection(self, document):
        self.document = document
        for tree in self.columns:
            sync_checks(tree, document)
        if self.catalog:
            self.summary.setText(f'ATLAS {self.catalog.version} · {self.platform.currentText()} · '
                                 f'{len(document.selected) if document else 0} selected TTPs')
