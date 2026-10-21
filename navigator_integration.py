"""Navigator Layer exchange and official SDK comparison. Workflow: README.md."""
from __future__ import annotations

from copy import deepcopy
import importlib.metadata
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import uuid

from attack_catalog import external_id, load_catalog, local_path, tactic_phases, DOMAIN_LABELS, catalog_identity, supports_navigator
from attack_versions import snapshot_pointer
from ttp_documents import TTPDocument, validate_document_name
from navigator_visuals import validate_visuals
from navigator_fields import validate_fields
from domain_model import valid_domain, identifier_pattern, DomainDefinition

LAYER_VERSION = "4.5"
NAVIGATOR_VERSION = "5.2.0"
SELECTION_MARKER = "TTP Selection Studio selected"
SUPPORTED_LAYER_VERSIONS = {"3.0", "4.0", "4.1", "4.2", "4.3", "4.4", "4.5"}


def sdk_version():
    try:
        return importlib.metadata.version("mitreattack-python")
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError("Install dependencies using the workspace requirements.txt.") from error


def validate_layer(payload, catalog=None):
    """Use the official SDK as well as explicit checks; retain raw precision/extensions."""
    from mitreattack.navlayers.core import Layer
    sdk_version()
    if not isinstance(payload, dict) or not isinstance(payload.get("name"), str) or not payload["name"].strip():
        raise ValueError("A Navigator layer needs a non-empty name.")
    if catalog is not None and catalog.dataset_id:
        if payload.get('domain') != catalog.domain or payload.get('x_ttp_studio_dataset', catalog.dataset_id) != catalog.dataset_id:
            raise ValueError('Layer edits must keep the exact domain and dataset.')
        payload = deepcopy(payload)
        payload.update(customDataURL=catalog.custom_source, x_ttp_studio_dataset=catalog.dataset_id)
        if catalog.domain not in DOMAIN_LABELS:
            definition = catalog.domain_definitions[catalog.domain].payload()
            if payload.get('x_ttp_studio_domain', definition) != definition:
                raise ValueError('Layer domain definition differs from its exact Bundle.')
            payload['x_ttp_studio_domain'] = definition
    custom = bool(payload.get('customDataURL') or payload.get('x_ttp_studio_dataset'))
    if (payload.get('domain') not in {*DOMAIN_LABELS, 'mitre-enterprise', 'mitre-mobile'} and
            not (custom and valid_domain(payload.get('domain')))):
        raise ValueError("Unknown Navigator domain.")
    if 'x_ttp_studio_domain' in payload:
        definition = DomainDefinition.read(payload['x_ttp_studio_domain'])
        if definition.id != payload['domain']:
            raise ValueError('Layer domain definition and identifier disagree.')
    validate_visuals(payload)
    validate_fields(payload)
    for flag in ('selectTechniquesAcrossTactics', 'selectSubtechniquesWithParent', 'selectVisibleTechniques'):
        if flag in payload and type(payload[flag]) is not bool:
            raise ValueError(flag + ' must be a boolean.')
    if 'customDataURL' in payload and not isinstance(payload['customDataURL'], str):
        raise ValueError('Custom data source must be a URL/path string.')
    if 'x_ttp_studio_dataset' in payload and (not isinstance(payload['x_ttp_studio_dataset'], str) or
                                            not re.fullmatch(r'[0-9a-f]{64}', payload['x_ttp_studio_dataset'])):
        raise ValueError('Custom dataset identity must be a SHA-256 digest.')
    versions = payload.get("versions", {})
    if not isinstance(versions, dict) or versions.get("layer", payload.get("version", "4.5")) not in SUPPORTED_LAYER_VERSIONS:
        raise ValueError("Unsupported Navigator Layer version; supported: 3.0–4.5.")
    rows = payload.get("techniques", [])
    if not isinstance(rows, list) or len(rows) > 20000:
        raise ValueError("Expected at most 20,000 technique rows.")
    for row in rows:
        validate_fields(row) if isinstance(row, dict) else None
        if not isinstance(row, dict) or not isinstance(row.get('techniqueID'), str) or not re.fullmatch(identifier_pattern(custom), row['techniqueID']):
            raise ValueError("Invalid techniqueID in Navigator layer.")
        if "enabled" in row and type(row["enabled"]) is not bool:
            raise ValueError("Technique enabled must be a boolean.")
        if "score" in row and (type(row["score"]) not in {int, float} or not math.isfinite(row["score"])):
            raise ValueError("Technique scores must be finite numbers.")
        if "color" in row and not re.fullmatch(r"(?:#[0-9a-fA-F]{6})?", row["color"]):
            raise ValueError("Technique colors must be blank or #RRGGBB.")
        if "comment" in row and not isinstance(row["comment"], str):
            raise ValueError("Technique comments must be text.")
        if "tactic" in row and not isinstance(row["tactic"], str):
            raise ValueError("Technique tactics must be text.")
        if 'showSubtechniques' in row and type(row['showSubtechniques']) is not bool:
            raise ValueError('showSubtechniques must be a boolean.')
    # SDK 6.2.1 currently coerces fractional scores to integers and does not accept
    # customDataURL. Validate a copy, then preserve original data for lossless IO.
    probe = deepcopy(payload)
    probe.pop("customDataURL", None)
    if custom:
        # SDK supports only the official domains and T-prefixed identifiers. Check
        # shared Layer structure on a probe; source-domain/ID checks above stay native.
        probe['domain'] = 'enterprise-attack'
        for row in probe.get('techniques', []):
            row['techniqueID'] = 'T' + row['techniqueID']
    for owner in [probe, *probe.get('techniques', [])]:
        for field in list(owner):
            if field.startswith('x_'):
                owner.pop(field)
    if 'filters' in probe and not probe['filters'].get('platforms'):
        # SDK assumes platforms[0] exists. An explicit empty platform selection
        # is valid for the native matrix and must survive the raw round trip.
        probe.pop('filters')
    # The SDK skips Divider objects in metadata even though Layer 4.5 allows them.
    # Their structure is checked above and retained in the original payload.
    for owner in [probe, *probe.get('techniques', [])]:
        for field in ('metadata', 'links'):
            if field in owner:
                owner[field] = [entry for entry in owner[field] if entry.get('divider') is not True]
    if "gradient" in probe:
        # SDK builds a discrete integer curve. Validate bounded probe data while
        # retaining the actual decimal bounds and alpha colors in the raw layer.
        probe["gradient"]["minValue"], probe["gradient"]["maxValue"] = 0, 100
    if Layer(probe).to_dict() is None:
        raise ValueError("The official MITRE SDK rejected the Navigator layer.")
    json.dumps(payload, allow_nan=False)
    result = deepcopy(payload)
    if "version" in result or result["domain"] in ('mitre-enterprise', 'mitre-mobile'):
        result["domain"] = {"mitre-enterprise": "enterprise-attack", "mitre-mobile": "mobile-attack"}.get(result["domain"], result["domain"])
        result.pop("version", None)
        result["versions"] = {**result.get("versions", {}), "layer": LAYER_VERSION, "navigator": NAVIGATOR_VERSION}
    return result


def read_layers(path, notify):
    path = Path(path).resolve()
    notify(f"Input file: {path}", 0, 0)
    notify("Output files: None (import preview in memory)", 0, 0)
    notify("[Navigator Import 1/4] Reading and validating layer file", 0, 1)
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Navigator import is limited to 10 MB.")
    raw = path.read_bytes()
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    payload = json.loads(raw.decode(encoding), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Invalid number: {value}")))
    layers = payload if isinstance(payload, list) else [payload]
    if not layers or len(layers) > 20:
        raise ValueError("Import one to twenty Navigator layers per file.")
    result = []
    for number, layer in enumerate(layers, 1):
        validated = validate_layer(layer)
        result.append(validated)
        notify("[Navigator Import 1/4] Layer validated by mitreattack-python", number, len(layers))
    return result


def layer_version(layer, fallback):
    value = layer.get("versions", {}).get("attack")
    if value is None:
        return fallback
    if not isinstance(value, str) or not re.fullmatch(r"v?\d+(?:\.\d+)?", value):
        raise ValueError("Layer ATT&CK version must be an explicit release number.")
    value = value.removeprefix("v")
    return value if "." in value else value + ".0"


def selection_flag(row):
    marker = next((entry.get("value") for entry in row.get("metadata", [])
                   if isinstance(entry, dict) and entry.get("name") == SELECTION_MARKER), None)
    return marker == "true" if marker in {"true", "false"} else row.get("enabled", True)


def grouping_scopes(catalog):
    """Structural parents can own expansion in a child's otherwise unmapped tactic."""
    result = {}
    for child,parent in catalog.parents.items():
        result.setdefault(external_id(catalog.records[parent]),set()).update(
            tactic_phases(catalog.records[child],catalog.domain) & catalog.tactics.keys())
    return result


def import_preview(layer, catalog, policy="enabled"):
    if layer["domain"] != catalog.domain:
        raise ValueError("Layer and catalog domains differ.")
    if layer_version(layer, catalog.version) != catalog.version:
        raise ValueError("Layer and catalog versions differ.")
    recorded = layer.get('x_ttp_studio_domain')
    definition = catalog.domain_definitions.get(catalog.domain)
    if recorded is not None and (definition is None or recorded != definition.payload()):
        raise ValueError('Layer domain definition differs from its exact Bundle.')
    lookup = {external_id(obj): key for key, obj in catalog.records.items()}
    selected, rows = set(), []
    grouping = grouping_scopes(catalog)
    for entry in layer.get("techniques", []):
        key = lookup.get(entry["techniqueID"])
        obj = catalog.records.get(key, {})
        phases = tactic_phases(obj, catalog.domain)
        valid_tactic = not entry.get("tactic") or entry["tactic"] in phases
        display_scope = ('showSubtechniques' in entry and entry.get('tactic') in grouping.get(entry['techniqueID'],set()))
        resolved = bool(key) and (valid_tactic or display_scope)
        wanted = (True if policy == "all" else ("score" in entry or bool(entry.get("color")))
                  if policy == "annotated" else selection_flag(entry))
        if not valid_tactic: wanted = False
        if resolved and wanted:
            selected.add(key)
        rows.append({"entry": entry, "name": obj.get("name", "Unknown/inactive technique"), "key": key,
                     "status": "Ready" if resolved else "Tactic mismatch" if key else "Unknown/inactive ID",
                     "selected": resolved and wanted})
    return {"rows": rows, "selected": selected,
            "unresolved": sum(row["status"] != "Ready" for row in rows)}


def imported_document(layer, catalog, policy="enabled"):
    if layer.get('x_ttp_studio_dataset') and layer['x_ttp_studio_dataset'] != catalog.dataset_id:
        raise ValueError('Navigator layer belongs to a different custom dataset.')
    if layer.get('customDataURL') and not catalog.dataset_id:
        raise ValueError('Load the matching custom STIX dataset before importing this layer.')
    preview = import_preview(layer, catalog, policy)
    try:
        name = validate_document_name(layer["name"])
    except ValueError:
        name = "Imported-Layer"
    document = TTPDocument(name, catalog, selected=preview["selected"], navigator_layer=deepcopy(layer),
                       navigator_import_selected={external_id(catalog.records[key]) for key in preview["selected"]})
    from ttp_selection import validate_selection_scopes
    from ttp_search import validate_search_fields
    document.selection_preferences = {'across_tactics': layer.get('selectTechniquesAcrossTactics', True),
                                      'with_family': layer.get('selectSubtechniquesWithParent', False),
                                      'visible_only': layer.get('selectVisibleTechniques', False)}
    if policy == 'enabled':
        document.selection_scopes = validate_selection_scopes(layer.get('x_ttp_studio_selection_scopes', {}), document.selected, catalog)
        if 'x_ttp_studio_selection_scopes' not in layer and not document.selection_preferences['across_tactics']:
            from ttp_selection import assign_cells
            cells = {(row['key'],slug) for row in preview['rows'] if row['selected']
                     for slug in tactic_phases(catalog.records[row['key']],catalog.domain) & catalog.tactics.keys()
                     if not row['entry'].get('tactic') or row['entry']['tactic'] == slug}
            assign_cells(document,cells)
    if 'x_ttp_studio_search_fields' in layer:
        document.search_fields = validate_search_fields(layer['x_ttp_studio_search_fields'])
    return document


def document_layer(document, validate=True):
    if not supports_navigator(document.catalog):
        raise ValueError("Navigator supports ATT&CK v4 and later. Export this historical document as JSON/CSV.")
    layer = deepcopy(document.navigator_layer) if document.navigator_layer else {
        "name": document.name, "domain": document.catalog.domain, "techniques": [],
        "selectTechniquesAcrossTactics": True, "selectSubtechniquesWithParent": False, "hideDisabled": False}
    old_version = layer_version(layer, document.catalog.version)
    if old_version != document.catalog.version:
        raise ValueError("Annotations belong to another ATT&CK version. Export before changing the document's version.")
    layer["name"] = document.name
    layer['selectTechniquesAcrossTactics'] = document.selection_preferences['across_tactics']
    layer['selectSubtechniquesWithParent'] = document.selection_preferences['with_family']
    layer['selectVisibleTechniques'] = document.selection_preferences.get('visible_only', False)
    if document.selection_scopes:
        layer['x_ttp_studio_selection_scopes'] = deepcopy(document.selection_scopes)
    else:
        layer.pop('x_ttp_studio_selection_scopes', None)
    layer['x_ttp_studio_search_fields'] = list(document.search_fields)
    if layer["domain"] != document.catalog.domain:
        raise ValueError("Annotations belong to another ATT&CK domain.")
    layer["domain"] = document.catalog.domain
    layer["versions"] = {"attack": document.catalog.version, "navigator": NAVIGATOR_VERSION, "layer": LAYER_VERSION}
    if document.catalog.dataset_id:
        layer['customDataURL'] = document.catalog.custom_source
        layer['x_ttp_studio_dataset'] = document.catalog.dataset_id
        if document.catalog.domain not in DOMAIN_LABELS:
            layer['x_ttp_studio_domain'] = document.catalog.domain_definitions[document.catalog.domain].payload()
    selected = {external_id(document.catalog.records[key]) for key in document.selected}
    known = {external_id(obj): obj for obj in document.catalog.records.values()}
    grouping = grouping_scopes(document.catalog)
    seen = set()
    for row in layer.get("techniques", []):
        attack_id = row["techniqueID"]
        obj = known.get(attack_id, {})
        phases = tactic_phases(obj, document.catalog.domain)
        valid_scope = attack_id in known and (not row.get("tactic") or row["tactic"] in phases)
        if valid_scope:
            seen.add(attack_id)
        display_scope = 'showSubtechniques' in row and row.get('tactic') in grouping.get(attack_id,set())
        if not valid_scope and not display_scope:
            row["enabled"] = False
        rows_metadata = [entry for entry in row.get("metadata", []) if entry.get("name") != SELECTION_MARKER]
        row["metadata"] = rows_metadata + [{"name": SELECTION_MARKER, "value": str(valid_scope and attack_id in selected).lower()}]
    for attack_id in sorted(selected - seen):
        layer.setdefault("techniques", []).append({"techniqueID": attack_id,
                                                   "metadata": [{"name": SELECTION_MARKER, "value": "true"}]})
    # A partial selection needs explicit tactic rows; copy untouched global annotations.
    for key, slugs in document.selection_scopes.items():
        if key not in document.selected:
            continue
        identity = external_id(document.catalog.records[key])
        rows = layer.setdefault('techniques', [])
        global_row = next((row for row in reversed(rows) if row['techniqueID'] == identity and not row.get('tactic')), {'techniqueID': identity})
        for slug in slugs:
            if not any(row['techniqueID'] == identity and row.get('tactic') == slug for row in rows):
                rows.append({**deepcopy(global_row), 'tactic': slug})
        for row in rows:
            if row['techniqueID'] == identity:
                metadata = [entry for entry in row.get('metadata', []) if entry.get('name') != SELECTION_MARKER]
                row['metadata'] = metadata + [{'name':SELECTION_MARKER, 'value':str(row.get('tactic') in slugs).lower()}]
    return validate_layer(layer) if validate else layer


def prune_empty_annotation_rows(document, candidate, rows):
    """Drop emptied annotation rows without changing imported enabled scopes."""
    empty_rows = [row for row in rows if set(row) <= {'techniqueID', 'tactic', 'comment'} and not row.get('comment')]
    if not empty_rows:
        return
    removing = {id(row) for row in empty_rows}
    remaining = [row for row in candidate['techniques'] if id(row) not in removing]
    enabled_ids = {row['techniqueID'] for row in remaining if row.get('enabled', True)}
    disabled_ids = {row['techniqueID'] for row in remaining if row.get('enabled') is False}
    for row in empty_rows:
        attack_id = row['techniqueID']
        if (attack_id in disabled_ids
                and attack_id not in enabled_ids):
            # This implicit enabled scope determines how the surviving
            # imported disabled scopes are interpreted during projection.
            row['enabled'] = True
            removing.remove(id(row))
            enabled_ids.add(attack_id)
    candidate['techniques'] = [row for row in candidate['techniques'] if id(row) not in removing]


def update_technique_fields(document, keys, fields, tactic=None):
    """Update fields atomically; removing absent fields never synthesizes a row."""
    if not keys or not set(keys) <= document.catalog.records.keys():
        raise ValueError("Choose techniques in the active document's domain and version.")
    candidate = deepcopy(document.navigator_layer) if document.navigator_layer else {
        "name": document.name, "domain": document.catalog.domain,
        "versions": {"attack": document.catalog.version, "navigator": NAVIGATOR_VERSION, "layer": LAYER_VERSION},
        "techniques": [], "selectSubtechniquesWithParent": False}
    if candidate["domain"] != document.catalog.domain or layer_version(candidate, document.catalog.version) != document.catalog.version:
        raise ValueError("Annotations belong to another domain or version.")
    if not set(fields) <= {"color", "score"}:
        raise ValueError("Unsupported technique field.")
    removals = {name for name, value in fields.items()
                if value is None or (name == 'color' and value == '')}
    assignments = set(fields) - removals
    changed = False
    empty_rows = []
    candidate.setdefault('techniques', [])
    for key in keys:
        obj = document.catalog.records[key]
        if tactic is not None and tactic and tactic not in tactic_phases(obj, document.catalog.domain):
            raise ValueError("This technique is not mapped to that tactic.")
        attack_id = external_id(obj)
        rows = [row for row in candidate["techniques"] if row["techniqueID"] == attack_id
                and (tactic is None or row.get("tactic", "") == tactic)]
        # A technique-wide assignment also needs an all-tactic row when the
        # imported layer only contains specific scopes. Clears never add rows.
        if assignments and (not rows or (tactic is None and not any(not row.get('tactic') for row in rows))):
            row = {"techniqueID": attack_id}
            if tactic:
                row["tactic"] = tactic
            candidate["techniques"].append(row)
            rows.append(row)
            changed = True
        for row in rows:
            removed = False
            for name, value in fields.items():
                if name in removals:
                    # An empty stored color is already clear. Leave its source
                    # representation untouched so an ineffective clear is a no-op.
                    if name in row and (name != 'color' or row[name]):
                        row.pop(name)
                        changed = True
                        removed = True
                elif row.get(name) != value:
                    row[name] = value
                    changed = True
            # A color-only row must disappear after a technique-wide clear.
            # Keeping just its identity suppresses normal selection styling
            # and synthesizes a grey disabled cell when unchecked. Preserve
            # meaningful imported fields and explicitly edited tactic scopes.
            if removed and tactic is None:
                empty_rows.append(row)
    if not changed:
        return False
    prune_empty_annotation_rows(document, candidate, empty_rows)
    validated = validate_layer(candidate, document.catalog)
    document.navigator_layer = validated
    return True


def export_layers(documents, target, notify, *, visible_only=False, visibility_contexts=None):
    notify("Input files: None (open document layers in memory)", 0, 0)
    notify(f"Output file: {Path(target).expanduser().resolve()}", 0, 0)
    if not 1 <= len(documents) <= 20:
        raise ValueError("Export one to twenty open layers per Navigator bundle.")
    from json_annotation_export import annotation_export_plan
    if visibility_contexts is None:
        visibility_contexts = [None] * len(documents)
    if len(visibility_contexts) != len(documents):
        raise ValueError('Each layer needs its own visibility context.')
    layers = []
    for number, document in enumerate(documents, 1):
        notify("[Layers 1/2] Validating open layers", number - 1, len(documents))
        plan = annotation_export_plan(document, visibility_contexts[number - 1], notify)
        notify(f'[Layers Export] {document.name}: hidden modified annotation cells: {len(plan.hidden_modified)}; '
               + ('omitting hidden annotations' if visible_only else 'preserving all annotations'), number, len(documents))
        layers.append(plan.payload(visible_only))
    result = write_json_atomic(layers, target, notify, "All Layers Export")
    notify("[Layers 2/2] Complete; document names and save states preserved", 2, 2)
    return result


def write_json_atomic(payload, target, notify, label="Navigator Export"):
    target = Path(target).expanduser().resolve()
    if target.suffix.casefold() != ".json":
        target = target.with_name(target.name + ".json")
    temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
    notify("Input files: None (validated in-memory data)", 0, 0)
    notify(f"Output file: {target}", 0, 0)
    notify(f"Temporary output file: {temporary}", 0, 0)
    notify(f"[{label} 1/3] Serializing data", 0, 3)
    content = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    try:
        notify(f"[{label} 2/3] Writing UTF-8 JSON", 1, 3)
        with temporary.open("x", encoding="utf-8", newline="") as stream:
            stream.write(content)
        notify(f"[{label} 3/3] Publishing file", 2, 3)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    notify(f"[{label} 3/3] Complete: {target}", 3, 3)
    return target


def export_layer(document, target, notify, *, visible_only=False, visibility=None):
    notify("Input files: None (document and annotation data in memory)", 0, 0)
    notify(f"Output file: {Path(target).expanduser().resolve()}", 0, 0)
    notify("[Navigator Export Prepare] Validating with the official SDK", 0, 1)
    from json_annotation_export import annotation_export_plan
    plan = annotation_export_plan(document, visibility, notify)
    notify(f'[Navigator Export] Hidden modified annotation cells: {len(plan.hidden_modified)}; '
           + ('omitting hidden annotations' if visible_only else 'preserving all annotations'), 1, 1)
    payload = plan.payload(visible_only)
    path = write_json_atomic(payload, target, notify)
    document.export_path = path
    document.export_format = "navigator"
    notify('[Navigator Export] Exchange file written; use Save / Save As to mark the complete Studio document saved.', 1, 1)
    if document.navigator_snapshots or document.domain_snapshots or document.migration_archives:
        notify('[Navigator Export] Other-domain/version data remain in memory; export Studio JSON to preserve all archives.', 1, 1)
    return path


def update_annotation(document, key, tactic, comment, score, color, links=None, metadata=None):
    attack_id = external_id(document.catalog.records[key])
    candidate = deepcopy(document.navigator_layer)
    if not candidate:
        candidate = {"name": document.name, "domain": document.catalog.domain,
                                    "versions": {"attack": document.catalog.version, "layer": LAYER_VERSION,
                                                 "navigator": NAVIGATOR_VERSION}, "techniques": []}
    if layer_version(candidate, document.catalog.version) != document.catalog.version:
        raise ValueError("Annotations belong to another ATT&CK version.")
    rows = candidate.setdefault("techniques", [])
    matches = [row for row in rows if row["techniqueID"] == attack_id and row.get("tactic", "") == tactic]
    if not matches:
        global_row = next((row for row in reversed(rows) if row['techniqueID'] == attack_id and not row.get('tactic')), {})
        entry = deepcopy(global_row) if tactic else {"techniqueID": attack_id}
        entry['techniqueID'] = attack_id
        if tactic:
            entry["tactic"] = tactic
        rows.append(entry)
        matches = [entry]
    for entry in matches:
        for field, value in (('links', links), ('metadata', metadata)):
            if value is not None:
                if value:
                    entry[field] = deepcopy(value)
                else:
                    entry.pop(field, None)
        if comment:
            entry["comment"] = comment
        else:
            entry.pop('comment', None)
        for field, value in (("score", score), ("color", color)):
            if value is None or value == "":
                entry.pop(field, None)
            else:
                entry[field] = value
    if not tactic:
        prune_empty_annotation_rows(document, candidate, matches)
    candidate = validate_layer(candidate, document.catalog)
    document.navigator_layer = candidate


def compare_documents(left, right):
    if left.catalog.dataset_id != right.catalog.dataset_id:
        raise ValueError('Selection comparison requires the same dataset.')
    if left.catalog.domain != right.catalog.domain:
        raise ValueError("Selection comparison requires matching ATT&CK domains.")
    if left.catalog.version != right.catalog.version:
        raise ValueError("Selection comparison requires matching ATT&CK versions.")
    if not supports_navigator(left.catalog):
        raise ValueError("Navigator comparison requires ATT&CK v4 or later.")
    a, b = set(left.selected), set(right.selected)
    colors = {"Both": "#66bb6a", "Left only": "#42a5f5", "Right only": "#ffa726"}
    layer = {"name": f"{left.name} vs {right.name}", "domain": left.catalog.domain,
             "versions": {"attack": left.catalog.version, "layer": LAYER_VERSION, "navigator": NAVIGATOR_VERSION},
             "selectSubtechniquesWithParent": False, "techniques": [],
             "legendItems": [{"label": label, "color": color} for label, color in colors.items()]}
    for key in sorted(a | b, key=lambda key: external_id(left.catalog.records[key])):
        label = "Both" if key in a & b else "Left only" if key in a else "Right only"
        layer["techniques"].append({"techniqueID": external_id(left.catalog.records[key]), "color": colors[label],
                                     "comment": label, "enabled": True})
    return validate_layer(layer, left.catalog), {"Both": len(a & b), "Left only": len(a - b), "Right only": len(b - a)}


def compare_versions(root, old_version, new_version, selected_ids, notify, domain="enterprise-attack"):
    """Diff verified local STIX 2.1 bundles through the SDK, without network requests."""
    from mitreattack.diffStix.changelog_helper import DiffStix, AttackChangesEncoder
    from loguru import logger
    logger.disable("mitreattack.diffStix")  # Application stages replace verbose per-object SDK logs.
    root = Path(root).resolve()
    notify("Output files: None (report in memory; SDK staging files are temporary)", 0, 0)
    notify("[Version Compare 1/4] Verifying both local snapshots", 0, 2)
    inputs, catalogs = [], []
    for number, version in enumerate((old_version, new_version), 1):
        pointer = snapshot_pointer(root, version)
        catalogs.append(load_catalog(root, notify, pointer).for_domain(domain))
        inputs.append(local_path(root, pointer[domain.split("-")[0] + "_bundle"]))
        notify("[Version Compare 1/4] Snapshot verified", number, 2)
    staging_root = root.parent.parent / "artifacts"
    staging_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sdk-diff-", dir=staging_root) as directory:
        staging = Path(directory)
        for label, source in zip(("old", "new"), inputs):
            target = staging / label / (domain + ".json")
            notify(f"Input file: {source}", 0, 0)
            notify(f"Temporary output file: {target.resolve()}", 0, 0)
            target.parent.mkdir()
            shutil.copyfile(source, target)
        notify("[Version Compare 2/4] Official SDK comparing STIX 2.1 bundles", 0, 0)
        diff = DiffStix(domains=[domain], old=str(staging / "old"), new=str(staging / "new"))
        notify("[Version Compare 3/4] Building report and selection impact", 0, 1)
        changes = json.loads(json.dumps(diff.get_changes_dict(), cls=AttackChangesEncoder))
        new_ids = {external_id(record) for record in catalogs[1].records.values()}
        report = {"sdk_version": sdk_version(), "stix_format": "2.1", "old_version": old_version,
                  "new_version": new_version, "domain": domain, "changes": changes,
                  "selected_ids": sorted(selected_ids), "unavailable_selected_ids": sorted(set(selected_ids) - new_ids)}
    notify("[Version Compare 4/4] Complete; temporary files removed", 1, 1)
    return report
