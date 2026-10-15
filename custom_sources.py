"""Bounded URL/file imports and isolated custom STIX catalogs. Workflow: README.md."""
from hashlib import sha256
import json
from pathlib import Path
import re
import uuid
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.parse import urljoin

from attack_catalog import Catalog, DOMAIN_LABELS, external_id, index_procedures, index_source_techniques, tactic_phases
from navigator_fields import web_url


class WebRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        web_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_source(location, notify, limit=128 * 1024 * 1024):
    remote = str(location).lower().startswith(('https://', 'http://'))
    source = web_url(str(location)) if remote else str(Path(location).expanduser().resolve())
    notify(f'Input {"URL" if remote else "file"}: {source}', 0, 0)
    notify('Output files: None (source validation in memory)', 0, 0)
    notify('[Source 1/4] Reading bounded JSON', 0, limit)
    if remote:
        stream = build_opener(WebRedirect()).open(Request(source, headers={'User-Agent': 'TTP-Selection-Studio'}), timeout=20)
    else:
        stream = Path(source).open('rb')
    data = bytearray()
    with stream:
        while chunk := stream.read(min(1024 * 1024, limit + 1 - len(data))):
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError(f'Source exceeds {limit // 1024 // 1024} MiB.')
            notify('[Source 1/4] Reading JSON bytes', len(data), limit)
    notify('[Source 2/4] Parsing JSON', 1, 4)
    try:
        payload = json.loads(data, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError('Source must be UTF-8/BOM or UTF-16 JSON.') from error
    return payload, bytes(data), source


def cache_source(root, data, notify):
    folder = Path(root).resolve() / 'custom'
    target = folder / (sha256(data).hexdigest() + '.json')
    notify(f'Output file: {target}', 0, 0)
    notify('[Source 4/4] Caching validated input', 3, 4)
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / ('.source-' + uuid.uuid4().hex + '.tmp')
    notify(f'Output temporary file: {temporary.resolve()}', 0, 0)
    try:
        with temporary.open('xb') as stream:
            stream.write(data)
        if target.exists() and target.read_bytes() == data:
            temporary.unlink()
        else:
            temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    notify('[Source 4/4] Validated source cached', 4, 4)
    return target


def collection_entries(payload, base):
    """An ATT&CK Collection Index offers explicit version choices, never auto-fetches them."""
    if not isinstance(payload, dict) or 'collections' not in payload:
        return []
    if not isinstance(payload['collections'], list):
        raise ValueError('Collection Index collections must be a list.')
    entries = []
    for collection in payload['collections']:
        if not isinstance(collection, dict) or not isinstance(collection.get('versions'), list):
            raise ValueError('Invalid Collection Index versions.')
        name = collection.get('name', collection.get('id', 'Collection'))
        if not isinstance(name, str):
            raise ValueError('Collection names/IDs must be text.')
        for version in collection['versions']:
            if len(entries) >= 1000:
                raise ValueError('Collection Index exceeds 1,000 version choices.')
            if not isinstance(version, dict) or not isinstance(version.get('version'), str):
                raise ValueError('Collection version must be text.')
            url = version.get('url', '')
            if not isinstance(url, str):
                raise ValueError('Collection version URL must be text.')
            if str(base).startswith(('http://', 'https://')):
                url = urljoin(base, url)
            web_url(url)
            entries.append({'name': name,
                            'version': version['version'], 'url': url})
    if not entries:
        raise ValueError('Collection Index has no accessible version entries.')
    return entries


def custom_catalog(payload, digest, source, version, notify):
    notify('Input bundle: validated JSON in memory; output files: None (custom catalog in memory)', 0, 0)
    notify('[Source 3/4] Validating ATT&CK-compatible STIX', 0, 4)
    if not isinstance(payload, dict) or payload.get('type') != 'bundle' or not isinstance(payload.get('objects'), list):
        raise ValueError('Expected a STIX Bundle containing ATT&CK tactics, matrix and techniques; standalone collections need their referenced Bundle.')
    objects = payload['objects']
    if not 1 <= len(objects) <= 200000:
        raise ValueError('STIX Bundle must contain 1–200,000 objects.')
    latest = {}
    for index, obj in enumerate(objects, 1):
        if not isinstance(obj, dict) or not isinstance(obj.get('id'), str) or not isinstance(obj.get('type'), str):
            raise ValueError('Every STIX object needs text id and type.')
        identity = obj['id']
        if not identity.startswith(obj['type'] + '--'):
            raise ValueError('STIX object id must match its type.')
        try:
            uuid.UUID(identity.split('--', 1)[1])
        except ValueError as error:
            raise ValueError('STIX object id must end in a UUID: ' + identity) from error
        for field in ('name', 'description', 'modified', 'x_mitre_shortname', 'x_mitre_version'):
            if field in obj and not isinstance(obj[field], str):
                raise ValueError(f'{identity}: {field} must be text.')
        for field in ('revoked', 'x_mitre_deprecated', 'x_mitre_is_subtechnique'):
            if field in obj and type(obj[field]) is not bool:
                raise ValueError(f'{identity}: {field} must be a boolean.')
        for field in ('x_mitre_domains', 'x_mitre_platforms', 'tactic_refs', 'aliases'):
            if field in obj and (not isinstance(obj[field], list) or any(not isinstance(v, str) for v in obj[field])):
                raise ValueError(f'{identity}: {field} must be a list of text.')
        for field in ('kill_chain_phases', 'external_references'):
            if field in obj and (not isinstance(obj[field], list) or any(not isinstance(v, dict) for v in obj[field])):
                raise ValueError(f'{identity}: {field} must be an object list.')
        for phase in obj.get('kill_chain_phases', []):
            if any(not isinstance(phase.get(k), str) for k in ('kill_chain_name', 'phase_name')):
                raise ValueError('Invalid kill-chain phase.')
        for ref in obj.get('external_references', []):
            if any(k in ref and not isinstance(ref[k], str) for k in ('source_name', 'external_id', 'url', 'description')):
                raise ValueError('Invalid external reference.')
        if obj['type'] == 'relationship' and any(not isinstance(obj.get(k), str) for k in ('source_ref', 'target_ref', 'relationship_type')):
            raise ValueError('Invalid STIX relationship.')
        old = latest.get(identity)
        if old is None or obj.get('modified', '') > old.get('modified', ''):
            latest[identity] = obj
        elif obj.get('modified', '') == old.get('modified', '') and obj != old:
            raise ValueError('Conflicting duplicate STIX object version: ' + identity)
        if index % 2000 == 0:
            notify('[Source 3/4] Validating STIX objects', index, len(objects))
    objects = list(latest.values())
    versions = {o['x_mitre_version'] for o in objects if o['type'] == 'x-mitre-collection' and 'x_mitre_version' in o}
    if len(versions) > 1:
        raise ValueError('Collections must have a single common release version.')
    version = next(iter(versions), version).removeprefix('v')
    if not re.fullmatch(r'\d+(?:\.\d+)?', version):
        raise ValueError('Enter a numeric release version for this custom Bundle (for example 19.2).')
    if '.' not in version:
        version += '.0'
    active = [o for o in objects if not o.get('revoked') and not o.get('x_mitre_deprecated')]
    stores, procedures, source_rows, parents, raw = {}, {}, {}, {}, {}
    domains = []
    for domain in DOMAIN_LABELS:
        scoped = [o for o in objects if domain in o.get('x_mitre_domains', []) or o['type'] == 'relationship']
        mapped = [o for o in active if domain in o.get('x_mitre_domains', []) or o['type'] == 'relationship']
        records = {o['id']: o for o in mapped if o['type'] == 'attack-pattern'}
        if records:
            ids = [external_id(o) for o in records.values()]
            if any(not re.fullmatch(r'T\d{4}(?:\.\d{3})?', value) for value in ids) or len(ids) != len(set(ids)):
                raise ValueError('Custom techniques require unique ATT&CK-compatible T#### or T####.### external IDs per domain.')
            if any(('.' in external_id(o)) != bool(o.get('x_mitre_is_subtechnique')) for o in records.values()):
                raise ValueError('Sub-technique ID format must match x_mitre_is_subtechnique.')
            tactics = {o['x_mitre_shortname']: o for o in mapped if o['type'] == 'x-mitre-tactic' and o.get('x_mitre_shortname')}
            if len(tactics) != sum(o['type'] == 'x-mitre-tactic' for o in mapped):
                raise ValueError('Tactic short names must be non-empty and unique within each domain.')
            matrices = [o for o in mapped if o['type'] == 'x-mitre-matrix']
            if not tactics or not matrices:
                raise ValueError(domain + ' needs x-mitre-tactic and x-mitre-matrix objects with x_mitre_domains.')
            tactic_ids = {o['id'] for o in tactics.values()}
            if any(set(o.get('tactic_refs', [])) - tactic_ids for o in matrices):
                raise ValueError('Matrix tactic_refs must resolve within the custom domain.')
            if any(not tactic_phases(o, domain) or tactic_phases(o, domain) - tactics.keys() or not o.get('name') for o in records.values()):
                raise ValueError('Every custom technique needs a name and valid domain tactic mappings.')
            if any(not o.get('name') for o in mapped if o['type'] != 'relationship'):
                raise ValueError('Custom catalog objects need names for browsing.')
            family_refs = {}
            for relation in mapped:
                if relation['type'] == 'relationship' and relation.get('relationship_type') == 'subtechnique-of':
                    child, parent = relation['source_ref'], relation['target_ref']
                    if child in records:
                        if parent not in records or family_refs.get(child, parent) != parent:
                            raise ValueError('Every active sub-technique must resolve to exactly one active parent.')
                        family_refs[child] = parent
            domains.append(domain)
        raw[domain] = {o['id']: o for o in scoped}
        stores[domain] = {o['id']: o for o in mapped if o['type'] != 'relationship'}
        procedures[domain] = index_procedures(scoped, stores[domain], notify, domain)
        source_rows[domain], parents[domain] = index_source_techniques(scoped, stores[domain], notify, domain)
        for child, parent in parents[domain].items():
            if child == parent or parent in parents[domain]:
                raise ValueError('Sub-technique relationships must be a single level without cycles.')
            if not records[child].get('x_mitre_is_subtechnique') or records[parent].get('x_mitre_is_subtechnique'):
                raise ValueError('Invalid sub-technique parent relationship.')
        if any(o.get('x_mitre_is_subtechnique') and o['id'] not in parents[domain] for o in records.values()):
            raise ValueError('Every active sub-technique needs an active parent in its domain.')
    if not domains:
        raise ValueError('No active ATT&CK-compatible techniques found.')
    catalog = Catalog(version, {}, {}, [], {}, {}, stores, procedures, source_rows, parents, domain='',
                      all_objects_by_domain=raw, dataset_id=digest, custom_source=source)
    return catalog.for_domain(domains[0])


def load_custom(root, location, version, notify):
    notify(f'Output cache directory: {Path(root).resolve() / "custom"}', 0, 0)
    payload, data, source = read_source(location, notify)
    entries = collection_entries(payload, source)
    if entries:
        return {'entries': entries, 'source': source}
    catalog = custom_catalog(payload, sha256(data).hexdigest(), source, version, notify)
    path = cache_source(root, data, notify)
    return {'catalog': catalog, 'path': path}


def load_layer_url(root, location, notify):
    notify(f'Output cache directory: {Path(root).resolve() / "custom"}', 0, 0)
    from navigator_integration import validate_layer
    payload, data, _ = read_source(web_url(location), notify, 10 * 1024 * 1024)
    layers = payload if isinstance(payload, list) else [payload]
    if not 1 <= len(layers) <= 20:
        raise ValueError('Use 1–20 Navigator layers.')
    for layer in layers:
        validate_layer(layer)
    return {'path': cache_source(root, data, notify)}
