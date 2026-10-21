"""Reviewed customDataURL acquisition; inspect, consent, cache, bind. Flow: README.md."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit

from custom_sources import read_source, custom_catalog, collection_entries, cache_source
from navigator_fields import web_url
from navigator_integration import validate_layer, layer_version, import_preview, imported_document, document_layer

MAX_BUNDLE_BYTES = 128 * 1024 * 1024


def resolve_location(value, layer_path, origin=''):
    """A Path is explicitly local; strings from remote layers retain URL semantics."""
    explicit_local = isinstance(value, Path)
    if explicit_local:
        value = str(value)
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Enter a Bundle URL or local JSON path.')
    value = value.strip()
    if any(ord(char) < 32 for char in value):
        raise ValueError('Source locations cannot contain control characters.')
    if explicit_local:
        path = Path(value).expanduser()
        return str((path if path.is_absolute() else Path(layer_path).resolve().parent / path).resolve())
    if re.match(r'^[A-Za-z]:[\\/]', value) or value.startswith('\\\\'):
        return str(Path(value).expanduser().resolve())
    scheme = urlsplit(value).scheme
    if scheme:
        return web_url(value)
    if origin:
        return web_url(urljoin(web_url(origin), value))
    if value.startswith('//'):
        raise ValueError('A protocol-relative URL needs the original layer URL.')
    path = Path(value).expanduser()
    return str((path if path.is_absolute() else Path(layer_path).resolve().parent / path).resolve())


def inspect_source(root, layer, version, location, layer_path, notify, origin='', policy='enabled',
                   limit=MAX_BUNDLE_BYTES):
    """No cache writes: a candidate is not accepted just because it downloaded."""
    layer = validate_layer(deepcopy(layer))
    if layer_version(layer, version) != version:
        raise ValueError('The Bundle must match the recorded ATT&CK version.')
    location = resolve_location(location, layer_path, origin)
    notify(f'Input source: {location}', 0, 0)
    notify('Output files: None (custom source review in memory; cache only after acceptance)', 0, 0)
    notify('[Custom Data 1/5] Acquiring the selected source', 0, 5)
    details = {}
    payload, data, source = read_source(location, notify, limit, details)
    notify('[Custom Data 2/5] Checking source type and dataset identity', 1, 5)
    entries = collection_entries(payload, details['final'])
    if entries:
        notify('[Custom Data 2/5] Collection Index ready; choose a Bundle explicitly', 2, 5)
        return {'entries': entries, 'transport': details}
    digest = sha256(data).hexdigest()
    # A digest-named cache is evidence only when its bytes match its name.
    path = Path(source)
    if not source.startswith(('http://', 'https://')) and path.parent == Path(root).resolve() / 'custom':
        if re.fullmatch(r'[0-9a-f]{64}', path.stem) and path.stem != digest:
            raise ValueError('Cached Bundle SHA-256 does not match its filename; choose another source.')
    declared = layer.get('customDataURL', '')
    provenance = resolve_location(declared, layer_path, origin) if declared else source
    catalog = custom_catalog(payload, digest, provenance, version, notify).for_domain(layer['domain'])
    if catalog.version != version:
        raise ValueError('Bundle release does not match this layer: expected ' + version + ', received ' + catalog.version)
    expected = layer.get('x_ttp_studio_dataset', '')
    candidate = deepcopy(layer)
    candidate.update(customDataURL=provenance, x_ttp_studio_dataset=digest)
    if catalog.domain not in ('enterprise-attack', 'mobile-attack', 'ics-attack'):
        candidate['x_ttp_studio_domain'] = catalog.domain_definitions[catalog.domain].payload()
    candidate['x_ttp_studio_source_review'] = {
        'declared_source': declared, 'resolved_source': provenance, 'acquired_from': source,
        'final_source': details['final'], 'previous_dataset_sha256': expected,
        'dataset_sha256': digest, 'changed_dataset_accepted': False}
    notify('[Custom Data 3/5] Validating domain, release, annotations and selection', 2, 5)
    preview = import_preview(candidate, catalog, policy)
    document_layer(imported_document(candidate, catalog, policy))
    cache = Path(root).resolve() / 'custom' / (digest + '.json')
    notify('[Custom Data 3/5] Candidate verified; awaiting explicit acceptance', 3, 5)
    return {'catalog': catalog, 'layer': candidate, 'preview': preview, 'data': data,
            'digest': digest, 'expected': expected, 'changed': bool(expected and expected != digest),
            'transport': details, 'cache': cache}


def accept_source(root, candidate, notify, allow_changed=False):
    """Publish verified bytes and a reviewed binding; never modify the input layer/file."""
    if candidate.get('changed') and not allow_changed:
        raise ValueError('The dataset has changed. Explicitly approve replacement or choose the original Bundle.')
    if sha256(candidate['data']).hexdigest() != candidate['digest']:
        raise ValueError('Reviewed source bytes changed; inspect the source again.')
    notify('Input files: None (verified candidate bytes in memory)', 0, 0)
    notify(f'Output file: {candidate["cache"]}', 0, 0)
    notify('[Custom Data 4/5] Caching the accepted Bundle by SHA-256', 3, 5)
    path = cache_source(root, candidate['data'], notify)
    layer = deepcopy(candidate['layer'])
    layer['x_ttp_studio_source_review']['changed_dataset_accepted'] = bool(candidate['changed'] and allow_changed)
    notify('[Custom Data 5/5] Source accepted for this layer; no workspace documents added', 5, 5)
    return {'layer': layer, 'catalog': candidate['catalog'], 'preview': candidate['preview'], 'path': path}
