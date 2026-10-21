# Family Score Aggregation and Matrix Exports

This guide applies to Fusion Studio layers on ATT&CK v4+. See the [project README](../README.md) for setup and the [formula guide](layer_score_formulas_en.md) for creating computed layers.

## Configure Parent/Sub-technique Aggregation

1. Open a document/matrix and assign Score values to parents or sub-techniques.
2. Choose **Navigator → Layer settings…**.
3. Enable **Show parent/sub-technique aggregate scores**.
4. Select **Average / Maximum / Minimum / Sum** and optionally **Count enabled unscored family members as zero**.
5. Save. Parent tooltips show the original **Score** and derived **Aggregate score** separately. The parent gradient uses the aggregate unless an explicit parent color overrides it.

For a parent scored 20 and two children scored 40 and 0 in the same tactic, with other children unscored and zero counting disabled:

| Function | Calculation | Result |
| --- | --- | ---: |
| Average | `(20+40+0)/3` | 20 |
| Maximum | `max(20,40,0)` | 40 |
| Minimum | `min(20,40,0)` | 0 |
| Sum | `20+40+0` | 60 |

Actual zero participates in calculations. Missing scores are omitted by default; enabling zero counting includes enabled unscored members as zero in every function, including minimum. A wholly unscored family remains unknown. Explicitly disabled members are excluded. Tactic scopes are calculated separately using the catalog's complete mapped family; platform/search filters affect visibility, not aggregation.

Original scores and selections are preserved. Standard layer `layout` fields store the settings within existing document/domain/version archives. Sums can exceed the existing gradient range; increase **Maximum score** when needed to distinguish values that would otherwise share the clamped endpoint color.

## Export SVG or Colored Excel

1. Set matrix platform/search/color visibility. Enable **Show all layers** when a combined view is wanted.
2. Choose **Navigator → Export matrix SVG…** or **Export matrix Excel…**.
3. Choose an existing destination directory, or create `examples` before selecting `examples/matrix.svg` or `examples/matrix.xlsx`.
4. For SVG, adjust **Settings** and optionally use **Preview SVG · no file written**; for Excel, keep the single-layer export dialog. Click **Export SVG / Export XLSX** and wait for background completion.

The application reports absolute final/temporary paths before **1/4 projection, 2/4 rendering, 3/4 writing, 4/4 publication**. Failed validation/writes or cancellation before publication preserve existing output and remove temporary files.

Inputs are in-memory layer/catalog snapshots; output is SVG or XLSX. Default exports expand all matching sub-techniques, including content outside the visible viewport. SVG can instead use expanded-only or no children. Platform/search, hidden disabled entries, color visibility and matching domain/version/dataset overlays are honored. Turning color visibility off also produces neutral exported cells.

**SVG** is a scalable vector matrix with IDs/names, original/aggregate scores, gradient/legend swatches and annotation hover context. Child techniques use an ASCII `>` marker and indentation.

**Single-layer Excel** contains three worksheets:

| Sheet | Contents |
| --- | --- |
| Matrix | Colored tactic columns, scores, cell comments and frozen headers |
| Techniques | Technique/parent IDs, selected/enabled state, original/aggregate scores, colors and notes; filterable |
| Layer Info | Domain/version, platform/search, formula provenance and legend |

Names/comments remain literal text even when starting with `=`. Excel's 32,767-character cell limit is enforced with a visible export failure rather than silent truncation. Use JSON for full oversized annotation text.

SVG/XLSX are presentation/analysis artifacts. They do not rename documents or mark complete project state saved. Export Studio JSON for original annotations and domain/version archives, or Navigator Layer JSON for exchanging the current layer.

## Advanced SVG Settings and Preview

In **Navigator → Export matrix SVG…**, choose the destination and open **Settings**. Options are local to this export dialog and do not change saved layer data.

| Setting | Operation |
| --- | --- |
| SVG theme | Dark (initial default) or Light for this export; changes presentation only; preview again after switching |
| Paper size | Custom, Letter, Legal, 11×17, 18×24 or 24×36 inches; presets lock width/height |
| Orientation | Portrait/Landscape for presets; swaps explicit Custom axes when both are set |
| Units | px, cm or in; changing units preserves physical size, using 96 logical pixels per inch |
| Image width / height | 0 = automatic; explicit values fit the whole matrix into the canvas without cropping |
| Header height | 0 = automatic; explicit heights fit header content into the requested area |
| Font | sans-serif, serif or monospace for header, legend and matrix |
| Header sections | Show/hide the whole header, layer name/description, domain/version, or platform/search text independently |
| Cell border | Enter a six-digit hexadecimal color, such as `#808080` |
| Sub-techniques | All matching children, children expanded when the dialog opened, or none |
| Legend | Show/hide; dock in the header or undock and specify X/Y/width/height in the chosen units; height 0 = automatic |

Expanded-only captures each parent/tactic independently, including Flat/Side/Mini view state. If the native matrix is still building, the dialog waits before enabling preview/export. The snapshot stays fixed even if background matrix work finishes later. Hidden/filtered data still follow the captured export filters.

An undocked legend can intentionally overlap the matrix and stays visible when the header is hidden. It must fit inside the image; otherwise validation asks you to change its position/size or canvas. Docked legends follow the header and disappear with it. Legend labels wrap; explicit legend heights scale the contents to fit. Smaller image/header/legend sizes produce smaller text rather than dropping rows. Numeric sizes are limited to 100000 logical pixels; image width must be at least 80 pixels and the matrix needs at least 40 pixels below the header.

Example: choose **cm**, width `20`, height `25`, header height `2`, **serif**, border `#808080`, and **Show children expanded when export opened**. Preview first. For a large matrix, increase width or narrow platform/search filters for readable text. Qt's preview fits the vector to its panel; the exported root retains the physical units and dimensions.

**Preview SVG · no file written** announces in-memory inputs/outputs, then shows **1/3 validate → 2/3 render → 3/3 ready**. The **Preview** tab displays the vector. Correct any invalid value and retry. Export then announces absolute final/temporary file paths and uses the four publication stages above. Settings freeze during work; cancellation or failure preserves existing output. Editing settings after export enables another export to the chosen destination.

Light/Dark is independent of the application theme. Opaque manual/tactic colors remain exact; transparent score/aggregate and overlay colors are recomposed against the chosen neutral background. Legend text/panels and disabled cells follow the theme; Light adds readable indicator backing and swatch borders. Advanced Mini export preserves selected outlines. SVG theme is not stored in layer JSON and does not affect Excel. Reopening the export dialog defaults to Dark. See [SVG theme examples and verification](svg_themes_en.md).

[Paper sizes and orientation](svg_paper_en.md) explains all five presets, physical unit conversions, Custom draft restoration and limits. Changing paper/direction retains header and legend sizes; an out-of-page detached legend needs an explicit adjustment.

## Export Every Open Layer into One Excel Workbook

1. Open the desired documents and set each layer's saved platform filters, colors, scores and enabled states.
2. Choose **Navigator → Export all open layers to Excel…** and select, for example, `examples/all-layers.xlsx` in an existing directory.
3. Review the complete layer list and domain/version column, then click **Export all layers XLSX**.
4. Wait for **1/4 validate → 2/4 project/render each layer → 3/4 write workbook → 4/4 atomic publication**. Absolute output and temporary paths appear before processing; inputs are immutable in-memory snapshots.

The result has **exactly one worksheet per open document**, in tab order (up to 50). Mixed Enterprise/Mobile/ICS, compatible versions and custom datasets remain independent. Every sheet uses its own saved platform filters, sorting, hidden-disabled setting and colors, with all matching children. The active transient search, hidden-colors toggle and combined-overlay toggle are not applied. An empty selection still exports its layer matrix; an explicit empty platform filter produces a labeled empty sheet.

Row 1 keeps the full layer name; row 2 identifies domain/version/platform; row 3 holds tactic headers. Colored matrix cells include IDs/names and scores; Excel comments retain selection/enabled state, annotations, Links and Metadata. Description, layer metadata/links/formula JSON and legend entries appear below the matrix. Headers are frozen at A4. This mode has no additional Techniques or Layer Info worksheets; single-layer Excel keeps those sheets.

Excel-invalid characters are replaced, long names are truncated to 31 UTF-16 units, and duplicates receive case-insensitive suffixes such as `Assessment (2)`; reserved `History` is renamed. Full names remain in row 1, and text beginning with `=` remains literal. Invalid controls or text/comments over 32,767 characters, unsupported pre-v4 historical layers or an invalid later layer abort the whole workbook visibly. Cancellation/write failure retains the previous file and removes temporary output. Source documents, selections and save markers remain unchanged; use Studio JSON for complete editable state.

## Examples and Verification

- [SVG example](../artifacts/layer-analysis-example.svg)
- [Colored Excel example](../artifacts/layer-analysis-example.xlsx)
- [SVG preview](../artifacts/layer-analysis-svg-preview.png)
- [Advanced SVG example](../artifacts/export-options/advanced.svg)
- [All-layer Excel example](../artifacts/export-options/all-layers.xlsx)
- [繁體中文手冊](aggregation_and_exports+_zh.md)

The root-level `audit_layer_analysis.py` checks existing arithmetic, SVG pixels and single-layer Excel. `audit_export_options.py` checks advanced options/units, actual vector pixels, all/expanded/no children, sheet names/domain separation, empty filters, atomic failure/cancellation and native preview/export actions. It prints absolute input/output paths before seven stages and writes examples/screenshots plus `artifacts/export-options/audit.json`. Run `.venv\Scripts\python.exe -B audit_export_options.py` with `QT_QPA_PLATFORM=offscreen`; setup is documented in the project README.
