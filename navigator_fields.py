"""Navigator presentation and structured annotations. Workflow: README.md."""
from urllib.parse import urlsplit


def web_url(value):
    if not isinstance(value, str) or any(ord(c) < 32 for c in value):
        raise ValueError('Enter an absolute HTTP or HTTPS URL.')
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Use an absolute HTTP(S) URL without embedded credentials.')
    # Accessing port also checks malformed ports.
    parsed.port
    return value


def validate_fields(owner):
    for field, keys in (('links', ('label', 'url')), ('metadata', ('name', 'value'))):
        entries = owner.get(field, [])
        if not isinstance(entries, list) or len(entries) > 500:
            raise ValueError(field + ' must contain at most 500 entries.')
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(field + ' entries must be objects.')
            if entry.get('divider') is True:
                continue
            if any(not isinstance(entry.get(key), str) for key in keys):
                raise ValueError(field + ' entries require text ' + ' and '.join(keys) + '.')


def presentation(layer):
    return (layer.get('layout', {}).get('layout', 'flat'), layer.get('sorting', 0),
            layer.get('filters', {}).get('platforms'))


def sorted_families(catalog, slug, families, appearance, sorting):
    from attack_catalog import external_id
    def key(identity):
        record = catalog.records[identity]
        name = record['name'].casefold()
        if sorting < 2:
            return (name, external_id(record))
        # A color overlay has no combined score. Sort by the active layer's
        # score/aggregate so toggling all colors cannot erase score ordering.
        source = getattr(appearance, 'active', appearance)
        style = source.cell(external_id(record), slug)
        score = style.get('aggregateScore')
        if score is None:
            score = style.get('score') or 0
        return (score, name, external_id(record))
    return [{**family, 'children': sorted(family['children'], key=key, reverse=sorting in (1, 3))}
            for family in sorted(families, key=lambda row: key(row['key']), reverse=sorting in (1, 3))]


def set_presentation(document, layout, sorting, platforms):
    from navigator_integration import document_layer, validate_layer
    layer = document_layer(document, validate=False)
    layer.setdefault('layout', {})['layout'] = layout
    layer['sorting'] = sorting
    if platforms is None:
        layer.setdefault('filters', {}).pop('platforms', None)
        if not layer['filters']:
            layer.pop('filters')
    else:
        layer.setdefault('filters', {})['platforms'] = list(platforms)
    document.navigator_layer = validate_layer(layer)

