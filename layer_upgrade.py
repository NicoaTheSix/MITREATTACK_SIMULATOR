"""Explicit annotation migration between ATT&CK catalogs. Workflow: README.md."""
from copy import deepcopy
from attack_catalog import external_id, tactic_phases, supports_navigator
from navigator_integration import document_layer, validate_layer, SELECTION_MARKER
from ttp_documents import TTPDocument, validate_document_name


def upgrade_preview(document, target, notify=lambda *args: None):
    notify('Input files: None; output files: None (immutable source/target catalogs in memory)', 0, 0)
    notify('[Upgrade 1/3] Comparing technique identities and scopes', 0, 3)
    if document.catalog.domain != target.domain or not supports_navigator(target):
        raise ValueError('Upgrade needs the same domain and a target release v4 or later.')
    layer = document_layer(document)
    source_ids = {external_id(o): key for key, o in document.catalog.records.items()}
    target_ids = {external_id(o): key for key, o in target.records.items()}
    target_raw = target.all_objects_by_domain.get(target.domain, {})
    replacements = {}
    for obj in target_raw.values():
        if (obj.get('type') == 'relationship' and obj.get('relationship_type') == 'revoked-by'
                and not obj.get('revoked') and not obj.get('x_mitre_deprecated')):
            before = target_raw.get(obj.get('source_ref'), {})
            after = target.records.get(obj.get('target_ref'), {})
            if before and after:
                replacements[external_id(before)] = external_id(after)
    # Selected IDs are present in document_layer, including otherwise unannotated selections.
    rows = []
    for index, annotation in enumerate(layer.get('techniques', []), 1):
        attack_id, scope = annotation['techniqueID'], annotation.get('tactic', '')
        old = document.catalog.records.get(source_ids.get(attack_id), {})
        new = target.records.get(target_ids.get(attack_id), {})
        replacement = replacements.get(attack_id, '')
        status = 'Unchanged' if new and old and old == new else 'Changed' if new else 'Replaced' if replacement else 'Unavailable'
        suggested = attack_id if new else replacement
        suggested_record = target.records.get(target_ids.get(suggested), {})
        changes = [{'field': field, 'before': old.get(field), 'after': suggested_record.get(field)}
                   for field in sorted(set(old) | set(suggested_record)) if old.get(field) != suggested_record.get(field)]
        valid_scope = bool(suggested) and (not scope or scope in tactic_phases(target.records[target_ids[suggested]], target.domain))
        if suggested and not valid_scope:
            status += ' · tactic removed'
        rows.append({'source_id': attack_id, 'source_scope': scope, 'annotation': deepcopy(annotation),
                     'selected': source_ids.get(attack_id) in document.selected,
                     'status': status, 'target_id': suggested, 'target_scope': scope if valid_scope else None,
                     'action': 'Copy' if suggested else 'Choose', 'reviewed': status == 'Unchanged', 'changes': changes})
        if index % 100 == 0:
            notify('[Upgrade 1/3] Resolving annotations', index, len(layer['techniques']))
    source_all = set(source_ids)
    added = sorted(set(target_ids) - source_all)
    notify(f'[Upgrade 1/3] {len(rows)} source rows; {len(added)} added target techniques', 1, 3)
    return {'rows': rows, 'added': added, 'layer': layer}


def migrate_layer(document, target, decisions, name, notify=lambda *args: None):
    preview = upgrade_preview(document, target, notify)
    if len(decisions) != len(preview['rows']):
        raise ValueError('Every source annotation row needs a migration decision.')
    ids = {external_id(o): key for key, o in target.records.items()}
    rows, selected, origins, audit = {}, set(), {}, []
    notify('[Upgrade 2/3] Applying reviewed mappings', 1, 3)
    for index, (source, decision) in enumerate(zip(preview['rows'], decisions), 1):
        if not decision.get('reviewed') or decision.get('action') not in ('Copy', 'Drop'):
            raise ValueError(f"Review {source['source_id']} / {source['source_scope'] or 'All tactics'} before creating the layer.")
        audit.append({'source_id': source['source_id'], 'source_scope': source['source_scope'],
                      'status': source['status'], 'changed_fields': [change['field'] for change in source['changes']], **decision})
        if decision['action'] == 'Drop':
            continue
        identity = decision.get('target_id')
        scope = decision.get('target_scope')
        if identity not in ids or scope is None or (scope and scope not in tactic_phases(target.records[ids[identity]], target.domain)):
            raise ValueError(f"Choose a valid target technique and tactic for {source['source_id']}.")
        row = deepcopy(source['annotation'])
        row['techniqueID'] = identity
        row.pop('tactic', None)
        if scope:
            row['tactic'] = scope
        if 'metadata' in row:
            row['metadata'] = [entry for entry in row['metadata'] if entry.get('name') != SELECTION_MARKER]
            if not row['metadata']:
                row.pop('metadata')
        key = (identity, scope)
        if key in rows:
            previous = rows[key]
            # Preserve compatible combined annotations, but require explicit resolution of scalar conflicts.
            for field in (set(previous) | set(row)) - {'comment', 'metadata', 'links', 'techniqueID', 'tactic'}:
                if field in previous and field in row and previous[field] != row[field]:
                    raise ValueError(f'Conflicting {field} at {identity}/{scope or "All tactics"}; drop or remap one source row.')
            merged = {**previous, **row}
            comments = [previous.get('comment', ''), row.get('comment', '')]
            if comments[0] and comments[1] and comments[0] != comments[1]:
                merged['comment'] = comments[0] + '\n\n[' + source['source_id'] + '] ' + comments[1]
            elif any(comments):
                merged['comment'] = next(c for c in comments if c)
            for field in ('metadata', 'links'):
                combined = []
                for entry in previous.get(field, []) + row.get(field, []):
                    if entry not in combined:
                        combined.append(entry)
                if combined:
                    merged[field] = combined
            rows[key] = merged
        else:
            rows[key] = row
        if source['selected']:
            selected.add(ids[identity])
        origins.setdefault(key, []).append(source['source_id'])
        notify('[Upgrade 2/3] Copying reviewed annotations', index, len(decisions))
    layer = deepcopy(preview['layer'])
    layer['name'] = validate_document_name(name)
    layer['versions']['attack'] = target.version
    layer['techniques'] = list(rows.values())
    if target.custom_source:
        layer['customDataURL'] = target.custom_source
        layer['x_ttp_studio_dataset'] = target.dataset_id
    else:
        layer.pop('customDataURL', None)
        layer.pop('x_ttp_studio_dataset', None)
    if 'platforms' in layer.get('filters', {}):
        layer['filters']['platforms'] = [p for p in layer['filters']['platforms'] if p in target.groups]
    layer['x_ttp_studio_upgrade'] = {'source_version': document.catalog.version,
                                    'source_dataset': document.catalog.dataset_id, 'target_dataset': target.dataset_id,
                                    'decisions': audit}
    validate_layer(layer)
    result = TTPDocument(layer['name'], target, selected=selected, navigator_layer=layer,
                         navigator_import_selected={external_id(target.records[key]) for key in selected})
    result.migration_archives = deepcopy(document.migration_archives) + [{
        'domain': document.catalog.domain, 'version': document.catalog.version,
        'dataset_id': document.catalog.dataset_id, 'custom_source': document.catalog.custom_source,
        'layer': deepcopy(preview['layer']), 'selected_stix_ids': sorted(document.selected),
        'import_selected': sorted(document.navigator_import_selected)}]
    # Only same-dataset history may participate in automatic version restoration.
    if document.catalog.dataset_id == target.dataset_id and document.catalog.version != target.version:
        result.navigator_snapshots[document.catalog.version] = {'layer': deepcopy(preview['layer']),
                                                               'import_selected': sorted(document.navigator_import_selected)}
    notify('[Upgrade 3/3] New layer created; source document preserved', 3, 3)
    return result
