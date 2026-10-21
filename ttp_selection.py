"""Selection preferences and tactic occurrence set operations. Workflow: README.md."""
from attack_catalog import tactic_phases

DEFAULT_PREFERENCES = {'across_tactics': True, 'with_family': False, 'visible_only': False}


def phases(catalog, key):
    return tactic_phases(catalog.records[key], catalog.domain) & catalog.tactics.keys()


def is_selected(selected, scopes, key, tactic):
    return key in selected and (key not in scopes or tactic in scopes[key])


def selected_cells(document):
    return {(key, slug) for key in document.selected if key in document.catalog.records
            for slug in document.selection_scopes.get(key, phases(document.catalog, key))
            if slug in phases(document.catalog, key)}


def family_keys(catalog, keys):
    roots = {catalog.parents.get(key, key) for key in keys}
    return set(keys) | (roots & catalog.records.keys()) | {key for key, parent in catalog.parents.items() if parent in roots}


def expand_cells(document, cells):
    result = set()
    prefs, catalog = document.selection_preferences, document.catalog
    for key, slug in cells:
        if key not in catalog.records or slug not in phases(catalog, key):
            continue
        keys = family_keys(catalog, {key}) if prefs['with_family'] else {key}
        for target in keys:
            result.update((target, s) for s in phases(catalog, target)
                          if prefs['across_tactics'] or s == slug)
    return result


def assign_cells(document, cells):
    """Compress all-tactic selection into the legacy set, retaining only partial overrides."""
    grouped = {}
    for key, slug in cells:
        if key in document.catalog.records and slug in phases(document.catalog, key):
            grouped.setdefault(key, set()).add(slug)
    document.selected = set(grouped)
    document.selection_scopes = {key: sorted(slugs) for key, slugs in grouped.items()
                                 if slugs != phases(document.catalog, key)}


def change_cells(document, cells, action, annotated=(), expand=True, visible=None):
    before = selected_cells(document)
    targets = expand_cells(document, cells) if expand else set(cells)
    if document.selection_preferences.get('visible_only', False):
        if visible is None:
            raise ValueError('Visible-only selection requires an explicit visible occurrence scope.')
        targets.intersection_update(visible)
    annotated = set(annotated) & targets
    choices = {'add': before | targets, 'remove': before - targets, 'replace': targets,
               'invert': before ^ targets, 'annotated': annotated, 'unannotated': targets - annotated}
    if action not in choices:
        raise ValueError('Unknown occurrence selection action.')
    assign_cells(document, choices[action])
    return before != selected_cells(document)


def validate_selection_scopes(value, selected, catalog):
    if not isinstance(value, dict) or set(value) - set(selected):
        raise ValueError('Partial selection scopes must belong to included TTPs.')
    result = {}
    for key, slugs in value.items():
        if not isinstance(slugs, list) or not slugs or any(not isinstance(s, str) for s in slugs) or len(set(slugs)) != len(slugs):
            raise ValueError('Partial selection scopes need unique non-empty tactic names.')
        if set(slugs) - phases(catalog, key):
            raise ValueError('Partial selection contains an unmapped tactic.')
        if set(slugs) != phases(catalog, key):
            result[key] = sorted(slugs)
    return result


def validate_preferences(value):
    if (not isinstance(value, dict) or set(value) - set(DEFAULT_PREFERENCES)
            or not {'across_tactics', 'with_family'} <= set(value)
            or any(type(v) is not bool for v in value.values())):
        raise ValueError('Selection preferences require boolean across_tactics, with_family and optional visible_only.')
    return {**DEFAULT_PREFERENCES, **value}
