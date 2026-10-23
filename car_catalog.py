"""Verified local CAR native snapshots and exact reference indexes. Workflow: README.md."""
from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
import json
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parent / 'data/car'
ID = re.compile(r'CAR-\d{4}-\d{2}-\d{3}')


def json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_value(v) for v in value]
    return value


@dataclass(frozen=True)
class CarCatalog:
    source: dict
    analytics: dict
    models: dict
    sensors: dict
    groups: dict
    references: dict
    sensor_fields: dict
    diagnostics: tuple

    @property
    def dataset_id(self):
        return self.source['dataset_sha256']

    def candidates(self, analytic):
        refs = set(analytic.get('data_model_references', []))
        return {key: sorted(refs & fields) for key, fields in self.sensor_fields.items() if refs & fields}

    def reference_known(self, reference):
        parts = reference.split('/')
        if len(parts) != 3 or parts[0] not in self.models:
            return False
        model = self.models[parts[0]]
        return parts[1] in {v['name'] for v in model['actions']} and parts[2] in {v['name'] for v in model['fields']}


def load_car(root=ROOT, notify=lambda *args: None):
    root = Path(root).resolve()
    manifest_path = root / 'source.json'
    notify('Input file: ' + str(manifest_path), 0, 0)
    notify('Output files: None (CAR catalog in memory)', 0, 0)
    notify('[CAR 1/4] Verifying fixed manifest and source hashes', 0, 4)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    files = manifest.get('files')
    if (manifest.get('schema') != 1 or not re.fullmatch('[0-9a-f]{40}', manifest.get('commit', ''))
            or not isinstance(files, dict) or not files or len(files) > 2000):
        raise ValueError('Invalid CAR manifest.')
    raw = {}
    for index, (relative, digest) in enumerate(sorted(files.items()), 1):
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Invalid CAR source path/hash.')
        notify('Input file: ' + str(path), 0, 0)
        payload = path.read_bytes()
        if len(payload) > 4*1024*1024 or sha256(payload).hexdigest() != digest:
            raise ValueError('CAR source hash/size mismatch: ' + relative)
        raw[relative] = payload
        if index % 20 == 0:
            notify('[CAR 1/4] Verified source files', index, len(files))
    notify('[CAR 2/4] Parsing native Analytics, Data Model and Sensors', 1, 4)
    collections = {'analytics': {}, 'data_model': {}, 'sensors': {}}
    diagnostics = []
    for relative, payload in raw.items():
        folder = relative.split('/')[0]
        if folder not in collections or not relative.endswith('.yaml'):
            continue
        record = json_value(yaml.safe_load(payload))
        if not isinstance(record, dict):
            raise ValueError('CAR YAML must contain an object: ' + relative)
        key = record.get('id') if folder == 'analytics' else Path(relative).stem
        if not isinstance(key, str) or (folder == 'analytics' and (not ID.fullmatch(key) or key != Path(relative).stem)):
            raise ValueError('CAR analytic ID/filename mismatch: ' + relative)
        if key in collections[folder]:
            raise ValueError('Duplicate CAR identity: ' + key)
        if folder == 'analytics':
            if not isinstance(record.get('title'), str) or not record['title']:
                raise ValueError('CAR analytic needs a title: ' + key)
            for field in ('coverage', 'implementations', 'platforms', 'data_model_references', 'unit_tests'):
                if field in record and not isinstance(record[field], list):
                    raise ValueError('Invalid CAR list ' + key + '/' + field)
            for coverage in record.get('coverage', []):
                if (not isinstance(coverage, dict) or not re.fullmatch(r'T\d{4}', str(coverage.get('technique', '')))
                        or 'subtechniques' in coverage and (not isinstance(coverage['subtechniques'], list) or any(
                            not isinstance(v, str) or not re.fullmatch(re.escape(coverage['technique'])+r'\.\d{3}', v) for v in coverage['subtechniques']))
                        or not isinstance(coverage.get('tactics', []), list)):
                    raise ValueError('Invalid CAR coverage: ' + key)
            if any(not isinstance(v, str) for v in record.get('platforms', []) + record.get('data_model_references', [])):
                raise ValueError('Invalid CAR string list: ' + key)
            if any(not isinstance(v, dict) or not isinstance(v.get('type'), str) for v in record.get('implementations', [])):
                raise ValueError('Invalid CAR implementation: ' + key)
            if not record.get('submission_date'):
                diagnostics.append(key + ': submission date not provided')
        record = {**record, '_source_path': relative, '_source_sha256': files[relative]}
        collections[folder][key] = record
    notify('[CAR 3/4] Indexing official by-technique buckets and exact data references', 2, 4)
    groups, references, sensor_fields = {}, {}, {}
    for key, analytic in collections['analytics'].items():
        seen = set()
        for number, coverage in enumerate(analytic.get('coverage', [])):
            parent = coverage['technique']
            if parent in seen:
                diagnostics.append(key + ': duplicate ' + parent + '; official grouping uses first coverage')
                continue
            seen.add(parent)
            # Matches the fixed generate_analytics.py: absent subtechniques != an empty list.
            scopes = coverage['subtechniques'] if 'subtechniques' in coverage else ['']
            for scope in scopes:
                groups.setdefault((parent, scope), set()).add(key)
        for ref in analytic.get('data_model_references', []):
            references.setdefault(ref, set()).add(key)
    for key, sensor in collections['sensors'].items():
        mappings = sensor.get('mappings', [])
        if not isinstance(mappings, list):
            raise ValueError('Invalid CAR sensor mappings: ' + key)
        fields = set()
        for mapping in mappings:
            if (not isinstance(mapping, dict) or not isinstance(mapping.get('object'), str)
                    or not isinstance(mapping.get('action'), str) or not isinstance(mapping.get('fields'), list)
                    or any(not isinstance(v, str) for v in mapping['fields'])):
                raise ValueError('Invalid native CAR sensor mapping: ' + key)
            fields.update(mapping['object']+'/'+mapping['action']+'/'+field for field in mapping['fields'])
        sensor_fields[key] = fields
    for key, model in collections['data_model'].items():
        if any(not isinstance(model.get(f), list) or any(not isinstance(v, dict) or not isinstance(v.get('name'), str)
                  for v in model[f]) for f in ('actions', 'fields')):
            raise ValueError('Invalid CAR data model: ' + key)
    digest = sha256(json.dumps({'commit': manifest['commit'], 'files': files}, sort_keys=True).encode()).hexdigest()
    source = {'repository': manifest.get('repository', 'https://github.com/mitre-attack/car'),
              'commit': manifest['commit'], 'dataset_sha256': digest}
    notify('[CAR 4/4] Ready: verified native catalog published', 4, 4)
    return CarCatalog(source, collections['analytics'], collections['data_model'], collections['sensors'],
                      {k: tuple(sorted(v)) for k, v in groups.items()},
                      {k: tuple(sorted(v)) for k, v in references.items()}, sensor_fields, tuple(diagnostics))
