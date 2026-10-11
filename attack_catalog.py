"""Read a local ATT&CK snapshot and project its platform/tactic/technique relationships."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable

Progress = Callable[[str, int, int], None]

DOMAIN_LABELS = {"enterprise-attack": "Enterprise", "mobile-attack": "Mobile", "ics-attack": "ICS"}
BROWSE_CATEGORIES = {
    "Mitigations": {"course-of-action": "Mitigations"},
    "Assets": {"x-mitre-asset": "Assets"},
    "Detections": {"x-mitre-detection-strategy": "Detection Strategies",
                   "x-mitre-analytic": "Analytics", "x-mitre-data-component": "Data Components"},
    "Groups": {"intrusion-set": "Groups"},
    "Software": {"malware": "Malware", "tool": "Tools"},
    "Campaigns": {"campaign": "Campaigns"},
}


@dataclass
class Catalog:
    version: str
    records: dict[str, dict]
    tactics: dict[str, dict]
    tactic_order: list[str]
    groups: dict[str, dict[str, list[str]]]
    parents: dict[str, str]
    objects_by_domain: dict[str, dict[str, dict]]
    procedures_by_domain: dict[str, dict[str, list[dict]]]


def external_id(record: dict) -> str:
    return next((ref.get("external_id", "") for ref in record.get("external_references", [])
                 if ref.get("source_name") in {"mitre-attack", "mitre-mobile-attack", "mitre-ics-attack"}), "")


def local_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("Missing snapshot path")
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("Snapshot pointer points outside the data directory")
    return result


def index_procedures(objects: list[dict], records: dict[str, dict], notify: Progress, domain: str) -> dict[str, list[dict]]:
    """Index described uses relationships from groups, software and campaigns to active techniques."""
    examples = defaultdict(list)
    source_types = {"intrusion-set", "malware", "tool", "campaign"}
    notify(f"[3/4 Procedures] Indexing {DOMAIN_LABELS[domain]} procedure examples", 0, len(objects))
    for number, relationship in enumerate(objects, 1):
        if number % 4000 == 0:
            notify(f"[3/4 Procedures] Reading {DOMAIN_LABELS[domain]} relationships", number, len(objects))
        if (relationship.get("type") != "relationship" or relationship.get("relationship_type") != "uses"
                or relationship.get("revoked") or relationship.get("x_mitre_deprecated")):
            continue
        source = records.get(relationship.get("source_ref"))
        target = records.get(relationship.get("target_ref"))
        if not source or not target or source.get("type") not in source_types or target.get("type") != "attack-pattern":
            continue
        examples[target["id"]].append({
            "relationship_id": relationship["id"], "source_ref": source["id"],
            "source_id": external_id(source), "source_name": source.get("name", source["id"]),
            "source_type": source["type"], "description": relationship.get("description", ""),
            "references": relationship.get("external_references", []),
        })
    for rows in examples.values():
        rows.sort(key=lambda row: (row["source_id"], row["source_name"], row["relationship_id"]))
    notify(f"[3/4 Procedures] Complete: {DOMAIN_LABELS[domain]} "
           f"{sum(len(rows) for rows in examples.values())} procedure examples", 1, 1)
    return dict(examples)

def load_catalog(root: Path, notify: Progress, pointer=None) -> Catalog:
    root = root.resolve()
    pointer_path = Path(pointer).resolve() if isinstance(pointer, (str, Path)) else root / "latest.json"
    notify(f"Input file: {pointer_path}" if not isinstance(pointer, dict) else "Input pointer: in memory (validated version selection)", 0, 0)
    notify("Output files: None (catalog is loaded into memory)", 0, 0)
    notify("[1/4 Resolve] Reading snapshot pointer", 0, 0)
    pointer = pointer if isinstance(pointer, dict) else json.loads(pointer_path.read_text(encoding="utf-8-sig"))
    manifest_path = local_path(root, pointer["manifest"])
    bundle_path = local_path(root, pointer["enterprise_bundle"])
    for path in (manifest_path, bundle_path):
        notify(f"Input file: {path}", 0, 0)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    version = pointer["attack_version"]
    if manifest.get("attack_version") != version:
        raise ValueError("Snapshot pointer and manifest versions differ")
    entry = next((item for item in manifest["files"]
                  if item.get("domain") == "enterprise-attack" and item["filename"] == bundle_path.name), None)
    if entry is None:
        raise ValueError("Enterprise bundle is missing from the manifest")
    notify(f"[1/4 Resolve] Complete: Enterprise ATT&CK v{version}", 1, 1)

    total = bundle_path.stat().st_size
    digest = hashlib.sha256()
    data = bytearray()
    with bundle_path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            data.extend(chunk)
            digest.update(chunk)
            notify("[2/4 Read] Reading and checking bundle", len(data), total)
    if digest.hexdigest() != entry["sha256"] or len(data) != entry["bytes"]:
        raise ValueError("Enterprise bundle size or SHA-256 does not match the manifest")
    notify("[2/4 Read] Parsing JSON", 0, 0)
    bundle = json.loads(data)
    del data
    objects = bundle.get("objects", [])
    if bundle.get("type") != "bundle" or not isinstance(objects, list):
        raise ValueError("Expected a STIX bundle")
    collection = next((obj for obj in objects if obj.get("type") == "x-mitre-collection"), {})
    if collection.get("x_mitre_version") != version:
        raise ValueError("Bundle collection version does not match the snapshot")
    records, tactics, relationships, matrix = {}, {}, [], []
    for number, obj in enumerate(objects, 1):
        if number % 2000 == 0:
            notify("[3/4 Index] Indexing active ATT&CK objects", number, len(objects))
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        kind = obj.get("type")
        if kind == "attack-pattern" and "enterprise-attack" in obj.get("x_mitre_domains", []):
            records[obj["id"]] = obj
        elif kind == "x-mitre-tactic":
            tactics[obj["x_mitre_shortname"]] = obj
        elif kind == "x-mitre-matrix":
            matrix = obj.get("tactic_refs", [])
        elif kind == "relationship" and obj.get("relationship_type") == "subtechnique-of":
            relationships.append(obj)
    # Early official snapshots predate tactic objects. Derive headings from their
    # own kill-chain phases without borrowing modern records or inventing TA IDs.
    historical_order = ["reconnaissance", "resource-development", "initial-access", "execution", "persistence",
                        "privilege-escalation", "defense-evasion", "credential-access", "discovery",
                        "lateral-movement", "collection", "command-and-control", "exfiltration", "impact"]
    phase_slugs = {phase["phase_name"] for obj in records.values() for phase in obj.get("kill_chain_phases", [])
                   if phase.get("kill_chain_name") == "mitre-attack"}
    missing = phase_slugs - tactics.keys()
    for slug in sorted(missing, key=lambda value: (historical_order.index(value) if value in historical_order else 999, value)):
        tactics[slug] = {"id": "historical-phase--" + slug, "type": "x-mitre-tactic", "x_mitre_shortname": slug,
                         "name": slug.replace("-", " ").title(), "_historical_phase": True}
    if missing:
        notify(f"[3/4 Index] Derived {len(missing)} historical phase headings from this release (no tactic IDs provided)", 1, 1)
    if not records or not tactics:
        raise ValueError("Catalog has no active techniques or tactic phases")
    parents = {obj["source_ref"]: obj["target_ref"] for obj in relationships
               if obj["source_ref"] in records and obj["target_ref"] in records}
    ranks = {ref: index for index, ref in enumerate(matrix)}
    order = sorted(tactics, key=lambda slug: (ranks.get(tactics[slug]["id"], 999),
                    historical_order.index(slug) if slug in historical_order and tactics[slug].get("_historical_phase") else 999, slug))
    groups = defaultdict(lambda: defaultdict(list))
    for number, (stix_id, obj) in enumerate(records.items(), 1):
        if number % 100 == 0:
            notify("[3/4 Index] Mapping platforms and tactics", number, len(records))
        phases = {phase["phase_name"] for phase in obj.get("kill_chain_phases", [])
                  if phase.get("kill_chain_name") == "mitre-attack" and phase["phase_name"] in tactics}
        for platform in obj.get("x_mitre_platforms", []):
            for slug in phases:
                groups[platform][slug].append(stix_id)
    ordered_platforms = sorted(groups, key=lambda value: (value != "Windows", value.casefold()))
    plain_groups = {platform: {slug: sorted(groups[platform][slug], key=lambda key: external_id(records[key]))
                              for slug in order if slug in groups[platform]} for platform in ordered_platforms}
    notify(f"[3/4 Index] Complete: {len(records)} active techniques/sub-techniques, "
           f"{len(plain_groups)} platforms", len(records), len(records))
    objects_by_domain = {"enterprise-attack": {
        obj["id"]: obj for obj in objects if not obj.get("revoked") and not obj.get("x_mitre_deprecated")
        and obj.get("type") != "relationship"
    }}
    procedures_by_domain = {"enterprise-attack": index_procedures(objects, objects_by_domain["enterprise-attack"], notify, "enterprise-attack")}
    for domain, pointer_key in (("mobile-attack", "mobile_bundle"), ("ics-attack", "ics_bundle")):
        if not pointer.get(pointer_key):
            objects_by_domain[domain] = {}
            procedures_by_domain[domain] = {}
            notify(f"[3/4 Library] {DOMAIN_LABELS[domain]} is not available in this historical version", 1, 1)
            continue
        path = local_path(root, pointer[pointer_key])
        notify(f"Input file: {path}", 0, 0)
        metadata = next((item for item in manifest["files"]
                         if item.get("domain") == domain and item["filename"] == path.name), None)
        if metadata is None:
            raise ValueError(f"{domain} bundle is missing from the manifest")
        content = bytearray()
        checksum = hashlib.sha256()
        size = path.stat().st_size
        with path.open("rb") as stream:
            while chunk := stream.read(4 * 1024 * 1024):
                content.extend(chunk)
                checksum.update(chunk)
                notify(f"[3/4 Library] Reading and checking {DOMAIN_LABELS[domain]}", len(content), size)
        if checksum.hexdigest() != metadata["sha256"] or len(content) != metadata["bytes"]:
            raise ValueError(f"{domain} bundle size or SHA-256 does not match the manifest")
        notify(f"[3/4 Library] Parsing {DOMAIN_LABELS[domain]} JSON", 0, 0)
        source = json.loads(content)
        del content
        if source.get("type") != "bundle" or not isinstance(source.get("objects"), list):
            raise ValueError(f"Expected a STIX bundle for {domain}")
        collection = next((obj for obj in source["objects"] if obj.get("type") == "x-mitre-collection"), {})
        if collection.get("x_mitre_version") != version:
            raise ValueError(f"{domain} collection version does not match the snapshot")
        objects_by_domain[domain] = {
            obj["id"]: obj for obj in source["objects"] if not obj.get("revoked")
            and not obj.get("x_mitre_deprecated") and obj.get("type") != "relationship"
        }
        procedures_by_domain[domain] = index_procedures(source["objects"], objects_by_domain[domain], notify, domain)
        notify(f"[3/4 Library] Complete: {DOMAIN_LABELS[domain]}", 1, 1)
    notify("[3/4 Library] Complete: six navigation categories indexed across all three domains", 1, 1)
    return Catalog(version, records, tactics, order, plain_groups, parents, objects_by_domain, procedures_by_domain)


