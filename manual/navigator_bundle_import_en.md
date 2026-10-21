# Open Multiple Navigator JSON Layers

## Open a complete bundle

1. Choose **File → Import Navigator Layer…** or press **Ctrl+Alt+O**. This is distinct from Studio JSON Open / Ctrl+O.
2. Choose a local Navigator JSON file containing one layer object or an array of 1–20 layers. UTF-8/BOM and UTF-16/BOM are supported; the file limit is 10 MiB. Each layer is validated before any documents open. A malformed layer rejects the entire file.
3. All layers are checked by default. **Select all layers** checks the entire list; **Deselect all layers** clears it. You can check individual rows for an explicit subset.
4. Click a row or use **Layer preview** to inspect its techniques. The list shows each layer's name, domain/version, source dataset and readiness/error. Hover a truncated status or dataset cell to read its complete text. Same-name layers remain separate.
5. Once every checked layer is ready, click **Open selected layers**. They open together as independent file tabs in JSON order, with the first checked layer active. Existing tabs, selections and annotations remain in place.

Unchecked layers are excluded only by your explicit choice. The importer never silently omits a checked layer to get past an error. An empty checkbox selection cannot open. The workspace supports at most 50 documents: a group that would exceed this is rejected whole.

## Independent domains, versions and selection policies

Each layer resolves against its own official or [custom domain](custom_domains_en.md), exact release and dataset identity. Custom domain definitions and ID mappings come from the exact Bundle. Changing preview focus restores that layer's version and policy; it does not switch the active workspace document.

A recorded ATT&CK version is fixed. Verified cached versions are previewed automatically, including releases different from the active file. If a required official snapshot is unavailable, **Load selected versions / Preview** explicitly prepares it using the existing version loader. It validates/downloads the snapshot cache without switching official `active.json` / `latest.json` pointers. If no version was recorded, choose a version for that layer; the current release is the initial choice. The table marks readiness using the preview's chosen version.

**Select techniques** is independent for each layer:

- **Enabled rows / saved Studio selection** restores inclusion markers when present; enabled state remains independent.
- **All listed rows** includes resolved rows even when disabled.
- **Rows with a score or color** includes resolved scored/colored rows; zero is a score.

The focused preview counts unique included TTPs and unresolved rows. Unknown/inactive IDs and tactic mismatches remain annotation rows and are excluded from selection. Comments, decimal scores, colors, enabled states, Links, Metadata, custom fields and tactic-specific annotations remain intact. Same-name layers receive different document UUIDs and are not merged.

## Custom sources

A layer with `x_ttp_studio_dataset` uses an exact loaded dataset or the hash-verified local Bundle at `<project-root>/data/attack/custom/<sha256>.json`. Its domain and recorded version must also match. This works even when that cached custom Bundle is not already open.

A legacy layer with only `customDataURL` can resolve automatically when one unambiguous loaded custom dataset matches that exact source string, release and domain. Multiple dataset hashes sharing the same source are ambiguous until explicitly resolved. A missing Bundle, hash mismatch, unavailable domain or incompatible release is shown on the corresponding row and blocks all checked layers. No official catalog is substituted for custom data.

To supply missing custom data, keep the preview open, focus that layer and press **Resolve custom data…**. Fetch its URL, Browse a local Bundle or validate a selected cache. Collection Index versions are explicit choices. Review domain/release, expected/actual digest, final source and unresolved rows, then **Use verified Bundle** to pin the source for that layer. A changed digest requires explicit replacement consent; no URL is fetched automatically. Cancel leaves the previous binding intact. See the [source-resolution guide](custom_data_url_import_en.md).

## Example

A file contains Enterprise v20.0, Mobile v11.3, a custom ICS layer and a second Enterprise layer with the same display name. Leave all four checked. Review each row's domain/version/source, resolve any missing snapshots, then click **Open selected layers** once. Four independent tabs open in array order.

If the custom ICS Bundle is missing, none of the checked layers open. Supply that Bundle and retry, or explicitly uncheck only that layer to open the other three. Cancel opens none. Importing the same file again creates additional independent documents within the 50-document limit.

## Files, progress and recovery

The input JSON path is displayed as an absolute path. Import previews report no output files; exact cached Bundle/manifest paths are announced as read. Progress covers **1/5 read/validate → 2/5 resolve each layer → 3/5 preview results → 4/5 validate every selected draft → 5/5 install the complete group**. Snapshot preparation announces its own absolute cache/staging outputs before writing. Preparing datasets and opening documents are separate: cancelled preparation can leave successfully verified caches, while no partial document group is installed.

Cancellation before deferred reading prevents file IO. Cancellation during resolution/draft preparation stops at worker checkpoints. Failed validation opens nothing; an insertion failure removes every inserted tab and restores the previous document list/active tab. Import does not write a Studio save or exchange file. The usual session checkpoint later records the new documents, including their independent domains, versions and datasets; keep deliberate Studio saves for durable editable copies.

Verification: run `audit_navigator_bundle.py` with the project's Python and `QT_QPA_PLATFORM=offscreen`. It reads cached official releases and isolated custom fixtures, announces absolute inputs/outputs and writes examples, preview screenshots and `audit.json` under `<project-root>/artifacts/navigator-bundle`. It checks mixed releases/domains, duplicate names, per-layer choices, custom source ambiguity/hash failures, cancellation, full-file/draft rejection, rollback, capacity and Studio/Navigator/session round trips.

[All guides](README.md) · [Studio files and recovery](studio_files_en.md) · [Custom sources and migration](advanced_navigator_en.md)
