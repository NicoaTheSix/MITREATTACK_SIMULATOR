"""Full upgrade completion summary, reason validation and navigation targets. Workflow: README.md."""
from copy import deepcopy
from hashlib import sha256

from attack_catalog import catalog_identity
from navigator_integration import validate_layer
from ttp_documents import validate_document_name
from upgrade_content import mapped_annotation
from upgrade_mapping import canonical, decision_targets, target_layer, resolution_value, resolved_layer
from upgrade_review import CATEGORIES, validate_reviews

REASON_LIMIT = 4096


def summary_token(document, target, decisions, reviews, resolutions, name):
    payload = [document.content_token(), catalog_identity(target), decisions, reviews, resolutions, name]
    return sha256(canonical(payload).encode('utf-8')).hexdigest()


def validate_reasons(preview, reasons):
    reasons = {} if reasons is None else reasons
    valid = {'source:' + str(i) for i in range(len(preview['rows']))} | {
        'added:' + item['id'] for item in preview['items'] if item['category'] == 'Added'}
    if not isinstance(reasons, dict) or any(not isinstance(key, str) or key not in valid for key in reasons):
        raise ValueError('Skip reasons must refer to current source rows or Added techniques.')
    if any(not isinstance(value, str) or len(value) > REASON_LIMIT for value in reasons.values()):
        raise ValueError('Each skip reason must be text of at most 4096 characters.')
    return deepcopy(reasons)


def base_summary(document, target, preview, decisions, reviews, resolutions, name, reasons):
    reasons = validate_reasons(preview, reasons)
    review_map = {r['id']: r for r in reviews if isinstance(r, dict) and isinstance(r.get('id'), str)} if isinstance(reviews, list) else {}
    if reviews is None:
        review_map = {item['id']: {'id': item['id'], 'reviewed': item['reviewed']} for item in preview['items']}
    decisions = decisions if isinstance(decisions, list) else []
    skips, skipped_ids = [], set()
    item_map = {item['id']: item for item in preview['items']}
    for index, row in enumerate(preview['rows']):
        decision = decisions[index] if index < len(decisions) and isinstance(decisions[index], dict) else {}
        if decision.get('action') == 'Drop':
            key = 'source:' + str(index)
            skips.append({'key': key, 'kind': 'Drop source', 'identity': row['source_id'], 'source_index': index,
                          'scope': row['source_scope'], 'category': item_map[row['source_id']]['category'], 'reason': reasons.get(key, '')})
    categories = []
    for item in preview['items']:
        review = review_map.get(item['id'], {})
        if item['category'] == 'Added' and not review.get('annotation_rows') and not review.get('selected_scopes'):
            key = 'added:' + item['id']
            skips.append({'key': key, 'kind': 'Skip Added annotation', 'identity': item['id'], 'category': 'Added',
                          'scope': '', 'reason': reasons.get(key, '')})
            skipped_ids.add(item['id'])
        elif (item['row_indices'] and all(i < len(decisions) and isinstance(decisions[i], dict) and decisions[i].get('action') == 'Drop'
               for i in item['row_indices']) and not review.get('annotation_rows')):
            skipped_ids.add(item['id'])
    for category in CATEGORIES:
        items = [item for item in preview['items'] if item['category'] == category]
        total = len(items)
        count = sum(review_map.get(item['id'], {}).get('reviewed') is True for item in items)
        skipped = sum(item['id'] in skipped_ids for item in items)
        categories.append({'category': category, 'total': total, 'reviewed': count, 'skipped': skipped,
                           'state': 'Empty' if not total else 'Incomplete' if count != total else 'Skipped' if skipped == total else 'Complete'})
    def provenance(catalog):
        return {'domain': catalog.domain, 'version': catalog.version, 'dataset_id': catalog.dataset_id, 'custom_source': catalog.custom_source}
    try:
        display_name = validate_document_name(name)
    except ValueError:
        display_name = name
    return {'schema': 1, 'source': provenance(document.catalog), 'target': provenance(target), 'source_name': document.name,
            'result_name': display_name, 'categories': categories, 'total': len(preview['items']),
            'reviewed': sum(c['reviewed'] for c in categories), 'source_rows': len(preview['rows']),
            'copy_rows': sum(isinstance(d, dict) and d.get('action') == 'Copy' for d in decisions),
            'drop_rows': sum(isinstance(d, dict) and d.get('action') == 'Drop' for d in decisions), 'skips': skips,
            'issues': [], 'can_submit': False, 'output_rows': None, 'selected_techniques': None, 'selected_occurrences': None,
            'conflicts': None, 'resolved_conflicts': None,
            'input_token': summary_token(document, target, decisions, reviews, resolutions, name)}


def final_summary(document, plan, decisions, reviews, resolutions, name, reasons, layer):
    result = base_summary(document, plan['target'], plan['preview'], decisions, reviews, resolutions, name, reasons)
    result.update(can_submit=True, output_rows=len(layer['techniques']), conflicts=len(plan['conflicts']),
                  resolved_conflicts=len(plan['conflicts']), selected_occurrences=len(plan['selection_cells']),
                  selected_techniques=len({key for key, scope in plan['selection_cells']}))
    return result


def build_summary(document, target, decisions, name, notify=lambda *args: None, *, reviews=None, resolutions=None, skip_reasons=None):
    from layer_upgrade import upgrade_preview, migration_plan
    notify('Input files: None; output files: None (complete upgrade summary in memory)', 0, 0)
    notify('[Upgrade summary 1/3] Comparing all identities and validating skip reasons', 0, 3)
    preview = upgrade_preview(document, target, notify)
    result = base_summary(document, target, preview, decisions, reviews, resolutions, name, skip_reasons)
    issues = result['issues']
    def issue(kind, message, **location):
        issues.append({'kind': kind, 'message': str(message), **location})
    try:
        validate_document_name(name)
    except ValueError as error:
        issue('name', error)
    review_map = {r['id']: r for r in reviews if isinstance(r, dict) and isinstance(r.get('id'), str)} if isinstance(reviews, list) else {}
    if reviews is None:
        review_map = {i['id']: {'id': i['id'], 'reviewed': i['reviewed']} for i in preview['items']}
    elif (not isinstance(reviews, list) or len(reviews) != len(preview['items']) or len(review_map) != len(reviews)
          or set(review_map) != {i['id'] for i in preview['items']}):
        issue('technique', 'Every current technique needs exactly one review.')
    for number, item in enumerate(preview['items'], 1):
        if number % 100 == 0:
            notify('[Upgrade summary 1/3] Checking complete technique reviews', number, len(preview['items']))
        review = review_map.get(item['id'], {})
        if review.get('reviewed') is not True:
            issue('technique', 'Technique review is incomplete.', identity=item['id'])
        try:
            validate_reviews({'items': [item]}, target, [{**review, 'id': item['id'], 'reviewed': True}])
        except ValueError as error:
            issue('technique', error, identity=item['id'])
    if not isinstance(decisions, list) or len(decisions) != len(preview['rows']):
        issue('mapping', 'Every source row needs exactly one mapping decision.')
    for index, source in enumerate(preview['rows']):
        decision = decisions[index] if isinstance(decisions, list) and index < len(decisions) else {}
        if not isinstance(decision, dict):
            issue('mapping', 'Invalid mapping decision.', source_index=index, identity=source['source_id'])
            continue
        if decision.get('reviewed') is not True:
            issue('mapping', 'Source mapping review is incomplete.', source_index=index, identity=source['source_id'])
        try:
            targets = decision_targets(decision, target)
            for destination in targets:
                row = mapped_annotation(source, destination)
                validate_layer(target_layer(preview['layer'], target, [row]), target)
        except ValueError as error:
            issue('mapping', error, source_index=index, identity=source['source_id'])
    notify('[Upgrade summary 2/3] Checking complete mapping and conflict readiness', 1, 3)
    plan = None
    try:
        plan = migration_plan(document, target, decisions, notify, reviews=reviews, require_review=False)
    except (ValueError, TypeError, KeyError) as error:
        if not any(i['kind'] in ('mapping', 'technique') for i in issues):
            issue('mapping', error)
    if plan:
        conflicts = plan['conflicts']
        result.update(conflicts=len(conflicts), resolved_conflicts=0,
                      selected_occurrences=len(plan['selection_cells']),
                      selected_techniques=len({key for key, scope in plan['selection_cells']}))
        supplied = resolutions if isinstance(resolutions, list) else []
        if resolutions is not None and not isinstance(resolutions, list):
            issue('conflict', 'Conflict resolutions must be a list.')
        expected = {(c['target_id'], c['target_scope'], c['field']): c for c in conflicts}
        found = {}
        for entry in supplied:
            key = tuple(entry.get(k) for k in ('target_id', 'target_scope', 'field')) if isinstance(entry, dict) else ()
            if len(key) != 3 or any(not isinstance(v, str) for v in key) or key not in expected or key in found:
                issue('conflict', 'Stale, unrelated or duplicate conflict resolution.')
            else:
                found[key] = entry
        for key, conflict in expected.items():
            location = {'target_id': conflict['target_id'], 'target_scope': conflict['target_scope'], 'field': conflict['field']}
            origins = [c['origin'] for c in conflict['candidates'] if c['origin'].startswith('source:')]
            if origins:
                location['source_index'] = int(origins[0].split(':')[1])
            try:
                if key not in found:
                    raise ValueError('Choose and review this conflict resolution.')
                action, value = resolution_value(conflict, found[key])
                row = {'techniqueID': key[0], **({'tactic': key[1]} if key[1] else {})}
                if action != 'clear':
                    row[key[2]] = value
                validate_layer(target_layer(preview['layer'], target, [row]), target)
                result['resolved_conflicts'] += 1
            except ValueError as error:
                issue('conflict', error, **location)
        if not any(i['kind'] == 'conflict' for i in issues):
            try:
                layer, _ = resolved_layer(plan, resolutions)
                result['output_rows'] = len(layer['techniques'])
            except ValueError as error:
                issue('conflict', error)
    result['can_submit'] = not issues
    for category in result['categories']:
        ids = {i['id'] for i in preview['items'] if i['category'] == category['category']}
        indices = {index for i in preview['items'] if i['id'] in ids for index in i['row_indices']}
        if any(i.get('identity') in ids or i.get('target_id') in ids or i.get('source_index') in indices for i in issues):
            category['state'] = 'Incomplete'
    notify('[Upgrade summary 3/3] Complete summary ready; unfinished items remain blocked', 3, 3)
    return result
