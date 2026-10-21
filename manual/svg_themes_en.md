# SVG Light and Dark themes

Use **Navigator → Export matrix SVG…**, choose a destination, then open **Settings → Image and header → SVG theme**. Choose **Dark** or **Light**. The initial choice is Dark, preserving the existing export default. The choice belongs to this export dialog; reopening the dialog starts at Dark.

## Preview and export

1. Set the matrix's desired platform, search, color visibility and overlay view before opening the export dialog.
2. Choose **Light** for a white canvas suitable for light reports, or **Dark** for a dark canvas.
3. Press **Preview SVG · no file written**. The Preview tab displays the actual SVG payload.
4. Inspect the header, techniques, disabled entries and legend. Existing size/font/border/legend/sub-technique settings continue to apply.
5. Press **Export SVG**. With the same settings and captured view, preview and file have identical SVG bytes.
6. To produce the other theme, return to Settings, change SVG theme and preview/export again. A changed setting marks the old preview as needing refresh in the status message; press Preview to see the new theme.

Changing SVG theme changes the exported presentation only. It does not edit selected TTPs, annotations, manual colors, scores, gradients, tactic backgrounds, saved files or the application's dark interface. SVG theme is not saved in Studio/Navigator layer JSON. It does not affect single-layer or multi-layer Excel exports. General application Light/Dark remains a separate feature.

## What changes with the theme

| Element | Behavior |
| --- | --- |
| Canvas, header and neutral cells | Use the selected theme's backgrounds and readable text colors. |
| Manual opaque technique colors | Keep their exact RGB color; text switches to contrasting black or white. |
| Transparent score/aggregate gradients | Preserve raw interpolated RGBA, then composite it against the theme's neutral cell background. Fully transparent values appear neutral. |
| Combined layers | Recompose each contributing source against the selected background, then use the existing equal-weight blend. Source order, per-source display switches and zero-opacity exclusion remain unchanged. |
| Disabled techniques | Use a distinct muted background and readable muted text. Hide disabled continues to remove them; Hide colors makes cells neutral while retaining enabled/disabled information in hover context. |
| Tactic backgrounds | Preserve explicitly configured colors and their contrasting labels. Mini's header background follows the SVG theme. |
| Legend | Panel and text follow the theme. Alpha swatches composite against their actual panel, with a visible border in Light. Hidden/docked/undocked settings remain independent. |
| Annotation indicators | Keep configured colors. Light adds a contrasting backing line so pale indicators remain visible. |
| Cell borders | Keep your configured border color. Choose a suitable custom color if desired. |

Transparent colors can look different between Light and Dark because their background changes. This is expected; the underlying gradient stops, scores and authored colors remain identical. The raw layer JSON remains the editable source of those values.

Both themes support Flat, Side and Mini, including black/white cells, original and aggregate scores, annotation markers, selected Mini borders and literal Chinese/English text. Preview uses the same renderer and settings as export. Very small canvas sizes still scale text. [Paper presets and orientation](svg_paper_en.md) are now available; manual font size and automatic text fitting remain separate pending features.

## Example

For a score gradient from `#ff000000` to `#ff0000ff` over 0–100, a score of 50 produces raw `#ff000080`. The exported cell appears `#f97a7a` on the Light neutral background `#f2f4f5`, or `#911213` on the Dark neutral background `#222526`. A fully opaque black cell remains black in both themes and receives white text. A white cell retains black text.

For reports, export the same captured matrix twice, for example `examples/matrix-light.svg` and `examples/matrix-dark.svg`, using an existing destination directory. Switch the theme between exports; no duplicate layer is necessary.

For programmatic use from the project environment:

```python
from matrix_exports import export_matrix

# document is an already loaded TTPDocument; report is the progress callback.
export_matrix(document, output_path, 'svg', report,
              svg_options={'theme': 'light'})
```

`theme` accepts exactly `light` or `dark`; omitted theme defaults to Dark. Invalid types/values fail validation before publication. Existing options can be combined with theme. [Advanced settings and Excel](aggregation_and_exports_en.md) describes the remaining controls.

## Processing and verification

Preview announces in-memory inputs/no output files, then **SVG Preview 1/3 validate → 2/3 render selected theme → 3/3 ready**. Export announces absolute destination/temporary paths before **Matrix Export 1/4 projection → 2/4 render selected theme → 3/4 write → 4/4 atomic publication**. Validation errors, cancellation and failed publication preserve an existing output file and clean up temporary files.

Program flow: `export_dialogs.py` captures the canonical theme value → `layer_analysis_dialogs.py` freezes options and coordinates background preview/export → `matrix_exports.py` renders Flat/Side/Mini → `svg_export.py` applies theme to the advanced canvas/header/legend → `svg_themes.py` projects SVG-only palette and alpha composition. `navigator_visuals.py` supplies raw RGBA in read-only appearance data. It retains the native matrix's existing appearance. Each module documents its workflow in the root README.

From the project root:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_svg_themes.py'
```

The seven-stage offline audit reports absolute inputs/outputs, then prepares fixtures → checks three layouts/two themes with actual rendered pixels and text contrast → checks headers/legends/hidden colors/aggregates → checks overlay composition → tests native bilingual settings/preview/identical file bytes → tests validation/failure/cancel/real Enterprise-Mobile-ICS → publishes `artifacts/svg-themes/audit.json`. SVG/PNG examples include `flat-light`, `flat-dark`, `side-light`, `side-dark`, `mini-light` and `mini-dark`. Native screenshots include `settings-en.png`, `settings-zh.png` and Light/Dark previews. Registered in `scripts/audit_linux.py`; that registration does not itself claim a native Linux pass.

Verification (2026-10-21): 146 dedicated checks and 635 regression checks passed (781 total). Static checks passed for 110 Python files, 601 local Markdown links and 810 unique translation keys/placeholders.

[Guide index](README.md) · [繁體中文](svg_themes+_zh.md).
