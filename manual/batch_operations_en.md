# Independent States and Batch Operations

## Inclusion and enabled state

Checkboxes mean **include this TTP in the selected export list**. Enabled state controls layer appearance, aggregate/formula participation and visibility when Hide disabled is enabled. These are independent: a checked disabled TTP is still exported; an unchecked enabled TTP can retain and display annotations in a Navigator layer. Selection changes never rewrite enabled flags or synthesize colors.

Use matrix **State… → Enable selected / Disable selected / Toggle selected states**, the Selected Techniques state menu, or Navigator's Enable/Disable selected actions. These affect all mapped scopes for the included TTPs. Technique context menus also offer whole-technique and **Enable/Disable in this tactic** actions, including on unchecked techniques. The single annotation editor has separate Include and Enabled checkboxes; its Enabled setting applies only to the chosen annotation scope. Specific rows override global rows. Colors/scores/comments/links/metadata survive disable/enable. In all-layer view other enabled layers can still contribute colors; state commands edit the active layer only.

Example: include T1053.005, add a comment and score, then Disable it. Its inclusion checkbox stays checked and the annotation data remains. Export Studio JSON or CSV: the selected row includes global `enabled` and ordered `tactic_enabled` entries. Navigator JSON saves actual state flags and reserved selection metadata, so importing your own disabled-but-included TTP restores both independently. Navigator layers contain customized entries as well as selected entries; Studio/CSV selected lists contain only included TTPs.

## Batch selection

Open the matrix and choose **Selection scope**:

- **Platform scope · includes hidden**: all techniques mapped to the current platform union, including collapsed/hidden disabled ones. Search text is ignored.
- **Search matches · excludes hidden**: direct name/ID matches, case insensitive and supporting spaces; hidden disabled rows are excluded. Ancestor context headings are not automatically selected.
- **Visible / expanded cells**: currently displayed matrix cells, including expanded children. This refers to filtered/expanded content, not just the pixels inside the scroll viewport.

Optionally choose one tactic. Structural grouping-only parents are not selectable. Click **Select…**:

- Select all in scope: add the scope, preserving selections outside it.
- Select only this scope: replace the entire included set.
- Deselect scope: remove only this scope.
- Invert scope: toggle membership only inside the scope.
- Select annotated only / Select unannotated only: replace the included set with the matching subset in scope.

Annotated means a non-empty comment/color/Links, a score including zero, user Metadata/dividers, or disabled state. The app's reserved inclusion metadata and expansion preferences do not count. For one tactic the effective annotation is checked; for all tactics any mapped annotation qualifies. Right-click a tactic header for Select/Deselect/Invert in that platform/tactic scope. Selection is still per technique ID across tactics; it never changes annotations or enabled state.

## Batch editing

Use **Batch edit selected…** in the matrix, **Batch edit included TTPs…** on Selected Techniques, or **Navigator → Batch edit selected TTPs…**. Targets are all included TTPs in the active document, including those outside matrix filters. The dialog starts with every field set to **Keep unchanged**.

Choose a scope: **Entire technique · all mapped scopes**, or one tactic with the affected count. TTPs not mapped to that tactic are skipped. Each field can be set or cleared independently:

The target list shows exact technique IDs/names; hover an entry to inspect its current global or chosen-tactic values before editing. The affected/skipped counts update when you change scope.

| Field | Set / replace | Clear / reset |
| --- | --- | --- |
| Enabled state | Enabled, Disabled, or toggle each affected scope | Default Enabled |
| Comment | Enter text, including line breaks | Remove comment |
| Score | Finite number; zero is valid | Unscored |
| Color | `#RRGGBB` | Remove explicit color; score gradient may remain |
| Links | Replace lists with entered labels/HTTP(S) URLs/dividers | Remove user links |
| Metadata | Replace lists with entered text names/values/dividers | Remove user metadata; preserve reserved inclusion metadata |

Example: select 20 TTPs, set Comment to `Validated in lab`, set Score to `0`, and leave Color/Links/Metadata/State unchanged. Apply updates only those two fields. A subsequent tactic-scoped edit changes only TTPs mapped to that tactic. Newly created tactic rows copy the current global annotation first so untouched fields survive; existing scope overrides remain independent.

**Clear all selected annotations…** opens a draft with all six fields set to Clear. Review the target count/scope, then Apply. It resets enabled state and removes known annotation fields while preserving inclusion, layout preferences and unknown extensions. To keep colors/scores, switch those fields back to Keep before applying. Unresolved historical annotation scopes are retained.

## Processing and preservation

Before editing, Output reports in-memory inputs and no output files. Progress covers validation, per-target draft updates and final validation. Batch dialogs run the update in a worker. Changes commit only after success; invalid scores/colors/URLs, Cancel or interrupted workers preserve the original document. State and selection actions also report their stages. No files are written until Export; those operations show resolved absolute output and temporary paths before writing.

Changes belong to one document/domain/version/dataset. Duplicates and in-memory domain/version archives preserve independent states. Session recovery and reopening Studio JSON remain separate unfinished features; export Studio JSON before closing when you need full annotations and archives. See [README](../README.md) for startup and the audit command.
