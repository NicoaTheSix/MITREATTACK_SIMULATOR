# Visible Selection, Saved Expansion and Gradient Presets

## Select Visible Techniques Only

In **Selection behavior…**, enable **Select visible techniques only**. It defaults Off and is independent for each file. It applies after cross-tactic and parent/children/sibling linking, so those options cannot introduce invisible occurrences.

Matrix clicks, Select… batches, tactic-header actions and Group/Software/Campaign/Mitigation Add/Remove use the active matrix's platform, search, hide-disabled and child-expansion state. Sidebar checkbox clicks use the sidebar's own filtered/expanded branches. “Visible” means logically displayed rows, including rows reached by scrolling; it does not mean only the current screen pixels. Structural parent headings remain unselectable. If the matrix is rebuilding or has no matching catalog, source actions cannot select anything under this preference; open the matrix and wait for Ready first.

**Example:** Choose Windows, Collapse all, enable family linking and visible-only selection. Check a parent: eligible visible parent occurrences are included, but collapsed children and Linux-only members are not. Expand all and check it again to include the visible children. Hide disabled techniques to exclude those rows, too.

Turning the preference on does not delete existing hidden choices. Remove/Invert affect only eligible visible targets. Replace, annotated and unannotated actions still replace the whole selected set with the eligible result. Explicit color, score, state and annotation editors retain their stated editing scope. Source counts show directly mapped IDs, so the number changed may be smaller after visibility filtering or larger through family linking.

## Save and Restore Expansion Modes

Use the dropdown beside **Expand annotated**, or these buttons:

| Control | Saved `layout.expandedSubtechniques` |
| --- | --- |
| Collapse all | `none` |
| Expand all | `all` |
| Expand annotated | `annotated` |
| Per-technique · saved | Global field removed; saved/imported per-parent/tactic row settings apply |

These modes work in Flat, Side and Mini. Save the Studio file to preserve the chosen mode on disk. Layer switching, duplication, reopening, Navigator exchange and session recovery restore it. Choosing a mode marks the document unsaved but leaves technique inclusion and annotations untouched.

Annotated mode opens families with an annotated mapped child: comment, user Metadata, Links, stored score including zero, explicit color, disabled state or active source Note. A parent-only comment does not qualify. Opening a family retains its other matching children. Search may temporarily open matching families; clearing search restores saved states. Individual arrows now save `showSubtechniques` per parent/tactic, preserve other families and switch to Per-technique mode. Explicit closed flags also apply in Mini; its legacy open default applies only to missing flags. See [individual expansion and mouse examples](detection_interaction_en.md).

**Example:** Add a child comment, choose Expand annotated, then Save. Reopen: that family opens while an unannotated family stays closed. Change the child annotation later and the annotated policy is recalculated.

SVG **Show children expanded when export opened** captures the actual view. Without a captured view, expanded-only projection uses the saved policy. Default SVG and Excel exports still include all matching children. CSV does not contain matrix display settings.

## Search Source Descriptions

Source sidebars and all eight matrix **TTPs from** kinds default to Name, ID and Description. **Source search fields…** switches them independently of the TTP search-field menu; Campaign supports Description too. See [source search controls](navigator_parity_controls_en.md) and [source batches](source_relationship_selection_en.md).

**Example:** Open Mitigations and enter a phrase from a mitigation's Description even if it is absent from its title. Then choose Mitigation in the matrix source row and enter the same phrase. Completion results show short IDs/names; hover for Description and choose the exact result before Add/Remove. Typed partial text cannot execute a previously selected item. Spaces and literal punctuation work; matching ignores case and outer whitespace. Data stays within the loaded catalog, without fetching another release. TTP-only controls stay hidden in library categories.

## Gradient Presets

Open **Layer settings… → Gradient preset**. Opening the dialog preserves the current gradient and starts on Custom. Choose a preset to fill its stops and score bounds:

| Preset | Range | Stops |
| --- | --- | --- |
| Red / Yellow / Green | 0–100 | `#ff6666`, `#ffe766`, `#8ec843` |
| Green / Yellow / Red | 0–100 | `#8ec843`, `#ffe766`, `#ff6666` |
| White / Blue | 0–100 | `#ffffff`, `#007acc` |
| Blue / White / Red | −100–100 | `#2166ac`, `#ffffff`, `#b2182b` |
| Purple / White / Orange | −100–100 | `#762a83`, `#ffffff`, `#e66101` |
| Transparent / Blue | 0–100 | `#007acc00`, `#007accff` |

**Example:** Give techniques scores −50, 0 and 50; choose Blue/White/Red and Save. They appear on the blue side, white midpoint and red side. For an increasing coverage scale, choose White/Blue; higher scores become bluer. These colors do not define a universal risk meaning: choose/document your own scale.

Manual edits return the selector to Custom; 2–32 RGB/RGBA stops and finite increasing bounds remain supported. Save validates and applies the draft; Cancel discards it. Selecting a preset does not assign scores, manual colors or inclusion. Explicit technique colors override score gradients; Clear color reveals the applicable score color. Alpha stops blend against the matrix background. Studio/Navigator JSON and recovery preserve actual colors/bounds; colored SVG/Excel render them. CSV retains its selected-technique/annotation format.

## Progress and Verification

Operations announce in-memory inputs/no direct output files before staged selection, source/index, expansion and preset progress. Intentional saves, exports and recovery checkpoints announce absolute final/temporary paths before atomic publication. Cancel or invalid settings preserve the original document.

From the project root, after installing dependencies:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -B .\audit_visibility_presets.py
```

The seven-stage audit announces absolute inputs and outputs before creating an isolated STIX fixture. It checks all layouts, visibility and family/tactic/source operations, literal Description completion including actual typing, every preset and Cancel, old-file compatibility, Studio/Navigator/session restoration and SVG/XLSX/CSV output. Examples, screenshots and `audit.json` go to `<project-root>/artifacts/visibility-presets`. Official dataset pointers are checked for preservation.

See [startup and workflow](../README.md), [selection and search](selection_and_search_en.md), [matrix display](matrix_display_en.md) and [files and recovery](studio_files_en.md).
