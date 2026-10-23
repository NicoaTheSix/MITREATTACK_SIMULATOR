# Bundled CAR source provenance

Upstream: https://github.com/mitre-attack/car

Fixed commit: `1b922fe1527d956e222a99473472e594f10f610b`.

`source.json` records the archive URL, archive SHA-256 and original per-file SHA-256 values for 136 retained files. Native records comprise 102 analytics, 13 data model objects and seven sensor records. Original source files, including this directory's upstream `README.md`, are unchanged. This provenance note and `source.json` are Fusion Studio additions outside that original file list.

The source is Apache License 2.0; retain and distribute [LICENSE.txt](LICENSE.txt) and [NOTICE.txt](NOTICE.txt). Source MITRE copyright and case number are in NOTICE. The CAR name and source attribution do not imply MITRE endorsement of Fusion Studio.

Acquisition: `scripts/download_car.py` reads the fixed codeload archive, checks bounded entries and allowed paths, writes native files and source/license material, hashes every retained file and publishes the manifest. It displays the absolute target and stage/file progress. It does not run upstream generators. Normal startup validates local hashes, parses YAML and builds memory indexes without downloading. See the [application workflow](../../README.md#car-integration) and [source acquisition workflow](../../scripts/README.md).

Grouping follows `scripts/generate_analytics.py` from this snapshot: first coverage entry per parent, absent sub-techniques in the technique-only bucket, explicit children in their own buckets. An explicitly empty child list produces no bucket. Native duplicate coverage remains in detail records. Sensor candidates follow `scripts/generate_sensors.py`: any exact intersection with native mapping triples, not a completeness guarantee. The acceptance audit compares every generated grouping against the fixed pure bucket loop.

The runtime dataset identity is SHA-256 of canonical, key-sorted JSON containing `commit` and `files` (Python default separators): `17ce7482f4396492aba8e7c18cb7df54093eec6b65742d2fd64462efc9badc63`. Workspace entries retain that identity and commit, plus the native analytic snapshot. Verification and acquisition logs are in `artifacts/car-integration/` and `artifacts/car-source-acquisition.log` relative to the application root.
