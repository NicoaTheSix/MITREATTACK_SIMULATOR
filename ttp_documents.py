"""In-memory TTP documents and atomic JSON/CSV export. Operation flow: README.md."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import csv
import io
import json
import hashlib
from pathlib import Path
import re
import uuid
from copy import deepcopy

from attack_catalog import Catalog, external_id, tactic_phases
from ttp_selection import DEFAULT_PREFERENCES


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def validate_document_name(value: str) -> str:
    name = value.strip()
    for suffix in ('.json', '.csv'):
        if name.casefold().endswith(suffix):
            name = name[:-len(suffix)]
            break
    if not name or name in {'.', '..'} or name.endswith('.'):
        raise ValueError('Enter a non-empty filename without a trailing dot.')
    if any(ord(char) < 32 or char in '<>:"/\\|?*' for char in name):
        raise ValueError('The name contains characters that cannot be used in a Windows filename.')
    if re.fullmatch(r'CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³]', name.split('.')[0], re.IGNORECASE):
        raise ValueError('This name is reserved by Windows. Choose another name.')
    if len(name.encode('utf-16-le')) // 2 > 250:
        raise ValueError('The filename is too long.')
    return name


@dataclass
class TTPDocument:
    name: str
    catalog: Catalog
    selected: set[str] = field(default_factory=set)
    document_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at_utc: str = field(default_factory=utc_now)
    export_path: Path | None = None
    exported_fingerprint: tuple | None = None
    navigator_layer: dict = field(default_factory=dict)
    navigator_import_selected: set[str] = field(default_factory=set)
    navigator_snapshots: dict = field(default_factory=dict)
    export_format: str | None = None
    domain_snapshots: dict = field(default_factory=dict)
    migration_archives: list = field(default_factory=list)
    selection_scopes: dict = field(default_factory=dict)
    selection_preferences: dict = field(default_factory=lambda: dict(DEFAULT_PREFERENCES))
    search_fields: list = field(default_factory=lambda: ['name', 'id'])
    save_path: Path | None = None
    saved_fingerprint: str | None = None
    saved_file_sha256: str | None = None
    atlas_document: TTPDocument | None = None
    car_workspace: dict = field(default_factory=dict)
    initial_name: str = field(init=False)

    def __post_init__(self):
        self.initial_name = self.name

    def fingerprint(self):
        # Omitting a false new preference preserves pre-feature recovery hashes.
        values = (self.name, self.catalog.version, self.catalog.domain, self.catalog.dataset_id, frozenset(self.selected),
                json.dumps(self.navigator_layer, sort_keys=True, ensure_ascii=False, allow_nan=False),
                json.dumps(self.navigator_snapshots, sort_keys=True, ensure_ascii=False, allow_nan=False),
                json.dumps(self.domain_snapshots, sort_keys=True, ensure_ascii=False, allow_nan=False),
                json.dumps(self.migration_archives, sort_keys=True, ensure_ascii=False, allow_nan=False),
                json.dumps(self.selection_scopes, sort_keys=True), json.dumps({k:v for k,v in self.selection_preferences.items()
                    if k != 'visible_only' or v}, sort_keys=True),
                json.dumps(self.search_fields))
        # Omit the extension when absent to preserve existing saved/recovery hashes.
        values += ((self.atlas_document.content_token(),) if self.atlas_document else ())
        return values + ((json.dumps(self.car_workspace, sort_keys=True, ensure_ascii=False, allow_nan=False),) if self.car_workspace else ())

    def content_token(self):
        """A deterministic disk/session baseline, independent of Python hash order."""
        fingerprint = list(self.fingerprint())
        fingerprint[4] = sorted(fingerprint[4])
        fingerprint.append(sorted(self.navigator_import_selected))
        return hashlib.sha256(json.dumps(fingerprint, ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()

    def set_catalog(self, catalog):
        if catalog.dataset_id != self.catalog.dataset_id:
            raise ValueError('Open a separate document or use the reviewed upgrade flow to switch datasets.')
        if catalog.domain != self.catalog.domain:
            if self.selected or self.navigator_layer or self.navigator_snapshots:
                self.domain_snapshots[self.catalog.domain] = {
                    "version": self.catalog.version, "selected_stix_ids": sorted(self.selected),
                    "navigator_layer": deepcopy(self.navigator_layer),
                    "navigator_import_selected": sorted(self.navigator_import_selected),
                    "selection_scopes": deepcopy(self.selection_scopes),
                    "navigator_snapshots": deepcopy(self.navigator_snapshots)}
            restored = self.domain_snapshots.pop(catalog.domain, {})
            self.selected = set(restored.get("selected_stix_ids", [])) & catalog.records.keys()
            self.navigator_layer = restored.get("navigator_layer", {})
            self.navigator_import_selected = set(restored.get("navigator_import_selected", []))
            self.navigator_snapshots = restored.get("navigator_snapshots", {})
            self.selection_scopes = restored.get('selection_scopes', {})
            # Do not attach annotations from a restored domain's older release to a new one.
            if restored.get("version", catalog.version) != catalog.version:
                if self.navigator_layer:
                    self.navigator_snapshots[restored["version"]] = {
                        "layer": self.navigator_layer, "import_selected": sorted(self.navigator_import_selected),
                        'selection_scopes':deepcopy(self.selection_scopes)}
                self.navigator_layer, self.navigator_import_selected = {}, set()
                restored_version = self.navigator_snapshots.pop(catalog.version, {})
                self.navigator_layer = restored_version.get("layer", {})
                self.navigator_import_selected = set(restored_version.get("import_selected", []))
                self.selection_scopes = restored_version.get('selection_scopes',self.selection_scopes)
            self.catalog = catalog
            self.normalize_selection_scopes()
            return
        if catalog.version != self.catalog.version:
            previous_scopes = deepcopy(self.selection_scopes)
            if self.navigator_layer or self.selection_scopes:
                self.navigator_snapshots[self.catalog.version] = {
                    "layer": deepcopy(self.navigator_layer), "import_selected": sorted(self.navigator_import_selected),
                    'selection_scopes': deepcopy(self.selection_scopes)}
            restored = self.navigator_snapshots.pop(catalog.version, {})
            self.navigator_layer = restored.get("layer", {})
            self.navigator_import_selected = set(restored.get("import_selected", []))
            self.selection_scopes = restored.get('selection_scopes', previous_scopes)
        self.catalog = catalog
        self.normalize_selection_scopes()

    def normalize_selection_scopes(self):
        from ttp_selection import phases
        self.selection_scopes = {key: sorted(set(slugs) & phases(self.catalog, key))
                                 for key, slugs in self.selection_scopes.items() if key in self.selected and key in self.catalog.records}
        empty = {key for key, slugs in self.selection_scopes.items() if not slugs}
        self.selected -= empty
        self.selection_scopes = {key: slugs for key, slugs in self.selection_scopes.items()
                                 if key not in empty and set(slugs) != phases(self.catalog,key)}

    @property
    def dirty(self):
        if self.saved_fingerprint is not None:
            return self.content_token() != self.saved_fingerprint
        if self.exported_fingerprint is None:
            return (bool(self.atlas_document and self.atlas_document.dirty)
                    or bool(self.car_workspace)
                    or bool(self.selected) or bool(self.navigator_layer) or bool(self.navigator_snapshots)
                    or bool(self.domain_snapshots) or bool(self.migration_archives) or bool(self.selection_scopes)
                    or {**DEFAULT_PREFERENCES, **self.selection_preferences} != DEFAULT_PREFERENCES
                    or self.search_fields != ['name', 'id'] or self.catalog.domain != "enterprise-attack" or self.name != self.initial_name)
        return self.fingerprint() != self.exported_fingerprint


def technique_comments(document: TTPDocument, key):
    """Project the effective global/scoped comments without changing layer data."""
    attack_id = external_id(document.catalog.records[key])
    comments = {row.get('tactic', ''): row.get('comment', '')
                for row in document.navigator_layer.get('techniques', []) if row['techniqueID'] == attack_id}
    order = {slug: number for number, slug in enumerate(document.catalog.tactic_order)}
    scoped = [{'tactic': slug, 'comment': comment}
              for slug, comment in sorted(comments.items(), key=lambda pair: (order.get(pair[0], len(order)), pair[0]))
              if slug and comment]
    return comments.get('', ''), scoped


def technique_states(document, key, rows=None):
    rows = ({(row['techniqueID'], row.get('tactic', '')): row for row in document.navigator_layer.get('techniques', [])}
            if rows is None else rows)
    attack_id = external_id(document.catalog.records[key])
    global_row = rows.get((attack_id, ''), {})
    enabled = global_row.get('enabled', True)
    phases = tactic_phases(document.catalog.records[key], document.catalog.domain)
    scoped = [{'tactic': slug, 'enabled': rows.get((attack_id, slug), global_row).get('enabled', True)}
              for slug in document.catalog.tactic_order if slug in phases]
    return enabled, scoped


def document_payload(document: TTPDocument, name=None):
    missing = document.selected - document.catalog.records.keys()
    if missing:
        raise ValueError("Document contains TTPs absent from its ATT&CK snapshot")
    records = document.catalog.records
    ttps = []
    for key in sorted(document.selected, key=lambda key: (external_id(records[key]), key)):
        obj = records[key]
        parent = document.catalog.parents.get(key)
        comment, tactic_comments = technique_comments(document, key)
        enabled, tactic_enabled = technique_states(document, key)
        tactic_slugs = tactic_phases(obj, document.catalog.domain) & document.catalog.tactics.keys()
        tactics = [{"tactic_id": external_id(document.catalog.tactics[slug]) or None,
                    "name": document.catalog.tactics[slug]['name'], "shortname": slug}
                   for slug in document.catalog.tactic_order if slug in tactic_slugs]
        ttps.append({"technique_id": external_id(obj), "stix_id": key, "name": obj['name'],
                     "is_subtechnique": bool(obj.get('x_mitre_is_subtechnique')),
                     "parent_technique_id": external_id(records[parent]) if parent else None,
                     "parent_technique_name": records[parent]['name'] if parent else None,
                     "platforms": sorted(set(obj.get('x_mitre_platforms', []))), "tactics": tactics,
                     "comment": comment, "tactic_comments": tactic_comments,
                     "enabled": enabled, "tactic_enabled": tactic_enabled})
        ttps[-1]['selected_tactics'] = [slug for slug in document.catalog.tactic_order
            if slug in tactic_slugs and (key not in document.selection_scopes or slug in document.selection_scopes[key])]
    payload = {"schema_version": "1.0", "document_id": document.document_id,
            "name": name or document.name, "created_at_utc": document.created_at_utc,
            "exported_at_utc": utc_now(),
            "attack": {"domain": document.catalog.domain, "version": document.catalog.version,
                       "source_url": "https://github.com/mitre-attack/attack-stix-data"},
            "selected_count": len(ttps),
            "selected_technique_ids": [row['technique_id'] for row in ttps], "selected_ttps": ttps}
    payload['navigator_import_selected'] = sorted(document.navigator_import_selected)
    payload.update(selection_scopes=deepcopy(document.selection_scopes),
                   selection_preferences=dict(document.selection_preferences), search_fields=list(document.search_fields))
    if document.navigator_layer:
        payload["navigator_layer"] = document.navigator_layer
    if document.catalog.dataset_id:
        payload['attack'].update(source_url=document.catalog.custom_source, dataset_sha256=document.catalog.dataset_id,
                                 custom=True)
    if document.navigator_snapshots:
        payload["navigator_snapshots"] = document.navigator_snapshots
    if document.domain_snapshots:
        payload["domain_snapshots"] = document.domain_snapshots
    if document.migration_archives:
        payload['migration_archives'] = document.migration_archives
    if document.atlas_document:
        payload['atlas_workspace'] = document_payload(document.atlas_document)
    if document.car_workspace:
        from car_documents import validate_workspace
        payload['car_workspace'] = validate_workspace(document.car_workspace)
    from car_documents import is_empty_catalog
    if is_empty_catalog(document.catalog):
        payload['attack']['car_surface'] = True
    return payload


CSV_FIELDS = ('schema_version', 'document_id', 'document_name', 'attack_domain', 'attack_version',
              'created_at_utc', 'exported_at_utc', 'selected_count', 'technique_id', 'stix_id', 'name',
              'is_subtechnique', 'parent_technique_id', 'parent_technique_name', 'platforms',
              'tactic_ids', 'tactic_names', 'tactic_shortnames', 'comment', 'tactic_comments',
              'attack_source_url', 'attack_dataset_sha256', 'enabled', 'tactic_enabled', 'selected_tactics',
              'content_type', 'car_id', 'car_snapshot', 'car_commit', 'car_analytic_json')


def csv_content(payload):
    if payload.get('atlas_workspace'):
        # Keep exact framework/domain/version columns on every row.
        return csv_content({k:v for k,v in payload.items() if k != 'atlas_workspace'}) + csv_content(
            payload['atlas_workspace']).partition('\n')[2]
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for row in payload['selected_ttps']:
        writer.writerow({
            'content_type': 'atlas_ttp' if payload['attack']['domain'] == 'atlas-atlas' else 'attack_ttp',
            'schema_version': payload['schema_version'], 'document_id': payload['document_id'],
            'document_name': payload['name'], 'attack_domain': payload['attack']['domain'],
            'attack_version': payload['attack']['version'], 'created_at_utc': payload['created_at_utc'],
            'attack_source_url': payload['attack']['source_url'],
            'attack_dataset_sha256': payload['attack'].get('dataset_sha256', ''),
            'exported_at_utc': payload['exported_at_utc'], 'selected_count': payload['selected_count'],
            'technique_id': row['technique_id'], 'stix_id': row['stix_id'], 'name': row['name'],
            'is_subtechnique': str(row['is_subtechnique']).lower(),
            'parent_technique_id': row['parent_technique_id'], 'parent_technique_name': row['parent_technique_name'],
            'platforms': '; '.join(row['platforms']),
            'tactic_ids': '; '.join(tactic['tactic_id'] or '' for tactic in row['tactics']),
            'tactic_names': '; '.join(tactic['name'] for tactic in row['tactics']),
            'tactic_shortnames': '; '.join(tactic['shortname'] for tactic in row['tactics']),
            'comment': row.get('comment', ''),
            'tactic_comments': json.dumps(row.get('tactic_comments', []), ensure_ascii=False, allow_nan=False),
            'enabled': str(row.get('enabled', True)).lower(),
            'tactic_enabled': json.dumps(row.get('tactic_enabled', []), ensure_ascii=False, allow_nan=False),
            'selected_tactics': json.dumps(row.get('selected_tactics', []), ensure_ascii=False),
        })
    for key, entry in payload.get('car_workspace', {}).get('entries', {}).items():
        if entry['included']:
            writer.writerow({'content_type': 'car_analytic', 'document_id': payload['document_id'],
                'document_name': payload['name'], 'name': entry['title'], 'car_id': entry['id'],
                'car_snapshot': entry['source']['dataset_sha256'], 'car_commit': entry['source']['commit'],
                'car_analytic_json': json.dumps(entry, ensure_ascii=False)})
    return stream.getvalue()


def _export_document(document: TTPDocument, target: Path, notify, file_format, frameworks=None):
    """Publish only after serialization succeeds, preserving an existing file on failure."""
    from framework_io import framework_payload, payload_documents, selection, FrameworkSelection
    opts = selection(frameworks)
    target = Path(target).expanduser().resolve()
    suffix = '.' + file_format
    if target.suffix.casefold() != suffix:
        target = target.with_name(target.name + suffix)
    temporary = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
    notify('Input files: None (active document and verified catalog in memory)', 0, 0)
    notify(f'Output file: {target}', 0, 0)
    notify(f'Temporary output file: {temporary}', 0, 0)
    notify('[Export 1/3 Prepare] Validating and serializing selected TTPs', 0, 3)
    payload = framework_payload(document, opts, target.stem)
    parts = payload_documents(payload)
    if file_format == 'csv':
        csv_parts = [csv_content(part) for part in parts]
        content = (csv_parts[0] + ''.join(part.partition('\n')[2] for part in csv_parts[1:])
                   if csv_parts else csv_content({'selected_ttps':[]}))
    else:
        content = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    count = sum(len(part['selected_ttps']) + len(part.get('atlas_workspace', {}).get('selected_ttps', [])) for part in parts)
    car_count = sum(sum(bool(e['included']) for e in part.get('car_workspace',{}).get('entries',{}).values()) for part in parts)
    notify(f'[Export 2/3 Write] Writing {count} selected TTPs; {car_count} CAR Analytics (ATT&CK={opts.attack}; ATLAS={opts.atlas}; CAR={opts.car})', 1, 3)
    try:
        # The temporary file is unique, and resides beside the requested export.
        with temporary.open('x', encoding='utf-8-sig' if file_format == 'csv' else 'utf-8', newline='') as stream:
            stream.write(content)
        notify(f'[Export 3/3 Publish] Publishing {file_format.upper()} file', 2, 3)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    document.name = target.stem
    document.export_path = target
    document.export_format = file_format
    document.exported_fingerprint = None if file_format == 'csv' or opts != FrameworkSelection() else document.fingerprint()
    if file_format == 'json':
        document.save_path = target
        document.saved_fingerprint = document.content_token() if opts == FrameworkSelection() else '0' * 64
        document.saved_file_sha256 = hashlib.sha256(content.encode('utf-8')).hexdigest()
    if file_format == 'csv':
        notify('[Export] CSV is an exchange file; use Save / Save As for a complete editable Studio document.', 1, 1)
    notify(f'[Export 3/3 Publish] Complete: {target}', 3, 3)
    return target


def export_document_json(document: TTPDocument, target: Path, notify, frameworks=None):
    return _export_document(document, target, notify, 'json', frameworks)


def export_document_csv(document: TTPDocument, target: Path, notify, frameworks=None):
    return _export_document(document, target, notify, 'csv', frameworks)
