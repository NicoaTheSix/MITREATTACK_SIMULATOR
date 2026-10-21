# Selection Preferences, Extended Search and Mitigation Batches

## Selection Behavior

Use **Selection behavior…** in the matrix or **Navigator → Selection behavior**. All three preferences belong to the active document and return when switching tabs:

| Option | Default | Behavior |
| --- | --- | --- |
| Select techniques across tactics | On | Checking/unchecking a technique affects all its mapped tactics |
| Select parent, children and siblings together | Off | Selecting a parent includes its children; selecting a child also includes its parent and siblings |
| Select visible techniques only | Off | After linking, keep only logically visible technique/tactic occurrences in the originating view |

With cross-tactic selection off, only the clicked tactic changes. Family linking includes only members mapped to that tactic; grouping-only parents are excluded. With cross-tactic/family linking on and visible-only off, the entire family can be included outside the visible platform/search filter. Visible-only intersects targets after linking, excluding collapsed children, hidden disabled rows and filtered occurrences. Matrix/source batches use the matrix; sidebar checkbox clicks use the sidebar. Rows reached by scrolling still count as visible. Changing a preference affects future operations, without retroactively widening/deleting existing choices or altering colors, scores, annotations or enabled states. See the [visibility and saved-expansion examples](visibility_expansion_presets_en.md).

**Example:** Disable cross-tactic selection and check T1053.005 under Execution. Its Persistence/Privilege Escalation occurrences remain unchecked. Selected Techniques still has one T1053.005 row and adds Selected tactics underneath. Duplicate sidebar branches for the same tactic stay synchronized. Re-enabling cross-tactic selection does not immediately change the existing choice; the next selection applies the new setting.

Select… add/replace/remove/invert and tactic-header actions also honor preferences. Annotated/unannotated selection classifies a technique across its tactics when cross-tactic selection is on; when off, each occurrence's effective annotation can be considered separately. Family linking can add extra family members. Filtering scopes the initial targets and does not clear selections outside that scope unless a replacement action is used.

For partial tactic selections, Batch edit defaults to **Selected tactic occurrences only**. Selected-color/score/state actions also edit only included cells. The editor still offers an explicit **Entire technique · all mapped scopes** or a particular tactic; whole-technique context commands retain their stated scope. Inclusion and Enabled remain independent: deselection never deletes annotations or disables techniques.

## Description and Data Sources Search

Choose **TTP search fields…** in the TTP sidebar or **Search fields…** in the matrix. They share the active document's field preferences, while retaining separate query text:

- Name and ATT&CK ID: enabled by default.
- Description: searches technique descriptions.
- Data Sources / Components / Log Sources: searches resolvable source/component names and log names/channels within the dataset.
- Detection Strategy: searches strategy Name/ID/Description through active direct `detects` mappings. This field starts Off and does not borrow modern strategies for old datasets; see [Detection Strategy examples](detection_interaction_en.md).

At least one field stays enabled. A literal case-insensitive substring in any enabled field matches; queries are not regular expressions. Spaces are accepted, and outer whitespace is trimmed only for comparison without rewriting input text/cursor position. Sidebar search runs on Enter or after about 180 ms; matrix search also feeds direct-match batch selection.

**Example 1:** Enable Description, disable Name/ID and search `PowerShell` to find descriptions mentioning it, including techniques with other titles. Matching branches retain necessary parent context.

**Example 2:** Enable only Data Sources. Search `Sysmon` or `WinEventLog:Security` in a recent dataset, or `Process Creation` in historical data. Results depend on the actual domain/release; absent relationships are not inferred.

Historical sources include technique `x_mitre_data_sources`, component `detects` relationships and source references. Modern indexing also follows active detection strategy → analytic → log-source/data-component references. Revoked detects relationships and inactive strategy/analytic objects are excluded. Names/channels come from the same snapshot, without mixing domains, versions or custom datasets.

A matching parent may display children as context. **Search matches** targets direct matches only; it does not include contextual relatives unless family preferences request them. SVG/Excel use the same fields. In library categories both TTP search controls are hidden. Groups, Software, Mitigations and Detections independently search Name/ID/Description; other categories retain Name/ID search.

## Add/Remove TTPs through a Mitigation

Both entry points have equivalent results:

1. Open a **Mitigations** entry in the active document's domain and click **Add all TTPs (N)** or **Remove all TTPs (N)**.
2. In the matrix, choose **TTPs from → Mitigation**, open the editable dropdown and search a name/ID such as `M1047`. Choose an exact entry, then click **Add techniques (N)** or **Remove techniques (N)**.

Campaign, Software and Group also support removal. All four source dropdowns default to Name/ID/Description; **Source search fields…** controls those fields independently of TTP search. Results still display and insert ID/name labels; hover for Description. Partial typed text only locates entries and cannot execute a stale previous entry. Entries without active targets are disabled, as are detail actions from another domain. See [source search controls](navigator_parity_controls_en.md).

Mitigations use only active direct `mitigates` relationships in the document's snapshot; other sources use `uses`. Targets are deduplicated; revoked/deprecated edges and indirect paths are excluded. N counts directly mapped technique IDs; family linking may make the actual result larger and visible-only can make it smaller. Source buttons start with all mapped tactics, then respect family/visible-only preferences. Selection scope/Tactic menus apply to the separate Select… operations.

**Example:** Include a technique unrelated to the chosen mitigation, then Add its targets. The unrelated choice remains. Remove affects the source targets (and relatives requested by family preferences). If another source also contributed a technique, Remove still removes it: source operations manipulate a set without per-source ownership tracking. Enabled states, comments, colors and scores remain untouched.

## Saving, Export and Progress

Studio JSON stores preferences, search fields and partial `selection_scopes`; full reopening and session recovery restore them. CSV adds `selected_tactics` per technique, separate from all mapped tactics and enabled states. Navigator JSON uses standard selection preference flags, tactic-specific inclusion Metadata and Studio extensions. External tools may remove extensions; verify scopes after round-tripping through them. Older Studio files without the optional fields use compatible defaults.

Layer duplication independently copies preferences/scopes; score formulas and reviewed migration respect tactic selection boundaries. Domain archives retain partial scopes. Version changes retain only valid tactics and never widen an invalid partial selection into the entire technique.

Operations announce in-memory inputs/no direct file outputs, then selection/index/source-resolution stages. Save/Export/Session writes retain absolute final/temporary path reporting and atomic publication. Querying alone never changes inclusion; changing preferences marks a document unsaved.

Verify from the project root:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -B .\audit_selection_search.py
```

Inputs are cached official data (including v11.3) plus an isolated generated STIX fixture. The announced absolute output directory is `<project-root>/artifacts/selection-search`, containing Studio/CSV/session examples, a screenshot and `audit.json`. Six stages cover preferences, historical/modern data sources, all layouts, mitigation add/remove, edits and persistence, verifying official pointers remain unchanged. See [README](../README.md) for startup and the [file guide](studio_files_en.md) for saving/recovery.
