"""Studio document IO and recoverable workspace snapshots. Workflow: README.md."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import uuid

from attack_catalog import DOMAIN_LABELS, external_id, load_catalog
from attack_versions import snapshot_pointer
from custom_sources import custom_catalog
from navigator_integration import validate_layer, write_json_atomic
from ttp_documents import TTPDocument, document_payload, validate_document_name, utc_now
from layer_analysis import snapshot_document
from ttp_selection import validate_preferences, validate_selection_scopes, DEFAULT_PREFERENCES
from ttp_search import validate_search_fields, DEFAULT_SEARCH_FIELDS
from domain_model import valid_domain, identifier_pattern
from framework_io import FrameworkSelection, selection, framework_payload, read_framework_document

LIMIT = 64 * 1024 * 1024


def read_json(path, notify, limit=LIMIT):
    path = Path(path).expanduser().resolve()
    notify(f'Input file: {path}', 0, 0)
    notify('Output files: None (validated draft in memory)', 0, 0)
    notify('[Studio Open 1/4] Reading bounded UTF-8 JSON', 0, 4)
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f'JSON exceeds {limit // (1024 * 1024)} MiB.')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON property: ' + key)
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('Non-finite JSON number: ' + value)
    payload = json.loads(data.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=nonfinite)
    # Also catches overflow such as 1e999.
    json.dumps(payload, allow_nan=False)
    return payload, sha256(data).hexdigest()


def strings(value, label, pattern=None):
    if not isinstance(value, list) or len(value) > 20000 or any(not isinstance(v, str) for v in value):
        raise ValueError(label + ' must be a list of at most 20,000 strings.')
    if len(value) != len(set(value)) or (pattern and any(not re.fullmatch(pattern, v) for v in value)):
        raise ValueError('Duplicate or invalid ' + label)
    return value


class StudioReader:
    """Resolve exact cached datasets; a saved file never initiates a network fetch."""
    def __init__(self, root, notify):
        self.root, self.notify = Path(root).resolve(), notify
        self.catalogs = {}

    def catalog(self, attack):
        if not isinstance(attack, dict) or not valid_domain(attack.get('domain')):
            raise ValueError('Missing or unknown ATT&CK domain.')
        version, digest = attack.get('version'), attack.get('dataset_sha256', '')
        if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+(?:\.\d+)?' if digest else r'\d+\.\d+', version):
            raise ValueError('Expected an exact ATT&CK version such as 19.2.')
        if not isinstance(digest, str) or (digest and not re.fullmatch(r'[0-9a-f]{64}', digest)):
            raise ValueError('Invalid custom dataset SHA-256.')
        if attack.get('custom') and not digest:
            raise ValueError('Custom datasets require their exact SHA-256 identity.')
        if attack.get('car_surface') is True:
            if version != '0.0' or digest or attack['domain'] != 'enterprise-attack':
                raise ValueError('Invalid CAR-only empty ATT&CK surface.')
            from car_documents import empty_catalog
            return empty_catalog()
        if attack['domain'] not in DOMAIN_LABELS and not digest:
            raise ValueError('A custom domain requires an exact custom Bundle SHA-256.')
        key = digest, version
        if key not in self.catalogs:
            self.notify('[Studio Open 2/4] Resolving exact dataset ' + version, 1, 4)
            try:
                if digest:
                    path = self.root / 'custom' / (digest + '.json')
                    bundle, actual = read_json(path, self.notify, 128 * 1024 * 1024)
                    if actual != digest:
                        raise ValueError('Cached custom Bundle SHA-256 mismatch.')
                    source = attack.get('source_url', '')
                    if not isinstance(source, str):
                        raise ValueError('Custom source must be text.')
                    catalog = custom_catalog(bundle, digest, source, version, self.notify)
                else:
                    catalog = load_catalog(self.root, self.notify, snapshot_pointer(self.root, version))
                if catalog.version != version:
                    raise ValueError('Cached Bundle release differs from the Studio document version.')
            except FileNotFoundError as error:
                raise ValueError(f'Missing cached ATT&CK {version}' + (f' Bundle {digest}' if digest else '')
                                 + '. Download that official version or load the matching custom Bundle first; then retry.') from error
            self.catalogs[key] = catalog
        catalog = self.catalogs[key].for_domain(attack['domain'])
        if digest:
            source = attack.get('source_url', '')
            if not isinstance(source, str):
                raise ValueError('Custom source must be text.')
            catalog = replace(catalog, custom_source=source)
        return catalog

    def layer(self, value, catalog):
        if not isinstance(value, dict):
            raise ValueError('Navigator annotations must be an object.')
        if not value:
            return {}
        result = validate_layer(value)
        if result['domain'] != catalog.domain:
            raise ValueError('Annotation domain does not match its archive.')
        version = result.get('versions', {}).get('attack')
        if version is not None and str(version) not in (catalog.version, catalog.version.removesuffix('.0')):
            raise ValueError('Annotation ATT&CK version does not match its archive.')
        if result.get('x_ttp_studio_dataset', catalog.dataset_id) != catalog.dataset_id:
            raise ValueError('Annotation dataset identity mismatch.')
        if result.get('customDataURL') and not catalog.dataset_id:
            raise ValueError('A custom layer cannot be restored onto official data.')
        if 'x_ttp_studio_domain' in result:
            definition = catalog.domain_definitions.get(catalog.domain)
            if definition is None or result['x_ttp_studio_domain'] != definition.payload():
                raise ValueError('Stored domain definition differs from its exact Bundle.')
        return result

    def selected(self, value, catalog):
        keys = set(strings(value, 'selected STIX IDs', r'attack-pattern--[0-9a-f-]{36}'))
        if keys - catalog.records.keys():
            raise ValueError('Selected TTPs are absent/inactive in the recorded dataset; no entries were discarded.')
        return keys

    def snapshots(self, value, attack):
        if not isinstance(value, dict) or len(value) > 100:
            raise ValueError('Invalid version archives (maximum 100).')
        result = deepcopy(value)
        for version, item in result.items():
            if not isinstance(item, dict):
                raise ValueError('Invalid version archive.')
            catalog = self.catalog({**attack, 'version': version})
            item['layer'] = self.layer(item.get('layer', {}), catalog)
            scopes = item.get('selection_scopes', {})
            checked = validate_selection_scopes(scopes, scopes.keys() if isinstance(scopes, dict) else [], catalog)
            if 'selection_scopes' in item:
                item['selection_scopes'] = checked
            strings(item.get('import_selected', []), 'archive import IDs', identifier_pattern(bool(catalog.dataset_id)))
        return result

    def document(self, payload):
        if isinstance(payload, dict) and 'studio_frameworks_version' in payload:
            return read_framework_document(self, payload)
        if not isinstance(payload, dict) or payload.get('schema_version') != '1.0':
            raise ValueError('Expected Studio schema_version 1.0. Use Import Navigator Layer for Navigator JSON.')
        name = payload.get('name', '')
        if not isinstance(name, str):
            raise ValueError('Document name must be text.')
        validate_document_name(name)
        identity = payload.get('document_id')
        if not isinstance(identity, str) or str(uuid.UUID(identity)) != identity:
            raise ValueError('Invalid Studio document UUID.')
        created = payload.get('created_at_utc')
        if not isinstance(created, str) or datetime.fromisoformat(created).utcoffset() is None:
            raise ValueError('Document creation time needs a timezone.')
        attack = payload.get('attack')
        catalog = self.catalog(attack)
        rows = payload.get('selected_ttps')
        if not isinstance(rows, list) or len(rows) > 20000 or any(not isinstance(row, dict) for row in rows):
            raise ValueError('Invalid selected_ttps list.')
        selected = self.selected([row.get('stix_id') for row in rows], catalog)
        ids = strings(payload.get('selected_technique_ids'), 'selected technique IDs', identifier_pattern(bool(catalog.dataset_id)))
        if type(payload.get('selected_count')) is not int or payload['selected_count'] != len(rows) or len(ids) != len(rows):
            raise ValueError('Selected TTP counts disagree.')
        if set(ids) != {row.get('technique_id') for row in rows} or any(
                external_id(catalog.records[row['stix_id']]) != row.get('technique_id') for row in rows):
            raise ValueError('Selected ATT&CK IDs and STIX IDs disagree.')
        self.notify('[Studio Open 3/4] Validating annotations and domain/version/migration archives', 2, 4)
        layer = self.layer(payload.get('navigator_layer', {}), catalog)
        imported = set(strings(payload.get('navigator_import_selected', ids), 'import selection IDs', identifier_pattern(bool(catalog.dataset_id))))
        snapshots = self.snapshots(payload.get('navigator_snapshots', {}), attack)
        domains = deepcopy(payload.get('domain_snapshots', {}))
        if not isinstance(domains, dict) or set(domains) - catalog.objects_by_domain.keys() or catalog.domain in domains:
            raise ValueError('Invalid inactive domain archives.')
        for domain, item in domains.items():
            if not isinstance(item, dict):
                raise ValueError('Invalid domain archive.')
            domain_attack = {**attack, 'domain': domain, 'version': item.get('version', catalog.version)}
            archived = self.catalog(domain_attack)
            self.selected(item.get('selected_stix_ids', []), archived)
            checked = validate_selection_scopes(item.get('selection_scopes', {}), item.get('selected_stix_ids', []), archived)
            if 'selection_scopes' in item:
                item['selection_scopes'] = checked
            item['navigator_layer'] = self.layer(item.get('navigator_layer', {}), archived)
            strings(item.get('navigator_import_selected', []), 'domain import IDs', identifier_pattern(bool(archived.dataset_id)))
            item['navigator_snapshots'] = self.snapshots(item.get('navigator_snapshots', {}), domain_attack)
        migrations = deepcopy(payload.get('migration_archives', []))
        if not isinstance(migrations, list) or len(migrations) > 100:
            raise ValueError('Invalid migration archives (maximum 100).')
        for item in migrations:
            if not isinstance(item, dict):
                raise ValueError('Invalid migration archive.')
            archived = self.catalog({'domain': item.get('domain'), 'version': item.get('version'),
                'dataset_sha256': item.get('dataset_id', ''), 'source_url': item.get('custom_source', '')})
            self.selected(item.get('selected_stix_ids', []), archived)
            item['layer'] = self.layer(item.get('layer', {}), archived)
            if 'selection_scopes' in item:
                item['selection_scopes'] = validate_selection_scopes(item['selection_scopes'],item.get('selected_stix_ids',[]),archived)
            strings(item.get('import_selected', []), 'migration import IDs', identifier_pattern(bool(archived.dataset_id)))
        document = TTPDocument(name, catalog, selected=selected, document_id=identity, created_at_utc=created,
            navigator_layer=layer, navigator_import_selected=imported, navigator_snapshots=snapshots,
            domain_snapshots=domains, migration_archives=migrations)
        document.selection_scopes = validate_selection_scopes(payload.get('selection_scopes', {}), selected, catalog)
        document.selection_preferences = validate_preferences(payload.get('selection_preferences', {
            'across_tactics':layer.get('selectTechniquesAcrossTactics',True),
            'with_family':layer.get('selectSubtechniquesWithParent',False),
            'visible_only':layer.get('selectVisibleTechniques',False)}))
        document.search_fields = validate_search_fields(payload.get('search_fields', DEFAULT_SEARCH_FIELDS))
        if 'car_workspace' in payload:
            from car_documents import validate_workspace
            document.car_workspace = validate_workspace(payload['car_workspace'])
        atlas = payload.get('atlas_workspace')
        if atlas is not None:
            if (not isinstance(atlas, dict) or not isinstance(atlas.get('attack'), dict) or 'atlas_workspace' in atlas
                    or atlas.get('attack', {}).get('domain') != 'atlas-atlas'
                    or catalog.domain == 'atlas-atlas'):
                raise ValueError('Invalid ATLAS workplace extension; nested workplaces are not supported.')
            document.atlas_document = self.document(atlas)
        self.notify('[Studio Open 4/4] Complete; validated document ready in memory', 4, 4)
        return document


def open_studio(root, path, notify, frameworks=None, fallback_catalog=None):
    path = Path(path).expanduser().resolve()
    if path.suffix.casefold() != '.json':
        raise ValueError('Open a Studio .json file.')
    payload, digest = read_json(path, notify)
    opts = selection(frameworks)
    notify(f'[Framework Read] ATT&CK={opts.attack}; ATLAS={opts.atlas}; CAR={opts.car}', 0, 0)
    reader = StudioReader(root, notify)
    document = (reader.document(payload) if opts == FrameworkSelection() and isinstance(payload, dict) and 'studio_frameworks_version' not in payload
                else read_framework_document(reader, payload, opts, fallback_catalog))
    if opts == FrameworkSelection():
        document.save_path = path
        document.saved_file_sha256 = digest
        document.saved_fingerprint = document.content_token()
    return document


def save_studio(document, target, notify, save_as=False, frameworks=None):
    opts = selection(frameworks)
    target = Path(target).expanduser().resolve()
    if target.suffix.casefold() != '.json':
        target = target.with_name(target.name + '.json')
    notify(f'Input file: {document.save_path}' if document.save_path else 'Input files: None (document draft in memory)', 0, 0)
    notify(f'Output file: {target}', 0, 0)
    notify('[Studio Save 1/3] Checking saved-file baseline', 0, 3)
    same_path = document.save_path and target == Path(document.save_path).resolve()
    if same_path and document.saved_file_sha256 and target.exists():
        with target.open('rb') as stream:
            digest = sha256(stream.read(LIMIT + 1)).hexdigest()
        if digest != document.saved_file_sha256:
            raise ValueError('This file changed outside the application. Reopen it or use Save As with another filename.')
    draft = snapshot_document(document)
    # Save preserves the in-app name; Save As adopts the requested filename.
    name = target.stem if save_as or not same_path else draft.name
    validate_document_name(name)
    if save_as or not same_path:
        draft.name = name
    payload = framework_payload(draft, opts)
    content = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if len(content.encode('utf-8')) > LIMIT:
        raise ValueError('Studio JSON exceeds the reopen limit of 64 MiB.')
    notify('[Studio Save 2/3] Writing complete document atomically', 1, 3)
    path = write_json_atomic(payload, target, notify, 'Studio Save')
    draft.save_path, draft.saved_file_sha256 = path, sha256(content.encode('utf-8')).hexdigest()
    draft.saved_fingerprint = draft.content_token() if opts == FrameworkSelection() else '0' * 64
    if opts != FrameworkSelection():
        notify('[Framework Write] Partial output saved; omitted content retained in memory. Save all three content types for a complete Workplace baseline.', 1, 1)
    notify('[Studio Save 3/3] Complete; source draft unchanged until accepted', 3, 3)
    return draft


def session_payload(documents, active_index, view, clean_exit=False):
    if not 0 <= len(documents) <= 50 or len({d.document_id for d in documents}) != len(documents):
        raise ValueError('Workspace supports at most 50 unique document IDs.')
    entries = []
    for document in documents:
        entries.append({'document': document_payload(document), 'initial_name': document.initial_name,
            'save_path': str(document.save_path) if document.save_path else None,
            'saved_fingerprint': document.saved_fingerprint, 'saved_file_sha256': document.saved_file_sha256,
            'content_token_version': 2,
            'dirty': document.dirty})
    return {'studio_session_version': '1.0', 'updated_at_utc': utc_now(), 'clean_exit': clean_exit,
            'documents': entries, 'active_index': active_index if documents else -1, 'view': deepcopy(view)}


def session_checksum(payload):
    return sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def write_session(payload, path, notify):
    notify('Input files: None (immutable workspace snapshot in memory)', 0, 0)
    notify(f'Output file: {Path(path).resolve()}', 0, 0)
    notify('[Session 1/3] Preparing recovery checkpoint', 0, 3)
    envelope = {'checksum': session_checksum(payload), 'workspace': payload}
    if len(json.dumps(envelope, ensure_ascii=False, indent=2).encode('utf-8')) > LIMIT:
        raise ValueError('Recovery checkpoint exceeds 64 MiB; save documents individually.')
    Path(path).resolve().parent.mkdir(parents=True, exist_ok=True)
    return write_json_atomic(envelope, path, notify, 'Session')


def read_session(root, path, notify):
    envelope, _ = read_json(path, notify)
    if not isinstance(envelope, dict) or not isinstance(envelope.get('workspace'), dict):
        raise ValueError('Invalid recovery checkpoint.')
    payload = envelope['workspace']
    if envelope.get('checksum') != session_checksum(payload) or payload.get('studio_session_version') != '1.0':
        raise ValueError('Recovery checkpoint checksum/schema mismatch; original file retained.')
    entries, active, view = payload.get('documents'), payload.get('active_index'), payload.get('view', {})
    if not isinstance(entries, list) or len(entries) > 50 or type(active) is not int or (
            entries and not 0 <= active < len(entries)) or (not entries and active != -1):
        raise ValueError('Invalid recovery document list/active tab.')
    if not isinstance(view, dict) or view.get('page', 'selected') not in ('selected', 'matrix', 'details','cases','car'):
        raise ValueError('Invalid recovery view.')
    if (type(view.get('car_browser_open',False)) is not bool or
            view.get('car_browser_kind','CAR Analytics') not in ('CAR Analytics','CAR Data Model','CAR Sensors')):
        raise ValueError('Invalid CAR browser recovery view.')
    if 'matrix_controls_expanded' in view and type(view['matrix_controls_expanded']) is not bool:
        raise ValueError('Invalid matrix controls recovery state.')
    if (not isinstance(view.get('atlas_cases_query',''),str) or len(view.get('atlas_cases_query',''))>10000
            or view.get('atlas_case_key') is not None and (not isinstance(view['atlas_case_key'],str) or len(view['atlas_case_key'])>500)):
        raise ValueError('Invalid case-study recovery view.')
    reader, documents = StudioReader(root, notify), []
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or type(entry.get('dirty')) is not bool:
            raise ValueError('Invalid recovery document state.')
        document = reader.document(entry.get('document'))
        initial = entry.get('initial_name', document.name)
        if not isinstance(initial, str):
            raise ValueError('Invalid initial document name.')
        validate_document_name(initial)
        document.initial_name = initial
        path_value = entry.get('save_path')
        if path_value is not None:
            if not isinstance(path_value, str) or not Path(path_value).is_absolute() or Path(path_value).suffix.casefold() != '.json':
                raise ValueError('Saved document path must be an absolute JSON filename.')
            document.save_path = Path(path_value).resolve()
        for field in ('saved_fingerprint', 'saved_file_sha256'):
            value = entry.get(field)
            if value is not None and (not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value)):
                raise ValueError('Invalid saved baseline digest.')
            setattr(document, field, value)
        if not document.saved_fingerprint:
            document.exported_fingerprint = () if entry['dirty'] else document.fingerprint()
        elif entry.get('content_token_version', 1) == 1 and not entry['dirty']:
            document.saved_fingerprint = document.content_token()
        if document.save_path and document.saved_file_sha256:
            try:
                with document.save_path.open('rb') as stream:
                    unchanged = sha256(stream.read(LIMIT + 1)).hexdigest() == document.saved_file_sha256
            except OSError:
                unchanged = False
            if not unchanged:
                document.saved_fingerprint = '0' * 64
                notify('[Session] Saved file missing/changed; recovered draft marked unsaved. Save will check for conflicts.', 1, 1)
        documents.append(document)
        notify('[Session 2/3] Validating recoverable documents', index, len(entries))
    if len({d.document_id for d in documents}) != len(documents):
        raise ValueError('Duplicate recovery document UUIDs.')
    notify('[Session 3/3] All documents validated; workspace ready for atomic restore', 3, 3)
    return {'documents': documents, 'active_index': active, 'view': view, 'clean_exit': payload.get('clean_exit', False)}
