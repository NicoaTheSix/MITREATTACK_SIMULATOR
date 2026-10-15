# Family Score Aggregation and Matrix Exports

This guide applies to TTP Selection Studio layers on ATT&CK v4+. See the [project README](../README.md) for setup and the [formula guide](layer_score_formulas_en.md) for creating computed layers.

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
4. Click **Export SVG / Export XLSX** in the export dialog and wait for background completion.

The application reports absolute final/temporary paths before **1/4 projection, 2/4 rendering, 3/4 writing, 4/4 publication**. Failed validation/writes or cancellation before publication preserve existing output and remove temporary files.

Inputs are in-memory layer/catalog snapshots; output is SVG or XLSX. Exports expand all matching sub-techniques, including content outside the visible viewport. Platform/search, hidden disabled entries, color visibility and matching domain/version overlays are honored. Turning color visibility off also produces neutral exported cells.

**SVG** is a scalable vector matrix with IDs/names, original/aggregate scores, gradient/legend swatches and annotation hover context. Child techniques use an ASCII `>` marker and indentation.

**Excel** contains three worksheets:

| Sheet | Contents |
| --- | --- |
| Matrix | Colored tactic columns, scores, cell comments and frozen headers |
| Techniques | Technique/parent IDs, selected/enabled state, original/aggregate scores, colors and notes; filterable |
| Layer Info | Domain/version, platform/search, formula provenance and legend |

Names/comments remain literal text even when starting with `=`. Excel's 32,767-character cell limit is enforced with a visible export failure rather than silent truncation. Use JSON for full oversized annotation text.

SVG/XLSX are presentation/analysis artifacts. They do not rename documents or mark complete project state saved. Export Studio JSON for original annotations and domain/version archives, or Navigator Layer JSON for exchanging the current layer.

## Examples and Verification

- [SVG example](../artifacts/layer-analysis-example.svg)
- [Colored Excel example](../artifacts/layer-analysis-example.xlsx)
- [SVG preview](../artifacts/layer-analysis-svg-preview.png)
- [繁體中文手冊](aggregation_and_exports+_zh.md)

The root-level `audit_layer_analysis.py` checks arithmetic, native controls, SVG pixels, Excel colors/values, atomic failure/cancellation and source preservation. Its run command is documented in the project README.
