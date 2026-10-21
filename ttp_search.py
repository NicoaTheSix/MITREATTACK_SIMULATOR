"""Version-local literal TTP search, including detection-backed data sources. Flow: README.md."""
from attack_catalog import external_id

SEARCH_FIELDS = ('name', 'id', 'description', 'data_sources', 'detection_strategies')
DEFAULT_SEARCH_FIELDS = ['name', 'id']


def source_search_text(obj, descriptions=False, fields=None):
    """One literal search field; display labels remain the object's name and ID."""
    fields = fields if fields is not None else ('name','id','description') if descriptions else ('name','id')
    values = {'name':obj.get('name',''), 'id':external_id(obj), 'description':obj.get('description','')}
    return '\n'.join(values[field] for field in fields)


def validate_search_fields(value):
    if not isinstance(value, list) or not value or any(not isinstance(v, str) for v in value) or len(value) != len(set(value)) or set(value) - set(SEARCH_FIELDS):
        raise ValueError('Choose one or more supported search fields.')
    return [field for field in SEARCH_FIELDS if field in value]


def search_index(catalog, notify=lambda *args: None):
    cached = getattr(catalog, '_ttp_search_index', None)
    if cached is not None:
        return cached
    notify('Input files: None (exact domain/version catalog in memory); output files: None', 0, 0)
    notify('[Search Index 1/3] Reading legacy data sources and active detection mappings', 0, 3)
    raw = catalog.all_objects_by_domain.get(catalog.domain, {}) or catalog.objects_by_domain[catalog.domain]
    objects = raw if isinstance(raw, dict) else {o['id']: o for o in raw}
    def active(o):
        return not o.get('revoked') and not o.get('x_mitre_deprecated')
    def source_text(identity, seen=None):
        seen = set() if seen is None else seen
        if identity in seen or len(seen) > 1000:
            return []
        seen.add(identity)
        obj = objects.get(identity, {})
        parts = []
        kind = obj.get('type')
        if kind in ('x-mitre-analytic','x-mitre-detection-strategy') and not active(obj):
            return []
        if kind in ('x-mitre-data-source', 'x-mitre-data-component'):
            parts += [obj.get('name', ''), external_id(obj)]
        refs = []
        if kind == 'x-mitre-detection-strategy':
            refs += obj.get('x_mitre_analytic_refs', [])
        if kind == 'x-mitre-data-component' and obj.get('x_mitre_data_source_ref'):
            refs.append(obj['x_mitre_data_source_ref'])
        for field in ('x_mitre_log_source_references', 'x_mitre_log_sources'):
            for row in obj.get(field, []):
                if not isinstance(row, dict):
                    continue
                parts += [row.get('name', ''), row.get('channel', '')]
                if row.get('x_mitre_data_component_ref'):
                    refs.append(row['x_mitre_data_component_ref'])
        for ref in refs:
            if isinstance(ref, str):
                parts += source_text(ref, seen)
        return [p for p in parts if isinstance(p, str)]
    sources = {key: list(obj.get('x_mitre_data_sources', [])) for key, obj in catalog.records.items()}
    strategies = {key: [] for key in catalog.records}
    for edge in objects.values():
        if edge.get('type') != 'relationship' or edge.get('relationship_type') != 'detects' or not active(edge):
            continue
        source, target = objects.get(edge.get('source_ref'), {}), edge.get('target_ref')
        if target in sources and active(source) and source.get('type') in ('x-mitre-data-component', 'x-mitre-detection-strategy'):
            sources[target] += source_text(source['id'])
            if (source.get('type') == 'x-mitre-detection-strategy' and
                    (not source.get('x_mitre_domains') or catalog.domain in source['x_mitre_domains'])):
                strategies[target].extend(source_search_text(source, descriptions=True).splitlines())
    notify('[Search Index 2/3] Building name/ID/description/data-source/detection-strategy fields', 1, 3)
    result = {key: {'name':obj.get('name', '').casefold(), 'id':external_id(obj).casefold(),
                    'description':obj.get('description', '').casefold(),
                    'data_sources':'\n'.join(dict.fromkeys(p for p in sources[key] if isinstance(p, str))).casefold(),
                    'detection_strategies':'\n'.join(dict.fromkeys(strategies[key])).casefold()}
              for key, obj in catalog.records.items()}
    catalog._ttp_search_index = result
    notify(f'[Search Index 3/3] Ready: {len(result)} techniques in {catalog.domain} v{catalog.version}', 3, 3)
    return result


def matches(catalog, key, query, fields=DEFAULT_SEARCH_FIELDS):
    query = query.strip().casefold()
    return not query or any(query in search_index(catalog).get(key, {}).get(field, '') for field in fields)
