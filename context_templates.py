"""Native Navigator custom URL actions, expanded only on user click. Flow: README.md."""
import re
from urllib.parse import quote
from attack_catalog import external_id
from navigator_fields import web_url

CONTEXT_KEY = 'x_ttp_studio_context_menu'
TOKENS = {prefix + suffix for prefix in ('technique_', 'parent_technique_', 'subtechnique_', 'tactic_')
          for suffix in ('attackID', 'stixID', 'name')} | {'subtechnique_attackID_suffix'}
PLACEHOLDER = re.compile(r'\{\{([a-zA-Z_]+)\}\}')


def validate_template(value):
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise ValueError('Context URL templates need 1–4096 characters.')
    tokens = PLACEHOLDER.findall(value)
    if set(tokens) - TOKENS or any(c in PLACEHOLDER.sub('',value) for c in '{}'):
        raise ValueError('Unknown or malformed context URL substitution.')
    # Substitutions belong in path/query, never in the network authority.
    from urllib.parse import urlsplit
    parsed = urlsplit(value)
    if '{' in parsed.netloc or '}' in parsed.netloc:
        raise ValueError('Context URL host must be fixed, without substitutions.')
    web_url(PLACEHOLDER.sub('example',value))


def validate_context(layer):
    entries = layer.get(CONTEXT_KEY, [])
    if not isinstance(entries, list) or len(entries) > 50:
        raise ValueError('Use at most 50 custom context actions.')
    for entry in entries:
        if (not isinstance(entry, dict) or not isinstance(entry.get('label'), str) or
                not entry['label'].strip() or len(entry['label']) > 200):
            raise ValueError('Each context action needs a label of 1–200 characters.')
        validate_template(entry.get('url'))
        if entry.get('subtechnique_url'): validate_template(entry['subtechnique_url'])
        elif 'subtechnique_url' in entry and not isinstance(entry['subtechnique_url'],str):
            raise ValueError('Sub-technique URL must be text.')


def resolve_context(entry, catalog, key, slug):
    """Missing parent/sub-technique values make that action unavailable."""
    validate_context({CONTEXT_KEY:[entry]})
    obj = catalog.records[key]
    parent = catalog.records.get(catalog.parents.get(key))
    tactic = catalog.tactics.get(slug)
    values = {}
    for prefix, record in [('technique_',obj),('parent_technique_',parent),
                           ('subtechnique_',obj if parent else None),('tactic_',tactic)]:
        if record:
            values.update({prefix+'attackID':external_id(record),prefix+'stixID':record['id'],
                           prefix+'name':record.get('x_mitre_shortname',record.get('name','').lower().replace(' ','-'))})
    if parent: values['subtechnique_attackID_suffix'] = external_id(obj).partition('.')[2]
    template = entry.get('subtechnique_url') if parent and entry.get('subtechnique_url') else entry['url']
    required = PLACEHOLDER.findall(template)
    if any(not values.get(token) for token in required): return None
    result = PLACEHOLDER.sub(lambda match:quote(values[match[1]],safe=''),template)
    return web_url(result)


class ContextEditor:
    """Editable draft table, wrapped to avoid a Qt import in pure validation."""
    def __init__(self, layer):
        from PySide6 import QtWidgets
        self.page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.page)
        hint = QtWidgets.QLabel('Custom right-click URL actions · {{technique_attackID}}, {{technique_stixID}}, '
            '{{technique_name}}, {{tactic_attackID}}, {{tactic_stixID}}, {{tactic_name}}. '
            'Optional sub-technique URL also accepts parent_technique_* / subtechnique_* and '
            '{{subtechnique_attackID_suffix}}. Opens only when clicked; HTTP(S) required.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QtWidgets.QTableWidget(0,3)
        self.table.setHorizontalHeaderLabels(['Label','URL template','Sub-technique URL (optional)'])
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        for entry in layer.get(CONTEXT_KEY,[]): self.add(entry)
        row = QtWidgets.QHBoxLayout()
        for text, callback in [('Add action',lambda:self.add({})), ('Remove row',self.remove),
                               ('Add ATT&CK example',lambda:self.add({'label':'ATT&CK technique',
                                 'url':'https://attack.mitre.org/techniques/{{technique_attackID}}/',
                                 'subtechnique_url':'https://attack.mitre.org/techniques/{{parent_technique_attackID}}/{{subtechnique_attackID_suffix}}/'}))]:
            button = QtWidgets.QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        layout.addLayout(row)

    def add(self, entry):
        from PySide6 import QtWidgets
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col,field in enumerate(('label','url','subtechnique_url')):
            self.table.setItem(row,col,QtWidgets.QTableWidgetItem(entry.get(field,'')))

    def remove(self):
        if self.table.currentRow() >= 0: self.table.removeRow(self.table.currentRow())

    def values(self):
        result = []
        for row in range(self.table.rowCount()):
            entry = {field:self.table.item(row,col).text().strip() for col,field in enumerate(('label','url','subtechnique_url'))}
            if not any(entry.values()): continue
            if not entry['subtechnique_url']: entry.pop('subtechnique_url')
            result.append(entry)
        validate_context({CONTEXT_KEY:result})
        return result
