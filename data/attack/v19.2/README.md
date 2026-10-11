# ATT&CK v19.2 Data Snapshot

Official STIX 2.1 data from [mitre-attack/attack-stix-data](https://github.com/mitre-attack/attack-stix-data).

Release: https://github.com/mitre-attack/attack-stix-data/releases/tag/v19.2

Published (UTC): 2026-08-05T22:58:54Z

Pinned commit: `6cda5ad8462c79e14fbb872f4e09059b18e0cfc4`

| Domain | Active tactics | Active techniques | Active sub-techniques |
| --- | ---: | ---: | ---: |
| enterprise-attack | 15 | 222 | 475 |
| mobile-attack | 12 | 77 | 47 |
| ics-attack | 12 | 79 | 18 |

Counts exclude revoked and deprecated objects; technique counts exclude sub-techniques. Original bundles retain all objects and relationships.

`manifest.json` records source URLs, byte sizes, SHA-256 hashes, and validation statistics. Hashes provide local integrity checks; they are not upstream signatures. `index.json` and `release.json` preserve source metadata; `LICENSE.txt` preserves MITRE terms.

Workflow: discover release, pin its commit, show paths, download to temporary files, validate bundles, publish the manifest, and update the parent `latest.json` pointer. See `../../../scripts/README.md` for rerun instructions and progress reporting.
