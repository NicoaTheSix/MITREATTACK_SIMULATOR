# MITRE ATT&CK Behavior Structure Simulator

A PySide6 desktop application for cybersecurity research that browses official MITRE ATT&CK data and lets researchers select techniques for a prospective behavior profile.

## Project Status

The current application provides a VS Code-inspired workspace, an Enterprise Platform → Tactic → Technique tree with nested sub-techniques, ID/name search, synchronized in-memory selections, technique details, Procedure Examples, and title/description copy actions. The far-left navigation rail provides Mitigations, Assets, Detections, Groups, Software, and Campaigns across available Enterprise, Mobile, and ICS data. The Version picker discovers official Enterprise releases, downloads and validates snapshots, supports offline switching to downloaded versions, and remembers the selected version.

This README documents implemented functionality, startup commands, inputs, outputs, progress, and verification. Remaining requirements and future design proposals are maintained in [NOTIMPLEMENTYET.md](NOTIMPLEMENTYET.md), including incomplete portions of otherwise working features.

The local Python virtual environment is `C:\Users\nick5\MITREATTACK_SIMULATOR`. The current interface uses English labels and original ATT&CK names. Technique selections are stored in memory; the selected dataset version is saved separately for the next launch.

## Research Context

MITRE ATT&CK describes observed adversary behavior through tactics, techniques, and sub-techniques. The interface presents catalog records and their relationships for inspection and selection. Technique pages explicitly label their current behavior-module support status.

## Current User Workflow

1. Launch the application and review the absolute catalog input paths and loading progress.
2. Browse the Enterprise Platform → Tactic → Technique tree or search by ID/name.
3. Inspect descriptions, the complete sub-technique family, Procedure Examples, and reference links; copy a title or description when needed.
4. Check or uncheck techniques and review the deduplicated Selected Techniques tab.
5. Browse the six library categories using their domain/type groups and ID/name search.
6. Open Version to refresh the official release list, download or select a snapshot, and rebuild the interface with that version's data.

## Development Documentation Requirements

Whenever a program is added or changed, maintain a README.md in the same directory describing its operation flow, inputs, outputs, execution steps, progress reporting, and failure handling. The repository README should link to those component documents as the project grows.

All programs must display absolute input and output file paths before processing begins and expose progress for every processing stage.

## Desktop Interface: Run and Operation Flow

Launch from PowerShell using the existing virtual environment:

```powershell
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\main.py'
```

The interface uses an explicit dark Qt palette and white selected-row text for consistent contrast across Windows themes. The UI follows a VS Code-inspired dark workspace: activity rail, resizable explorer sidebar, central editor tabs, bottom Output panel, and blue status bar. `Ctrl+B` toggles the sidebar, `Ctrl+J` toggles Output, `Ctrl+F` focuses search, and `Ctrl+Q` exits. Normal browsing performs no network requests and creates no output files. Selections are held in memory and are lost when the application exits.

`main.py` owns the Qt interface and progress worker. `attack_catalog.py` handles catalog resolution, integrity verification, and platform/tactic relationships. Both programs are documented here in their own directory.

### Inputs and Outputs

At startup, absolute paths are shown in the terminal and in the Output panel before each input is read:

1. `D:\MITREATTACK_SIMULATOR\data\attack\active.json` identifies the saved version when present; otherwise `D:\MITREATTACK_SIMULATOR\data\attack\latest.json` identifies the default snapshot. An invalid saved choice falls back to `latest.json` with a visible message.
2. The resolved snapshot manifest, currently `D:\MITREATTACK_SIMULATOR\data\attack\v19.2\manifest.json`.
3. The resolved Enterprise bundle, currently `D:\MITREATTACK_SIMULATOR\data\attack\v19.2\enterprise-attack-19.2.json`.
4. The resolved Mobile and ICS bundles, currently `D:\MITREATTACK_SIMULATOR\data\attack\v19.2\mobile-attack-19.2.json` and `D:\MITREATTACK_SIMULATOR\data\attack\v19.2\ics-attack-19.2.json`.

Paths are resolved from the program location, independently of the working directory. `--data-dir 'ABSOLUTE_DIRECTORY'` selects another data root. Local browsing displays `Output files: None`. Version discovery, downloads, and switching display their cache and saved-pointer outputs as described in Version Selection Workflow. The optional verification command below displays its screenshot output path before loading and saves that file after checks pass.

### Processing and Visible Progress

1. **Resolve:** show input/output paths, read the snapshot pointer and manifest, and verify version agreement.
2. **Read:** read the Enterprise bundle in chunks with byte progress, check its size and SHA-256 against the manifest, and parse its JSON with an activity indicator.
3. **Index and library:** exclude revoked/deprecated records, index active techniques and tactics, resolve `subtechnique-of` relationships, and map `x_mitre_platforms` with `mitre-attack` kill-chain phases. Verify and read the Mobile/ICS bundles and index the six library categories. Report object, mapping, and transfer progress.
4. **Tree and navigation lists:** construct Platform → Tactic → Technique branches in small GUI batches, nest sub-techniques under their parent, and populate the six library category models in batches of 100 entries. Display progress and enable category buttons once loading completes.

File reading and indexing run in a background Qt thread. Tree construction runs in timer batches in the UI thread. The Output panel records stage progress and errors; the status bar shows the active stage and progress bar. Closing during loading requests cancellation and waits for the worker to finish before destroying the window.

### Explorer Behavior

- Platform names come directly from active Enterprise records; Windows is displayed first.
- Tactics follow the official matrix order when present. Early versions derive historical phase headings from their own technique mappings, as described in Version Selection Workflow.
- Techniques are placed using their actual platform and tactic mappings. A technique may appear in multiple branches.
- Sub-techniques use official parent relationships. If a parent is needed only as a grouping node in a particular branch, its checkbox is omitted.
- Platform and tactic nodes are navigation groups. Only mapped technique/sub-technique nodes have checkboxes.
- Selecting a row displays its ID, name, platforms, tactics, original description, and official reference link. Parent and child detail pages also show the complete active sub-technique family with platforms and current-branch mapping status. Related entries are clickable and navigate to a correctly mapped tree branch. Parent tooltips show mapped/total sub-technique counts.
- Search uses literal, case-insensitive ID/name matching, preserves ancestor branches, and expands matches. Descriptions retain source text, including Markdown/citation notation.
- Checking a technique synchronizes all occurrences of that same STIX ID. Parent and child selection are independent; checking a parent does not automatically select its sub-techniques.
- The Selected Techniques tab deduplicates IDs across branches and provides a clear action. Clicking a selected entry opens its details.
- Technique pages show the current behavior-module support status. Remaining scenario and simulation requirements are listed in [NOTIMPLEMENTYET.md](NOTIMPLEMENTYET.md).

### Verification and Preview

Run a bounded UI verification with an optional screenshot:

```powershell
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\main.py' --smoke-test --screenshot 'D:\MITREATTACK_SIMULATOR\artifacts\ui-preview.png'
```

The check validates all selectable tree mappings, PowerShell's official parent relationship, recursive ID search and an empty search result, duplicate checkbox synchronization, independent parent/child selection, clearing selections, and detail rendering. It reports four verification stages, saves the preview, and exits. For headless verification, set the process environment variable `QT_QPA_PLATFORM=offscreen`. The normal application does not set this variable. Offscreen previews explicitly load the installed Segoe UI and Consolas font files from the Windows Fonts directory, showing their absolute input paths, because the offscreen backend may not discover system fonts automatically.

Missing files, mismatched versions, hash failures, or malformed catalogs are displayed in the editor and Output panel. The UI remains available for inspecting the error. Verification mode returns nonzero on load/check failure or timeout. The TTP tree covers Enterprise. The six library navigation categories browse Enterprise, Mobile, and ICS with explicit domain grouping.

### Far-left Navigation Categories

The far-left rail contains TTP plus the six requested ATT&CK sections. Clicking a category switches the explorer panel and central details; the TTP tree and in-memory technique selection remain intact. `Ctrl+B` shows/hides the sidebar independently of the active category. `Ctrl+F` searches the current category. Normal navigation reads local snapshots and does not make network requests.

| Category | Local STIX object types and grouping |
| --- | --- |
| TTP | Enterprise Platform → Tactic → Technique → Sub-technique |
| Mitigations | Domain → course-of-action |
| Assets | Domain → x-mitre-asset; the current snapshot contains 18 ICS assets |
| Detections | Domain → Detection Strategies, Analytics, Data Components |
| Groups | Domain → intrusion-set |
| Software | Domain → Malware, Tools |
| Campaigns | Domain → campaign |

Library sections show active records only. An object that exists in multiple domains is displayed in each domain's list, preserving that domain's source record. Domain headings with no matching entries are omitted. Searching by name or available ATT&CK ID preserves the domain/type ancestors. Category details include the source name, ID, domain, type, optional platforms/aliases, dates, description, and available official reference link. Library records have no scenario checkboxes; technique selection remains in TTP. Assets are ICS device/system categories, separate from the TTP platform hierarchy.

### Procedure Examples and Copy Actions

Technique detail pages include a Procedure Examples table with source ID, name, the relationship's procedure description, and available reference links. The index comes from active STIX `uses` relationships whose source is an active group, malware, tool, or campaign and whose target is the exact active technique/sub-technique. Parent techniques do not inherit child examples. Revoked/deprecated sources, targets, and relationships are excluded. A zero-example technique displays an explicit empty-state message.

`attack_catalog.py` indexes these relationships for each loaded domain with visible progress. TTP displays Enterprise examples; the catalog also indexes relationships for every available Mobile/ICS bundle. Each relationship keeps its own ID and references. Clicking an example's source name switches to the correct Groups, Software, or Campaigns domain record.

Native **Copy** buttons appear beside the record title and Description heading and follow those headings during scrolling/resizing. They are available on technique and library detail pages. Title copies the name alone, excluding the ATT&CK ID. Description copies the complete original description text, retaining source Markdown/citation notation, and excludes metadata, sibling tables, and procedure examples. The button briefly shows **Copied**, and the status bar confirms the action. Empty descriptions have disabled copy actions. Navigation/loading/error pages clear copy contents to prevent stale copies.

Copy actions read in-memory text and write to the system clipboard; they create no files. The terminal reports the input/output file status and two copy stages before and after the operation. Existing catalog file inputs remain unchanged, and no additional download is required.

## Complete Catalog Audit

`audit_catalog.py`, documented here in the same directory, checks the downloaded data and the actual UI against an independently derived reference from raw STIX objects. Run it with the existing virtual environment:

```powershell
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\audit_catalog.py'
```

Use a process-local `QT_QPA_PLATFORM=offscreen` environment variable for a headless audit. Normal application startup does not need this setting. `--data-dir` selects a snapshot root and `--report-dir` selects the output directory.

The program prints absolute source and output paths before reading or writing the corresponding files. Default outputs are `D:\MITREATTACK_SIMULATOR\artifacts\catalog-audit.json`, `D:\MITREATTACK_SIMULATOR\artifacts\catalog-audit.md`, `D:\MITREATTACK_SIMULATOR\artifacts\scheduled-job-preview.png`, `D:\MITREATTACK_SIMULATOR\artifacts\navigation-preview.png`, and `D:\MITREATTACK_SIMULATOR\artifacts\procedure-preview.png`.

Processing reports seven stages:

1. Verify SHA-256 hashes and byte sizes for all original snapshot artifacts and validate all three domain bundles.
2. Independently derive active Enterprise records, platform/tactic mappings, matrix ordering, required metadata, and sub-technique parent relationships from raw STIX objects; derive procedure examples independently for all three domains.
3. Compare every actual UI row against the reference, checking missing/extra/duplicate mappings, labels, hierarchy, and grouping-only parents.
4. Test ID search, complete description rendering, related-family visibility, exact procedure counts/source identities/full relationship descriptions, and synchronized check/uncheck behavior for every active Enterprise record.
5. Check all six library category lists against raw source records across all domains, category buttons, representative search/detail rendering, unmatched searches, and preserved TTP selection. Then check all Scheduled Task/Job children and their platform/tactic branches, independent parent selection, and cross-platform related-entry navigation.
6. Verify actual title/description button clicks and clipboard contents, button positions, stale-content clearing, procedure-source navigation, and selected-text contrast. Clipboard tests preserve and restore all original MIME formats. Capture Scheduled Task/Job, ICS Assets, and Procedure Examples with copy buttons. The procedure preview selects a short standalone technique description so both headings and the example table fit in view.
7. Save JSON/Markdown results and return success only if no errors are found.

The current snapshot regression includes all five active T1053 children: At, Cron, Scheduled Task, Systemd Timers, and Container Orchestration Job. Only At and Scheduled Task map to Windows. A shorter Windows branch is expected, rather than missing data. Parent detail pages and child detail pages expose the full active family and current-branch status so this distinction is visible.

The report covers all three downloaded domains at the data level, Enterprise at the TTP UI level, and all six library sections across Enterprise, Mobile, and ICS. Revoked/deprecated records are excluded intentionally. Errors are recorded in the report and return a nonzero exit status; input/load failures are reported with the stage that failed.

## Local ATT&CK Data

Run the official-data downloader with the project virtual environment:

```powershell
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' 'D:\MITREATTACK_SIMULATOR\scripts\download_attack_data.py'
```

See [scripts/README.md](scripts/README.md) for the complete operation flow, absolute input/output paths, progress stages, and failure handling. Versioned STIX 2.1 snapshots are stored under `data/attack/v<version>` and include Enterprise, Mobile, and ICS. `data/attack/latest.json` identifies the latest successfully downloaded snapshot. The TTP tree uses the selected Enterprise bundle.

The downloader queries the official latest stable GitHub release and pins its commit before downloading. Each snapshot preserves the upstream license, catalog index, release metadata, SHA-256 hashes, and active technique statistics. Original bundles retain revoked and deprecated objects; active counts exclude them. See the snapshot README and manifest for the exact version and provenance.

## References

- [MITRE ATT&CK](https://attack.mitre.org/)
- [ATT&CK Getting Started](https://attack.mitre.org/resources/)
- [Enterprise ATT&CK Techniques](https://attack.mitre.org/techniques/)
- [Qt for Python / PySide6 Documentation](https://doc.qt.io/qtforpython-6/)

This is an independent research project and is not affiliated with or endorsed by MITRE.

## Version Selection Workflow

The top menu bar contains **Version (vX.Y)**. Open it to search all Enterprise ATT&CK releases in the official [STIX collection index](https://github.com/mitre-attack/attack-stix-data/blob/master/index.json), sorted numerically newest first. The picker shows matching domain availability, the index date in UTC, and Current / Downloaded / Download status. Opening the picker refreshes the official list in a background thread; **Refresh online** repeats discovery. Regular startup stays offline. If discovery fails, the cached official index remains available and the picker labels the failure. **Switch version** downloads a missing snapshot, verifies it, rebuilds the tree and library categories, and updates the displayed version. Existing versions switch offline after integrity checks. A zero-entry category reflects absent objects in that historical release.

`attack_versions.py` implements discovery, cache management, immutable-commit downloads and validation. `version_dialog.py` provides the picker and background worker. Both are documented here in the same source directory. `attack_catalog.py` accepts a selected snapshot pointer and treats absent historical Mobile/ICS domains as empty; it never mixes a different release into the selected one. The picker covers every numeric Enterprise release advertised by the official index. Mobile-only beta release labels are not separate Enterprise versions; only exact domain version matches are loaded.

Input paths are resolved before use: the data root (default `D:\MITREATTACK_SIMULATOR\data\attack`), cached `versions-cache.json`, snapshot `vX.Y\index.json` and `manifest.json`, and each versioned domain bundle. Network inputs are official GitHub API and raw HTTPS URLs and are logged explicitly. Output paths are displayed before writing: `versions-cache.json` and its `.part` file; `vX.Y\index.json`, `LICENSE.txt`, available domain bundles, `manifest.json`, `README.md`, and corresponding unique `.vX.Y-<uuid>` staging paths; then `active.json` and `active.json.part`. Metadata-only reads produce no output file. UI progress appears in the picker, main Output pane, status bar, and terminal.

1. **Discover (1/4):** resolve the upstream master commit, read its pinned index, validate official domain URLs, and atomically cache the index. Display cached status if offline.
2. **Prepare/download (2/4):** validate an existing local snapshot or download only matching domains into a unique staging directory; display absolute paths and transferred bytes.
3. **Validate (3/4):** check bundle structure, collection version and technique domains; compute manifest sizes/SHA-256; load every available domain and procedure index before publishing the completed snapshot directory.
4. **Switch (4/4):** atomically save `active.json`, rebuild all models, reset stale searches/details, retain selected STIX IDs present in the new catalog, and report selections absent from the new version. Sidebar, procedure examples and copy actions now use the selected release.

`latest.json` continues to describe the downloader's latest snapshot. `active.json` records the user's version choice for the next desktop launch. An unreadable/invalid saved choice falls back to `latest.json` with visible progress. Download, validation or persistence failures leave the current interface and previous active pointer usable. Damaged existing cache directories are preserved and reported rather than overwritten. Cancel/Close cooperatively stops at the next progress boundary; an active HTTPS read can take up to its 30-second socket timeout. No background data request is made at application startup. The full `audit_catalog.py` audit explicitly checks `latest.json`; `audit_versions.py` independently exercises discovery, historical loading, switching, failure preservation, and restart persistence.

Early official snapshots (including v1.0) contain no tactic objects. For those releases, headings are derived from their own technique kill-chain phases, ordered by the familiar Enterprise phase sequence, and identified by a historical-heading tooltip. No modern tactic records or fabricated official TA identifiers are inserted. Existing tactic objects and matrix ordering remain authoritative when present.


To rerun the version audit (official discovery, downloads of v1.0/v11.2 if absent, six visible audit stages, isolated Qt switching and restart tests):

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\audit_versions.py'
```

The audit displays its absolute input root, report (`artifacts\version-audit.json`), screenshot (`artifacts\version-preview.png`), and unique `artifacts\version-audit-data-<uuid>` test root before writing. It downloads real snapshots into the ordinary data cache, then uses hard links to immutable input artifacts in its isolated root; tests write only isolated active/latest pointers and leave the user's saved choice untouched. Retained audit directories provide reproducible evidence without duplicating bundle bytes. For a targeted three-stage picker check, append `--picker-only`; it simulates an offline metadata fetch, verifies cached version access, search and completed progress, and writes `artifacts\version-picker-audit.json` plus the picker preview. The date column is **Updated (UTC)**, reflecting the official index's `modified` field.
