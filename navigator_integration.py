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

from attack_catalog import external_id, load_catalog, local_path, tactic_phases, DOMAIN_LABELS
from attack_versions import snapshot_pointer
from ttp_documents import TTPDocument, validate_document_name

LAYER_VERSION = "4.5"
NAVIGATOR_VERSION = "5.2.0"
SELECTION_MARKER = "TTP Selection Studio selected"
SUPPORTED_LAYER_VERSIONS = {"3.0", "4.0", "4.1", "4.2", "4.3", "4.4", "4.5"}


def sdk_version():
    try:
        return importlib.metadata.version("mitreattack-python")
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError("Install dependencies using the workspace requirements.txt.") from error


def validate_layer(payload):
    """Use the official SDK as well as explicit checks; retain raw precision/extensions."""
    from mitreattack.navlayers.core import Layer
    sdk_version()
    if not isinstance(payload, dict) or not isinstance(payload.get("name"), str) or not payload["name"].strip():
        raise ValueError("A Navigator layer needs a non-empty name.")
    if payload.get("domain") not in {"enterprise-attack", "mobile-attack", "ics-attack", "mitre-enterprise", "mitre-mobile"}:
        raise ValueError("Unknown Navigator domain.")
    versions = payload.get("versions", {})
    if not isinstance(versions, dict) or versions.get("layer", payload.get("version", "4.5")) not in SUPPORTED_LAYER_VERSIONS:
        raise ValueError("Unsupported Navigator Layer version; supported: 3.0–4.5.")
    rows = payload.get("techniques", [])
    if not isinstance(rows, list) or len(rows) > 20000:
        raise ValueError("Expected at most 20,000 technique rows.")
    for row in rows:
        if not isinstance(row, dict) or not re.fullmatch(r"T\d{4}(?:\.\d{3})?", row.get("techniqueID", "")):
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
    # SDK 6.2.1 currently coerces fractional scores to integers and does not accept
    # customDataURL. Validate a copy, then preserve original data for lossless IO.
    probe = deepcopy(payload)
    probe.pop("customDataURL", None)
    if Layer(probe).to_dict() is None:
        raise ValueError("The official MITRE SDK rejected the Navigator layer.")
    json.dumps(payload, allow_nan=False)
    result = deepcopy(payload)
    if "version" in result or result["domain"].startswith("mitre-"):
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


def import_preview(layer, catalog, policy="enabled"):
    if layer["domain"] != catalog.domain:
        raise ValueError("Layer and catalog domains differ.")
    if layer_version(layer, catalog.version) != catalog.version:
        raise ValueError("Layer and catalog versions differ.")
    lookup = {external_id(obj): key for key, obj in catalog.records.items()}
    selected, rows = set(), []
    for entry in layer.get("techniques", []):
        key = lookup.get(entry["techniqueID"])
        obj = catalog.records.get(key, {})
        phases = tactic_phases(obj, catalog.domain)
        valid_tactic = not entry.get("tactic") or entry["tactic"] in phases
        resolved = bool(key) and valid_tactic
        wanted = (True if policy == "all" else ("score" in entry or bool(entry.get("color")))
                  if policy == "annotated" else selection_flag(entry))
        if resolved and wanted:
            selected.add(key)
        rows.append({"entry": entry, "name": obj.get("name", "Unknown/inactive technique"), "key": key,
                     "status": "Ready" if resolved else "Tactic mismatch" if key else "Unknown/inactive ID",
                     "selected": resolved and wanted})
    return {"rows": rows, "selected": selected,
            "unresolved": sum(row["status"] != "Ready" for row in rows)}


def imported_document(layer, catalog, policy="enabled"):
    preview = import_preview(layer, catalog, policy)
    try:
        name = validate_document_name(layer["name"])
    except ValueError:
        name = "Imported-Layer"
    return TTPDocument(name, catalog, selected=preview["selected"], navigator_layer=deepcopy(layer),
                       navigator_import_selected={external_id(catalog.records[key]) for key in preview["selected"]})


def document_layer(document):
    if float(document.catalog.version) < 4:
        raise ValueError("Navigator supports ATT&CK v4 and later. Export this historical document as JSON/CSV.")
    layer = deepcopy(document.navigator_layer) if document.navigator_layer else {
        "name": document.name, "domain": document.catalog.domain, "techniques": [],
        "selectTechniquesAcrossTactics": True, "selectSubtechniquesWithParent": False, "hideDisabled": False}
    old_version = layer_version(layer, document.catalog.version)
    if old_version != document.catalog.version:
        raise ValueError("Annotations belong to another ATT&CK version. Export before changing the document's version.")
    layer["name"] = document.name
    if layer["domain"] != document.catalog.domain:
        raise ValueError("Annotations belong to another ATT&CK domain.")
    layer["domain"] = document.catalog.domain
    layer["versions"] = {"attack": document.catalog.version, "navigator": NAVIGATOR_VERSION, "layer": LAYER_VERSION}
    selected = {external_id(document.catalog.records[key]) for key in document.selected}
    known = {external_id(obj): obj for obj in document.catalog.records.values()}
    originally_enabled = {row["techniqueID"] for row in layer.get("techniques", []) if row.get("enabled", True)}
    seen = set()
    for row in layer.get("techniques", []):
        attack_id = row["techniqueID"]
        obj = known.get(attack_id, {})
        phases = tactic_phases(obj, document.catalog.domain)
        valid_scope = attack_id in known and (not row.get("tactic") or row["tactic"] in phases)
        if valid_scope:
            seen.add(attack_id)
        if attack_id not in document.navigator_import_selected or attack_id not in selected or attack_id not in originally_enabled:
            row["enabled"] = attack_id in selected
        if not valid_scope:
            row["enabled"] = False
        rows_metadata = [entry for entry in row.get("metadata", []) if entry.get("name") != SELECTION_MARKER]
        row["metadata"] = rows_metadata + [{"name": SELECTION_MARKER, "value": str(attack_id in selected).lower()}]
    for attack_id in sorted(selected - seen):
        layer.setdefault("techniques", []).append({"techniqueID": attack_id, "enabled": True, "color": "#007acc",
                                                   "metadata": [{"name": SELECTION_MARKER, "value": "true"}]})
    return validate_layer(layer)


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


def export_layer(document, target, notify):
    notify("Input files: None (document and annotation data in memory)", 0, 0)
    notify(f"Output file: {Path(target).expanduser().resolve()}", 0, 0)
    notify("[Navigator Export Prepare] Validating with the official SDK", 0, 1)
    payload = document_layer(document)
    payload["name"] = Path(target).stem
    path = write_json_atomic(payload, target, notify)
    document.name = path.stem
    document.export_path = path
    document.export_format = "navigator"
    document.exported_fingerprint = None if document.navigator_snapshots or document.domain_snapshots else document.fingerprint()
    if document.navigator_snapshots or document.domain_snapshots:
        notify('[Navigator Export] Other-domain/version data remain in memory; export Studio JSON to preserve all archives.', 1, 1)
    return path


def update_annotation(document, key, tactic, comment, score, color):
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
        entry = {"techniqueID": attack_id}
        if tactic:
            entry["tactic"] = tactic
        rows.append(entry)
        matches = [entry]
    for entry in matches:
        entry["comment"] = comment
        for field, value in (("score", score), ("color", color)):
            if value is None or value == "":
                entry.pop(field, None)
            else:
                entry[field] = value
    validate_layer(candidate)
    document.navigator_layer = candidate


def compare_documents(left, right):
    if left.catalog.domain != right.catalog.domain:
        raise ValueError("Selection comparison requires matching ATT&CK domains.")
    if left.catalog.version != right.catalog.version:
        raise ValueError("Selection comparison requires matching ATT&CK versions.")
    if int(left.catalog.version.split(".")[0]) < 4:
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
    return validate_layer(layer), {"Both": len(a & b), "Left only": len(a - b), "Right only": len(b - a)}


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
