"""Immutable Navigator JSON annotation visibility plans. Workflow: README.md."""
from copy import deepcopy
from dataclasses import dataclass

from attack_catalog import external_id, tactic_phases
from navigator_integration import document_layer, grouping_scopes, SELECTION_MARKER, validate_layer
from navigator_visuals import LayerAppearance
from matrix_expansion import expanded_family
from ttp_search import matches


def modified_annotation(row):
    """Navigator modified(), excluding Studio's inclusion-only metadata."""
    metadata = [m for m in row.get('metadata', []) if m.get('name') != SELECTION_MARKER]
    standard = {'techniqueID', 'tactic', 'score', 'color', 'enabled', 'comment',
                'metadata', 'links', 'showSubtechniques'}
    return bool('score' in row or row.get('color') or row.get('enabled') is False
                or row.get('comment') or row.get('links') or metadata
                or row.get('showSubtechniques') or set(row) - standard)


def matrix_visibility(matrix):
    """Capture logical displayed cells, including grouping parents; ignore scrolling."""
    from attack_matrix import MATRIX_ID
    cells = set()
    for column in matrix.columns:
        if column['frame'].isHidden():
            continue
        slug = column['slug']
        if 'view' in column:
            for family in column['view'].families:
                if family['frame'].isHidden():
                    continue
                cells.add((external_id(matrix.catalog.records[family['root'].key]), slug))
                if family['toggle'].isChecked():
                    cells.update((external_id(matrix.catalog.records[child.key]), slug)
                                 for child in family['children'] if not child.isHidden())
        else:
            tree = column['tree']
            for index in range(tree.topLevelItemCount()):
                root = tree.topLevelItem(index)
                if root.isHidden():
                    continue
                cells.add((external_id(matrix.catalog.records[root.data(0, MATRIX_ID)]), slug))
                if root.isExpanded():
                    cells.update((external_id(matrix.catalog.records[root.child(i).data(0, MATRIX_ID)]), slug)
                                 for i in range(root.childCount()) if not root.child(i).isHidden())
    return frozenset(cells)


def saved_visibility(document, layer, context=None):
    """Project saved filters/expansion, or the active matrix's frozen controls."""
    from attack_matrix import ALL_PLATFORMS, matrix_columns
    context = context or {}
    if 'visible_cells' in context:
        return frozenset(context['visible_cells'])
    catalog = document.catalog
    platform = context.get('platform', layer.get('filters', {}).get('platforms', ALL_PLATFORMS))
    # Imported filters can contain names absent from this exact release. Keep
    # them in JSON while projecting only supported platforms, like the UI.
    if isinstance(platform, (list, tuple, set)):
        platform = [name for name in platform if name in catalog.groups]
    elif platform != ALL_PLATFORMS and platform not in catalog.groups:
        platform = []
    query = context.get('query', '').strip().casefold()
    appearance = LayerAppearance(layer, catalog)
    cells = set()
    for slug, families in matrix_columns(catalog, platform):
        for family in families:
            key = family['key']
            root_match = matches(catalog, key, query, document.search_fields)
            children = [child for child in family['children']
                        if (root_match or matches(catalog, child, query, document.search_fields))
                        and not appearance.cell(external_id(catalog.records[child]), slug)['hidden']]
            if not ((root_match and not appearance.cell(external_id(catalog.records[key]), slug)['hidden']) or children):
                continue
            cells.add((external_id(catalog.records[key]), slug))
            expanded = expanded_family(appearance, catalog, key, slug, family['children'],
                                       layer.get('layout', {}).get('layout') == 'mini')
            if expanded or (query and children):
                cells.update((external_id(catalog.records[child]), slug) for child in children)
    return frozenset(cells)


@dataclass(frozen=True)
class AnnotationExportPlan:
    layer: dict
    visible: frozenset
    effective_rows: tuple
    hidden_modified: tuple

    @property
    def hidden_techniques(self):
        return len({row['techniqueID'] for row in self.hidden_modified})

    def payload(self, visible_only=False):
        if type(visible_only) is not bool:
            raise ValueError('Visible annotation export must be a boolean.')
        result = deepcopy(self.layer)
        if not visible_only:
            return result
        rows = []
        for row in self.effective_rows:
            identity = row['techniqueID'], row.get('tactic', '')
            if identity in self.visible:
                rows.append(deepcopy(row))
            else:
                # Keep inclusion independent from annotation visibility. No global
                # annotation may leak back into a hidden tactic on reimport.
                marker = [deepcopy(m) for m in row.get('metadata', [])
                          if m.get('name') == SELECTION_MARKER and m.get('value') == 'true']
                if marker:
                    rows.append({'techniqueID': row['techniqueID'], 'tactic': row['tactic'], 'metadata': marker})
        result['techniques'] = rows
        return validate_layer(result)


def annotation_export_plan(document, context=None, notify=lambda *args: None):
    notify('Input files: None (document/catalog and matrix visibility in memory)', 0, 0)
    notify('Output files: None (immutable JSON export preview)', 0, 0)
    notify('[JSON Preview 1/3] Validating complete annotations', 0, 3)
    layer = document_layer(document)
    visible = saved_visibility(document, layer, context)
    lookup = {external_id(obj): obj for obj in document.catalog.records.values()}
    grouping = grouping_scopes(document.catalog)
    index = {(row['techniqueID'], row.get('tactic', '')): row for row in layer.get('techniques', [])}
    effective, unresolved = [], []
    for (identity, slug), row in index.items():
        if identity not in lookup or (slug and slug not in tactic_phases(lookup[identity], document.catalog.domain)
                                     and not ('showSubtechniques' in row and slug in grouping.get(identity, set()))):
            unresolved.append(deepcopy(row))
    for number, (identity, obj) in enumerate(lookup.items(), 1):
        mapped = tactic_phases(obj, document.catalog.domain) & document.catalog.tactics.keys()
        phases = mapped | grouping.get(identity, set())
        if not phases and (identity, '') in index:
            unresolved.append(deepcopy(index[identity, '']))
        for slug in sorted(phases):
            row = index.get((identity, slug), index.get((identity, '')))
            if row is not None:
                resolved = {**deepcopy(row), 'tactic': slug}
                if slug not in mapped:
                    # This is a displayed family heading, not a selectable
                    # occurrence of the parent in the child's tactic.
                    resolved.setdefault('showSubtechniques', False)
                    resolved['metadata'] = [m for m in resolved.get('metadata', []) if m.get('name') != SELECTION_MARKER]
                    resolved['metadata'].append({'name': SELECTION_MARKER, 'value': 'false'})
                effective.append(resolved)
        if number % 100 == 0 or number == len(lookup):
            notify('[JSON Preview 2/3] Resolving technique / tactic annotations', number, len(lookup))
    hidden = [row for row in effective if (row['techniqueID'], row['tactic']) not in visible and modified_annotation(row)]
    # Unresolved imports cannot be visible, but full export must retain them.
    hidden.extend(row for row in unresolved if modified_annotation(row))
    notify('[JSON Preview 3/3] Hidden modified annotation cells: ' + str(len(hidden)), 3, 3)
    return AnnotationExportPlan(layer, visible, tuple(effective), tuple(hidden))
