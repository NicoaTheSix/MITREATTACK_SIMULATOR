# Matrix Display and Annotation Indicators

See the [project README](../README.md) for startup. These features apply to compatible Navigator layers in Enterprise, Mobile, ICS and custom ATT&CK datasets.

## Independent Names and IDs

1. Open a document, then open its matrix from the TTP sidebar.
2. Toggle **Show names** and **Show IDs** independently. Names default On, IDs Off.
3. Both On shows the ID and name; both Off leaves unlabeled cells and tactic headings. Checkboxes, colors and hover information remain usable.
4. Switch to **Mini**: labels and custom tactic header backgrounds are suppressed, and the toolbar controls are disabled. Returning to Flat/Side restores the saved choices.

These are presentation choices. Full technique IDs/names remain in tooltips, details and selected-TTP JSON/CSV. Name/ID flags also apply to tactic headers. They do not change inclusion, annotations or scoring.

## Tactic Header Background

Check **Tactic background**, then use **Header color…** to choose a color. Choosing a color enables its display. Text contrast adjusts automatically. Uncheck the option to hide the background while retaining its color.

Alternatively use **Navigator → Layer settings… → Display** to edit all display flags and the six-digit `#RRGGBB` header color in one draft. Save applies a validated result; Cancel or invalid color leaves the document unchanged. Display preferences can be configured in this tab even while Mini is active; Mini still suppresses them visually.

| Stored field | Meaning |
| --- | --- |
| `layout.showName` | Show technique/tactic names |
| `layout.showID` | Show technique/tactic ATT&CK IDs |
| `showTacticRowBackground` | Show the shared tactic header color in Flat/Side |
| `tacticRowBackground` | Header color, default `#dddddd` |

These settings are independent per layer. Switching tabs, duplicating layers, Studio Save/reopen, Navigator exchange, domain/version archives and session recovery preserve them. Editing them makes the layer unsaved until Studio Save.

## Expand Annotated

Click **Expand annotated** to expand families whose mapped children have annotations and collapse the other families. It follows the current platform projection and checks each tactic separately. Comments, user Metadata, Links, a stored score including **0**, manual color, explicit disabled state and active source Notes count as annotations. A parent comment alone does not qualify an unannotated child.

The operation expands a **family**: once open, its siblings remain visible under the existing search/hide-disabled filters. It does not remove unannotated siblings or add any technique to the selected list. Example: a parent with five children and one child comment opens; another parent with only a parent comment stays collapsed.

Expand annotated, Expand all and Collapse all save `layout.expandedSubtechniques` as `annotated`, `all` and `none`. These mark the file unsaved and restore on layer switches, Save/reopen, Navigator exchange and recovery. Individual arrows now preserve other families and save standard per-tactic `showSubtechniques` flags, switching the dropdown to **Per-technique · saved**. Mini honors explicit closed flags. Search may open matching families temporarily; clearing it restores saved states without saving automatic search expansion. Selection and annotations are unchanged. To export this view, choose SVG **Show children expanded when export opened**. See [individual expansion examples](detection_interaction_en.md), [global modes](visibility_expansion_presets_en.md) and [SVG/Excel exports](aggregation_and_exports_en.md).

## Annotation Indicators

| Visual | Meaning |
| --- | --- |
| Yellow underline | Nonempty comment, user Metadata or a source STIX Note |
| Blue underline | Assigned Links |
| Both lines | Both categories apply |
| No line from selection alone | Reserved selection metadata and divider-only lists are ignored |

Indicators work in Flat/Side/Mini, including selected or disabled cells and when **Show layer colors** is off. Scores/colors/states qualify for annotated expansion but do not create note/link lines by themselves. Clearing the final comment/Metadata or Links removes its indicator on repaint. A yellow line may remain after clearing an editable comment if source Notes or other user Metadata still exist.

Hover to read full identity, comments, Metadata, Links and source Notes. Notes are read-only content from active STIX `note` objects referencing the technique in the exact domain/version/dataset. Revoked/deprecated Notes and unrelated references are ignored. Notes do not become editable comments or selected-row CSV comment fields. Custom Bundles can contain Notes without a `name`; they use `abstract` and `content`.

**Show all layers** combines indicators from compatible layers independently of colored overlap. The tooltip identifies source-layer annotation text, including a source that has annotations without color. Label switches/header color still come from the active layer.

## Export and Processing

SVG uses the saved label flags, Flat/Side header background and yellow/blue underlines. Mini SVG keeps compact cells with annotation/state symbols and tooltips. Both Excel modes use a labeled vertical matrix according to the stored flags even when the native view is Mini. Header fills preserve saved colors; yellow bottom borders mark notes/Metadata and blue right borders mark Links. Excel comments retain full IDs/names and source Note text. Details sheets and JSON/CSV retain identities regardless of display choices.

Display edits announce **Input files: None / Output files: None** before **1/2 validate → 2/2 apply**. Annotated expansion announces no file I/O before **1/2 resolve → 2/2 update columns**. Save/export/recovery operations show absolute final/temporary paths before their existing stage progress. Source catalog reads announce their absolute input paths; rendering/viewing Notes never writes Bundles. Invalid settings and Cancel preserve previous state.

## Verification

Run `.venv\Scripts\python.exe -B audit_matrix_display.py` with `QT_QPA_PLATFORM=offscreen`. It reports absolute paths and seven stages, verifies actual painted pixels and clearing, scope/selection independence, Mini/Side behavior, source Notes, file/recovery round trips and SVG/Excel readback. Examples and `audit.json` are in `artifacts/matrix-display`.

- [SVG example](../artifacts/matrix-display/matrix.svg)
- [Excel example](../artifacts/matrix-display/matrix.xlsx)
- [繁體中文手冊](matrix_display+_zh.md)
