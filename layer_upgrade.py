"""Explicit annotation migration between ATT&CK catalogs. Workflow: README.md."""
from copy import deepcopy
from attack_catalog import external_id, tactic_phases, supports_navigator
from navigator_integration import document_layer, validate_layer
from ttp_documents import TTPDocument, validate_document_name
from upgrade_review import CATEGORIES, classify_upgrade, validate_reviews
from upgrade_mapping import contributions, find_conflicts, resolved_layer


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
                replacements.setdefault(external_id(before), set()).add(external_id(after))
    # Ambiguous successors require an explicit mapping; never silently pick one.
    replacements = {identity: next(iter(ids)) for identity, ids in replacements.items() if len(ids) == 1}
    # Selected IDs are present in document_layer, including otherwise unannotated selections.
    rows = []
    for index, annotation in enumerate(layer.get('techniques', []), 1):
        attack_id, scope = annotation['techniqueID'], annotation.get('tactic', '')
        old = document.catalog.records.get(source_ids.get(attack_id), {})
        new = target.records.get(target_ids.get(attack_id), {})
        replacement = replacements.get(attack_id, '')
        status = 'Unchanged' if new and old and old == new else 'Changed' if new else 'Replaced' if replacement else 'Removed'
        suggested = attack_id if new else replacement
        suggested_record = target.records.get(target_ids.get(suggested), {})
        changes = [{'field': field, 'before': old.get(field), 'after': suggested_record.get(field)}
                   for field in sorted(set(old) | set(suggested_record)) if old.get(field) != suggested_record.get(field)]
        valid_scope = bool(suggested) and (not scope or scope in tactic_phases(target.records[target_ids[suggested]], target.domain))
        if suggested and not valid_scope:
            status += ' · tactic removed'
        rows.append({'source_id': attack_id, 'source_scope': scope, 'annotation': deepcopy(annotation),
                     'selected': (source_ids.get(attack_id) in document.selected and
                                  (source_ids.get(attack_id) not in document.selection_scopes or scope in document.selection_scopes[source_ids[attack_id]])),
                     'status': status, 'target_id': suggested, 'target_scope': scope if valid_scope else None,
                     'action': 'Copy' if suggested else 'Choose', 'reviewed': status == 'Unchanged', 'changes': changes})
        if index % 100 == 0:
            notify('[Upgrade 1/3] Resolving annotations', index, len(layer['techniques']))
    source_all = set(source_ids)
    added = sorted(set(target_ids) - source_all)
    notify(f'[Upgrade 1/3] {len(rows)} source rows; {len(added)} added target techniques', 1, 3)
    items = classify_upgrade(document, target, rows, replacements, notify)
    return {'rows': rows, 'added': added, 'layer': layer, 'items': items,
            'counts': {category: sum(item['category'] == category for item in items) for category in CATEGORIES}}


def migration_plan(document, target, decisions, notify=lambda *args: None, *, reviews=None, require_review=True):
    preview = upgrade_preview(document, target, notify)
    if not isinstance(decisions, list) or len(decisions) != len(preview['rows']):
        raise ValueError('Every source annotation row needs a migration decision.')
    notify('[Upgrade 2/3] Validating reviews and explicit mapping destinations', 1, 3)
    effective_reviews = reviews
    if not require_review:
        effective_reviews = ([{'id': item['id'], 'reviewed': True} for item in preview['items']] if reviews is None
                             else [{**item, 'reviewed': True} for item in reviews])
    technique_reviews, additions, added_selection = validate_reviews(preview, target, effective_reviews)
    entries, audit, cells = contributions(preview, target, decisions, additions, notify, require_review=require_review)
    ids = {external_id(obj): key for key, obj in target.records.items()}
    cells.update((ids[identity], scope) for identity, scope in added_selection)
    conflicts = find_conflicts(entries)
    notify('[Upgrade 2/3] Mapping and conflict preview ready', len(entries) or 1, len(entries) or 1)
    return {'preview': preview, 'target': target, 'entries': entries, 'decisions': audit,
            'technique_reviews': technique_reviews, 'selection_cells': cells, 'conflicts': conflicts}


def migrate_layer(document, target, decisions, name, notify=lambda *args: None, *, reviews=None, resolutions=None, skip_reasons=None):
    plan = migration_plan(document, target, decisions, notify, reviews=reviews)
    preview = plan['preview']
    notify('[Upgrade 2/3] Applying reviewed field conflict resolutions', 1, 3)
    layer, resolution_audit = resolved_layer(plan, resolutions)
    layer['name'] = validate_document_name(name)
    selection_cells = plan['selection_cells']
    selected = {key for key, scope in selection_cells}
    from upgrade_summary import final_summary
    completion = final_summary(document, plan, decisions, reviews, resolutions, name, skip_reasons, layer)
    for skip in completion['skips']:
        if 'source_index' in skip:
            plan['decisions'][skip['source_index']]['skip_reason'] = skip['reason']
        else:
            next(r for r in plan['technique_reviews'] if r['id'] == skip['identity'])['skip_reason'] = skip['reason']
    layer['x_ttp_studio_upgrade'] = {'source_version': document.catalog.version,
                                    'source_dataset': document.catalog.dataset_id, 'target_dataset': target.dataset_id,
                                    'decisions': plan['decisions'], 'review_schema': 2,
                                    'technique_reviews': plan['technique_reviews'], 'category_counts': preview['counts'],
                                    'conflict_resolutions': resolution_audit, 'final_summary': completion}
    result = TTPDocument(layer['name'], target, selected=selected, navigator_layer=layer,
                         navigator_import_selected={external_id(target.records[key]) for key in selected})
    from ttp_selection import assign_cells
    assign_cells(result,selection_cells)
    result.selection_preferences = dict(document.selection_preferences)
    result.search_fields = list(document.search_fields)
    result.migration_archives = deepcopy(document.migration_archives) + [{
        'domain': document.catalog.domain, 'version': document.catalog.version,
        'dataset_id': document.catalog.dataset_id, 'custom_source': document.catalog.custom_source,
        'layer': deepcopy(preview['layer']), 'selected_stix_ids': sorted(document.selected),
        'import_selected': sorted(document.navigator_import_selected), 'selection_scopes':deepcopy(document.selection_scopes)}]
    # Only same-dataset history may participate in automatic version restoration.
    if document.catalog.dataset_id == target.dataset_id and document.catalog.version != target.version:
        result.navigator_snapshots[document.catalog.version] = {'layer': deepcopy(preview['layer']),
                                                               'import_selected': sorted(document.navigator_import_selected)}
    notify('[Upgrade 3/3] New layer created; source document preserved', 3, 3)
    return result
