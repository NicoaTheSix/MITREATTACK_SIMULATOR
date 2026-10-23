# CAR Analytics, Data Model and Sensors

Fusion Studio includes a fixed local snapshot of MITRE's Cyber Analytics Repository (CAR). CAR analytics are independent research content, alongside the ATT&CK and ATLAS TTP selections in each Workplace. Selecting an analytic does not select its mapped techniques.

## Browse, sort and filter

The complete **CAR Browser** is an upper reference tab beside **Technique Details**. Its **×** and **Close CAR Browser** context action close it independently of documents and other reference tabs. All analytic/model/sensor links reuse it. Workplace can reopen its retained in-memory view; session recovery preserves tab visibility, active page and category, restoring the category list rather than individual detail navigation. Inclusion and annotations are unchanged by tab visibility.

Choose **CAR Analytics** in the left activity rail to display its searchable sidebar. Click a sidebar row or press Enter on the selected row to open its analytic detail in CAR Browser. **Workplace → Open CAR Browser** also opens the chosen analytic, or the full category browser when no entry is chosen. In the full browser, **Analytics** shows an Include checkbox followed by the six official attributes: ID, Name, Submission Date, ATT&CK Techniques, Implementations and Applicable Platforms. Click a header to reverse sorting. Dates use calendar order, names ignore case, equal values use ascending CAR IDs, and missing values stay last in either direction. Multi-value columns sort their displayed summaries, rather than counts. Resize columns or scroll horizontally to inspect long values.

Search the name or ID, combine platform and implementation-tool filters, or enable **Only included Analytics**. These actions do not change inclusion. Click rows to highlight; Ctrl/Shift extends the highlighted selection. Check Include, or use **Add highlighted Analytics to Workplace** / **Remove highlighted Analytics from Workplace**, to change inclusion explicitly. Double-click a row, use **View Analytic information**, or use its context menu to read details. All native implementations remain available, including repeated tools and link-only implementations.

## Follow technique relationships

The **By ATT&CK Technique** tab has parent technique, sub-technique scope and analytic columns. **N/A — technique only** means that native coverage did not specify sub-techniques. A mapping to `T1036.003` does not imply a mapping to sibling `T1036.005`. Parent detail pages aggregate related analytics with their actual scope identified. Grouping follows the fixed snapshot's `generate_analytics.py`; duplicate parent coverage uses the first occurrence for grouping, while the complete native record remains visible.

Click parent, child and analytic links to navigate inside Fusion Studio. Technique details contain **Related CAR Analytics** and a return link. **Back to CAR results** restores the browser's existing query, filters, sort and list tab. Navigation is read-only. Technique IDs resolve against the current document's domain, version and dataset; missing, revoked or deprecated mappings and tactic mismatches remain visible in the resolution details. Resolution never switches datasets automatically. ATLAS has no inferred direct CAR mapping.

## Inspect Data Model and Sensors

The left rail has separate **CAR Data Model** and **CAR Sensors** icons, labels and tooltips. They open sidebar lists; click an entry or press Enter to open its content. **Workplace → Open CAR Browser** remains available. In the full browser, expand a model object to browse its actions and fields. Detail links find analytics that reference the exact object/action/field scope. Original descriptions and complete records remain available.

Sensors are separate tool/version entries. Their pages retain native mappings and notes. Candidate analytics have at least one exact `object/action/field` intersection with that sensor's native mappings, matching the fixed generator's rule. The page lists the intersecting fields. A partial intersection is a candidate, not evidence of complete telemetry or a validated detection. Missing data requirements are explicitly unknown. Actions and fields are not multiplied into unsupported sensor mappings.

## Include analytics in a Workplace

**Workplace → Workspace Selections** contains a collapsible **CAR Analytics (n)** section with its own count. It is separate from the ATT&CK/ATLAS TTP count. Highlight rows with Ctrl/Shift, then right-click to view information or remove the highlighted analytics. Cancelling a menu does nothing. Removal clears inclusion and retains the native analytic snapshot and any stored annotations. Repeated adds do not duplicate entries. Each document is independent; duplicated layers copy CAR state independently, and stale actions cannot modify another document.

## Save, reopen, export and recover

Native read/write options contain ATT&CK, ATLAS and **Include CAR Analytics**, all enabled by default. At least one content type is required; CAR-only is valid. **Save / Save As** and **Open Studio JSON** preserve `car_workspace` schema 1: keys are dataset SHA-256 plus CAR ID, and each entry records title, repository, commit, original analytic, inclusion and annotation fields. Unselected entries remain archived for future edits. Old documents without this extension open with no CAR selections.

Only saving all three content types establishes a complete saved baseline. Partial output leaves the full Workplace dirty. Excluding CAR removes its references and content from that output; excluding CAR on read skips parsing its block. CAR-only Studio files can reopen without ATT&CK disk datasets. A missing exact CAR snapshot retains the saved analytic and provenance with an **Unresolved snapshot** label; opening does not download or substitute a newer source.

Automatic recovery always includes all content and uses the existing startup restoration and Output notice. The asterisk, close/exit checks and duplicate behavior also include CAR changes. Sorting, highlighting and navigation do not make documents dirty.

CSV exports add `content_type` values `attack_ttp`, `atlas_ttp` and `car_analytic`. CAR rows use `car_id`, `car_snapshot`, `car_commit` and `car_analytic_json`, leaving `technique_id` empty. CSV is an exchange report, not a complete reopen format. Navigator and matrix Excel project only explicitly selected TTPs; they cannot store CAR inclusion. Use Studio JSON for complete CAR preservation. CAR-only Navigator/matrix export reports this limitation instead of creating fake techniques.

## Source, progress and limits

The bundled source is `mitre-attack/car@1b922fe1527d956e222a99473472e594f10f610b`: 102 analytics, 13 model objects and seven sensor records. `data/car/source.json` records per-file SHA-256; original Apache 2.0 LICENSE and NOTICE are retained. See [provenance](../data/car/PROVENANCE.md).

Startup reports absolute manifest/source paths, then verification → parsing → indexing → publication progress in a worker. CAR failure is diagnosed separately and leaves ATT&CK/ATLAS available. Inclusion reports memory-only inputs/outputs, identity validation → mutation → view/recovery synchronization. Saves report actual input, final and temporary absolute paths before serialization and atomic publication; errors leave the original file intact. All test settings, sessions and examples use `artifacts/car-integration/`.

CAR tests and commands are reference text only. This integration does not deploy queries, run SIEM searches, execute unit tests from upstream, validate sensor readiness or infer detection effectiveness. Portable source bundles, deployment management and evidence scoring remain future work.

See [Studio files and recovery](studio_files_en.md) and the [guide index](README.md).

## Collapsible code and JSON panels

Implementation code, coverage JSON, complete native records and Data Model/Sensor JSON are framed code blocks. Each entry opens with every block collapsed. Click the arrow/title to expand; the header **Copy** button also works while collapsed and copies the complete original block with its whitespace, escapes and Unicode. Actual implementation code is separated from metadata JSON for direct copying. Editors are read-only, monospaced and scroll long lines horizontally. **Copied** briefly confirms the operation. Switching entries resets the panels; changing language keeps the current expansion state and code. These actions do not edit selections, annotations or files. The program reports in-memory inputs/no file output and update/copy progress.
