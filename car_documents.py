"""Independent CAR inclusion, snapshot identity and native/CSV payloads. Workflow: README.md."""
from copy import deepcopy
import json
import re
from car_catalog import ID


def validate_workspace(value):
    if value == {}:
        return {}
    if not isinstance(value, dict) or value.get('schema') != 1 or not isinstance(value.get('entries'), dict) or len(value['entries']) > 10000:
        raise ValueError('Invalid CAR workspace schema/entries.')
    for key, entry in value['entries'].items():
        if not isinstance(entry, dict) or not isinstance(entry.get('source'), dict):
            raise ValueError('Invalid CAR analytic reference.')
        source = entry['source']; identity = entry.get('id')
        if (not isinstance(identity, str) or not ID.fullmatch(identity)
                or not re.fullmatch('[0-9a-f]{64}', source.get('dataset_sha256', ''))
                or not re.fullmatch('[0-9a-f]{40}', source.get('commit', ''))
                or key != source['dataset_sha256'] + ':' + identity
                or not isinstance(entry.get('title'), str) or type(entry.get('included')) is not bool
                or not isinstance(entry.get('record', {}), dict) or entry.get('record', {}).get('id', identity) != identity
                or not isinstance(entry.get('annotations', {}), dict)):
            raise ValueError('Invalid CAR snapshot, ID, inclusion or display snapshot.')
    json.dumps(value, allow_nan=False)
    return deepcopy(value)


def change_inclusion(document, catalog, identities, include, owner=None):
    if owner is not None and owner != document.document_id:
        raise ValueError('CAR action belongs to another Workplace.')
    if type(include) is not bool or not isinstance(identities, (set, list, tuple)):
        raise ValueError('Invalid CAR inclusion command.')
    identities = set(identities)
    state = validate_workspace(document.car_workspace) or {'schema': 1, 'entries': {}}
    keys = set()
    for identity in identities:
        if ':' in identity and identity in state['entries']:
            keys.add(identity)
        else:
            snapshot, _, analytic_id = identity.partition(':')
            if not analytic_id:
                analytic_id, snapshot = identity, catalog.dataset_id if catalog else ''
            if catalog is None or snapshot != catalog.dataset_id or analytic_id not in catalog.analytics:
                raise ValueError('CAR analytic is unavailable in the exact catalog.')
            key = catalog.dataset_id + ':' + analytic_id
            if not include and key not in state['entries']:
                continue
            keys.add(key)
            if key not in state['entries']:
                record = deepcopy(catalog.analytics[analytic_id])
                state['entries'][key] = {'id': analytic_id, 'title': record['title'], 'source': dict(catalog.source),
                                         'record': record, 'included': False, 'annotations': {}}
    for key in keys:
        state['entries'][key]['included'] = include
    if keys:
        document.car_workspace = validate_workspace(state)


def included(document):
    return {k: e for k, e in document.car_workspace.get('entries', {}).items() if e['included']}


def empty_catalog():
    from attack_catalog import Catalog
    return Catalog('0.0', {}, {}, [], {'CAR-only': {}}, {}, {'enterprise-attack': {}}, {}, {}, {})


def is_empty_catalog(catalog):
    return catalog.version == '0.0' and not catalog.records
