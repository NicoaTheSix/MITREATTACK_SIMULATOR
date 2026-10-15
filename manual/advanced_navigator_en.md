# Advanced Navigator Workflows

## Matrix presentation

Open the matrix from the TTP sidebar. Choose **Flat**, **Side** or **Mini** beside Platform. Flat uses an expandable vertical family tree; Side places parents beside their child lists; Mini groups compact technique squares with their parent. Click to select, double-click for details, hover for names/scores/annotations and right-click for technique actions. Use the small arrow or Expand/Collapse all for children.

Choose **Name ↑ / ↓** or **Score ↑ / ↓**. Score sorting uses the displayed family aggregate when enabled, otherwise the technique score; missing scores count as zero. Sorting changes display order, not scores or selected TTPs. Use **Multiple… / Platforms (…)…** to check several platforms. They form a union; unchecking all shows an empty matrix. The ordinary Platform dropdown is a shortcut for one platform or all platforms. Search combines with platform filters.

Layout, sorting and platform choices belong to the active layer and are saved in Navigator JSON (`layout.layout`, `sorting`, `filters.platforms`) and the full layer in Studio JSON. Switching layers restores those settings. Imported unknown platform names remain in the JSON but have no matching matrix cells. **Show all layers** only combines layers using the same domain, release and dataset identity.

In the all-layer color view, score ordering still uses the active layer's scores/aggregates; color mixing does not create a combined score.

SVG follows the selected layout, platform union, search, sorting and colors and expands all matching children. Excel keeps a readable labeled vertical matrix with the same filtered/sorted cells; its Layer Info sheet identifies the native layout, and Techniques includes Links/Metadata JSON. It does not imitate Mini squares or Side columns.

## Links and Metadata

For independent Enable/Disable controls and multi-technique annotation editing, see [Independent States and Batch Operations](batch_operations_en.md). Export inclusion and enabled state are separate; inclusion no longer generates a default blue color.

Right-click a technique and choose **Edit technique annotation…**. Choose its tactic scope, then use the **Links** and **Metadata** tabs. Links have a label and URL; Metadata has a name and text value. Add/remove rows or dividers, then Save. Save each scope before switching scopes; Cancel discards the current draft. The Include checkbox controls TTP selection separately from annotations.

For example, attach a link labeled `Investigation` to `https://example.org/case/123`, and metadata `Owner = Detection team`, `Confidence = High`. Metadata is visible in technique hover text. Safe HTTP(S) links appear as **Open: …** in the context menu. New or changed links require absolute HTTP(S) URLs without embedded credentials. Other protocols already present in imported data are retained but not opened by this app.

Use **Layer settings… → Layer links / Layer metadata** for layer-level entries. Save updates the layer atomically; invalid entries leave it unchanged. Existing entry extensions and dividers are retained. The app's reserved selection metadata is maintained automatically and excluded from the technique editor. Navigator JSON and Studio JSON preserve full global/scoped annotations, links, metadata and extension fields. CSV remains a selected-TTP report with comments and dataset provenance; use JSON for full structured layer data.

## URL layers and custom STIX

Choose **File → Load layer URL / custom STIX…**. For a Navigator URL, paste a direct HTTP(S) JSON URL and press **Load and validate preview**. Open continues to the existing Navigator import preview, where you choose the layer/selection policy and resolve the recorded ATT&CK release. A website HTML page is not a layer JSON file.

For custom data, choose **Custom STIX Bundle / Collection**, paste a URL or Browse to a JSON file. An ATT&CK Collection Index lists its versions; choose one, then press Load again to fetch that exact Bundle. A Bundle containing `x-mitre-collection` is accepted directly. A standalone collection object with only references must be supplied together with its referenced objects in a Bundle. This is an ATT&CK-compatible catalog loader, not a general-purpose STIX viewer.

Bundles need active techniques with unique domain-specific `T####` / `T####.###` external IDs, names, valid domain kill-chain phases, `x-mitre-tactic`, `x-mitre-matrix`, and consistent `x_mitre_domains`. Sub-techniques need an active single-level parent. Latest STIX object versions are chosen by `modified`; conflicting duplicates, invalid fields and ambiguous IDs fail before a document opens. Collection release metadata takes precedence; otherwise supply a numeric fallback release. Choose an available domain in the preview, then **Open as a new document**.

Operations show the resolved absolute input file or source URL and cache directory before processing, followed by read/parse/validate/cache stages. Validated bytes are atomically cached at `<project-root>/data/attack/custom/<sha256>.json`; official snapshots and `active.json`/`latest.json` are preserved. Navigator inputs are limited to 10 MiB / 20 layers; custom data to 128 MiB / 200,000 objects. HTTP(S) requests have a 20-second socket timeout; redirects must remain HTTP(S). Cancel requests stop at processing checkpoints; errors do not install a partial document.

Custom documents record source and SHA-256 identity in Studio JSON; CSV includes source/hash columns; Navigator JSON includes `customDataURL` and `x_ttp_studio_dataset`. Local sources are absolute local paths, so their Navigator layers are portable together with the Bundle: load the same Bundle first on another machine. Only web URLs are directly usable by the official browser Navigator. A custom layer never silently resolves against same-version official data. Load its matching custom Bundle first, then import the layer; no embedded custom data URL is fetched automatically. Official release switching is offered on official files; load another custom dataset separately or migrate through the review workflow. Ctrl+N always creates an official Enterprise document.

## Reviewed layer upgrades

Choose **Navigator → Review and upgrade layer…**. Select a cached official release, or an open custom dataset in the same domain. To make a different official release available, download it with Version on an official document first. Press **Load target and compare**. All source annotation rows and selected unannotated TTPs are listed. Hover a source ID to inspect its full original annotation. Added target IDs are listed separately and stay unselected until you choose them in the new matrix.

Unchanged mappings start reviewed. Changed techniques, removed tactic scopes, unavailable IDs and replacements require review. Replacement suggestions use explicit STIX `revoked-by` relationships; unavailable/deprecated IDs without that relationship have no guessed replacement. Choose **Copy**, a searchable target technique and target tactic (or All tactics), then mark Reviewed. **Drop** explicitly omits that source annotation row. **Show only rows requiring review** and **Mark visible decisions reviewed** help review larger layers; creation still validates every decision.

Select a source row to inspect the complete before/after field changes and original annotation in the read-only pane below the table. Changes include all catalog fields, so descriptions, mappings and extension changes also require review; the exported decision log records changed field names.

Example: a revoked source ID contains `comment = Lab observation`, a score, color, links and metadata. Copy it to the suggested replacement after checking its meaning and choose a valid target tactic. The new layer receives those annotations and selection status. When multiple rows map to one target scope, compatible data combines, distinct comments are retained and link/metadata duplicates are removed. Conflicting scalar values such as two different scores/colors/enable flags stop creation: remap or Drop one conflicting row. A removed tactic never silently becomes All tactics.

**Create migrated layer** requires all rows to be reviewed and all Copy targets/scopes valid. A new tab uses the target catalog/version; the original file stays unchanged. The source layer is archived in the result, and `x_ttp_studio_upgrade` records each decision. Progress covers comparison, mapping and completion. No file is written until you export. Studio JSON preserves the archive; Navigator JSON preserves the migrated layer and decisions. As elsewhere in this app, session recovery and Studio JSON reopening are not yet implemented—export important work before exit.

See the [project README](../README.md) for startup and audit commands, and the [official Navigator layer format](https://github.com/mitre-attack/attack-navigator/blob/master/layers/spec/v4.5/layerformat.md) for exchange fields.

Custom release numbers identify that dataset's own release: modern custom STIX with version `1.0` still supports Navigator operations. The pre-v4 restriction concerns historical official ATT&CK data. Migration source archives are written under `migration_archives` in Studio JSON with their source domain/version/dataset identity; they cannot automatically restore into a different dataset through Version switching.
