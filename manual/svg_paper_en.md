# SVG paper sizes and orientation

Open **Navigator → Export matrix SVG…**, choose a destination, then **Settings → Image and header**. Set **Paper size**, **Orientation** and **Units**. The initial choice remains **Custom** with automatic width/height; existing exports keep their previous default behavior.

## Choose a paper preset

| Paper size | Portrait dimensions (inches) | Portrait logical pixels |
| --- | --- | --- |
| US Letter | 8.5 × 11 | 816 × 1056 |
| US Legal | 8.5 × 14 | 816 × 1344 |
| Small | 11 × 17 | 1056 × 1632 |
| Medium | 18 × 24 | 1728 × 2304 |
| Large | 24 × 36 | 2304 × 3456 |

**Portrait** places the shorter side horizontally; **Landscape** swaps the axes. A preset fixes the canvas dimensions and locks the width/height inputs. Switching paper or orientation updates the displayed dimensions in the current unit. Header height, font, theme, legend, border and child-display settings are retained.

The preset sets the SVG canvas. The existing renderer fits the complete matrix into the available area below the header. Flat, Side and Mini, Light/Dark, all/expanded/no children and captured matrix filters remain supported.

## Units and physical size

Choose **px**, **cm** or **in**. Conversions use 96 logical pixels per inch and 2.54 cm per inch. Letter Portrait therefore displays `816 × 1056 px`, `21.59 × 27.94 cm` or `8.5 × 11 in`; Landscape displays the same physical sheet with the axes exchanged.

The dialog retains canonical physical sizes, so repeated unit changes do not accumulate display-rounding drift. Header height and legend X/Y/width/height also retain their physical sizes. Input limits follow the selected unit while enforcing the existing maximum of 100000 logical pixels per length. The controls display six decimal places; export uses the retained physical value, including at the maximum.

The Preview tab fits the vector to its panel. The SVG root's physical width/height and its 96-DPI viewBox determine the actual output dimensions.

## Return to Custom

Choosing **Custom** restores the most recently edited custom width/height and direction, even after changing units or visiting several presets. Preset values do not overwrite this draft. In Custom, width and height become editable again.

- `0` on either axis keeps its existing **Auto** behavior.
- When both dimensions are positive, Orientation becomes available and reflects the explicit dimensions. Switching it swaps width/height once.
- When either axis is Auto, Orientation is disabled; the renderer resolves that axis from the matrix.
- Editing a custom dimension updates the direction display without silently rotating your input.
- Returning to Custom Auto after a preset visit restores the original automatic settings.

For an A4-sized canvas, choose Custom, select cm and enter width `21`, height `29.7`; select Landscape to swap to `29.7 × 21`. This uses the normal custom-size path.

## Preserve header and legend settings

Paper/direction changes preserve their current physical dimensions and placement. A detached legend is not automatically moved or shrunk to fit another paper. If it falls outside the new canvas, preview/export reports the existing validation error; adjust its placement/size or choose a larger page. Likewise, an explicit header height must leave at least 40 logical pixels for the matrix. A failed preview keeps the controls editable and does not write output.

## Example: Letter Landscape report

1. Open SVG export and choose **US Letter**.
2. Choose **Landscape**, then **in**. Width/height show `11` and `8.5` and are locked.
3. Set header height to `1.25` in, choose the desired SVG theme and keep the legend docked.
4. Press **Preview SVG · no file written** and inspect the complete matrix.
5. Press **Export SVG**. The file root has `width="11in"`, `height="8.5in"` and `viewBox="0 0 1056 816"`.
6. To use a custom canvas instead, choose Custom and revise its restored dimensions. Preview again after changing settings.

The same captured view/settings produce byte-identical preview and export payloads. Cancelling the dialog writes no file. Paper and orientation belong to this export dialog; they do not change saved layer JSON, document selections/annotations, save markers or Excel output. Reopening the dialog starts with Custom Auto.

## Programmatic use

```python
from matrix_exports import export_matrix

# document is already loaded; report receives stage progress.
export_matrix(document, output_path, 'svg', report,
              svg_options={'size': 'letter', 'orientation': 'landscape'})
```

Valid size IDs are `custom`, `letter`, `legal`, `small`, `medium`, `large`; direction IDs are `portrait` and `landscape`. Omitted size defaults to Custom. Presets resolve dimensions in the selected unit. Valid explicit width/height values are overridden by the preset; invalid numeric values are still rejected. Custom width/height remain authoritative: the backend derives direction from positive dimensions, and does not rotate legacy API inputs. To rotate a programmatic Custom canvas, exchange its width/height.

All lengths use the selected unit. When specifying `unit='in'` or `'cm'` programmatically, also supply other lengths you want in that unit, such as `legend_width`. The GUI converts those existing values automatically when Units changes.

## Processing and verification

Before Preview, the application announces in-memory input/no output file, then **SVG Preview 1/3 validate → 2/3 render → 3/3 ready**. Export announces absolute destination and temporary paths before **Matrix Export 1/4 project → 2/4 render → 3/4 write → 4/4 atomic publication**. Invalid pages, out-of-bounds content, cancellation and failed publication preserve previous output and remove temporary files.

`svg_sizing.py` defines physical presets, conversion and direction rules → `export_dialogs.py` maintains canonical physical lengths and an independent Custom draft → `svg_export.py` validates and resolves preset dimensions for the renderer → `layer_analysis_dialogs.py` runs the shared preview/export path → `matrix_exports.py` writes the SVG atomically. `svg_export.UNITS` remains available for existing callers. Each module documents its flow in the root README.

From the project root:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_svg_paper.py'
```

The offline audit lists absolute input/output paths, then prepares fixtures → checks every preset/direction/unit through real SVG XML/Qt rendering → checks Custom/Auto/header/legend/layout/theme → exercises native controls/unit round trips/Custom restoration/limits → tests bilingual preview/export equality/cancel → tests publication errors and source preservation → publishes `artifacts/svg-paper/audit.json`. The directory also holds 30 preset SVG examples, `settings-en.png`, `settings-zh.png`, `preview.png` and `native.svg`. Registered in `scripts/audit_linux.py`; registration does not itself claim native Linux verification.

Verification (2026-10-21): 266 dedicated checks and 394 regression checks passed (660 total). Static checks passed for 112 Python sources, 627 local Markdown links and 825 unique translation keys/placeholders.

[SVG themes](svg_themes_en.md) · [Advanced exports](aggregation_and_exports_en.md) · [Guide index](README.md) · [繁體中文](svg_paper+_zh.md).
