# Source Result Batches and Related Technique Selection

[繁體中文](source_relationship_selection+_zh.md) · [Complete feature tracker](../NOTIMPLEMENTYET.md)

## Add or Remove All Search Results

Open Groups, Software, Campaigns, Mitigations, Assets or Detections in the sidebar. Choose Name/ID/Description through **Source search fields…**, then enter a literal query. The summary shows matching sources in the active document's domain, deduplicated mapped techniques and mapped tactic occurrences.

- **Add all results** adds the union of related techniques, retaining unrelated selections.
- **Remove all results** removes that union, retaining unrelated selections.
- An empty query means all supported sources in the current category. Results without mappings leave the document unchanged.
- Other domains remain browsable but are excluded from this document's batch. Analytics in Detections are browse-only, not selection sources.

**Example:** two matching groups both map to T1059, and one also maps to T1059.001. The summary reports two sources and two unique techniques. Add all results includes each technique once while retaining other choices. Remove all results removes those two IDs even if another source previously added them: source ownership is not tracked.

Typing, choosing an entry or closing a dropdown never changes included TTPs. Add/Remove applies immediately without another confirmation dialog. A stale catalog or any invalid source ID rejects the entire batch rather than partially applying it.

## Matrix Source Picker

**TTPs from** supports eight kinds: Campaign, Software, Group, Mitigation, Asset, Detection Strategy, Data Component and Data Source.

1. Choose a kind, then browse or enter a name/ID/description query. Matching ignores case and supports spaces.
2. Choose an exact result for single-source **Add techniques / Remove techniques**.
3. While typing partial text, use **Add all results / Remove all results** for the matching union; single-entry buttons stay disabled.
4. Clearing the text means all entries of that kind. Choosing an exact result narrows the result batch to that entry.
5. **View source** opens the native page, mapped-technique table and Add all TTPs / Remove all TTPs controls.

Data Component labels group the exact `Data Source : Component`. Colliding labels include full STIX IDs. Component search fields consider both the component and its resolved parent, so Name-only searches can find components through the source name. Detections also includes a Data Sources library.

**Example:** choose Detection Strategy, leave only Description enabled, and enter a phrase. The summary counts the technique union across matching strategies. For one strategy, select its exact completion before Add techniques.

## Mapping Semantics

Source dropdown, completion and sidebar results now provide a temporary matrix preview on mouse hover. Cyan outlines identify mapped occurrences; dashed parent outlines identify related collapsed children. Use **Show matrix preview** in the sidebar to retain source results beside the matrix. Leaving restores the original display without changing inclusion, annotations or dirty state. See the [hover guide](source_hover_preview_en.md) for scope and cleanup rules.

| Source | Related techniques |
| --- | --- |
| Group / Software / Campaign | Active source `uses` technique |
| Mitigation | Active source `mitigates` technique |
| Asset | Reverse lookup of technique `targets` asset |
| Detection Strategy | Active strategy `detects` technique |
| Data Component | Legacy direct `detects`, or explicit strategy/analytic log-source references |
| Data Source | Union of components whose `x_mitre_data_source_ref` resolves to this source |

The modern component path follows Strategy `detects` Technique, Strategy `x_mitre_analytic_refs` to an Analytic, and `x_mitre_log_source_references[*].x_mitre_data_component_ref` to the Component. Details label these **Explicit reference path (derived mapping)** separately from original STIX relationships, with local links to the strategy, analytic, component and source.

Only the document's exact dataset/domain/version contributes. Revoked/deprecated sources, techniques, edges or analytics, missing references and wrong object types do not contribute. Names never create relationships. Legacy technique data-source text remains searchable through TTP Data Sources, without inventing source IDs or edges. Historical versions lacking a source kind show an empty list. A mapping is reference information, not evidence that detection was deployed or tested.

## Preferences and Counts

Source actions start from all mapped tactics, then follow family, across-tactic and visible-only preferences. Summary counts precede these preferences; completion reports actual changed tactic occurrences. Platform filters, matrix technique search and collapsed children affect eligibility when visible-only is enabled. The separate Select… scope controls do not restrict source buttons.

**Example:** choose Windows, Collapse all, family linking and visible-only. Adding a component cannot introduce collapsed children or Linux-only targets. Earlier unrelated choices remain included.

Enabled state is independent of inclusion. Source operations preserve scores, explicit colors, comments, Links, Metadata and disabled states. Existing Studio/Navigator/CSV exports and recovery preserve selected technique/tactic sets. Relationships are rebuilt from the matching cached Bundle; CSV does not gain source ownership tracking.

## Processing Flow and Files

Catalog loading announces absolute Bundle/pointer paths before the existing background worker builds direct mappings, strategy/analytic/component paths and source unions with progress. Queries use in-memory indexes. Selection announces no input/output files, then reports three stages: resolve/validate the whole union, apply preferences, and complete. Failures preserve the document. Selection itself writes no export file.

Save/Save As and exports retain resolved absolute-path announcements, validation and atomic publication. Unsaved-document prompts and recovery retain their existing behavior.

From the project root:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_source_selection.py'
```

The seven-stage audit announces absolute `<project-root>/data/attack` and `<project-root>/artifacts/source-selection` paths before reading cached official snapshots and isolated three-domain fixtures. It checks independent raw-STIX references, overlapping unions, duplicate names, invalid/revoked paths, visibility/family preferences, stale-catalog rejection and Studio/Navigator/CSV/recovery round trips. Outputs include `audit.json`, examples and screenshots. It downloads no data and changes no official pointers.
