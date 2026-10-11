"""Download the latest official ATT&CK release using only the Python standard library."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from urllib.request import Request, urlopen

REPOSITORY = "mitre-attack/attack-stix-data"
API = f"https://api.github.com/repos/{REPOSITORY}"
DOMAINS = ("enterprise-attack", "mobile-attack", "ics-attack")
MAX_BYTES = 150 * 1024 * 1024


def progress(stage: str, message: str) -> None:
    print(f"[{stage}] {message}", flush=True)


def retry_io(action):
    """Allow bounded retries for transient Windows sharing violations."""
    for attempt in range(12):
        try:
            return action()
        except PermissionError as error:
            if getattr(error, "winerror", None) not in (32, 33) or attempt == 11:
                raise
            progress("File access", f"Windows sharing lock; retry {attempt + 1}/11")
            time.sleep(min(0.5 * (attempt + 1), 2.0))


def cleanup(path: Path) -> None:
    try:
        retry_io(lambda: path.unlink(missing_ok=True))
    except OSError as error:
        progress("Cleanup", f"Could not remove {path}: {error}")


def read_json(path: Path) -> dict:
    def load():
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    return retry_io(load)

def request(url: str):
    return urlopen(Request(url, headers={
        "User-Agent": "MITREATTACK_SIMULATOR-dataset-downloader",
        "Accept": "application/json" if url.startswith(API) else "*/*",
    }), timeout=60)


def fetch_json(url: str) -> dict:
    progress("1/5 Discover", f"Reading {url}")
    with request(url) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Metadata exceeds the download size limit")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")
    return result


def download(url: str, target: Path, stage: str) -> tuple[Path, dict]:
    """Stage bytes in a .part file; the caller validates before publishing."""
    partial = target.with_name(target.name + ".part")
    progress(stage, f"Source: {url}")
    progress(stage, f"Output: {target}")
    digest = hashlib.sha256()
    received = 0
    last_report = time.monotonic()
    try:
        with request(url) as response, retry_io(lambda: partial.open("wb")) as output:
            total = int(response.headers.get("Content-Length") or 0)
            if total > MAX_BYTES:
                raise ValueError("Download exceeds the size limit")
            while chunk := response.read(256 * 1024):
                received += len(chunk)
                if received > MAX_BYTES:
                    raise ValueError("Download exceeds the size limit")
                output.write(chunk)
                digest.update(chunk)
                if time.monotonic() - last_report >= 1:
                    amount = f"{received / total:.0%}" if total else "total unknown"
                    progress(stage, f"{received:,} bytes ({amount})")
                    last_report = time.monotonic()
        if total and received != total:
            raise ValueError(f"Incomplete download: {received} / {total} bytes")
        progress(stage, f"Download complete: {received:,} bytes")
        return partial, {"filename": target.name, "url": url,
                         "bytes": received, "sha256": digest.hexdigest()}
    except BaseException:
        cleanup(partial)
        raise


def write_json(target: Path, value: dict) -> None:
    partial = target.with_name(target.name + ".part")
    try:
        retry_io(lambda: partial.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"))
        retry_io(lambda: partial.replace(target))
    finally:
        cleanup(partial)


def validate_bundle(bundle: dict, version: str, domain: str) -> dict:
    if bundle.get("type") != "bundle" or not isinstance(bundle.get("objects"), list):
        raise ValueError(f"{domain}: expected a STIX bundle with an objects array")
    objects = bundle["objects"]
    if not objects or any(not isinstance(obj, dict) for obj in objects):
        raise ValueError(f"{domain}: empty or malformed objects array")
    collections = [obj for obj in objects if obj.get("type") == "x-mitre-collection"]
    if len(collections) != 1 or collections[0].get("x_mitre_version") != version:
        raise ValueError(f"{domain}: collection version does not match {version}")
    active = [obj for obj in objects if not obj.get("revoked", False)
              and not obj.get("x_mitre_deprecated", False)]
    patterns = [obj for obj in active if obj.get("type") == "attack-pattern"]
    if not patterns or any(domain not in obj.get("x_mitre_domains", []) for obj in patterns):
        raise ValueError(f"{domain}: missing techniques or incorrect domain")
    subtechniques = sum(bool(obj.get("x_mitre_is_subtechnique")) for obj in patterns)
    counts = Counter(obj.get("type", "unknown") for obj in objects)
    return {
        "objects_total": len(objects),
        "object_types": dict(sorted(counts.items())),
        "active_tactics": sum(obj.get("type") == "x-mitre-tactic" for obj in active),
        "active_techniques": len(patterns) - subtechniques,
        "active_subtechniques": subtechniques,
        "active_attack_patterns": len(patterns),
        "excluded_revoked_or_deprecated_objects": len(objects) - len(active),
        "validation": "JSON, bundle structure, collection version, and technique domains checked; not full STIX schema validation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "data" / "attack")
    args = parser.parse_args()
    root = args.output_dir.expanduser().resolve()
    print(f"Python executable: {Path(sys.executable).resolve()}", flush=True)
    print("Input files: None (official HTTPS sources)", flush=True)
    print(f"Output root: {root}", flush=True)
    print("Discovery output files: None (metadata is held in memory)", flush=True)

    release = fetch_json(f"{API}/releases/latest")
    tag = release.get("tag_name", "")
    if release.get("draft") or release.get("prerelease") or not re.fullmatch(r"v\d+\.\d+", tag):
        raise ValueError(f"Unexpected stable release tag: {tag!r}")
    version = tag[1:]
    commit = fetch_json(f"{API}/commits/{tag}")
    sha = commit.get("sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Release commit SHA is missing or malformed")
    progress("1/5 Discover", f"Complete: ATT&CK {tag}, commit {sha}")

    snapshot = root / tag
    raw_root = f"https://raw.githubusercontent.com/{REPOSITORY}/{sha}"
    artifacts = ["index.json", "LICENSE.txt"] + [f"{domain}-{version}.json" for domain in DOMAINS]
    outputs = [snapshot / name for name in artifacts + ["release.json", "manifest.json", "README.md"]]
    outputs.append(root / "latest.json")
    print("Resolved output files (before writing):", flush=True)
    for path in outputs:
        print(f"  {path}", flush=True)
        if path.suffix != ".md":
            print(f"  Temporary: {path.with_name(path.name + '.part')}", flush=True)
    print("Validation input files: downloaded .part files listed above", flush=True)
    progress("2/5 Prepare", f"Creating output directory: {snapshot}")
    snapshot.mkdir(parents=True, exist_ok=True)
    write_json(snapshot / "release.json", {"release": release, "commit_sha": sha})
    progress("2/5 Prepare", "Complete")

    files = []
    temporary: Path | None = None
    try:
        temporary, record = download(f"{raw_root}/index.json", snapshot / "index.json", "3/5 Catalog")
        index = read_json(temporary)
        for domain in DOMAINS:
            expected = f"/{domain}/{domain}-{version}.json"
            matches = [entry for collection in index.get("collections", [])
                       for entry in collection.get("versions", [])
                       if entry.get("version") == version and entry.get("url", "").endswith(expected)]
            if len(matches) != 1:
                raise ValueError(f"Official index does not contain exactly one {domain} {version} entry")
        retry_io(lambda: temporary.replace(snapshot / "index.json"))
        files.append(record)
        progress("3/5 Catalog", "Index validated")
        temporary, record = download(f"{raw_root}/LICENSE.txt", snapshot / "LICENSE.txt", "3/5 Catalog")
        if not temporary.read_text(encoding="utf-8").strip():
            raise ValueError("Empty license file")
        retry_io(lambda: temporary.replace(snapshot / "LICENSE.txt"))
        files.append(record)
        progress("3/5 Catalog", "Complete: index and license saved")

        for number, domain in enumerate(DOMAINS, 1):
            filename = f"{domain}-{version}.json"
            temporary, record = download(f"{raw_root}/{domain}/{filename}", snapshot / filename,
                                         f"4/5 Data {number}/{len(DOMAINS)}")
            progress("4/5 Validate", f"Checking {temporary}")
            bundle = read_json(temporary)
            record["domain"] = domain
            record["statistics"] = validate_bundle(bundle, version, domain)
            retry_io(lambda: temporary.replace(snapshot / filename))
            files.append(record)
            stats = record["statistics"]
            progress("4/5 Validate", f"{domain}: {stats['active_tactics']} tactics, "
                     f"{stats['active_techniques']} techniques, {stats['active_subtechniques']} sub-techniques")

        manifest = {"attack_version": version, "stix_format": "2.1",
                    "repository": f"https://github.com/{REPOSITORY}",
                    "release_url": release["html_url"], "release_published_at": release["published_at"],
                    "commit_sha": sha, "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
                    "files": files}
        progress("5/5 Publish", "Writing manifest and snapshot documentation")
        write_json(snapshot / "manifest.json", manifest)
        rows = ["| Domain | Active tactics | Active techniques | Active sub-techniques |",
                "| --- | ---: | ---: | ---: |"]
        for entry in files:
            if "domain" in entry:
                stats = entry["statistics"]
                rows.append(f"| {entry['domain']} | {stats['active_tactics']} | "
                            f"{stats['active_techniques']} | {stats['active_subtechniques']} |")
        (snapshot / "README.md").write_text(
            f"# ATT&CK {tag} Data Snapshot\n\n"
            f"Official STIX 2.1 data from [{REPOSITORY}](https://github.com/{REPOSITORY}).\n\n"
            f"Release: {release['html_url']}\n\nPublished (UTC): {release['published_at']}\n\n"
            f"Pinned commit: `{sha}`\n\n" + "\n".join(rows) + "\n\n"
            "Counts exclude revoked and deprecated objects; technique counts exclude sub-techniques. "
            "Original bundles retain all objects and relationships.\n\n"
            "`manifest.json` records source URLs, byte sizes, SHA-256 hashes, and validation statistics. "
            "Hashes provide local integrity checks; they are not upstream signatures. "
            "`index.json` and `release.json` preserve source metadata; `LICENSE.txt` preserves MITRE terms.\n\n"
            "Workflow: discover release, pin its commit, show paths, download to temporary files, "
            "validate bundles, publish the manifest, and update the parent `latest.json` pointer. "
            "See `../../../scripts/README.md` for rerun instructions and progress reporting.\n",
            encoding="utf-8")
        write_json(root / "latest.json", {"attack_version": version,
                   "manifest": f"{tag}/manifest.json",
                   "enterprise_bundle": f"{tag}/enterprise-attack-{version}.json",
                   "mobile_bundle": f"{tag}/mobile-attack-{version}.json",
                   "ics_bundle": f"{tag}/ics-attack-{version}.json"})
        progress("5/5 Publish", f"Complete: {snapshot / 'manifest.json'}")
        return 0
    finally:
        if temporary is not None:
            cleanup(temporary)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        progress("Cancelled", "Download interrupted; latest.json was not updated unless publishing completed")
        raise SystemExit(130)
    except Exception as error:
        progress("Failed", f"{type(error).__name__}: {error}")
        raise SystemExit(1)

