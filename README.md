<p align="center">
  <img src="assets/ttp-selection-studio-icon-pixel.png" alt="TTP Selection Studio pixel icon" width="128" height="128">
</p>

# TTP Selection Studio

A PySide6 desktop application for cybersecurity research that creates independent TTP selection documents and exports the selected techniques as JSON or CSV, using official MITRE ATT&CK data.

## Project Status

The current application provides File → New File / Ctrl+N, multiple independent document tabs, per-document ATT&CK snapshots and domain selection, File → Export / Ctrl+Shift+E, File → Export CSV, and a VS Code-inspired workspace. Enterprise, Mobile, and ICS support a Platform → Tactic → Technique tree with nested sub-techniques, ID/name search, synchronized selections, technique details, Procedure Examples, and title/description copy actions. New files default to Enterprise; right-click the filename and choose **ATT&CK Domain → Enterprise / Mobile / ICS**. The far-left navigation rail provides Mitigations, Assets, Detections, Groups, Software, and Campaigns across available domains. The Version picker discovers official releases, downloads and validates snapshots, supports offline switching to downloaded versions, and remembers the selected release.

The TTP sidebar also opens a right-side ATT&CK Matrix with expandable sub-technique families, platform filtering, ID/name search and checkbox synchronization with the document and original tree.

Navigator integration adds **File → Import Navigator Layer / Ctrl+O**, **Export Navigator Layer**, technique annotation editing, comparison of open selections, and background comparison of downloaded ATT&CK snapshots using the official `mitreattack-python` SDK.

This README documents implemented functionality, startup commands, inputs, outputs, progress, and verification. Remaining requirements and future design proposals are maintained in [NOTIMPLEMENTYET.md](NOTIMPLEMENTYET.md), including incomplete portions of otherwise working features.

The local Python virtual environment is `C:\Users\nick5\MITREATTACK_SIMULATOR`. The current interface uses English labels and original ATT&CK names. Open documents and their edits are held in memory. Studio JSON, CSV and Navigator Layer export write a selected document to disk; the dataset version chosen in the Version picker is saved separately for the next launch. Navigator Layer import is implemented; reopening the Studio's own JSON schema is tracked in NOTIMPLEMENTYET.md.

## Research Context

MITRE ATT&CK describes observed adversary behavior through tactics, techniques, and sub-techniques. The interface presents catalog records and their relationships for inspection and selection. Its product workflow is to assemble and export selected TTPs. Technique pages explain that checking a TTP includes it in the active document.

## Current User Workflow

1. Launch the application and review the absolute catalog input paths and loading progress.
2. Browse the document's Platform → Tactic → Technique tree or search by ID/name. New files use Enterprise; right-click the filename and choose **ATT&CK Domain** to select Mobile or ICS. Use **Open ATT&CK Matrix** in the TTP sidebar to browse the right-side tactic matrix for that domain.
3. Inspect descriptions, the complete sub-technique family, Procedure Examples, and reference links; copy a title or description when needed.
4. Use File → New File or Ctrl+N to create another empty document. Check or uncheck techniques and review that document in Selected Techniques.
5. Browse the six library categories using their domain/type groups and ID/name search.
6. Open Version to refresh the official release list or change the active document's snapshot. Other documents retain their own snapshots.
7. Use File → Export, Ctrl+Shift+E, or the Selected Techniques export button to write the active document. Choose its filename and location; the tab adopts the exported filename.

## Per-Document Enterprise, Mobile and ICS Domains

Enterprise, Mobile, and ICS are ATT&CK **domains**, separate from the release selected using **Version**. Every startup document and **New File / Ctrl+N** uses Enterprise, including a new file created while a Mobile or ICS file is active. Navigator import creates a file using the imported layer's recorded domain.

Right-click a document filename and choose **ATT&CK Domain → Enterprise / Mobile / ICS**. The current domain has a checkmark. The menu targets the clicked file, so changing an inactive file does not activate it or change another document. Missing domains in historical snapshots are disabled with their release number. Choosing an unavailable domain through a programmatic call reports an error and leaves document data intact.

Each document retains separate in-memory selections and Navigator annotations for its domains. Switching away archives the current non-empty state; switching back restores it against the document's current release. The filename and document identity remain the same. Domain/version appear in tab tooltips, selection summaries, TTP summaries, matrix summaries and comparison selectors. Domain changes affect changed-content tracking; returning to an empty Enterprise file leaves no unnecessary empty archives.

`attack_catalog.py` projects each domain's verified active records, official tactic/matrix order, platforms and parents. It uses `mitre-attack`, `mitre-mobile-attack`, or `mitre-ics-attack` kill chains as appropriate. Historical phases are derived from their own source records when tactic objects are absent. Technique search/details, Procedure Examples, parent labels, bulk source selection, and the matrix use this projection. Cross-domain library browsing remains available; bulk actions require the source domain to match the file.

JSON, CSV, and Navigator Layer exports include only the active domain's selected-TTP list, with its correct domain, release, tactic IDs/names, platforms and parent metadata. Studio JSON additionally preserves inactive domain state in an optional `domain_snapshots` map: each entry records its release, `selected_stix_ids`, `navigator_layer`, `navigator_import_selected`, and `navigator_snapshots`. CSV/Navigator exports cannot preserve all inactive domain/version archives and leave such documents marked changed. Export Studio JSON to preserve the complete state before closing. Reopening that Studio JSON schema and session recovery remain unimplemented; archives are restored inside the current running session.

Navigator Layer imports resolve their own domain and exact release. Selection comparison requires both domain and release to match. SDK version comparison uses the active file's domain. A release switch preserves the file's domain; `version_dialog.py` disables unavailable release/domain combinations and its worker verifies availability before updating `active.json`. Dataset pointers remember releases, while new files continue to default to Enterprise.

Domain switching reports **Input files: None (verified catalog in memory)** and **Output files: None** before **1/3 resolve**, **2/3 archive/restore**, and **3/3 tree/matrix rebuild and ready**. A background tab reports completion after its in-memory update. Active tree/matrix rebuilding uses the existing incremental Qt timers with actions disabled until ready. Downloads, SDK comparisons, imports and exports retain the absolute-path and stage progress described below.

### Three-Domain Verification

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\audit_domains.py'
```

`audit_domains.py` lives beside this README. Before processing it displays absolute pointer/report/output directory paths, then resolved raw STIX bundle paths and individual export/readback paths. Six visible stages independently verify source platform/tactic mappings, actual right-click domain actions, every selectable tree/matrix ID, domain-specific JSON/CSV/Navigator exports, scoped decimal annotations, restored per-domain state, inactive-tab changes, Enterprise defaults, bulk-add boundaries, historical availability and failed-worker pointer preservation, actual Mobile/ICS SDK version differences, native imports and comparison constraints. It performs no downloads and leaves active/latest pointers unchanged.

Outputs are `D:\MITREATTACK_SIMULATOR\artifacts\domain-audit.json` and a unique `artifacts\domain-audit-<uuid>` directory with three-domain export samples and UI previews. The report is published as PASS only after all assertions succeed; failures return a nonzero exit code. Existing catalog, document, matrix, related-TTP and Navigator audits provide regression coverage.

## Development Documentation Requirements

Whenever a program is added or changed, maintain a README.md in the same directory describing its operation flow, inputs, outputs, execution steps, progress reporting, and failure handling. The repository README should link to those component documents as the project grows.

All programs must display absolute input and output file paths before processing begins and expose progress for every processing stage.

## Desktop Interface: Run and Operation Flow

Launch from PowerShell using the existing virtual environment:

```powershell
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\main.py'
```

The interface uses an explicit dark Qt palette and white selected-row text for consistent contrast across Windows themes. The UI follows a VS Code-inspired dark workspace: activity rail, resizable explorer sidebar, central editor tabs, bottom Output panel, and blue status bar. `Ctrl+B` toggles the sidebar, `Ctrl+J` toggles Output, `Ctrl+F` focuses search, and `Ctrl+Q` exits. Normal browsing performs no network requests and creates no output files. Open documents are held in memory; export changes to JSON before exiting. Exported files remain on disk. Import/reopening and unsaved-document exit prompts are listed in NOTIMPLEMENTYET.md.

The application and its windows use the pixel-style shield/node/checkmark icon at `D:\MITREATTACK_SIMULATOR\assets\ttp-selection-studio-icon-pixel.png`. `configure_application()` resolves this input relative to `main.py`, independently of the working directory. Before reading it, the terminal displays its absolute path and `Output files: None (application/window icon in memory)`. Icon progress has two stages: **1/2 load** and **2/2 apply** through `QApplication.setWindowIcon()`, which supplies the default icon for the main window and dialogs. A missing or unreadable image produces a visible message and uses the system default without blocking startup. Restart the application after updating the icon. See [assets/README.md](assets/README.md) for the design and generation workflow.

`main.py` owns the Qt interface and progress worker. `attack_catalog.py` handles catalog resolution, integrity verification, and platform/tactic relationships. `ttp_documents.py` manages document identities, export state and atomic JSON/CSV publishing. `audit_documents.py` verifies the actual file shortcuts, document switching and export behavior. These programs are documented here in their own directory.

On Windows, startup calls `configure_windows_taskbar()` before creating `QApplication`, assigning the process the stable AppUserModelID `TTPSelectionStudio.Desktop` with two progress stages. A process ID and Qt window icon alone do not supply a custom taskbar group/pinning icon for every Python host. `MainWindow.configure_native_taskbar()` also calls `windows_taskbar.py` before showing the native window. Through `SHGetPropertyStoreForWindow`, it sets the window's explicit AppUserModelID, `RelaunchIconResource`, `RelaunchDisplayNameResource` and `RelaunchCommand`. The icon resource is `D:\MITREATTACK_SIMULATOR\assets\ttp-selection-studio-icon-pixel.ico,0`; the relaunch command uses the current environment's `pythonw.exe` when available, `main.py`, and the absolute `--data-dir`. This supplies a project icon and complete pinned-app launch command even with Microsoft Store Python.

`windows_taskbar.py` is documented here in its source directory. Its flow is **1/3 prepare** (show the absolute ICO input path and no file outputs), **2/3 apply** (four per-window properties), and **3/3 verify** (read all four properties back from Windows). It initializes/releases COM as needed and releases the property-store reference. Metadata stays in Windows memory; startup writes no icon files. This step is skipped outside Windows and in Qt offscreen previews. A missing ICO or Windows API failure is reported in the terminal and Output panel without blocking startup. The PNG remains the Qt window icon; the ICO supplies the taskbar group and relaunch artwork.

The ICO contains transparent 16/32/48/64/128/256-pixel images using nearest-neighbor scaling. Regenerate it with [scripts/build_windows_icon.py](scripts/build_windows_icon.py); see [scripts/README.md](scripts/README.md) for exact paths, stages and failure handling. Windows `LoadImageW` loaded all six sizes, and a real native Qt window retained all four properties. The pre-fix running window had none of these properties; validating only its Qt icon handles was insufficient. Restart to load this permanent fix. If an old pinned Python shortcut remains, replace it with the running TTP application.

Implementation follows Microsoft's [process AppUserModelID startup requirement](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-setcurrentprocessexplicitappusermodelid) and [window taskbar icon/relaunch properties](https://learn.microsoft.com/en-us/windows/win32/properties/props-system-appusermodel-relaunchiconresource).

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
- The Selected Techniques tab deduplicates IDs across branches and provides a clear action. Each selected sub-technique displays its parent ID and name on the next line; this is relationship metadata and leaves checkbox selection independent. Sub-technique detail pages also show the parent beneath the title. Clicking a selected entry opens its details.
- Technique pages describe adding a selected TTP to the active document. Remaining export/editor extensions are listed in [NOTIMPLEMENTYET.md](NOTIMPLEMENTYET.md).

### Verification and Preview

Run a bounded UI verification with an optional screenshot:

```powershell
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\main.py' --smoke-test --screenshot 'D:\MITREATTACK_SIMULATOR\artifacts\ui-preview.png'
```

The check validates all selectable tree mappings, PowerShell's official parent relationship, recursive ID search and an empty search result, duplicate checkbox synchronization, independent parent/child selection, clearing selections, and detail rendering. It reports four verification stages, saves the preview, and exits. For headless verification, set the process environment variable `QT_QPA_PLATFORM=offscreen`. The normal application does not set this variable. Offscreen previews explicitly load installed Segoe UI, Consolas and Microsoft JhengHei font files from the Windows Fonts directory, showing their absolute input paths, because the offscreen backend may not discover system fonts automatically. JhengHei supplies Traditional Chinese glyphs for user annotation previews.

Missing files, mismatched versions, hash failures, or malformed catalogs are displayed in the editor and Output panel. The UI remains available for inspecting the error. Verification mode returns nonzero on load/check failure or timeout. The TTP tree covers the file's selected Enterprise, Mobile, or ICS domain. The six library navigation categories browse all available domains with explicit domain grouping.

### Far-left Navigation Categories

The far-left rail contains TTP plus the six requested ATT&CK sections. Clicking a category switches the explorer panel and central details; the TTP tree and in-memory technique selection remain intact. `Ctrl+B` shows/hides the sidebar independently of the active category. `Ctrl+F` searches the current category. Normal navigation reads local snapshots and does not make network requests.

Each entry displays a 32 × 32 blue pixel icon with its original label centered underneath. TTP reuses the application icon; Mitigations uses a protective barrier, Assets an industrial controller, Detections a magnifying glass with a signal, Groups grouped people, Software a terminal window, and Campaigns a flag with timeline nodes. These are project-designed visual metaphors for the categories, based on the official definitions. See [assets/navigation/README.md](assets/navigation/README.md) for icon previews, definition sources and generation prompts. `main.py` loads the seven absolute asset paths through `load_navigation_icons()`, displaying **1/3 paths**, **2/3 per-icon loading**, and **3/3 completion** before use. Loading writes no files. Missing/unreadable artwork leaves its text button available. Icons are prepared at 32/64/96 pixels using nearest-neighbor scaling for pixel edges and different display scaling; category labels, tooltips, accessible names, selection and switching remain available.

The top menu provides **Settings → Show navigation labels**, checked by default. With labels enabled, each navigation button is 112 × 68 pixels; disabling the setting switches to icons only and a compact 56 × 48 layout. Hovering over a button shows its category name in a tooltip, including TTP. Text and accessible names remain assigned even when labels are hidden. Missing icons retain a text fallback and enough rail width to show the full category name. Changing this preference preserves the active category, document and selected techniques.

`main.py` stores this setting as `navigation/show_labels` in `D:\MITREATTACK_SIMULATOR\data\ui-settings.ini`, independently of the selected ATT&CK data directory. Startup resolves this path from the program location, shows the absolute input path and no-output status, then reports **1/2 read** and **2/2 complete**. Missing preferences default to showing labels; unreadable or invalid settings report a message and use the same default. A menu toggle shows the absolute output path before processing, then reports **1/3 prepare**, **2/3 apply/save**, and **3/3 complete** in the terminal and Output panel. Qt synchronizes the INI setting so the next launch restores the choice. Save failures are visible and leave the requested layout usable for the current session. Verification can provide an isolated `settings_path` when constructing `MainWindow` to avoid changing the user's preference.

| Category | Local STIX object types and grouping |
| --- | --- |
| TTP | Document's Enterprise / Mobile / ICS domain → Platform → Tactic → Technique → Sub-technique |
| Mitigations | Domain → course-of-action |
| Assets | Domain → x-mitre-asset; the current snapshot contains 18 ICS assets |
| Detections | Domain → Detection Strategies, Analytics, Data Components |
| Groups | Domain → intrusion-set |
| Software | Domain → Malware, Tools |
| Campaigns | Domain → campaign |

Library sections show active records only. An object that exists in multiple domains is displayed in each domain's list, preserving that domain's source record. Domain headings with no matching entries are omitted. Searching by name or available ATT&CK ID preserves the domain/type ancestors. Category details include the source name, ID, domain, type, optional platforms/aliases, dates, description, and available official reference link. Library records have no scenario checkboxes; technique selection remains in TTP. Assets are ICS device/system categories, separate from the TTP platform hierarchy.

### Related Techniques on Library Pages

Below Description, **Mitigations** displays **Techniques Addressed by Mitigation**. **Software** (Malware and Tools), **Campaigns** and **Groups** display **Techniques Used by Software/Campaign/Group**. These tables have **Domain**, **ID**, **Name**, and **Use** columns. Use preserves the original relationship description and its HTTPS reference links. Sub-technique names include their official parent ID/name. A count reports relationship rows; an entry without active relationships shows an explicit empty state.

`attack_catalog.py` indexes exact active STIX `mitigates` edges from course-of-action objects and `uses` edges from intrusion-set (group), malware, tool, and campaign objects to attack-pattern objects. Revoked/deprecated relationships and unavailable/inactive endpoints are excluded. Rows are sorted by technique ID and relationship ID, and separate edges retain their own descriptions. Parent relationships only provide labels: parents/children do not inherit each other's associations. Each page uses its selected domain and document's snapshot, so Enterprise, Mobile and ICS records do not mix across domains or versions.

Click a technique ID or name to open its local detail page. Enterprise links open the existing selectable TTP explorer. Mobile/ICS links open reference detail pages with Description, parent links, Procedure Examples, title/description copy buttons and a **Back to source entry** link. Mobile/ICS selection/export remains a future extension. Normal browsing reads the verified catalog in memory and needs no network; external reference links open the browser only when clicked.

The catalog's **3/4 Related TTPs** stage displays indexing progress for each domain after the existing absolute manifest/bundle input paths. Missing historical domains receive empty indexes. Page rendering reports `Input files: None` (verified in-memory catalog) and `Output files: None`, then **Related TTPs 1/2** rendering progress and **2/2** completion in terminal, Output and status bar. It writes no files.

### Add All TTPs from a Source Entry

Open an entry matching the document's Enterprise, Mobile, or ICS domain in **Campaigns**, **Software** (Malware or Tools), or **Groups**, then click **Add all TTPs (N)** above its detail page. `N` counts unique directly related active techniques/sub-techniques. One click adds the entry's full set to the active document, preserving existing selections. Repeated clicks add no duplicates. The operation stays on the source page and synchronizes every sidebar occurrence, the matrix, Selected Techniques, the document's change marker and its subsequent JSON/CSV exports.

The operation uses the source entry's exact active `uses` relationships in the current document's ATT&CK snapshot. It does not traverse group → software → technique chains or infer additional parents/children. A sub-technique contributes parent metadata in the normal selection/export format; its parent is selected only if directly related or already checked. Entry counts can differ from table row counts when multiple relationships target the same TTP. The button is disabled for empty entries and for entries from another domain; its tooltip explains which document domain to choose. Mitigations and other categories do not expose this source action. Merely browsing an entry does not change selections.

`main.py` renders the native action bar and performs the operation. Navigation to another detail page clears stale action context; loading blocks actions, and each click resolves against the currently active document/catalog. It reports `Input files: None` (verified relationships and document in memory) and `Output files: None` before three stages:

1. **Add all TTPs 1/3:** resolve the source's exact relationships and deduplicate its target STIX IDs.
2. **Add all TTPs 2/3:** check newly selected targets across all tree branches with recursive checkbox handling suppressed; show progress for larger batches.
3. **Add all TTPs 3/3:** synchronize the active document, matrix and selection list once, then report added, already selected, unavailable and total counts.

The operation writes no files. Export continues to use its existing three stages and displays absolute final/temporary JSON/CSV paths before writing. Bulk additions affect only the active document, and other documents retain their own selections and snapshots.

### Dedicated Sidebar TTP Search

The **Search TTP name or ID…** field appears only in the **TTP** sidebar category. Enter a literal technique ID such as `T1053.005`, or part of its name. Searches are case-insensitive and run after a 180 ms typing pause or immediately on Enter. Matching sub-techniques preserve/expand their platform, tactic and parent branches. A matching parent displays its children; clearing the field restores the full tree, and an unmatched query leaves no result rows. In TTP context, Ctrl+F focuses this field.

Mitigations, Assets, Detections, Groups, Software and Campaigns show only their own category-specific ID/name filter; the TTP field is hidden. Ctrl+F focuses the visible category filter. Filtering a category never switches to TTP. All sidebar search fields accept spaces, including pauses between words, leading/trailing spaces and repeated spaces. Filtering trims outer whitespace in a temporary query without rewriting the editable text or moving its cursor; internal spaces remain literal. Category/document/version switches clear stale filters and cancel pending search timers. Browsing and filtering preserve selected TTPs and do not change export content. The matrix retains its independent search field.

`main.py` owns these controls. TTP search reports `Input files: None` and `Output files: None` before **TTP Search 1/2** filtering and **2/2** completion. Loading a new catalog disables the field until the rebuilt tree is ready. Closing the window stops both sidebar search timers. No search operation writes a file.

### Related TTP and Search Audit

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\audit_related_ttps.py'
```

`audit_related_ttps.py`, documented here in its source directory, prints absolute input paths for `data\attack\latest.json` and all three resolved bundles before reading, and absolute output paths for `artifacts\related-ttp-audit.json`, `artifacts\bulk-ttps-example.json`, `artifacts\bulk-ttps-example.csv` and the three `*-techniques-preview.png` images before writing. Export/readback also displays absolute paths before use. It performs no downloads and does not modify snapshot pointers or user documents.

1. Derive an independent relationship reference from raw STIX for all three domains.
2. Compare every source/target relationship, original description/reference and ordering; exercise revoked/deprecated and missing-target exclusion.
3. Open tables for available mitigations, malware, tools, campaigns and groups in each domain; verify headings, counts, columns, parent names, copy actions, local navigation, return links and empty states.
4. Verify that every category shows only its own search field and Ctrl+F targets that field. Use native typing/Enter and debounced ID/name search; pause after spaces before continuing multi-word TTP/category names. Verify space/cursor preservation, ancestor branches, clearing, unmatched results, category-filter independence and retained selections.
5. Click the native bulk action for malware, tools, campaigns and groups. Compare exact added sets to raw relationships; verify retained selections, idempotent clicks, document change markers, all tree/matrix checkboxes, unique selection rows, JSON/CSV IDs and parent metadata. Exercise independent documents and disabled/stale/missing/unsupported source actions.
6. Capture Mitigations, Software and Campaigns table previews, including their bulk action where supported.
7. Write the PASS report after all checks succeed. Failed assertions/timeouts produce a nonzero process exit; they do not publish a passing report.

### Procedure Examples and Copy Actions

Technique detail pages include a Procedure Examples table with source ID, name, the relationship's procedure description, and available reference links. The index comes from active STIX `uses` relationships whose source is an active group, malware, tool, or campaign and whose target is the exact active technique/sub-technique. Parent techniques do not inherit child examples. Revoked/deprecated sources, targets, and relationships are excluded. A zero-example technique displays an explicit empty-state message.

`attack_catalog.py` indexes these relationships for each loaded domain with visible progress. TTP displays examples from the active document's domain. Each relationship keeps its own ID and references. Clicking an example's source name switches to the correct Groups, Software, or Campaigns domain record.

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

See [scripts/README.md](scripts/README.md) for the complete operation flow, absolute input/output paths, progress stages, and failure handling. Versioned STIX 2.1 snapshots are stored under `data/attack/v<version>` and include the domains available in that release. `data/attack/latest.json` identifies the latest successfully downloaded snapshot. The TTP tree uses the document's selected domain bundle.

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
4. **Switch (4/4):** atomically save `active.json`, change only the active document's catalog, rebuild all models, reset stale searches/details, retain selected STIX IDs present in the new catalog, and report selections absent from the new version. Other documents retain their prior selections and catalog references. Activating a document restores its verified in-memory snapshot without a new download or changing `active.json`. Sidebar, procedure examples, copy actions and JSON export use that document's release.

`latest.json` continues to describe the downloader's latest snapshot. `active.json` records the user's version choice for the next desktop launch. An unreadable/invalid saved choice falls back to `latest.json` with visible progress. Download, validation or persistence failures leave the current interface and previous active pointer usable. Damaged existing cache directories are preserved and reported rather than overwritten. Cancel/Close cooperatively stops at the next progress boundary; an active HTTPS read can take up to its 30-second socket timeout. No background data request is made at application startup. The full `audit_catalog.py` audit explicitly checks `latest.json`; `audit_versions.py` independently exercises discovery, historical loading, switching, failure preservation, and restart persistence.

Early official snapshots (including v1.0) contain no tactic objects. For those releases, headings are derived from their own technique kill-chain phases, ordered by the familiar Enterprise phase sequence, and identified by a historical-heading tooltip. No modern tactic records or fabricated official TA identifiers are inserted. Existing tactic objects and matrix ordering remain authoritative when present.


To rerun the version audit (official discovery, downloads of v1.0/v11.2 if absent, six visible audit stages, isolated Qt switching and restart tests):

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\audit_versions.py'
```

The audit displays its absolute input root, report (`artifacts\version-audit.json`), screenshot (`artifacts\version-preview.png`), and unique `artifacts\version-audit-data-<uuid>` test root before writing. It downloads real snapshots into the ordinary data cache, then uses hard links to immutable input artifacts in its isolated root; tests write only isolated active/latest pointers and leave the user's saved choice untouched. Retained audit directories provide reproducible evidence without duplicating bundle bytes. For a targeted three-stage picker check, append `--picker-only`; it simulates an offline metadata fetch, verifies cached version access, search and completed progress, and writes `artifacts\version-picker-audit.json` plus the picker preview. The date column is **Updated (UTC)**, reflecting the official index's `modified` field.

## TTP Documents and JSON/CSV Export

The product workflow is **New File → select TTPs → Export JSON or CSV**. At startup, the application creates `Untitled-1`. **File → New File** and **Ctrl+N** create additional `Untitled-N` documents and activate an empty selection. Document tabs sit above the existing Technique Details / Selected Techniques tabs. Switching document tabs restores each file's checked TTPs and ATT&CK snapshot. Repeated occurrences of a TTP in the tree synchronize within the active document, and exports deduplicate by STIX ID. A parent and its sub-techniques remain independent selections.

**File → Export…**, **Ctrl+Shift+E**, and the **Export JSON / CSV…** button in Selected Techniques export the active document through a native file dialog. The user chooses an absolute output location. The export dialog offers JSON and CSV filters. **File → Export CSV…** opens CSV export directly. The selected format determines the appended extension when it is missing; the previous export format is proposed for that document next time. An empty selection produces a valid zero-selection document. Successful export changes the document tab to the output filename without its extension and records that path as the next dialog's default. Subsequent document-name, selection or dataset-version changes display `*` on the document tab and window title until exported; reverting to the last exported name/selection/version clears it. Each export writes a snapshot of that document and does not merge selections from other files.

New documents have no disk path until exported. Open documents, their selections and their verified catalog references remain in memory. The Version picker changes only the active document. Previously open documents continue to use their original snapshot when activated. The version stored in `active.json` is the most recent explicit Version-picker choice, rather than an open-document session.

### JSON Format

The exported UTF-8 JSON uses `schema_version: "1.0"` and includes:

| Field | Content |
| --- | --- |
| `document_id`, `name` | Stable document UUID and exported filename stem |
| `created_at_utc`, `exported_at_utc` | Document creation and export timestamps |
| `attack` | Document domain (`enterprise-attack`, `mobile-attack`, or `ics-attack`), actual dataset version, and official source URL |
| `selected_count` | Number of unique selected techniques/sub-techniques |
| `selected_technique_ids` | Sorted ATT&CK IDs, such as `T1053.005` and `T1059.001` |
| `selected_ttps` | One row per selection: `technique_id`, `stix_id`, `name`, `is_subtechnique`, `parent_technique_id`, `parent_technique_name`, `platforms`, and `tactics` |

Each tactic contains `tactic_id`, `name` and `shortname`; historical snapshots with no official tactic object export `tactic_id: null` for derived phase headings. `parent_technique_id` and `parent_technique_name` are null for a parent technique. Platform/tactic metadata reflects the source technique's complete mapping, not just the branch in which its box was checked. Techniques are sorted by ATT&CK ID and STIX ID for consistent output; this order describes a selection list rather than an execution sequence. An actual example generated by the document audit is available at [artifacts/selected-ttps-example.json](artifacts/selected-ttps-example.json).

### File Operations and Visible Progress

`ttp_documents.py` implements the in-memory document model and JSON/CSV export serialization. `main.py` owns the file menu, shortcuts, document tabs, native export dialog and progress messages. No input file is reread during ordinary export: the selected document and its verified catalog are already in memory.

- **New File (1/2–2/2):** display `Input files: None` and `Output files: None`, preserve the previous document, create an empty document and confirm its name.
- **Activate document (1/2–2/2):** display in-memory input/output status, restore selections, and reuse or rebuild the document's catalog tree with visible catalog/tree progress.
- **Export (1/3 Prepare):** show the absolute final output path and the unique temporary path beside it before writing, verify all selected records are present in the document's snapshot, and serialize the selected JSON/CSV format.
- **Export (2/3 Write):** write UTF-8 JSON or UTF-8-with-BOM CSV to the unique temporary file and report the selected count.
- **Export (3/3 Publish):** replace the chosen output atomically, update the document's filename/exported state, and display the final absolute path.

Cancelling the dialog creates no file and leaves document state intact. Serialization/write/publish failures display an error in Output, the status bar and an error dialog; the previously published target and exported state are preserved. Temporary files are removed after a failed publish. Export destination folders must already exist. No network connection is required for exporting or switching already open document tabs. Remaining import, session recovery, application-exit prompts and editor features are tracked in [NOTIMPLEMENTYET.md](NOTIMPLEMENTYET.md).

## Document and Export Audit

Run the seven-stage audit with the existing environment:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\audit_documents.py'
```

`audit_documents.py` displays `D:\MITREATTACK_SIMULATOR\data\attack\latest.json` as its initial input, and absolute paths for the report `artifacts\ttp-document-audit.json`, preview `artifacts\ttp-documents-preview.png`, example `artifacts\selected-ttps-example.json`, and a unique `artifacts\ttp-document-audit-<uuid>` directory with individual test exports before writing. It also reads the already downloaded v1.0 manifest/bundles for the historical-file test, showing their paths before use. The document audit performs no downloads and does not modify the user's active/latest dataset pointers.

1. Verify the default document, Ctrl+N assignment and empty JSON export.
2. Exercise JSON/CSV File-menu exports and inspect exact IDs, Unicode filenames, names, parent IDs/names, STIX identities, platforms/tactics and duplicate synchronization. Verify CSV parity, BOM encoding, empty/header-only exports, root techniques, Unicode/quote/newline round trips, and failed CSV publishing.
3. Send actual Ctrl+N / Ctrl+Shift+E key events, trigger File New, switch documents, and verify selection independence and exported-change markers.
4. Verify cancelled dialogs, extension handling, rejected invalid selections, and failed atomic publishing preserving existing JSON and document state.
5. Change the active file to v1.0, export it, and verify another file retains/restores its v19.2 selection and full tree.
6. Exercise JSON and CSV filters in the selection-page export dialog, missing extensions and remembered format defaults; write both example files.
7. Exercise native right-click actions on inactive tabs; verify rename cancellation, invalid names, export defaults and changed-state markers; verify close cancellation, failed/successful pre-close exports, index adjustments, last-tab replacement and adjacent catalog restoration. Capture the menu preview and save a passing report only after all checks succeed.


### Document Tab Context Menu

Right-click a file-name tab above Technique Details / Selected Techniques to open **Close File** and **Rename…**. The menu acts on the clicked document, including inactive tabs, without first changing the active document. Right-clicking empty tab-bar space shows no menu. Actions are unavailable during catalog rebuilding.

**Rename…** opens a name dialog. A blank name, Windows-reserved names, invalid filename characters, a trailing dot, or an overlong name is rejected. A supplied `.json` or `.csv` suffix is removed from the displayed document name. Rename changes the in-memory document title and its export-change marker while retaining its identity, selected TTPs and dataset snapshot. Existing exported files keep their current paths and contents. The next export proposes the new name in the previous export directory, or the home directory for a new document. Both active and inactive tabs can be renamed.

**Close File** removes the clicked document tab. If its content/name has unexported changes, a Save / Discard / Cancel dialog appears: Save runs that document's export dialog with its previous format, Discard closes it, and Cancel keeps it open. A cancelled or failed export also keeps it open. Closing an inactive document preserves the active document's selections and correctly adjusts its tab index. Closing the active document activates an adjacent document and restores its snapshot. Closing the last tab creates a fresh empty Untitled document so New/Export and the explorer continue to work.

Rename and Close File display two stages in the terminal, Output pane and status bar. Before changing in-memory state, they report no input/output files. A pre-close export displays its final and temporary absolute output paths through the normal three-stage export flow. Successful export is the only part of these operations that writes a file. Application-wide exit prompts and session recovery remain listed in NOTIMPLEMENTYET.md.

### CSV Format and Parent Technique Names

**File → Export CSV…** exports the active document as a CSV file. The general **Export…** dialog and Selected Techniques export button can also choose **CSV files (*.csv)**. Each selected technique/sub-technique occupies one data row, sorted by ATT&CK ID and STIX ID, with no duplicates across tree branches. An empty selection exports the header only. JSON continues to use schema version 1.0 and now also includes `parent_technique_name` alongside the existing parent ID.

CSV columns are `schema_version`, `document_id`, `document_name`, `attack_domain`, `attack_version`, `created_at_utc`, `exported_at_utc`, `selected_count`, `technique_id`, `stix_id`, `name`, `is_subtechnique`, `parent_technique_id`, `parent_technique_name`, `platforms`, `tactic_ids`, `tactic_names`, and `tactic_shortnames`. Document/version metadata is repeated on each data row; a header-only CSV has no metadata values. Root techniques have blank parent columns. Multiple platforms/tactics are joined with `; ` inside their cells; CSV quoting preserves commas, quotes and embedded newlines. Boolean values are `true` / `false`. Files use UTF-8 with a BOM to make Unicode recognition easier in Excel. The actual audit sample is [artifacts/selected-ttps-example.csv](artifacts/selected-ttps-example.csv).

For a selected sub-technique, Selected Techniques shows a second line such as `Parent: T1059  Command and Scripting Interpreter`. The technique detail page displays the same parent ID/name beneath the sub-technique title. Both exports record this official parent relationship even when the parent itself is unchecked. Parent metadata does not create another selected TTP or another CSV row.

CSV uses the same three export stages, absolute final/temporary paths, atomic publishing, failure preservation and document exported-state updates as JSON. The previous per-document export format is used for the next general export or pre-close Save dialog. `audit_documents.py` writes `artifacts\selected-ttps-example.csv` in addition to its JSON example/report/preview and unique test-directory exports, displaying these output paths before writing.

## ATT&CK Matrix View

Click **Open ATT&CK Matrix** in the TTP sidebar to open the **ATT&CK Matrix** page on the right. The original Platform → Tactic → Technique tree remains available. The matrix follows the official tactic/matrix order and shows one horizontally arranged column per tactic with mapped techniques. Each column has its own vertical scroll area, and the outer page scrolls horizontally to the remaining tactics. Long technique names wrap inside each column. `Ctrl+B` can hide the sidebar to give the matrix more room, and `Ctrl+J` can hide Output.

The **Platform** dropdown offers **All Platforms** and every platform in the active document's domain catalog. All Platforms merges mapped records across platforms and deduplicates them within each tactic. Choosing a platform shows only that platform's actual mappings. A column header counts visible parent/family entries. A parent label such as `Scheduled Task/Job (5)` gives the number of mapped active sub-techniques in that platform/tactic; click the native arrow to open its children. In Enterprise v19.2, All Platforms shows five T1053 children, while Windows shows At and Scheduled Task and therefore displays `(2)`. Parents needed only to group mapped children have no checkbox when they are not themselves mapped in that scope.

The matrix has independent case-insensitive ID/name search. Child matches retain and expand their parent family; a matching parent displays its scoped children. Columns with no matches are hidden, and an unmatched query displays an empty state. **Expand all** and **Collapse all** operate on the matrix columns. Counts in parentheses describe the platform/tactic family before text filtering; a searched column header shows matching/total family counts. Double-click a technique or press Enter to open its existing details page, including parent metadata, Procedure Examples and copy buttons.

Checkboxes share the active document's selection with the sidebar tree and Selected Techniques. Checking a child leaves its parent's selection independent, and repeated occurrences synchronize across tactic columns. Platform/search filtering does not remove a document's selections. JSON and CSV export use the same selected IDs regardless of the current matrix filter. Creating a file, switching documents or changing the active document's ATT&CK version updates the matrix's catalog and checkboxes. Historical releases without sub-techniques still show their own phase/technique columns. Opening the matrix tab from a library section returns the workspace to TTP context.

### Matrix Module and Progress

`attack_matrix.py`, documented here in its source directory, projects verified catalog mappings and renders the matrix. `main.py` owns the sidebar entry, right-side tab and synchronization with document selection. The matrix is built when opened, so ordinary startup does not create its column models. No new input files are read and no output files are written by matrix browsing; its input is the already verified in-memory catalog. Existing catalog loading continues to show absolute snapshot input paths before use.

1. **Scope (1/3):** report `Input files: None` and `Output files: None`, resolve exact platform/tactic mappings, and identify parent/child families.
2. **Columns (2/3):** build one tactic column per GUI timer batch with completed/total progress. This retains the event loop for scrolling and other UI work.
3. **Ready (3/3):** apply search visibility and the current document's checked IDs, then report completion.

Progress appears in the terminal, Output and status bar. Changing platform or dataset stops the previous matrix build and clears stale models before rebuilding. Selection synchronization blocks recursive checkbox signals. Closing the application stops the matrix timer before the window is destroyed. Matrix-based exports use the existing three-stage JSON/CSV writer and display their absolute final and temporary output paths before writing.

### Matrix Audit and Preview

`audit_matrix.py` checks the matrix projection against independently derived raw Enterprise STIX mappings across all platforms plus All Platforms, and exercises actual native matrix controls and document/export integration.

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\audit_matrix.py'
```

The audit prints the absolute initial pointer `D:\MITREATTACK_SIMULATOR\data\attack\latest.json` and the resolved Enterprise bundle before reading. It also loads the cached v1.0 snapshot for the historical-view test, showing those manifest/bundle paths. Before writing, it displays absolute paths for `artifacts\matrix-audit.json`, `artifacts\matrix-preview.png`, `artifacts\matrix-selection-example.json`, and `artifacts\matrix-selection-example.csv`. It performs no downloads and does not change the user's dataset pointers.

Seven stages verify raw reference mappings; every platform/tactic family and checkbox scope; sidebar opening and official column order; native arrow/checkbox actions, tree synchronization and exports; search/expand/collapse/platform filtering; independent documents, historical restoration and detail/library navigation; then the rendered preview and final report. The screenshot shows All Platforms with the Scheduled Task/Job families expanded in Execution, Persistence and Privilege Escalation. The original catalog and document audits remain available for their respective workflows.

## Navigator and Official Python SDK Integration

The desktop exchanges [ATT&CK Navigator Layer files](https://github.com/mitre-attack/attack-navigator/tree/master/layers) and calls the official [mitreattack-python](https://github.com/mitre-attack/mitreattack-python) SDK. The existing PySide6 interface, verified STIX 2.1 catalog and direct source-to-technique bulk-selection rules remain the application's foundation. Navigator is available through its standard file format and an explicit website-opening action.

### Dependencies and Setup

The working environment uses **Python 3.11**, **PySide6 6.12.0**, and **mitreattack-python 6.2.1**. Direct dependencies are pinned in `requirements.txt`; `requirements-lock.txt` records the tested environment, including the SDK's transitive dependencies. Installation/checking was performed in the existing `C:\Users\nick5\MITREATTACK_SIMULATOR` virtual environment. Its dependency check reports no broken requirements.

```powershell
Write-Output 'Input file: D:\MITREATTACK_SIMULATOR\requirements.txt'
Write-Output 'Output directory: C:\Users\nick5\MITREATTACK_SIMULATOR\Lib\site-packages'
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -m pip install -r 'D:\MITREATTACK_SIMULATOR\requirements.txt'
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -m pip check
```

Installation reads the pinned dependency file, downloads the SDK/dependencies from the package index with pip progress, and writes to the displayed environment directory. Missing SDK dependencies cause an integration operation to display an error; ordinary catalog browsing does not require an SDK import at startup. The SDK and Navigator have Apache-2.0 licenses; see their respective LICENSE/NOTICE files when redistributing dependencies. MITRE dataset attribution/terms remain those recorded with each downloaded snapshot.

### File Exchange

**File → Export Navigator Layer…** exports the active document as Layer **4.5** JSON with the document's exact ATT&CK version and Enterprise, Mobile, or ICS domain. The general Export dialog also offers **Navigator Layer files (*.json)** and remembers this format for the next export/pre-close Save. The export includes selected technique IDs, independently handles parents/sub-techniques, and assigns a blue annotation to a newly selected technique without an existing row. Studio JSON and CSV remain available. Navigator supports ATT&CK v4 and later; documents using earlier releases can still export Studio JSON/CSV, while Navigator export/comparison returns an explicit error.

**File → Import Navigator Layer… / Ctrl+O** opens a native preview. UTF-8 (with or without BOM) and UTF-16 with BOM are supported. A file can contain one layer or an array of up to 20 layers; the preview lets the user choose one layer to import. Files are limited to 10 MB and each layer to 20,000 technique rows. Layer schemas 3.0–4.5 are accepted where supported by SDK validation; legacy domain/version fields are normalized. Enterprise, Mobile, and ICS layers resolve against their recorded domain, independently of the currently open file. A missing domain snapshot produces an explicit error and leaves open documents unchanged.

The recorded ATT&CK release is authoritative. If that version differs from the active document, **Load version / Preview** validates or downloads its exact snapshot using the existing pinned-version workflow, without writing `active.json` or changing other open documents. An unversioned layer displays an explicit version selector, initially set to the active snapshot. Unknown/inactive IDs and tactic mismatches appear in the resolution column; they remain preserved annotation rows but are excluded from selection. Import only commits after **Import as new document**, creating a separate tab with synchronized tree/matrix selections.

The preview offers three selection policies: enabled rows (or explicit Studio selection metadata), all listed rows, and rows with a score/color. A score of zero is still a scored row. Repeated rows for the same ID are deduplicated for document selection while tactic-specific annotation rows remain separate. Cancel, read/validation errors, and failed snapshot preparation leave existing documents untouched. Layer `customDataURL` and reference links are retained as data; importing does not fetch these URLs.

Navigator annotations represent more than document selection. Export records an explicit `TTP Selection Studio selected` marker in standard row metadata so an application-generated file can restore its exact selected IDs. Original disabled tactic rows stay disabled while an unchanged imported selection remains selected through another row. Removed selections disable their rows; newly selected IDs are added. Unknown rows remain disabled in the exported layer. Existing comments, colors, decimal scores, links, metadata, filters and supported display settings are retained.

`navigator_integration.py` invokes the SDK's `Layer` parser to validate supported structures, with explicit checks for IDs, finite scores, colors and schema versions. SDK 6.2.1 coerces fractional scores to integers and rejects `customDataURL` in its internal model. We therefore validate a copy (omitting only that extension from the SDK probe) and export the preserved original JSON values. This avoids loss of decimal precision and supported extension data. No SDK source files are patched.

### Technique Annotations and Document State

A technique detail page in the active document's domain exposes **Edit Navigator annotation…**. The native editor supports an all-tactic or individual tactic scope, comment, optional finite numeric score, optional `#RRGGBB` color, and an **Include this TTP in the document** checkbox. Existing imported scope data is loaded for editing. Save validates a temporary copy before changing the active document and synchronizes the checkbox with all tree/matrix occurrences. Cancel or invalid values preserve document state.

Comments/colors/scores are document data and affect the changed-content marker. Studio JSON conditionally includes `navigator_layer`; its existing selected-TTP schema remains version 1.0. CSV continues to represent the selected TTP list and does not contain the full annotation model: exporting an annotated document as CSV leaves it marked changed. A pre-close Save that does not preserve all annotations keeps the document open. Use Studio JSON or Navigator Layer for annotation persistence.

When the active document changes ATT&CK versions, annotations are archived separately by source version and restored when that version is selected again. Other-version annotations are included in the optional Studio JSON `navigator_snapshots` field. Navigator Layer exports only the current version's layer; if other-version annotations remain archived, the document stays changed until a Studio JSON export preserves all versions. Other document tabs retain their own snapshots/annotations. Application-wide exit prompts and recovery remain tracked in NOTIMPLEMENTYET.md.

### Selection and Version Comparison

**Navigator → Compare open TTP documents…** displays common techniques, left-only techniques and right-only techniques for two open documents using the same ATT&CK version and domain. It exports a validated Navigator Layer with a legend: green = both, blue = left only, orange = right only. Comparing different domains or snapshot versions is explicitly rejected; comparisons do not modify the source documents.

**Navigator → Compare ATT&CK versions…** compares two downloaded snapshots for the active document's Enterprise, Mobile, or ICS domain through the SDK's actual `DiffStix` engine. It verifies both snapshot manifests/hashes before processing local STIX **2.1** bundles. The native result table includes SDK classifications for additions, major/minor/other changes, patches, revocations, deprecations and deletions across supported object types. It also lists selected IDs unavailable in the target version, helping review migration impact before using the existing Version switch. An absent historical domain fails explicitly. The comparison itself does not switch versions, migrate IDs, modify selections or write dataset pointers.

The SDK reads standard `<domain>.json` filenames, so the adapter copies verified bundles into a generated `artifacts\sdk-diff-<random>` staging directory. Absolute input/temporary output paths are displayed before file copies. The directory is automatically removed after completion or an exception. An explicit **Export version comparison JSON…** writes the SDK result plus domain, versions, format and selection impact. The result's release labels come from verified manifests; the SDK may print an unknown-release-hash notice for these Collection bundles without preventing the STIX comparison. No network access is required for comparing already downloaded snapshots.

**Navigator → Open ATT&CK Navigator website** opens the official browser application only when clicked. Exported layers can then be opened using Navigator's layer-file loading controls. The desktop does not automatically upload documents or annotation files.

### Source Modules and Visible Progress

All integration programs reside alongside this README:

| Module | Operation flow |
| --- | --- |
| `navigator_integration.py` | Validate SDK layer copies, preserve raw annotations, resolve IDs, serialize atomic layer/report exports, compare selections, and run the official SDK over verified local bundles. |
| `navigator_dialogs.py` | Native import/version previews, selection policies, scoped annotation editing, selection comparison and background-worker lifecycle. |
| `ttp_documents.py` | Track annotation-sensitive fingerprints, per-version annotation archives, remembered export formats and annotation-preserving Studio JSON. |
| `main.py` | File/Navigator menu actions, Ctrl+O, annotation toolbar action, new imported tabs, selection synchronization and pre-close preservation. |
| `audit_navigator.py` | Seven-stage integration audit, generated fixtures, exports, UI screenshots and final report. |

Import displays the absolute source filename and reports no file output for the preview, followed by **1/4 read/SDK validation**, **2/4 snapshot resolution**, **3/4 preview ready**, and **4/4 new-document commit**. Downloading a missing snapshot uses the existing absolute-path and four-stage version workflow. Annotation editing displays no file inputs/outputs, then **1/2 editing** and **2/2 saved** or cancellation. Selection comparison reports no file inputs/outputs and **1/2 comparison**, **2/2 counts**.

Layer/report export displays absolute final and unique sibling temporary paths before **1/3 serialization**, **2/3 UTF-8 write**, and **3/3 atomic publication**. Failed writes preserve the existing output and document export state, and remove temporary files. Version comparison shows **SDK initialization**, then **1/4 verify snapshots**, **2/4 SDK comparison**, **3/4 report/selection impact**, **4/4 completion and cleanup**. Progress appears in the terminal, Output, dialog/status labels and progress bars.

Import parsing/snapshot preparation and SDK comparison use background workers. Controls prevent starting a second operation or using a stale snapshot preview. Closing a busy integration dialog requests cancellation and waits for its current SDK stage to finish before destroying the worker; closing the main window follows the same rule. The comparison SDK has a visible initialization stage before entering the worker. During the SDK comparison, the progress bar is indeterminate because the SDK does not provide a reliable overall percentage. Dataset loading retains the existing worker/tree-build flow.

### Navigator Integration Audit

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\audit_navigator.py'
```

The audit prints the absolute `data\attack\latest.json` input and all resolved cached bundle paths before use. It prints output paths for `artifacts\navigator-audit.json`, `navigator-import-preview.png`, `navigator-version-comparison-preview.png`, and every fixture/export inside a unique `artifacts\navigator-audit-<uuid>` directory before writing. Export readbacks display their input paths. It performs no downloads and does not change active/latest dataset pointers.

1. Validate through the installed official SDK; verify UTF-8/UTF-16, Unicode, decimal scores, selection policies, unknown IDs/tactic mismatches and rejected malformed fields.
2. Exercise native import cancellation/preview/commit, independent documents, synchronized selections, exact layer round trips, Studio JSON/CSV behavior and failed atomic publication.
3. Exercise the native annotation action and scoped editor; verify changed-state tracking, failed annotation preservation and remembered Navigator export filters.
4. Compare selected sets through the native dialog, reject mixed/historical versions, and verify annotation archives plus exact cached-version preview resolution.
5. Run the actual SDK comparison in the background on v19.2/v11.2 STIX 2.1 snapshots; verify selection impact, read-only document behavior, staging cleanup, result-table population and report export.
6. Exercise invalid/multiple-layer inputs and preview invalidation when the selected layer/version changes.
7. Publish a PASS report only after every assertion succeeds. Failed checks produce a nonzero process exit and do not publish a passing report. Existing catalog, documents, matrix and bulk-TTP audits remain separate regression checks.

