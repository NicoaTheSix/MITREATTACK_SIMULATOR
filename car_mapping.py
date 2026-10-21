"""Native CAR coverage resolution without parent/sibling expansion. Workflow: README.md."""
from attack_catalog import external_id, tactic_phases


def resolve_technique(catalog, identity, tactics=()):
    active = {external_id(v): (k, v) for k, v in catalog.records.items()}
    key, obj = active.get(identity, ('', {}))
    status = 'Resolved'
    if not obj:
        obj = next((o for o in catalog.all_objects_by_domain.get(catalog.domain, {}).values()
                    if o.get('type') == 'attack-pattern' and external_id(o) == identity), {})
        status = 'Revoked' if obj.get('revoked') else 'Deprecated' if obj.get('x_mitre_deprecated') else 'Unresolved in current dataset'
    phases = tactic_phases(obj, catalog.domain) if obj else set()
    actual = {external_id(catalog.tactics[s]) for s in phases if s in catalog.tactics}
    return {'id': identity, 'key': key, 'name': obj.get('name', identity), 'status': status,
            'tactic_mismatch': sorted(set(tactics) - actual), 'domain': catalog.domain, 'version': catalog.version,
            'dataset_sha256': catalog.dataset_id}


def related_analytics(car, identity):
    if '.' in identity:
        return [(identity, key) for key in car.groups.get((identity.split('.')[0], identity), ())]
    return [(scope or 'N/A — technique only', key) for (parent, scope), keys in sorted(car.groups.items())
            if parent == identity for key in keys]
