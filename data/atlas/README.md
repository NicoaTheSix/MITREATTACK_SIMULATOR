# Pinned MITRE ATLAS data

Official repository: https://github.com/mitre-atlas/atlas-data

Source commit: `3259f388d19cbcca11bacf12a0ef97f4198f711b`; content release `2026.09`; native format `6.0.0`. The unmodified upstream YAML contains 16 tactics, 208 techniques including 88 sub-techniques, 40 mitigations and 73 case studies. Original copyright and Apache-2.0 terms are in the adjacent upstream `LICENSE`. `source.json` records original URLs and SHA-256 checksums.

Absolute source: `D:\MITREATTACK_SIMULATOR\data\atlas\ATLAS-2026.09.yaml`; provenance: `D:\MITREATTACK_SIMULATOR\data\atlas\source.json`. Application flow: **1/3** verify source checksum, **2/3** parse YAML with PyYAML safe loading and preserve native data/relations in an internal catalog projection, **3/3** validate/cache the projection at `D:\MITREATTACK_SIMULATOR\data\attack\custom\<SHA-256>.json`. All paths appear in the application's output before processing. ATT&CK data and active/latest pointers are separate.

The projection retains native case-study objects and relationship fields; it is not upstream's generated STIX. `scripts/download_atlas.py` reproduces the pinned acquisition; its workflow is in `scripts/README.md`. No download occurs during normal UI startup. Future releases require explicit source/schema review and a new provenance record.
