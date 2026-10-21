# Matrix Preview on Source Result Hover

[繁體中文](source_hover_preview+_zh.md) · [Source batches](source_relationship_selection_en.md) · [Feature tracker](../NOTIMPLEMENTYET.md)

## Matrix Dropdown and Completion Results

1. Open ATT&CK Matrix and choose a **TTPs from** source kind.
2. Open the dropdown, or type a phrase to show completion results.
3. Move the mouse over a result. Cyan outlines temporarily identify its mapped techniques.
4. Leave the result area or press Escape to restore the original display. Use the existing Add techniques / Add all results buttons to actually include TTPs.

Campaign, Software, Group, Mitigation, Asset, Detection Strategy, Data Component and Data Source are supported. STIX IDs identify results even when names match. A source without mappings clears the previous preview rather than retaining another source's highlight.

**Example:** search for two groups sharing a phrase and move between their results. Only the currently hovered source is previewed, even during rapid movement. Leaving the list removes all temporary outlines.

## Preview from the Source Sidebar

Search Groups / Software / Campaigns / Mitigations / Assets / Detections, then click **Show matrix preview**. The category/query stay on the left and the current document's matrix appears on the right. Once the matrix is ready, hover sidebar results to preview them.

Hover never switches pages automatically. If the right side shows details, use that button first. Category headings, Analytics, unsupported rows and other-domain entries do not preview the active file. Clicking a result retains its normal details-page behavior, separately from hover.

## Outlines and Scope

| Indicator | Meaning |
| --- | --- |
| Solid cyan outline | The exact technique/tactic occurrence belongs to the source mapping |
| Dashed parent outline | Related children in this tactic are currently collapsed |
| No outline | No mapping, or the occurrence is outside the visible projection |

Flat, Side and Mini share this behavior. A dashed parent is only a hint: it is neither included as a source technique nor checked or expanded. Existing controls own expansion; hovering preserves it.

Mappings use the exact dataset/domain/version, cover each technique's valid mapped tactics, and are restricted to the current platform projection. Search and Hide disabled retain their visibility rules. Hidden disabled children do not produce misleading parent hints; a hint requires an otherwise displayable child that is collapsed.

**Family, across-tactic and visible-only selection preferences do not alter preview mappings.** Preview describes source relationships; Add/Remove applies selection preferences. Sources do not specify a single tactic, so one technique can be outlined in several valid tactic columns.

**Example:** a source maps only to a sub-technique. With Collapse all, its parent gets a dashed outline only in the child's mapped tactic. The same parent in another tactic stays ordinary. Hover neither expands the family nor includes the parent.

## Layers and Restoration

The preview is an independent drawing effect over the existing fill; annotation indicators remain visible. With **Show all layers**, blended backgrounds, source colors, scores, comments, Links/Metadata, enabled states and inclusion stay unchanged. Preview outlines also work when Show layer colors is off.

The preview clears on leaving the result area, hiding dropdown/completion lists, Escape or keyboard browsing, wheel scrolling, query/kind/category changes, matrix filters/rebuilds, file/domain/version/dataset changes, matrix hiding and application close. Each result view owns its preview: a delayed leave from another popup cannot clear the newly hovered result.

These actions do not change dirty tracking, create layers or run inclusion commands. Preview state is absent from Studio, Navigator, CSV, SVG, Excel and recovery data. Screenshots can naturally capture the temporary outlines.

## Processing Flow and Verification

Each preview announces no input/output files, then reports two stages: resolve the in-memory source mapping and repaint transient outlines. Leaving clears only preview state, repaints original cells and reports restoration. No download or file write occurs. The sidebar matrix entry also announces no files and reports opening/completion, using existing matrix-build progress when columns need creation.

From the project root:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_source_preview.py'
```

The audit announces resolved absolute paths for `<project-root>/data/attack`, its own script and `<project-root>/artifacts/source-preview`. Seven stages cover native-teardown subprocess exit, actual mouse movement, exact before/after pixels in every layout, parent hints, completion/sidebar results, rapid movement, scrolling/closing, empty results, other domains, file switching, overlays, export isolation and pointer preservation.

Outputs include `audit.json`, an isolated fixture, Studio example, SVG exported during hover and before/after screenshots. No downloads occur and official pointers remain unchanged. `--lifecycle-only` checks native Qt destruction without file IO. The watcher checks the event type before accessing a viewport, avoiding access while a view is partly destroyed.
