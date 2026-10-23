"""Exact-dataset, all-or-nothing Navigator layer drafts. Workflow: README.md."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from attack_versions import prepare_version
from navigator_integration import imported_document, import_preview, layer_version, document_layer, validate_layer
from studio_files import StudioReader
from ttp_documents import TTPDocument

MAX_OPEN_DOCUMENTS = 50


class LayerImportResolver:
    """A preview owns its caches; resolving never changes official pointers or tabs."""
    def __init__(self, root, candidates=()):
        self.root = Path(root).resolve()
        self.candidates = tuple(candidates)
        self.catalogs = {}
        for catalog in candidates:
            self.catalogs.setdefault((catalog.dataset_id, catalog.version), catalog)

    def catalog(self, layer, chosen_version, notify, download=False, discovery=None):
        recorded = layer_version(layer, chosen_version)
        if chosen_version != recorded:
            raise ValueError('The chosen snapshot must match this layer\'s recorded ATT&CK version.')
        source = layer.get('customDataURL', '')
        digest = layer.get('x_ttp_studio_dataset', '')
        custom = bool(source or digest)
        if custom and not digest:
            matches = {catalog.dataset_id: catalog for catalog in self.candidates
                       if catalog.dataset_id and catalog.version == recorded and catalog.custom_source == source
                       and layer['domain'] in catalog.objects_by_domain}
            if len(matches) != 1:
                raise ValueError('Custom URL needs one matching loaded dataset at this version/domain. '
                                 'Choose Resolve custom data… to fetch, validate or choose the matching Bundle. '
                                 'Custom URLs are not fetched automatically.')
            digest = next(iter(matches))
            self.catalogs.setdefault((digest, recorded), matches[digest])
        key = digest, recorded
        if not custom and key not in self.catalogs and download:
            self.catalogs[key] = prepare_version(self.root, recorded, discovery or {}, notify)[0]
        reader = StudioReader(self.root, notify)
        reader.catalogs = self.catalogs
        catalog = reader.catalog({'domain': layer['domain'], 'version': recorded, 'custom': custom,
                                  'dataset_sha256': digest, 'source_url': source})
        if catalog.version != recorded:
            raise ValueError('Resolved catalog does not match the layer\'s exact release.')
        if custom:
            catalog = replace(catalog, custom_source=source or catalog.custom_source)
        return catalog

    def preview(self, layers, indices, versions, policies, notify, download=False, discovery=None):
        notify('Input files: None (validated layers in memory; exact catalog inputs follow)', 0, 0)
        notify('Output files: None (independent layer previews in memory)', 0, 0)
        result = {}
        for number, index in enumerate(indices, 1):
            notify(f'[Layer Batch 2/5] Resolving layer {index + 1}: {layers[index]["name"]}', number - 1, len(indices))
            try:
                if policies[index] not in ('enabled', 'all', 'annotated'):
                    raise ValueError('Choose a supported technique selection policy for each layer.')
                layer = validate_layer(layers[index])
                catalog = self.catalog(layer, versions[index], notify, download, discovery)
                preview = import_preview(layer, catalog, policies[index])
                # Validate selection extensions before marking a layer ready.
                draft = imported_document(layer, catalog, policies[index])
                document_layer(draft)
                result[index] = {'catalog': catalog, 'preview': preview, 'error': ''}
            except InterruptedError:
                raise
            except (ValueError, TypeError, KeyError, OSError) as error:
                result[index] = {'catalog': None, 'preview': None, 'error': str(error)}
            notify(f'[Layer Batch 3/5] Layer {index + 1}: ' + (result[index]['error'] or 'Ready'), number, len(indices))
        return result


def build_import_documents(layers, indices, versions, policies, catalogs, notify):
    """Return every selected draft, or raise before exposing any document."""
    if not indices or len(indices) > 20 or len(set(indices)) != len(indices):
        raise ValueError('Choose one to twenty distinct layers.')
    if any(type(index) is not int or not 0 <= index < len(layers) for index in indices):
        raise ValueError('Layer indices must identify entries in the imported file.')
    notify('Input files: None; output files: None (selected Navigator layers in memory)', 0, 0)
    documents = []
    for number, index in enumerate(indices, 1):
        notify(f'[Layer Batch 4/5] Validating complete draft {number}/{len(indices)}', number - 1, len(indices))
        catalog = catalogs[index]
        if policies[index] not in ('enabled', 'all', 'annotated'):
            raise ValueError('Choose a supported technique selection policy for each layer.')
        if catalog.version != versions[index] or layer_version(layers[index], versions[index]) != catalog.version:
            raise ValueError('A layer preview belongs to another ATT&CK version; preview again.')
        draft = imported_document(validate_layer(deepcopy(layers[index])), catalog, policies[index])
        document_layer(draft)
        documents.append(draft)
    notify('[Layer Batch 4/5] All selected drafts validated; no workspace changes yet', len(indices), len(indices))
    return documents


def validate_import_documents(documents, existing):
    """Preflight the whole install before changing a tab or the active document."""
    if not isinstance(documents, (list, tuple)) or not 1 <= len(documents) <= 20:
        raise ValueError('Open one to twenty validated layers per batch.')
    if len(existing) + len(documents) > MAX_OPEN_DOCUMENTS:
        raise ValueError('Opening this batch would exceed 50 documents. Close some files and retry; no layers were added.')
    identities = {doc.document_id for doc in existing}
    for doc in documents:
        if not isinstance(doc, TTPDocument) or doc.document_id in identities:
            raise ValueError('Imported documents need new, distinct document identities.')
        identities.add(doc.document_id)
        if not doc.selected <= doc.catalog.records.keys():
            raise ValueError('Imported selection contains techniques absent from its exact catalog.')
        # A completed draft must still match its dataset before UI installation.
        layer = doc.navigator_layer
        if layer and (layer['domain'] != doc.catalog.domain or layer_version(layer, doc.catalog.version) != doc.catalog.version
                      or layer.get('x_ttp_studio_dataset', doc.catalog.dataset_id) != doc.catalog.dataset_id):
            raise ValueError('Imported annotations belong to another domain, version or dataset.')
        from car_documents import is_empty_catalog, validate_workspace
        if is_empty_catalog(doc.catalog):
            if doc.navigator_layer or doc.selected or doc.selection_scopes:
                raise ValueError('An empty CAR-only surface cannot contain ATT&CK annotations or selections.')
            validate_workspace(doc.car_workspace)
        else:
            document_layer(doc)
