# Detection Strategy Search, Saved Family Expansion and Source JSON

## Find Techniques by Detection Strategy

Open **TTP search fields…** in the sidebar or **Search fields…** in the matrix. Enable **Detection Strategy · Name / ID / Description**. It starts Off; Name/ID remain the defaults. To search only strategy content, enable this field and turn the other fields off. At least one field stays enabled.

**Example:** Open a recent ATT&CK release, enable only Detection Strategy and enter an actual strategy ID such as `DET0001`, or a phrase from its title/description. Results are the techniques directly detected by matching active strategies in that snapshot. IDs and availability vary by domain/version. Search accepts spaces and literal punctuation, ignores case and trims outer whitespace only for comparison. A release with no strategy objects has no matches; a newer dataset is never borrowed.

The index uses active direct `detects` relationships from `x-mitre-detection-strategy`. Revoked/deprecated strategies and relationships are excluded. It searches the strategy's own name, ID and Description, rather than just analytic log-source names. Existing Data Sources search remains separate. The sidebar, Flat/Side/Mini, Select… → Search matches, and filtered SVG/Excel projections share the field preference. Save/reopen, duplication, Navigator extensions and session recovery retain it. Detections library search also includes Description; the TTP field controls stay hidden in library categories.

## Save Individual Parent Expansion

Click a parent's arrow to open or close its children in one tactic. This now saves its `showSubtechniques` state and marks the file unsaved. It does not select techniques or modify their annotation/state fields.

**Example:** Choose Expand all, then close one parent under Execution. The expansion dropdown changes to **Per-technique · saved**. That parent stays closed under Execution while its other tactic occurrences and other families keep their states. Switch Flat → Side → Mini, search and clear, Save and reopen: the individual open/closed states return.

When leaving a global all/none/annotated policy, the program first records its per-parent/tactic states, including families outside the current platform filter, then edits only the clicked family. This avoids closing unrelated families when changing modes. A required scoped row copies inherited global annotations before adding the expansion flag, preserving comments, score, color, links, Metadata and enabled state. Expansion-only structural parents remain grouping-only.

Search can temporarily open a matching family; this automatic expansion is not saved or marked dirty. Clearing search restores stored states. Manual arrow changes during a search are intentional saved edits, while other temporary search expansions are not captured. Mini honors explicit closed flags; its legacy open default applies where no per-row flag exists. Global Expand all/Collapse all/Expand annotated still replace the active policy. The Per-technique choice returns to stored row settings.

Flags survive layer switching, duplication, Studio/Navigator exchange and recovery. SVG expanded-only export uses the captured view, or saved per-family states if no view snapshot is supplied. Default SVG and Excel exports still include all matching children.

## Ctrl / Cmd / Shift Mouse Selection

| Matrix action | Result |
| --- | --- |
| Left-click a label/cell | Replace inclusion with the clicked technique and any linked occurrences |
| Ctrl / Cmd / Shift + left-click | Toggle the clicked technique and linked occurrences in the current selection |
| Flat checkbox without modifiers | Keep the existing additive checkbox behavior |
| Parent branch arrow | Edit expansion only |
| Double-click | Open details |

Shift toggles membership; it does not select an alphabetical range. The clicked occurrence decides whether the linked group is added or removed, so removing an already-selected parent cannot accidentally add unselected children. Cross-tactic, family and visible-only preferences still apply. With visible-only enabled, collapsed/filtered relatives cannot be added through linking. Colors, scores, comments and enabled states stay unchanged. The TTP sidebar and keyboard checkbox workflow retain their existing behavior.

**Example:** Click technique A, Ctrl-click B to keep both, then Shift-click B to remove B. Ordinary-click C to replace the current selection with C. With cross-tactic selection Off, only the clicked tactic occurrence is targeted.

## Hover and Copy Source STIX / TAXII JSON

Open a technique, sub-technique, actual tactic or library object detail page. Two buttons appear above the description:

- **Copy STIX JSON** copies the complete original source object.
- **Copy TAXII envelope** copies a locally generated TAXII 2.1 wrapper containing that one object.

Hover over either button for about 300 ms. A small read-only window shows the corresponding JSON, with the object's STIX ID, domain and release. Move into the window to scroll through long objects. Click **Copy complete JSON** there or the original button, then paste into a text editor or another tool. Leaving the buttons and popup dismisses the window after a short delay. Switching objects/pages resets the preview and cached JSON so the previous object cannot be copied accidentally. The popup is constrained to the available screen and does not activate an editing window.

**Example:** Browse a technique, hover Copy STIX JSON and inspect `external_references`, `kill_chain_phases` and custom `x_mitre_*` fields. Click, open a text editor and paste. The content contains source data, including fields omitted from the formatted detail page; Studio comments/colors and current TTP selections are not injected into it.

For TAXII mode the shape is:

```json
{
  "objects": [
    { "type": "attack-pattern", "id": "attack-pattern--...", "name": "..." }
  ],
  "more": false
}
```

This example abbreviates the object; the clipboard includes it in full. The wrapper follows the [TAXII 2.1 envelope](https://docs.oasis-open.org/cti/taxii/v2.1/os/taxii-v2.1-os.html). It is built from the loaded local snapshot, not downloaded from a TAXII server. It includes one object version and no separate relationship, marking or other dependency objects; it is not a complete dependency Bundle. Other services may require authentication, permissions, dependencies or a different import format. No network upload or TAXII synchronization takes place.

Copy uses the browsed object's domain/version, including cross-domain links. Platform/index/library-heading pages and synthetic historical tactics have no original STIX object and hide the buttons. Unicode, nested fields, references and custom properties remain intact. JSON preview/copy never changes source Bundles or the selected document.

## Progress and Verification

Operations report in-memory inputs and no direct output files before search, gesture, expansion, preview and clipboard stages. Expansion edits validate a complete draft before replacing the layer. Clipboard serialization failures preserve the previous clipboard text. File Save/Export/Session operations announce absolute final/temporary paths before their existing atomic publication stages.

Run from the project root after installing dependencies:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -B .\audit_detection_interaction.py
```

Seven stages check real official/isolated detection mappings, actual native mouse clicks in all layouts, individual expansion/inherited annotations, scrollable hover/clipboard/paste behavior, and Studio/Navigator/session/SVG/CSV round trips. Absolute inputs/outputs are announced first. Fixtures, example files, screenshots and `audit.json` go to `<project-root>/artifacts/detection-interaction`; official snapshot pointers are checked for preservation. See [startup and program flow](../README.md), [selection/search](selection_and_search_en.md), [matrix display](matrix_display_en.md) and [saving/recovery](studio_files_en.md).
