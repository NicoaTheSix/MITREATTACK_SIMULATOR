"""Discover, download and validate official ATT&CK versions. Workflow: README.md."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import time
from urllib.request import Request, urlopen
import uuid

from attack_catalog import DOMAIN_LABELS, load_catalog, local_path
from scripts.download_attack_data import validate_bundle, write_json

REPO = "mitre-attack/attack-stix-data"
RAW = f"https://raw.githubusercontent.com/{REPO}"
API = f"https://api.github.com/repos/{REPO}"
LIMIT = 150 * 1024 * 1024


def version_key(version):
    return tuple(int(part) for part in version.split("."))


def parse_versions(index):
    """Keep every Enterprise release, with only exactly matching domain releases."""
    by_version = {}
    for collection in index.get("collections", []):
        for entry in collection.get("versions", []):
            version = entry.get("version", "")
            if not re.fullmatch(r"\d+\.\d+", version):
                continue
            for domain in DOMAIN_LABELS:
                expected = f"{RAW}/master/{domain}/{domain}-{version}.json"
                if entry.get("url") == expected:
                    domains = by_version.setdefault(version, {})
                    if domain in domains:
                        raise ValueError(f"Duplicate index entry: {domain} {version}")
                    domains[domain] = dict(entry)
    result = [{"version": version, "domains": domains}
              for version, domains in by_version.items() if "enterprise-attack" in domains]
    if not result:
        raise ValueError("Official index contains no Enterprise releases")
    return sorted(result, key=lambda row: version_key(row["version"]), reverse=True)


def fetch(url, notify, target=None):
    notify(f"[Version transfer] Input URL: {url}", 0, 0)
    notify(f"Output file: {target.resolve() if target else 'None (metadata in memory)'}", 0, 0)
    request = Request(url, headers={"User-Agent": "MITREATTACK_SIMULATOR-version-browser", "Accept": "application/json"})
    content = bytearray()
    last = time.monotonic()
    with urlopen(request, timeout=30) as response:
        size = int(response.headers.get("Content-Length") or 0)
        if size > LIMIT:
            raise ValueError("Official file exceeds size limit")
        while chunk := response.read(256 * 1024):
            content.extend(chunk)
            if len(content) > LIMIT:
                raise ValueError("Official file exceeds size limit")
            if time.monotonic() - last > 0.5:
                notify(f"[Version transfer] {len(content):,} bytes", len(content), size)
                last = time.monotonic()
    if size and len(content) != size:
        raise ValueError("Incomplete official download")
    if target:
        target.write_bytes(content)
    notify(f"[Version transfer] Complete: {len(content):,} bytes", 1, 1)
    return content


def cached_discovery(root, notify):
    root = root.resolve()
    candidates = [root / "versions-cache.json"]
    candidates.extend(sorted(root.glob("v*/index.json"), reverse=True))
    for path in candidates:
        try:
            notify(f"Input file: {path.resolve()}", 0, 0)
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            if path.name == "versions-cache.json":
                sha, index = value["commit_sha"], value["index"]
            else:
                manifest = path.parent / "manifest.json"
                notify(f"Input file: {manifest.resolve()}", 0, 0)
                sha = json.loads(manifest.read_text(encoding="utf-8-sig"))["commit_sha"]
                index = value
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
                continue
            rows = parse_versions(index)
            return {"commit_sha": sha, "index": index, "versions": rows,
                    "source": f"Cached official index: {path.resolve()}"}
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return {"versions": [], "source": "No cached official index; refresh online."}


def discover_versions(root, notify):
    root = root.resolve()
    notify("[Version 1/4 Discover] Input files: None (official HTTPS metadata)", 0, 0)
    cache = root / "versions-cache.json"
    notify(f"Output file: {cache}; temporary: {cache.with_name(cache.name + '.part')}", 0, 0)
    try:
        commit = json.loads(fetch(f"{API}/commits/master", notify))
        sha = commit.get("sha", "")
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("Invalid upstream commit")
        index = json.loads(fetch(f"{RAW}/{sha}/index.json", notify))
        rows = parse_versions(index)
    except InterruptedError:
        raise
    except Exception as error:
        value = cached_discovery(root, notify)
        if not value["versions"]:
            raise
        value["source"] = f"Offline / refresh failed ({type(error).__name__}); {value['source']}"
        notify(f"[Version 1/4 Discover] {value['source']}", 1, 1)
        return value
    root.mkdir(parents=True, exist_ok=True)
    write_json(cache, {"commit_sha": sha, "checked_at_utc": datetime.now(timezone.utc).isoformat(), "index": index})
    notify(f"[Version 1/4 Discover] Complete: {len(rows)} available Enterprise versions", 1, 1)
    return {"commit_sha": sha, "index": index, "versions": rows, "source": "Live official index (commit " + sha[:12] + ")"}


def snapshot_pointer(root, version):
    if not re.fullmatch(r"\d+\.\d+", version):
        raise ValueError("Invalid ATT&CK version")
    path = root.resolve() / f"v{version}" / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    if manifest.get("attack_version") != version:
        raise ValueError("Manifest version mismatch")
    pointer = {"attack_version": version, "manifest": str(path.relative_to(root.resolve())).replace("\\", "/")}
    for entry in manifest["files"]:
        domain = entry.get("domain")
        if domain in DOMAIN_LABELS:
            bundle = local_path(path.parent, entry["filename"])
            pointer[domain.split("-")[0] + "_bundle"] = str(bundle.relative_to(root.resolve())).replace("\\", "/")
    if "enterprise_bundle" not in pointer:
        raise ValueError("Enterprise bundle missing")
    return pointer


def local_versions(root):
    versions = set()
    for path in root.glob("v*/manifest.json"):
        try:
            version = path.parent.name[1:]
            snapshot_pointer(root, version)
            versions.add(version)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return versions


def prepare_version(root, version, discovery, notify):
    """Validate a cached snapshot or publish a fully checked new snapshot before use."""
    root = root.resolve()
    if not re.fullmatch(r"\d+\.\d+", version):
        raise ValueError("Invalid version")
    snapshot = root / f"v{version}"
    notify(f"[Version 2/4 Prepare] Input directory: {snapshot}", 0, 0)
    notify("Output files: None for a valid cached snapshot", 0, 0)
    if snapshot.exists():
        try:
            pointer = snapshot_pointer(root, version)
            catalog = load_catalog(root, notify, pointer)
            notify("[Version 3/4 Validate] Cached snapshot verified", 1, 1)
            return catalog, pointer
        except InterruptedError:
            raise
        except Exception as error:
            # Preserve damaged snapshots as evidence; do not overwrite them in place.
            raise ValueError(f"Cached v{version} cannot be used: {error}. Move its directory aside and retry.") from error
    row = next((row for row in discovery.get("versions", []) if row["version"] == version), None)
    sha = discovery.get("commit_sha", "")
    if row is None or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Version is absent from the official index; refresh the version list")
    staging = root / (f".v{version}-" + uuid.uuid4().hex)
    artifacts = ["index.json", "LICENSE.txt"] + [f"{domain}-{version}.json" for domain in row["domains"]]
    notify("[Version 2/4 Prepare] Resolved output paths before writing", 0, 0)
    for name in artifacts + ["manifest.json", "README.md"]:
        notify(f"Output file: {snapshot / name}; staging: {staging / name}", 0, 0)
    staging.mkdir(parents=True)
    try:
        files = []
        for number, name in enumerate(artifacts, 1):
            domain = next((domain for domain in row["domains"] if name == f"{domain}-{version}.json"), None)
            relative = f"{domain}/{name}" if domain else name
            url = f"{RAW}/{sha}/{relative}"
            notify(f"[Version 2/4 Download] {name}", number, len(artifacts))
            content = fetch(url, notify, staging / name)
            entry = {"filename": name, "url": url, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
            notify(f"[Version 3/4 Validate] Checking {name}", number, len(artifacts))
            if domain:
                entry["domain"] = domain
                entry["statistics"] = validate_bundle(json.loads(content), version, domain)
            elif name == "index.json":
                if not any(item["version"] == version for item in parse_versions(json.loads(content))):
                    raise ValueError("Pinned index no longer contains requested version")
            elif not content.decode("utf-8").strip():
                raise ValueError("Empty upstream license")
            files.append(entry)
        manifest = {"attack_version": version, "stix_format": "2.1", "repository": f"https://github.com/{REPO}",
                    "commit_sha": sha, "downloaded_at_utc": datetime.now(timezone.utc).isoformat(), "files": files}
        write_json(staging / "manifest.json", manifest)
        (staging / "README.md").write_text(
            f"# ATT&CK v{version} snapshot\n\nOfficial STIX 2.1 data pinned to `{sha}`.\n\n"
            "Available domains: " + ", ".join(row["domains"]) + ".\n\n"
            "Workflow: show absolute paths, download to staging, check bundle versions and domains, "
            "record sizes/hashes, load the catalog, then publish the directory. The desktop writes active.json "
            "only after successful validation. Missing historical domains stay empty. See ../../../README.md.\n",
            encoding="utf-8")
        # Validate the entire prospective catalog while the published cache is unchanged.
        staged_pointer = {"attack_version": version, "manifest": staging.name + "/manifest.json"}
        for domain in row["domains"]:
            staged_pointer[domain.split("-")[0] + "_bundle"] = staging.name + f"/{domain}-{version}.json"
        catalog = load_catalog(root, notify, staged_pointer)
        notify("[Version 3/4 Validate] Publishing fully validated snapshot", 1, 1)
        staging.rename(snapshot)
        return catalog, snapshot_pointer(root, version)
    finally:
        if staging.exists():
            # Target is generated directly inside the chosen data root, never supplied by index data.
            if staging.resolve().parent != root or not staging.name.startswith(".v"):
                raise ValueError("Unexpected staging path")
            shutil.rmtree(staging)
