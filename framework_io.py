"""Selective ATT&CK/ATLAS file projections. Operation flow: README.md."""
from copy import copy
from typing import NamedTuple
import uuid


class FrameworkSelection(NamedTuple):
    attack: bool = True
    atlas: bool = True
    car: bool = True


def selection(value=None):
    if value is None:
        return FrameworkSelection()
    if isinstance(value, dict):
        if set(value) not in ({'attack', 'atlas'}, {'attack', 'atlas', 'car'}):
            raise ValueError('Choose ATT&CK and ATLAS explicitly.')
        value = (value['attack'], value['atlas'], value.get('car', True))
    if isinstance(value, (tuple, list)) and len(value) == 2:
        value = (*value, True)
    if not isinstance(value, (tuple, list)) or len(value) != 3 or any(type(v) is not bool for v in value):
        raise ValueError('Content choices must be booleans: ATT&CK, ATLAS, CAR.')
    if not any(value):
        raise ValueError('Select at least one framework.')
    return FrameworkSelection(*value)


def framework_payload(document, frameworks=None, name=None):
    """Omitted frameworks never appear in the serialized selection/archives."""
    from ttp_documents import document_payload
    from car_documents import validate_workspace
    opts = selection(frameworks)
    if opts.attack:
        view = copy(document)
        if not opts.atlas:
            view.atlas_document = None
        elif document.atlas_document is not None:
            view.atlas_document = copy(document.atlas_document)
            view.atlas_document.car_workspace = {}
        if not opts.car:
            view.car_workspace = {}
        return document_payload(view, name)
    return {'studio_frameworks_version': '1.0', 'name': name or document.name,
            'document_id': document.document_id, 'created_at_utc': document.created_at_utc,
            'frameworks': ({'atlas': document_payload(document.atlas_document) if document.atlas_document else None} if opts.atlas else {}),
            **({'car_workspace': validate_workspace(document.car_workspace)} if opts.car else {})}


def framework_documents(document, frameworks=None, atlas_catalog=None):
    """Navigator represents frameworks as independent, domain-scoped layers."""
    from ttp_documents import TTPDocument
    opts = selection(frameworks)
    result = [document] if opts.attack else []
    if opts.atlas and document.atlas_document:
        result.append(document.atlas_document)
    if not result and opts.atlas and atlas_catalog is not None:
        result.append(TTPDocument(document.name + '-ATLAS', atlas_catalog))
    if not result:
        raise ValueError('Navigator/Excel matrix output requires ATT&CK or ATLAS TTP content. Save CAR in Studio JSON or typed CSV.')
    return result


def payload_documents(payload):
    """Project CSV rows from either the legacy document or framework envelope."""
    if 'studio_frameworks_version' in payload:
        values = [value for value in payload['frameworks'].values() if value is not None]
        if payload.get('car_workspace'):
            values.append({'document_id': payload['document_id'], 'name': payload['name'], 'selected_ttps': [],
                           'car_workspace': payload['car_workspace']})
        return values
    return [payload]


def read_framework_document(reader, payload, frameworks=None, fallback_catalog=None):
    """Validate chosen frameworks only; skipped datasets are never resolved."""
    from attack_catalog import load_catalog
    from ttp_documents import TTPDocument, document_payload
    opts = selection(frameworks)
    if not isinstance(payload, dict):
        raise ValueError('Expected a Studio JSON document.')
    if 'studio_frameworks_version' in payload:
        parts = payload.get('frameworks')
        if (payload['studio_frameworks_version'] != '1.0' or not isinstance(parts, dict)
                or (not parts and 'car_workspace' not in payload) or set(parts) - {'attack', 'atlas'}):
            raise ValueError('Invalid framework document envelope.')
    else:
        if payload.get('schema_version') != '1.0':
            raise ValueError('Expected Studio schema_version 1.0.')
        parts = {'attack': {k:v for k,v in payload.items() if k not in ('atlas_workspace', 'car_workspace')},
                 'atlas': payload.get('atlas_workspace')}
    attack = parts.get('attack') if opts.attack else None
    atlas = parts.get('atlas') if opts.atlas else None
    if attack is not None:
        if not isinstance(attack, dict) or 'atlas_workspace' in attack or 'studio_frameworks_version' in attack:
            raise ValueError('Invalid ATT&CK framework document.')
        document = reader.document(attack)
    else:
        # The UI still needs its current catalog for an empty ATT&CK surface.
        # This is an in-memory anchor, never a dataset from the skipped file.
        if fallback_catalog is None and opts.car and 'car_workspace' in payload:
            from car_documents import empty_catalog
            catalog = empty_catalog()
        else:
            catalog = fallback_catalog or load_catalog(reader.root, reader.notify)
        reader.catalogs.setdefault((catalog.dataset_id, catalog.version), catalog)
        anchor = TTPDocument(payload.get('name', ''), catalog)
        anchor_payload = document_payload(anchor)
        for field in ('name', 'document_id', 'created_at_utc'):
            anchor_payload[field] = payload.get(field)
        document = reader.document(anchor_payload)
    if atlas is not None:
        if (not isinstance(atlas, dict) or not isinstance(atlas.get('attack'), dict)
                or atlas['attack'].get('domain') != 'atlas-atlas' or 'atlas_workspace' in atlas or 'studio_frameworks_version' in atlas
                or document.catalog.domain == 'atlas-atlas'):
            raise ValueError('Invalid ATLAS framework document.')
        document.atlas_document = reader.document(atlas)
    if opts.car and 'car_workspace' in payload:
        from car_documents import validate_workspace
        document.car_workspace = validate_workspace(payload['car_workspace'])
    if opts != FrameworkSelection():
        # A filtered import is an independent draft; it must not own/overwrite
        # the complete source file or collide with an already-open document.
        document.document_id = str(uuid.uuid4())
    return document
