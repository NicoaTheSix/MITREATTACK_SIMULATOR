"""Lossless ATLAS v6 adapter into the shared catalog. Workflow: README.md."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import uuid

import yaml

from custom_sources import custom_catalog, cache_source

DOMAIN = 'atlas-atlas'
SOURCE = 'mitre-atlas'
DATA = Path(__file__).resolve().parent / 'data' / 'atlas'


def project_atlas(native):
    """Retain native objects/relationships; the matrix projection is an internal view."""
    if not isinstance(native, dict) or native.get('format-version') != '6.0.0':
        raise ValueError('Supported ATLAS format-version: 6.0.0.')
    version = native['collection']['version']
    if not isinstance(version, str) or not re.fullmatch(r'\d{4}\.\d{2}(?:\.\d+)?', version):
        raise ValueError('ATLAS needs an exact YYYY.MM[.patch] content version.')
    groups = [('tactics', 'x-mitre-tactic'), ('techniques', 'attack-pattern'),
              ('mitigations', 'course-of-action'), ('case-studies', 'x-atlas-case-study')]
    entries = [(native['matrix'], 'x-mitre-matrix')]
    for field, kind in groups:
        if not isinstance(native.get(field), dict):
            raise ValueError('Missing ATLAS object mapping: ' + field)
        for key, obj in native[field].items():
            if obj.get('id') != key or not isinstance(obj.get('name'), str):
                raise ValueError('Invalid ATLAS object: ' + key)
            entries.append((obj, kind))
    identities = {obj['id']: kind + '--' + str(uuid.UUID(obj['uuid'])) for obj, kind in entries}
    if len(set(identities.values())) != len(entries):
        raise ValueError('Duplicate ATLAS object identity.')
    relations = native['relationships']
    edges = [edge for mapping in relations.values() for rows in mapping.values() for edge in rows]
    if any(e['source'] not in identities or e['target'] not in identities for e in edges):
        raise ValueError('Unresolved ATLAS relationship endpoint.')
    parents = {e['source']: e['target'] for e in edges if e['relationship-type'] == 'specializes'}
    slugs = {key: key.lower().replace('.', '-') for key in native['tactics']}
    ordered = sorted((e for e in edges if e['relationship-type'] == 'sequences'), key=lambda e:e['position'])
    if set(e['target'] for e in ordered) != set(slugs):
        raise ValueError('ATLAS matrix sequence does not cover its tactics.')
    objects = []
    for original, kind in entries:
        key = original['id']
        section = ('tactics' if kind == 'x-mitre-tactic' else 'techniques' if kind == 'attack-pattern'
                   else 'mitigations' if kind == 'course-of-action' else 'studies')
        obj = {'id': identities[key], 'type': kind, 'name': original['name'],
               'description': original.get('description', ''), 'x_mitre_domains': [DOMAIN],
               'created': original.get('created-date', '') + 'T00:00:00Z',
               'modified': original.get('modified-date', '') + 'T00:00:00Z',
               'external_references': [{'source_name': SOURCE, 'external_id': key,
                   'url': f'https://atlas.mitre.org/{section}/{key}'}],
               'x_atlas_native': deepcopy(original),
               'x_atlas_relationships': deepcopy(relations.get(key, {}))}
        for ref in original.get('references', []):
            obj['external_references'].append({'source_name': ref.get('id', 'reference'),
                'description': ref.get('title', ''), **({'url':ref['url']} if ref.get('url') else {})})
        if original.get('attack-reference'):
            ref = original['attack-reference']
            obj['external_references'].append({'source_name':'mitre-attack', 'external_id':ref['id'], 'url':ref['url']})
        if kind == 'x-mitre-tactic':
            obj['x_mitre_shortname'] = slugs[key]
        elif kind == 'x-mitre-matrix':
            obj['tactic_refs'] = [identities[e['target']] for e in ordered]
        elif kind == 'attack-pattern':
            obj['x_mitre_platforms'] = list(original.get('platforms', []))
            obj['x_mitre_is_subtechnique'] = key in parents
            obj['kill_chain_phases'] = [{'kill_chain_name': DOMAIN, 'phase_name': slugs[e['target']]}
                for e in relations.get(key, {}).get('achieves', [])]
        objects.append(obj)
    for edge in edges:
        relation = {'specializes':'subtechnique-of', 'mitigates':'mitigates'}.get(edge['relationship-type'])
        if relation:
            identity = str(uuid.uuid5(uuid.NAMESPACE_URL, f'atlas:{edge["source"]}:{relation}:{edge["target"]}'))
            objects.append({'type':'relationship', 'id':'relationship--' + identity,
                'source_ref':identities[edge['source']], 'target_ref':identities[edge['target']],
                'relationship_type':relation, 'description':edge.get('description', '')})
    return {'type':'bundle', 'id':'bundle--'+str(uuid.uuid5(uuid.NAMESPACE_URL,'atlas:'+version)),
        'x_ttp_studio_domains':[{'id':DOMAIN, 'name':'ATLAS', 'kill_chain_name':DOMAIN, 'reference_source':SOURCE}],
        'x_atlas_native':deepcopy(native), 'objects':objects}, version


def load_atlas_catalog(root, notify):
    path, manifest = DATA / 'ATLAS-2026.09.yaml', DATA / 'source.json'
    notify(f'Input file: {path.resolve()}', 0, 0)
    notify(f'Input provenance: {manifest.resolve()}', 0, 0)
    notify(f'Output cache directory: {(Path(root) / "custom").resolve()}', 0, 0)
    notify('[ATLAS 1/3] Verifying pinned source checksum', 0, 3)
    data = path.read_bytes()
    provenance = json.loads(manifest.read_text(encoding='utf-8'))
    if sha256(data).hexdigest() != provenance['files'][path.name]['sha256']:
        raise ValueError('ATLAS source checksum mismatch.')
    notify('[ATLAS 2/3] Reading native tactics, techniques, mitigations and case studies', 1, 3)
    native = yaml.safe_load(data)
    bundle, version = project_atlas(native)
    bundle['x_atlas_provenance'] = provenance
    encoded = (json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    digest = sha256(encoded).hexdigest()
    catalog = custom_catalog(bundle, digest, provenance['files'][path.name]['url'], version, notify)
    target = Path(root).resolve() / 'custom' / (digest + '.json')
    notify(f'Output file: {target}', 0, 0)
    if not target.exists() or sha256(target.read_bytes()).hexdigest() != digest:
        cache_source(root, encoded, notify)
    notify('[ATLAS 3/3] Ready: native metadata preserved; matrix projection cached', 3, 3)
    return catalog
