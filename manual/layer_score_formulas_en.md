# Layer Score Formulas: Manual and Examples

This guide explains score definitions and native formula layers in TTP Selection Studio, with optional exchange through the official ATT&CK Navigator.

## Current Support

Use **Navigator → Create layer from score formula…** in the desktop application. Native arithmetic supports numbers, variables `a`–`z`, unary signs, `+`, `-`, `*`, `/`, and parentheses, with up to 26 matching domain/version sources on ATT&CK v4+. Comparison/boolean/function expressions are not implemented; the [official Navigator](https://mitre-attack.github.io/attack-navigator/) provides a broader expression interface.

## Meaning of Formulas and Scores

A formula calculates a new score from the source scores for the same technique. If `a` and `b` contain scores of 80 and 60, `(a+b)/2` produces 70. Define the meaning of each score before calculating. All data below are hypothetical.

## Example: Detection Gaps

- **a: Threat technique list.** Use `1` for techniques included in this threat analysis and `0` for the others.
- **b: Detection capability.** Use `1` for verified detection capability and `0` for a confirmed absence of detection capability.

```text
a * (1 - b)
```

| Technique | a: Threat technique | b: Detectable | Result | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Technique A | 1 | 0 | 1 | Detection gap in this analysis |
| Technique B | 1 | 1 | 0 | Detection capability exists |
| Technique C | 0 | 0 | 0 | Outside this threat analysis |

Color result `1` red to help prioritize detection improvements. This is a gap indicator under the chosen scoring rules, not an attack probability. Untested techniques remain unknown; decide whether to exclude them or handle them separately before calculating.

## Operating Steps

### 1. Prepare Source Layers in the Desktop Application

1. Start the application using the [project README](../README.md).
2. Create two files with **Navigator → New layer** and rename them “Threat Techniques” and “Detection Capability.” Use the same ATT&CK domain and version.
3. In the threat layer, the matrix's **Add from → Group / Software / Campaign** controls can add related techniques. Selection and color do not automatically assign scores.
4. Use **Score selected…** or the individual TTP annotation editor to enter the example's `0`/`1` scores. Record evidence, verification methods, and dates in Comment.
5. Explicitly assign both source scores for each technique participating in the calculation. Keep unknown values distinct from `0` until their handling is defined.

### 2. Create a Native Formula Layer

1. Open **Navigator → Create layer from score formula…** and verify the source names mapped to `a` and `b`.
2. Enter a result name and `a * (1 - b)`. Sources must share a domain and ATT&CK version.
3. The default **Missing scores** policy preserves unknowns: missing/disabled referenced scores leave that result unscored. Select the zero policy only when this interpretation is intentional.
4. Click **Create result layer**. Background progress shows 1/4 validation, 2/4 snapshot reading, 3/4 calculation and 4/4 completion, then opens a separate result tab.
5. Check the three example cases and configure a 0–1 gradient with result `1` colored red through **Layer settings…**.

Calculations use original Score values for every mapped technique/tactic in the selected union of referenced sources. Unused variables do not introduce missing inputs. Constant formulas such as `50` use all listed sources' selected union. Results record the expression and source names/UUIDs without modifying sources. Displayed parent aggregates are separate from formula inputs.

### 3. Export and Exchange with the Official Tool

1. Export a Navigator Layer JSON through the existing file export controls, or use **Navigator → Export all open layers…** for sources/results. Choose an existing folder, or create `examples` before saving `examples/layers.navigator.json`.
2. The application reports absolute final/temporary paths before validation, writing and publication.
3. **Navigator → Open ATT&CK Navigator website** opens the official tool for loading the exported JSON. For broader expressions, use its **Create Layer from Other Layers** and **Score Expression** controls.
4. Import external result layers through **File → Import Navigator Layer**.

Formula inputs are in-memory snapshots and their output is a new layer; disk files are written only by a separate export. Source manual colors are not inherited into native results, so they cannot override the computed gradient. Division by zero, unknown variables, nonfinite results and unsupported syntax fail without creating partial layers. For SVG/XLSX, see [Aggregation and Matrix Exports](aggregation_and_exports_en.md).

## Other Analysis Examples

| Purpose | Score definition | Formula | Interpretation |
| --- | --- | --- | --- |
| Before/after comparison | a = after, b = before; same 0–100 scoring rules | `a-b` | Positive values indicate improvement |
| Combine two assessments | Same metric and scale in a and b | `(a+b)/2` | Mean assessment score |
| Count shared threat techniques | Each of a, b, c uses 0/1 list membership | `a+b+c` | Number of lists containing a technique |
| Identify common techniques | Both a and b use 0/1 membership | `a*b` | 1 means membership in both lists |

## Verification Checklist

- Match source domains/ATT&CK versions and verify variable assignments.
- Document score definitions, scales, evidence, and unknown-value handling. Unscored and `0` are different.
- Calculations are per technique; separate tactic annotations can yield different results.
- **Show all layers** blends displayed colors. Formula calculations generate a new layer containing computed scores.
- Verify a small known dataset before processing a full list.

## References

- [Official layer formula documentation](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#creating-layers-from-other-layers)
- [Official score documentation](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#scoring-techniques)
- [Official Navigator repository](https://github.com/mitre-attack/attack-navigator)
- [繁體中文手冊](layer_score_formulas+_zh.md)
