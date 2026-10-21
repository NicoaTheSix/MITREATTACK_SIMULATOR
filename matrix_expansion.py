"""Saved per-parent/tactic expansion without changing annotations. Workflow: README.md."""
from copy import deepcopy
from attack_catalog import external_id, tactic_phases
from navigator_integration import document_layer, validate_layer
from navigator_visuals import LayerAppearance


def expanded_family(appearance, catalog, key, slug, children, mini=False):
    """Global policy takes precedence; absent policy uses explicit row flags."""
    active = getattr(appearance,'active',appearance)
    mode = active.layer.get('layout',{}).get('expandedSubtechniques')
    if mode == 'all': return True
    if mode == 'none': return False
    if mode == 'annotated':
        return any(appearance.cell(external_id(catalog.records[child]),slug).get('annotated') for child in children)
    identity = external_id(catalog.records[key])
    row = active.rows.get((identity,slug),active.rows.get((identity,''),{}))
    return row.get('showSubtechniques',mini)


def save_family_expansion(document, key, slug, expanded, observed=(), mini=False, notify=lambda *args:None):
    """Freeze a global policy into explicit rows, then change just the clicked family."""
    catalog = document.catalog
    if type(expanded) is not bool or key not in catalog.records or slug not in catalog.tactics:
        raise ValueError('Choose a parent technique, mapped tactic and boolean expansion state.')
    children = {}
    for child,parent in catalog.parents.items():
        for phase in tactic_phases(catalog.records[child],catalog.domain) & catalog.tactics.keys():
            children.setdefault((parent,phase),[]).append(child)
    if (key,slug) not in children:
        raise ValueError('This parent has no mapped sub-techniques in that tactic.')
    layer = document_layer(document,validate=False)
    appearance = LayerAppearance(layer,catalog)
    global_mode = layer.get('layout',{}).get('expandedSubtechniques')
    observed = dict(observed)
    identities = list(children) if global_mode is not None else [(key,slug)]
    rows = layer.setdefault('techniques',[])
    index = {(row['techniqueID'],row.get('tactic','')):row for row in rows}
    for number,(parent,phase) in enumerate(identities,1):
        identity = external_id(catalog.records[parent])
        state = expanded if (parent,phase)==(key,slug) else observed.get((parent,phase),
            expanded_family(appearance,catalog,parent,phase,children[parent,phase],mini))
        row = index.get((identity,phase))
        if row is None:
            # A scoped expansion flag must not mask an inherited global annotation.
            row = deepcopy(index.get((identity,''),{}))
            row.update(techniqueID=identity,tactic=phase)
            rows.append(row)
            index[identity,phase] = row
        row['showSubtechniques'] = state
        if number % 50 == 0 or number == len(identities):
            notify('[Family Expansion 2/3] Preserving per-tactic family states',number,len(identities))
    layer.setdefault('layout',{}).pop('expandedSubtechniques',None)
    validated = validate_layer(layer)
    changed = validated != document.navigator_layer
    if changed: document.navigator_layer = validated
    return changed
