"""Side and Mini matrix widgets, sharing the existing technique actions. Flow: README.md."""
from PySide6 import QtCore, QtWidgets
from attack_catalog import external_id


class TechniqueCell(QtWidgets.QPushButton):
    def __init__(self, owner, key, slug, selectable, mini=False):
        super().__init__()
        self.owner, self.key, self.slug, self.mini = owner, key, slug, mini
        self.selectable = selectable
        obj = owner.catalog.records[key]
        self.label = obj['name']
        self.attack_id = external_id(obj)
        self.setCheckable(selectable)
        self.setChecked(key in owner.selected)
        self.clicked.connect(lambda checked: owner.selection_requested.emit(key, checked) if selectable else None)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda pos: owner.technique_menu(key, slug, self, self.mapToGlobal(pos)) if selectable else None)
        if mini:
            self.setFixedSize(30, 30)
        else:
            self.setMinimumWidth(142)
            self.setMaximumWidth(178)
        self.refresh()

    def mouseDoubleClickEvent(self, event):
        self.owner.detail_requested.emit(self.key, self.slug)
        event.accept()

    def refresh(self):
        style = self.owner.appearance.cell(self.attack_id, self.slug)
        self.projection = style
        notes = [self.attack_id + '  ' + self.label]
        notes.append('Active layer state: ' + ('Enabled' if style.get('activeEnabled', style['enabled']) else 'Disabled'))
        notes.append('Included in export: ' + str(self.key in self.owner.selected))
        for label, field in [('Score', 'score'), ('Aggregate score', 'aggregateScore'), ('Comment', 'comment')]:
            if style.get(field) is not None and style.get(field) != '':
                notes.append(f'{label}: {style[field]}')
        for entry in style.get('metadata', []):
            if 'name' in entry and entry['name'] != 'TTP Selection Studio selected':
                notes.append(f"{entry['name']}: {entry['value']}")
        for entry in style.get('links', []):
            if 'label' in entry:
                notes.append(f"{entry['label']}: {entry['url']}")
        for entry in style.get('sources', []):
            notes.append(f"{entry['name']}: {entry['color']} · score {entry.get('score')}")
        if not self.selectable:
            notes.append('Grouping only; parent is not mapped to this scope')
        self.setToolTip('\n'.join(notes))
        bg = style['background'] if self.owner.show_colors.isChecked() else ''
        fg = style['foreground'] if self.owner.show_colors.isChecked() else '' if style['enabled'] else '#999999'
        self.setStyleSheet('QPushButton {background:' + (bg or '#222526') + ';color:' + (fg or '#6caedf') +
                           ';border:1px solid #555;padding:3px;} QPushButton:checked {border:3px solid #3794ff;}')
        mark = 'i' if style.get('comment') or style.get('metadata') or style.get('links') else ''
        if self.mini:
            self.setText(('+' if self.isChecked() else mark) if style['enabled'] else 'x')
        else:
            # QPushButton has no word wrapping; explicit line breaks keep names visible.
            import textwrap
            prefix = '[x] ' if self.isChecked() else '[ ] ' if self.selectable else ''
            lines = textwrap.wrap(prefix + self.label, 20)
            self.setText('\n'.join(lines))
            self.setFixedHeight(len(lines) * (self.fontMetrics().height() + 3) + 10)


class FamilyView(QtWidgets.QWidget):
    def __init__(self, owner, slug, families, mini=False):
        super().__init__()
        self.owner, self.slug = owner, slug
        self.families = []
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
        for family in families:
            frame = QtWidgets.QFrame()
            frame.setStyleSheet('QFrame {border:1px solid #41484d;}')
            row = QtWidgets.QHBoxLayout(frame)
            row.setContentsMargins(3, 3, 3, 3)
            row.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
            root = TechniqueCell(owner, family['key'], slug, family['selectable'], mini)
            row.addWidget(root, 0, QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
            child_panel = QtWidgets.QWidget()
            children_layout = QtWidgets.QGridLayout(child_panel) if mini else QtWidgets.QVBoxLayout(child_panel)
            children_layout.setContentsMargins(0, 0, 0, 0)
            children_layout.setSpacing(2)
            children_layout.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
            children = []
            for number, key in enumerate(family['children']):
                cell = TechniqueCell(owner, key, slug, True, mini)
                children.append(cell)
                if mini:
                    children_layout.addWidget(cell, number // 4, number % 4)
                else:
                    children_layout.addWidget(cell)
            row.addWidget(child_panel, 0, QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
            toggle = QtWidgets.QToolButton()
            toggle.setCheckable(True)
            toggle.setText('▸')
            toggle.setToolTip('Expand/collapse sub-techniques')
            toggle.toggled.connect(lambda checked, panel=child_panel, button=toggle:
                                   (panel.setVisible(checked), button.setText('▾' if checked else '▸')))
            toggle.setVisible(bool(children))
            row.insertWidget(0, toggle, 0, QtCore.Qt.AlignmentFlag.AlignTop)
            row.addStretch()
            layout.addWidget(frame)
            self.families.append({'frame': frame, 'root': root, 'children': children, 'panel': child_panel, 'toggle': toggle})
            toggle.setChecked(mini or root.projection.get('showSubtechniques', False))
            child_panel.setVisible(toggle.isChecked() and bool(children))
        layout.addStretch()

    def refresh(self):
        for family in self.families:
            for cell in [family['root'], *family['children']]:
                cell.blockSignals(True)
                cell.setChecked(cell.key in self.owner.selected)
                cell.blockSignals(False)
                cell.refresh()

    def filter(self, query):
        count = 0
        for family in self.families:
            root = family['root']
            match = query in (root.attack_id + ' ' + root.label).casefold()
            child_visible = False
            for child in family['children']:
                visible = (match or query in (child.attack_id + ' ' + child.label).casefold()) and not child.projection['hidden']
                child.setVisible(visible)
                child_visible |= visible
            visible = (match and not root.projection['hidden']) or child_visible
            family['frame'].setVisible(visible)
            count += int(visible)
            if query and child_visible:
                family['toggle'].setChecked(True)
        return count

    def set_expanded(self, expanded):
        for family in self.families:
            family['toggle'].setChecked(expanded)
