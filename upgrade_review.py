"""Complete identity review for catalog upgrades. Workflow: README.md."""
from copy import deepcopy

from attack_catalog import external_id, tactic_phases
from matrix_display import annotation_flags

CATEGORIES = ('Added', 'Changed', 'Removed', 'Replaced', 'Unchanged')


def classify_upgrade(document, target, rows, replacements, notify):
    before = {external_id(obj): obj for obj in document.catalog.records.values()}
    after = {external_id(obj): obj for obj in target.records.values()}
    linked = {}
    for index, row in enumerate(rows):
        linked.setdefault(row['source_id'], []).append(index)
    identities = sorted(before.keys() | after.keys() | linked.keys())
    items = []
    for index, identity in enumerate(identities, 1):
        old, new = before.get(identity, {}), after.get(identity, {})
        category = ('Unchanged' if old == new else 'Changed') if old and new else (
            'Added' if new else 'Replaced' if replacements.get(identity) else 'Removed')
        target_id = identity if new else replacements.get(identity, '')
        target_record = after.get(target_id, {})
        indices = linked.get(identity, [])
        items.append({'id': identity, 'category': category, 'source_name': old.get('name', ''),
                      'target_id': target_id, 'target_name': target_record.get('name', ''),
                      'row_indices': indices,
                      'annotated': any(annotation_flags(rows[i]['annotation'])['annotated'] for i in indices),
                      'reviewed': category == 'Unchanged' and all(rows[i]['reviewed'] for i in indices),
                      'changes': [{'field': field, 'before': old.get(field), 'after': target_record.get(field)}
                                  for field in sorted(old.keys() | target_record.keys())
                                  if old.get(field) != target_record.get(field)]})
        if index % 100 == 0:
            notify('[Upgrade 1/3] Classifying all technique identities', index, len(identities))
    return items


def validate_reviews(preview, target, reviews):
    """Require every identity, including items hidden by UI filters, to be reviewed."""
    items = {item['id']: item for item in preview['items']}
    if reviews is None:
        reviews = [{'id': item['id'], 'reviewed': item['reviewed']} for item in preview['items']]
    if not isinstance(reviews, list) or any(not isinstance(r, dict) or not isinstance(r.get('id'), str) for r in reviews):
        raise ValueError('Technique reviews must be a list of identity decisions.')
    if len(reviews) != len(items) or {r['id'] for r in reviews} != set(items):
        raise ValueError('Review every technique exactly once, including hidden items.')
    ids = {external_id(obj): obj for obj in target.records.values()}
    audit, additions, selection = [], [], set()
    for review in reviews:
        identity = review['id']
        item = items[identity]
        if review.get('reviewed') is not True:
            raise ValueError(f'Review {identity} ({item["category"]}) before creating the layer.')
        annotations = review.get('annotation_rows', [])
        scopes = review.get('selected_scopes', [])
        if not isinstance(annotations, list) or not isinstance(scopes, list):
            raise ValueError('Added annotations and selected scopes must be lists.')
        if item['category'] != 'Added' and scopes:
            raise ValueError('Only Added items accept new explicit selection in this review.')
        annotation_id = item['target_id']
        if annotations and annotation_id not in ids:
            raise ValueError('Choose an active target before editing target annotations.')
        seen = set()
        phases = set(tactic_phases(ids.get(annotation_id, {}), target.domain))
        for row in annotations:
            if not isinstance(row, dict) or row.get('techniqueID') != annotation_id:
                raise ValueError('An added annotation must belong to its reviewed technique.')
            scope = row.get('tactic', '')
            if not isinstance(scope, str) or (scope and scope not in phases) or scope in seen:
                raise ValueError('Choose a valid, unique tactic for each added annotation.')
            seen.add(scope)
            additions.append(deepcopy(row))
        if any(not isinstance(scope, str) or scope not in phases for scope in scopes) or len(set(scopes)) != len(scopes):
            raise ValueError('Choose valid, unique tactic occurrences for added selection.')
        selection.update((identity, scope) for scope in scopes)
        audit.append({'id': identity, 'category': item['category'], 'reviewed': True,
                      'action': ('Annotate / include' if annotations or scopes else 'Skip added')
                                if item['category'] == 'Added' else 'Edited target' if annotations else 'Reviewed',
                      'annotation_rows': deepcopy(annotations), 'selected_scopes': list(scopes)})
    return audit, additions, selection


def merge_annotation(rows, row, origin):
    identity, scope = row['techniqueID'], row.get('tactic', '')
    key = (identity, scope)
    if key not in rows:
        rows[key] = deepcopy(row)
        return
    previous = rows[key]
    for field in (previous.keys() | row.keys()) - {'comment', 'metadata', 'links', 'techniqueID', 'tactic'}:
        if field in previous and field in row and previous[field] != row[field]:
            raise ValueError(f'Conflicting {field} at {identity}/{scope or "All tactics"}; drop or remap one source row.')
    merged = {**previous, **deepcopy(row)}
    comments = [previous.get('comment', ''), row.get('comment', '')]
    if comments[0] and comments[1] and comments[0] != comments[1]:
        merged['comment'] = comments[0] + '\n\n[' + origin + '] ' + comments[1]
    elif any(comments):
        merged['comment'] = next(c for c in comments if c)
    for field in ('metadata', 'links'):
        combined = []
        for entry in previous.get(field, []) + row.get(field, []):
            if entry not in combined:
                combined.append(deepcopy(entry))
        if combined:
            merged[field] = combined
    rows[key] = merged
