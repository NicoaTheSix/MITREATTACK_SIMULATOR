"""Independent technique states and atomic batch edits. Operation flow: README.md."""
from copy import deepcopy
from attack_catalog import external_id, tactic_phases
from navigator_fields import validate_fields, web_url
from navigator_integration import (LAYER_VERSION, NAVIGATOR_VERSION, SELECTION_MARKER,
                                   layer_version, validate_layer, prune_empty_annotation_rows)

EDIT_FIELDS = {'comment', 'score', 'color', 'links', 'metadata', 'enabled'}


def rows_by_scope(document):
    return {(row['techniqueID'], row.get('tactic', '')): row for row in document.navigator_layer.get('techniques', [])}


def effective_row(document, key, tactic='', rows=None):
    rows = rows_by_scope(document) if rows is None else rows
    identity = external_id(document.catalog.records[key])
    return rows.get((identity, tactic), rows.get((identity, ''), {}))


def is_annotated(row):
    return (bool(row.get('comment')) or bool(row.get('color')) or 'score' in row
            or row.get('enabled') is False or bool(row.get('links'))
            or any(entry.get('name') != SELECTION_MARKER for entry in row.get('metadata', [])))


def annotated_keys(document, keys, tactic=None):
    rows = rows_by_scope(document)
    result = set()
    for key in keys:
        phases = tactic_phases(document.catalog.records[key], document.catalog.domain)
        scopes = [tactic] if tactic is not None else [''] + list(phases)
        if any(is_annotated(effective_row(document, key, slug, rows)) for slug in scopes):
            result.add(key)
    return result


def apply_selection(selected, scope, action, annotated=()):
    selected, scope, annotated = set(selected), set(scope), set(annotated) & set(scope)
    operations = {'add': lambda: selected | scope, 'replace': lambda: scope,
                  'remove': lambda: selected - scope, 'invert': lambda: selected ^ scope,
                  'annotated': lambda: annotated, 'unannotated': lambda: scope - annotated}
    if action not in operations:
        raise ValueError('Unknown selection action.')
    return operations[action]()


def batch_patch(document, keys, patch, tactic=None, notify=lambda *args: None):
    """Validate a draft then commit once. None clears a field; absent fields stay intact."""
    if tactic == '__selected__':
        from layer_analysis import snapshot_document
        from ttp_selection import selected_cells
        draft = snapshot_document(document)
        keys = set(keys)
        if not keys or not keys <= document.selected:
            raise ValueError('Selected-occurrence editing requires included TTPs.')
        notify('Input files: None; output files: None (immutable selected-occurrence draft)',0,0)
        whole = keys - document.selection_scopes.keys()
        if whole:
            batch_patch(draft,whole,patch,None,notify)
        for slug in document.catalog.tactic_order:
            scoped = {key for key in keys - whole if (key,slug) in selected_cells(document)}
            if scoped:
                batch_patch(draft,scoped,patch,slug,notify)
        changed = draft.navigator_layer != document.navigator_layer
        if changed:
            document.navigator_layer = draft.navigator_layer
        return {'changed':changed, 'keys':keys, 'layer':deepcopy(document.navigator_layer)}
    notify('Input files: None; output files: None (active layer draft in memory)', 0, 0)
    notify('[Batch Edit 1/3] Validating targets and requested fields', 0, 3)
    keys = set(keys)
    if not keys or not keys <= document.catalog.records.keys():
        raise ValueError('Choose techniques from the active document.')
    if not patch or not set(patch) <= EDIT_FIELDS:
        raise ValueError('Choose at least one supported field to edit.')
    if tactic is not None and tactic not in document.catalog.tactics:
        raise ValueError('Unknown tactic scope.')
    if patch.get('enabled') not in (None, 'toggle') and type(patch.get('enabled')) is not bool:
        raise ValueError('Enabled state must be a boolean, toggle or reset.')
    validate_fields({field: patch[field] for field in ('metadata', 'links') if patch.get(field) is not None})
    for entry in patch.get('links') or []:
        if entry.get('divider') is not True:
            web_url(entry['url'])
    eligible = {key for key in keys if tactic is None or tactic in tactic_phases(document.catalog.records[key], document.catalog.domain)}
    if not eligible:
        raise ValueError('None of the selected techniques map to this tactic.')
    candidate = deepcopy(document.navigator_layer) if document.navigator_layer else {
        'name': document.name, 'domain': document.catalog.domain,
        'versions': {'attack': document.catalog.version, 'layer': LAYER_VERSION, 'navigator': NAVIGATOR_VERSION}, 'techniques': []}
    if candidate.get('domain') != document.catalog.domain or layer_version(candidate, document.catalog.version) != document.catalog.version:
        raise ValueError('The annotations belong to another domain/version.')
    rows = candidate.setdefault('techniques', [])
    prunable = []
    for number, key in enumerate(sorted(eligible), 1):
        identity = external_id(document.catalog.records[key])
        phases = tactic_phases(document.catalog.records[key], document.catalog.domain)
        matches = [row for row in rows if row['techniqueID'] == identity and
                   (row.get('tactic', '') == tactic if tactic is not None else
                    not row.get('tactic') or row.get('tactic') in phases)]
        assigning = any(value is not None for value in patch.values())
        global_row = next((row for row in reversed(rows) if row['techniqueID'] == identity and not row.get('tactic')), {})
        clearing_inherited = tactic is not None and not matches and any(value is None and field in global_row
                            and (field != 'metadata' or any(entry.get('name') != SELECTION_MARKER for entry in global_row[field]))
                            for field, value in patch.items())
        if (assigning or clearing_inherited) and (not matches or (tactic is None and not any(not row.get('tactic') for row in matches))):
            row = deepcopy(global_row) if tactic else {'techniqueID': identity}
            row['techniqueID'] = identity
            if tactic:
                row['tactic'] = tactic
            rows.append(row)
            matches.append(row)
        for row in matches:
            for field, value in patch.items():
                if field == 'metadata':
                    reserved = [entry for entry in row.get('metadata', []) if entry.get('name') == SELECTION_MARKER]
                    user_entries = [] if value is None else [deepcopy(entry) for entry in value if entry.get('name') != SELECTION_MARKER]
                    if user_entries or reserved:
                        row['metadata'] = user_entries + reserved
                    else:
                        row.pop('metadata', None)
                elif value is None:
                    row.pop(field, None)
                elif field == 'enabled' and value == 'toggle':
                    row[field] = not row.get(field, True)
                else:
                    row[field] = deepcopy(value)
            if tactic is None:
                prunable.append(row)
        if number % 50 == 0 or number == len(eligible):
            notify('[Batch Edit 2/3] Updating technique annotations in the draft', number, len(eligible))
    prune_empty_annotation_rows(document, candidate, prunable)
    candidate = validate_layer(candidate, document.catalog)
    changed = candidate != document.navigator_layer
    # An absent clear must also leave a genuinely empty document unchanged.
    if not document.navigator_layer and not candidate.get('techniques'):
        changed = False
    if changed:
        document.navigator_layer = candidate
    notify(f'[Batch Edit 3/3] Ready: {len(eligible)} affected TTPs; selection preserved', 3, 3)
    return {'changed': changed, 'keys': eligible, 'layer': deepcopy(document.navigator_layer)}
