"""Explicit upgrade destinations and fingerprint-bound conflict decisions. Workflow: README.md."""
from copy import deepcopy
from hashlib import sha256
import json

from attack_catalog import external_id, tactic_phases
from navigator_integration import validate_layer, SELECTION_MARKER
from navigator_fields import validate_fields
from upgrade_content import mapped_annotation

COMBINED = {'comment', 'links', 'metadata', 'techniqueID', 'tactic'}


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    except (TypeError, ValueError) as error:
        raise ValueError('Resolution values must be finite JSON values.') from error


def decision_targets(decision, target):
    """Normalize legacy single destinations and explicit lists without guessing scopes."""
    if decision.get('action') == 'Drop':
        return []
    if decision.get('action') != 'Copy':
        raise ValueError('Review the source row and choose Copy or Drop.')
    targets = decision.get('targets', [{'target_id': decision.get('target_id'), 'target_scope': decision.get('target_scope')}])
    if not isinstance(targets, list) or not 1 <= len(targets) <= 100:
        raise ValueError('Copy needs one to one hundred explicit target destinations.')
    records = {external_id(obj): obj for obj in target.records.values()}
    seen, scopes_by_id, result = set(), {}, []
    common = decision.get('annotation_patch', {})
    if not isinstance(common, dict):
        raise ValueError('Target annotation edits must be objects.')
    for item in targets:
        if not isinstance(item, dict) or item.keys() - {'target_id', 'target_scope', 'annotation_patch'}:
            raise ValueError('Each target needs only a technique, tactic and optional annotation patch.')
        identity, scope = item.get('target_id'), item.get('target_scope')
        if (not isinstance(identity, str) or identity not in records or not isinstance(scope, str) or
                scope and scope not in tactic_phases(records[identity], target.domain)):
            raise ValueError('Choose a valid target technique and tactic for every destination.')
        key = (identity, scope)
        if key in seen:
            raise ValueError('Duplicate target technique/tactic destinations are not allowed.')
        seen.add(key)
        scopes = scopes_by_id.setdefault(identity, set())
        if scopes and (not scope or '' in scopes):
            raise ValueError('All tactics cannot overlap explicit tactics for the same target in one source mapping.')
        scopes.add(scope)
        patch = item.get('annotation_patch', {})
        if not isinstance(patch, dict):
            raise ValueError('Each target annotation patch must be an object.')
        result.append({'target_id': identity, 'target_scope': scope, 'annotation_patch': {**deepcopy(common), **deepcopy(patch)}})
    return result


def target_layer(original, target, rows):
    layer = deepcopy(original)
    layer['versions']['attack'] = target.version
    layer['techniques'] = deepcopy(rows)
    layer.pop('x_ttp_studio_domain', None)
    if target.custom_source:
        layer['customDataURL'], layer['x_ttp_studio_dataset'] = target.custom_source, target.dataset_id
    else:
        layer.pop('customDataURL', None)
        layer.pop('x_ttp_studio_dataset', None)
    if 'platforms' in layer.get('filters', {}):
        layer['filters']['platforms'] = [p for p in layer['filters']['platforms'] if p in target.groups]
    return layer


def contributions(preview, target, decisions, additions, notify, *, require_review):
    entries, audit, selected = [], [], set()
    records = {external_id(obj): (key, obj) for key, obj in target.records.items()}
    for index, (source, decision) in enumerate(zip(preview['rows'], decisions)):
        if not isinstance(decision, dict) or (require_review and decision.get('reviewed') is not True):
            raise ValueError(f"Review {source['source_id']} before creating the layer.")
        targets = decision_targets(decision, target)
        audit.append({'source_id': source['source_id'], 'source_scope': source['source_scope'],
                      'status': source['status'], 'changed_fields': [c['field'] for c in source['changes']],
                      **deepcopy(decision), 'targets': deepcopy(targets)})
        for branch, destination in enumerate(targets):
            row = mapped_annotation(source, destination)
            entries.append({'origin': f'source:{index}:{branch}',
                            'label': source['source_id'] + ('/' + source['source_scope'] if source['source_scope'] else ''), 'row': row})
            if source['selected']:
                key, obj = records[destination['target_id']]
                selected.update((key, slug) for slug in tactic_phases(obj, target.domain)
                                if not destination['target_scope'] or slug == destination['target_scope'])
        notify('[Upgrade 2/3] Expanding explicit mapping destinations', index + 1, len(decisions))
    for index, row in enumerate(additions):
        entries.append({'origin': f'target:{index}', 'label': 'Target draft ' + row['techniqueID'], 'row': deepcopy(row)})
    if len(entries) > 20000:
        raise ValueError('Expanded migration exceeds 20,000 annotation contributions.')
    for entry in entries:
        row = entry['row']
        validate_fields(row)
        if 'metadata' in row:
            had_entries = bool(row['metadata'])
            row['metadata'] = [m for m in row['metadata'] if m.get('name') != SELECTION_MARKER]
            if had_entries and not row['metadata']:
                row.pop('metadata')
    canonical(entries)
    # Validate every candidate, so resolving a conflict cannot conceal an invalid source edit.
    validate_layer(target_layer(preview['layer'], target, [e['row'] for e in entries]), target)
    return entries, audit, selected


def grouped_entries(entries):
    grouped = {}
    for entry in entries:
        row = entry['row']
        grouped.setdefault((row['techniqueID'], row.get('tactic', '')), []).append(entry)
    return grouped


def find_conflicts(entries):
    conflicts = []
    for (identity, scope), group in grouped_entries(entries).items():
        fingerprint = sha256(canonical(group).encode('utf-8')).hexdigest()
        fields = set().union(*(entry['row'].keys() for entry in group)) - COMBINED
        for field in sorted(fields):
            candidates = [{'origin': entry['origin'], 'label': entry['label'], 'value': deepcopy(entry['row'][field])}
                          for entry in group if field in entry['row']]
            if len({canonical(c['value']) for c in candidates}) > 1:
                conflicts.append({'target_id': identity, 'target_scope': scope, 'field': field,
                                  'fingerprint': fingerprint, 'candidates': candidates})
    return conflicts


def resolution_value(conflict, resolution):
    if resolution.get('reviewed') is not True or resolution.get('fingerprint') != conflict['fingerprint']:
        raise ValueError('Review the current conflict again; its candidates changed or it is not acknowledged.')
    action = resolution.get('action')
    if action == 'candidate':
        candidate = next((c for c in conflict['candidates'] if c['origin'] == resolution.get('origin')), None)
        if candidate is None:
            raise ValueError('Choose a current conflict candidate.')
        value = deepcopy(candidate['value'])
    elif action == 'custom' and 'value' in resolution:
        value = deepcopy(resolution['value'])
        canonical(value)
    elif action == 'clear':
        value = None
    else:
        raise ValueError('Choose a candidate, a custom JSON value or clear the field.')
    return action, value


def resolve_entries(entries, resolutions=None):
    conflicts = find_conflicts(entries)
    if resolutions is None:
        resolutions = []
    if not isinstance(resolutions, list):
        raise ValueError('Conflict resolutions must be a list.')
    expected = {(c['target_id'], c['target_scope'], c['field']): c for c in conflicts}
    chosen, audit = {}, []
    for resolution in resolutions:
        if not isinstance(resolution, dict):
            raise ValueError('Each conflict resolution must be an object.')
        parts = (resolution.get('target_id'), resolution.get('target_scope'), resolution.get('field'))
        if any(not isinstance(part, str) for part in parts):
            raise ValueError('A conflict resolution needs a target, tactic and field.')
        if parts not in expected or parts in chosen:
            raise ValueError('Stale, unrelated or duplicate conflict resolutions are not allowed.')
        conflict = expected[parts]
        action, value = resolution_value(conflict, resolution)
        chosen[parts] = (action, value)
        audit.append({**deepcopy(resolution), 'resolved_value': value})
    missing = next((key for key in expected if key not in chosen), None)
    if missing:
        raise ValueError(f'Conflicting {missing[2]} at {missing[0]}/{missing[1] or "All tactics"}; review this conflict before creating the layer.')
    rows = []
    for (identity, scope), group in grouped_entries(entries).items():
        row, comments = {'techniqueID': identity}, []
        if scope:
            row['tactic'] = scope
        for entry in group:
            annotation = entry['row']
            for field in annotation.keys() - COMBINED:
                row[field] = deepcopy(annotation[field])
            comment = annotation.get('comment', '')
            if comment and all(comment != old[1] for old in comments):
                comments.append((entry['label'], comment))
            for field in ('links', 'metadata'):
                if field in annotation:
                    combined = row.setdefault(field, [])
                    for value in annotation[field]:
                        if value not in combined:
                            combined.append(deepcopy(value))
            if 'comment' in annotation:
                row.setdefault('comment', '')
        if comments:
            row['comment'] = comments[0][1] + ''.join('\n\n[' + label + '] ' + comment for label, comment in comments[1:])
        for field in list(row):
            decision = chosen.get((identity, scope, field))
            if decision:
                if decision[0] == 'clear':
                    row.pop(field)
                else:
                    row[field] = deepcopy(decision[1])
        rows.append(row)
    return rows, audit


def resolved_layer(plan, resolutions=None):
    rows, audit = resolve_entries(plan['entries'], resolutions)
    layer = validate_layer(target_layer(plan['preview']['layer'], plan['target'], rows), plan['target'])
    return layer, audit
