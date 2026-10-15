"""In-memory TTP documents and atomic JSON/CSV export. Operation flow: README.md."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import csv
import io
import json
from pathlib import Path
import re
import uuid
from copy import deepcopy

from attack_catalog import Catalog, external_id, tactic_phases


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
    initial_name: str = field(init=False)

    def __post_init__(self):
        self.initial_name = self.name

    def fingerprint(self):
        return (self.name, self.catalog.version, self.catalog.domain, self.catalog.dataset_id, frozenset(self.selected),
                json.dumps(self.navigator_layer, sort_keys=True, ensure_ascii=False, allow_nan=False),
                json.dumps(self.navigator_snapshots, sort_keys=True, ensure_ascii=False, allow_nan=False),
                json.dumps(self.domain_snapshots, sort_keys=True, ensure_ascii=False, allow_nan=False),
                json.dumps(self.migration_archives, sort_keys=True, ensure_ascii=False, allow_nan=False))

    def set_catalog(self, catalog):
        if catalog.dataset_id != self.catalog.dataset_id:
            raise ValueError('Open a separate document or use the reviewed upgrade flow to switch datasets.')
        if catalog.domain != self.catalog.domain:
            if self.selected or self.navigator_layer or self.navigator_snapshots:
                self.domain_snapshots[self.catalog.domain] = {
                    "version": self.catalog.version, "selected_stix_ids": sorted(self.selected),
                    "navigator_layer": deepcopy(self.navigator_layer),
                    "navigator_import_selected": sorted(self.navigator_import_selected),
                    "navigator_snapshots": deepcopy(self.navigator_snapshots)}
            restored = self.domain_snapshots.pop(catalog.domain, {})
            self.selected = set(restored.get("selected_stix_ids", [])) & catalog.records.keys()
            self.navigator_layer = restored.get("navigator_layer", {})
            self.navigator_import_selected = set(restored.get("navigator_import_selected", []))
            self.navigator_snapshots = restored.get("navigator_snapshots", {})
            # Do not attach annotations from a restored domain's older release to a new one.
            if restored.get("version", catalog.version) != catalog.version:
                if self.navigator_layer:
                    self.navigator_snapshots[restored["version"]] = {
                        "layer": self.navigator_layer, "import_selected": sorted(self.navigator_import_selected)}
                self.navigator_layer, self.navigator_import_selected = {}, set()
                restored_version = self.navigator_snapshots.pop(catalog.version, {})
                self.navigator_layer = restored_version.get("layer", {})
                self.navigator_import_selected = set(restored_version.get("import_selected", []))
            self.catalog = catalog
            return
        if catalog.version != self.catalog.version:
            if self.navigator_layer:
                self.navigator_snapshots[self.catalog.version] = {
                    "layer": deepcopy(self.navigator_layer), "import_selected": sorted(self.navigator_import_selected)}
            restored = self.navigator_snapshots.pop(catalog.version, {})
            self.navigator_layer = restored.get("layer", {})
            self.navigator_import_selected = set(restored.get("import_selected", []))
        self.catalog = catalog

    @property
    def dirty(self):
        if self.exported_fingerprint is None:
            return (bool(self.selected) or bool(self.navigator_layer) or bool(self.navigator_snapshots)
                    or bool(self.domain_snapshots) or bool(self.migration_archives) or self.catalog.domain != "enterprise-attack" or self.name != self.initial_name)
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
    payload = {"schema_version": "1.0", "document_id": document.document_id,
            "name": name or document.name, "created_at_utc": document.created_at_utc,
            "exported_at_utc": utc_now(),
            "attack": {"domain": document.catalog.domain, "version": document.catalog.version,
                       "source_url": "https://github.com/mitre-attack/attack-stix-data"},
            "selected_count": len(ttps),
            "selected_technique_ids": [row['technique_id'] for row in ttps], "selected_ttps": ttps}
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
    return payload


CSV_FIELDS = ('schema_version', 'document_id', 'document_name', 'attack_domain', 'attack_version',
              'created_at_utc', 'exported_at_utc', 'selected_count', 'technique_id', 'stix_id', 'name',
              'is_subtechnique', 'parent_technique_id', 'parent_technique_name', 'platforms',
              'tactic_ids', 'tactic_names', 'tactic_shortnames', 'comment', 'tactic_comments',
              'attack_source_url', 'attack_dataset_sha256', 'enabled', 'tactic_enabled')


def csv_content(payload):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for row in payload['selected_ttps']:
        writer.writerow({
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
        })
    return stream.getvalue()


def _export_document(document: TTPDocument, target: Path, notify, file_format):
    """Publish only after serialization succeeds, preserving an existing file on failure."""
    target = Path(target).expanduser().resolve()
    suffix = '.' + file_format
    if target.suffix.casefold() != suffix:
        target = target.with_name(target.name + suffix)
    temporary = target.with_name(target.name + '.' + uuid.uuid4().hex + '.tmp')
    notify('Input files: None (active document and verified catalog in memory)', 0, 0)
    notify(f'Output file: {target}', 0, 0)
    notify(f'Temporary output file: {temporary}', 0, 0)
    notify('[Export 1/3 Prepare] Validating and serializing selected TTPs', 0, 3)
    payload = document_payload(document, target.stem)
    content = csv_content(payload) if file_format == 'csv' else json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    notify(f'[Export 2/3 Write] Writing {len(payload["selected_ttps"])} selected TTPs', 1, 3)
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
    document.exported_fingerprint = None if file_format == "csv" and (document.navigator_layer or document.navigator_snapshots or document.domain_snapshots or document.migration_archives) else document.fingerprint()
    if file_format == "csv" and (document.navigator_layer or document.navigator_snapshots or document.domain_snapshots or document.migration_archives):
        notify('[Export] CSV saved active TTPs and their comments; use Studio JSON to preserve complete layer settings, colors/scores and domain/version archives.', 1, 1)
    notify(f'[Export 3/3 Publish] Complete: {target}', 3, 3)
    return target


def export_document_json(document: TTPDocument, target: Path, notify):
    return _export_document(document, target, notify, 'json')


def export_document_csv(document: TTPDocument, target: Path, notify):
    return _export_document(document, target, notify, 'csv')
