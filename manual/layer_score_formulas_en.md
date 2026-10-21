# Layer Score Formulas: Manual and Examples

This guide explains score definitions and native formula layers in Fusion Studio, with optional exchange through the official ATT&CK Navigator.

## Current Support

Use **Navigator → Create layer from score formula…**. Up to 26 source snapshots map to variables `a`–`z` and must share the domain, version and exact dataset. Official ATT&CK v4+ and compatible custom data are supported. The dialog provides **Formula and scope** and **Inherit properties** tabs. Opening it and calculating do not write files.

| Expression | Example | Meaning |
| --- | --- | --- |
| Arithmetic and power | `(a+b)/2`, `a%2`, `a^2` | Average, remainder, exponent |
| Comparison | `a>b`, `a>=75`, `a==b`, `a!=b` | Numeric 1 if true, otherwise 0 |
| Boolean | `(a>b) and (a>=75)`, `a or b`, `a xor b`, `not a` | Nonzero is true; results are 1/0 |
| Conditional | `a>b ? 25 : 10` | Choose a score based on the condition |
| Functions | `max(a,b)`, `sqrt(abs(a-b))`, `round(a/3,2)` | Compute using the allowlisted functions |

Powers use `^`, associate right-to-left, and precede unary signs: `2^3^2` is 512, `-2^2` is -4. `and`/`or` and conditional branches short-circuit arithmetic evaluation. Choose **Formula syntax** before creating the result. The dialog defaults to **Navigator scalar**; select **Studio scalar** when reproducing earlier Studio arithmetic. Existing saved layers keep their stored results.

### Scalar syntax and functions (NAV-018)

Both scalar syntaxes provide constants `pi`, `e`, `tau`, `phi`, `true`, `false`. In Studio calculation mode, a listed source layer `e` takes precedence over Euler's constant; use `exp(1)` for the constant. Navigator calculation mode first tries an empty-scope constant, as explained below.

| Function family | Available functions and arguments |
| --- | --- |
| Existing arithmetic | `abs(x)`, `min(...)`, `max(...)`, `sqrt(x)`, `pow(x,y)`, `log(x[,base])`, `exp(x)` |
| Rounding | `round(x[,digits])`, `floor(x)`, `ceil(x)`; Navigator also accepts digits for floor/ceil |
| Trigonometry, radians | `sin(x)`, `cos(x)`, `tan(x)`, `asin(x)`, `acos(x)`, `atan(x)`, `atan2(y,x)` |
| Hyperbolic | `sinh(x)`, `cosh(x)`, `tanh(x)`, `asinh(x)`, `acosh(x)`, `atanh(x)` |
| Logarithms and small values | `log2(x)`, `log10(x)`, `log1p(x)`, `expm1(x)` |
| Real utilities | `cbrt(x)`, `sign(x)`, `fix(x[,digits])`, `mod(x,y)` |
| Studio extension | Case-sensitive `nthRoot(x[,root])`; default root 2, negative x requires an odd integer root, negative root takes the reciprocal |

`log(x)` is natural logarithm. `fix` truncates toward zero with roundoff correction, `cbrt(-8)` is -2, and `sign` returns -1/0/1. Real domains still apply: `asin(2)`, `acosh(.5)`, `atanh(1)` and zero roots fail. The new `fix` precision is 0–15 in both modes; `mod` has the Navigator behavior in both modes.

| Behavior | Navigator scalar (new dialog default) | Studio scalar (earlier arithmetic / API default) |
| --- | --- | --- |
| Case | Lowercases the whole expression; `SIN(PI/2)` → 1 | Case-sensitive; write `sin(pi/2)` |
| Half rounding | `round(2.5)` → 3, `round(-2.5)` → -3 | Ties to even: 2 and -2 |
| Decimal digits | Integer 0–15 for round/floor/ceil/fix, with roundoff correction | round accepts integer ±100; floor/ceil take one argument |
| Comparison | Relative tolerance 1e-12 / absolute 1e-15; `.1+.2==.3` → 1 | Exact floating comparison; that example → 0 |
| Chained comparison | Adjacent operands, short-circuit: `3>2>1` → 1; `(3>2)>1` → 0 | Write `(a<b) and (b<c)` explicitly |
| `not` precedence | Unary: `not 0>1` → 0 | Earlier rule: `not 0>1` → 1 |
| Remainder | `%`, infix `mod`, `mod(x,y)` use floor quotient; `5 mod -3` → -1; `3%0` → 3 | `%` retains its earlier behavior and rejects zero divisor; new `mod(x,y)` is available |
| nth root | Rejected: official lowercasing changes `nthRoot` into undefined `nthroot` | `nthRoot(-8,3)` → -2; `nthRoot(16,-2)` → .25 |

Navigator examples: `0<=a<=100 ? round(a,2) : 0`, `max(0, sin(pi/2)*a)`, `mod(a,10)`. An example with `a=80` gives 80, 80 and 0 respectively. Syntax is recorded in `x_ttp_studio_formula.syntax`; old provenance without it means historical Studio semantics. Studio/Navigator JSON and session recovery preserve the field. Exporting a result does not ask official Navigator to recalculate it.

This scalar subset is checked against [Navigator v5.3.2's lowercasing/evaluation pipeline](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/services/viewmodels.service.ts) and mathjs 15.2.0; see the [reproducible fixtures](../scripts/formula-reference/README.md). It does not implement all mathjs grammar: implicit multiplication, factorial, postfix percentages, assignment, arbitrary calls, arrays/matrices, units, complex numbers and objects are rejected. NAV-019 provides the missing-score/scope mode and NAV-020 adds the automatic-gradient policy below.

### Calculation modes: missing scores and scope (NAV-019)

**Calculation mode** is separate from **Formula syntax**. Each new dialog defaults to **Studio · chosen scope and missing-score policy**. To use official source-score rules, choose **Navigator · official missing scores and scope**. It fixes syntax to Navigator scalar and disables the Studio **Calculation scope** and **Missing scores** controls. Switching back restores your previous Studio choices. Settings and descriptions are scrollable on smaller displays.

| Rule | Studio calculation mode (default) | Navigator calculation mode |
| --- | --- | --- |
| Targets | Selected source union or Entire matrix | Every active mapped technique/tactic with a score in at least one referenced source |
| Source inclusion and visibility | Selected scope follows checkboxes; matrix scope ignores display filters | Checkboxes, platform/search filters, hidden/disabled state and collapsed children do not limit calculation |
| One referenced input missing | Keep result unscored, or explicitly substitute zero | Substitute zero |
| Every referenced input missing | Follow the chosen Studio policy | Leave unscored, without creating a synthetic zero; empty results are valid |
| Stored score on a disabled source | Count as missing | Use the stored score |
| Genuine stored zero | A score | A score; enough to make that cell a candidate |
| Constant | Use the chosen scope | Try an empty source scope first, then initialize every active mapped matrix cell |
| Unscored result state | Disabled unless explicitly inherited | Enabled by default; explicit Enabled inheritance can change it |

For `(a+b)/2`, `a=80` and missing `b` produces **40** in Navigator mode, even when that source TTP is unselected or disabled. If both inputs are missing, the result stays unscored. A score in an unused source does not add targets; an inheritance-only source can copy annotations/states but does not supply computed scores. Scores are per Technique/Tactic; the same technique can have separate execution/persistence results. Parent aggregate displays are not formula inputs.

The empty-scope probe also respects short-circuit branches: `0 ? a : 50` initializes the whole matrix to 50 without reading source `a`. A standalone `e` becomes Euler's constant in this mode even if layer `e` is listed; for `e+a`, the failed empty-scope probe is followed by per-cell evaluation using source `e` (or zero when that source is missing). `exp(1)` always requests the constant. A nonconstant formula over completely unscored sources produces a valid empty result layer.

Navigator mode projects serialized source annotations in file order: a global row expands to mapped tactics, and a later row replaces the earlier whole row for that cell. A later exact row without Score clears that cell's earlier global Score; a later global row can replace an earlier exact row. Studio retains its existing exact-row/global fallback. Calculation remains bounded to the current catalog's active mapped cells; unresolved/inactive rows are not new computation targets and remain in the source documents.

Workflow: select compatible sources → choose Navigator calculation mode → enter the formula and result name → choose **Automatic gradient mode** or explicit inheritance → **Create result layer** → review scores → Save/Export separately. The five visible stages announce in-memory inputs/outputs, validate the mode/probe, read snapshots, calculate/inherit, validate the complete result and publish one independent tab. Errors/cancellation publish no partial result and preserve sources.

`x_ttp_studio_formula` records `mode`, `syntax`, effective `scope: "navigator"`, `missing: "zero-if-any-score"` and `evaluation: "constant"` or `"scored-union"`. Studio mode records its chosen scope/policy. Studio JSON, Navigator JSON and recovery retain these values. Historical records without `mode` mean Studio behavior and are preserved without recomputation. CSV keeps selected computed TTP annotations, rather than the complete formula configuration.

### Automatic result gradients (NAV-020)

In **Formula and scope**, **Automatic gradient mode** offers **Follow calculation mode** (default), **Studio · source colors and range including zero/one**, and **Navigator · official result range and binary colors**. Follow uses Studio gradients for Studio calculation mode and official gradients for Navigator calculation mode. You can choose either gradient policy independently of the score/scope policy.

| Computed scores | Navigator automatic gradient |
| --- | --- |
| Different positive or negative values, e.g. 20/40/80 or -80/-20 | Actual minimum/maximum; official red/yellow/green colors |
| Range exactly 0–1, e.g. 0/1 or 0/.25/1 | Transparent white `#ffffff00` → blue `#66b1ffff`, bounds 0–1 |
| One score, identical scores, or a constant formula | Default red/yellow/green with bounds 0–100 |
| No computed score | Default red/yellow/green with bounds 0–100; no synthetic scores or fills |
| An explicit **Score gradient** source | Exact source gradient overrides the automatic policy, including its bounds and alpha |

The default official palette is `#ff6666ff`, `#ffe766ff`, `#8ec843ff`. The 0–1 trigger uses exact result bounds and can include fractional intermediate scores. All-zero or all-one results have no range and keep the default palette; a near-zero lower bound such as `1e-16` does not trigger the 0–1 preset. Constant 200 retains bounds 0–100 and displays the upper endpoint; it does not change the stored score. Studio keeps the first referenced source's palette with a range including zero and at least one.

To see the difference, assign two Tactic cells scores 20 and 80 → choose Navigator calculation mode → leave **Automatic gradient mode: Follow calculation mode** → create. Bounds become 20–80. For a membership result with scores 0 and 1, zero is transparent and one is blue. To retain a chosen source palette/bounds, use **Inherit properties → Score gradient → source**; this disables the automatic dropdown while retaining its prior choice. Clearing the source selection re-enables it. Manual colors still override score colors, and explicitly disabled result cells retain their disabled appearance. Scores computed before Enabled inheritance still determine automatic bounds.

Policy changes create a new result without changing source scores, selections, enabled states or annotations. `x_ttp_studio_formula.gradient_mode` records the resolved automatic policy (`studio` or `navigator`); `inheritance.gradient` records an overriding source. Studio JSON, Navigator JSON and recovery preserve the resulting gradient and provenance. Older results without `gradient_mode`, including pre-NAV-020 Navigator calculations, keep their stored historical gradient without recomputation. CSV remains a selected-TTP annotation export, not a complete layer configuration.

The checked-in reference executes the actual v5.3.2 [formula service](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/services/viewmodels.service.ts) and [Gradient class](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/classes/gradient.ts), with pinned development-only dependencies. It compares serialized palette/bounds and scores. Native matrix, overlay and SVG/Excel keep their existing continuous RGBA interpolation/compositing; this is not a pixel-identical recreation of the official 100-sample RGB renderer. See the [reference workflow](../scripts/formula-reference/README.md) for regeneration and the seven-stage offline gradient audit, including actual native colors, SVG pixels and Excel fills. The application requires no Node/TypeScript packages.

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
3. In the threat layer, the matrix's **TTPs from → Group / Software / Campaign / Mitigation** controls can add related techniques. Selection and color do not automatically assign scores.
4. Use **Score selected…** or the individual TTP annotation editor to enter the example's `0`/`1` scores. Record evidence, verification methods, and dates in Comment.
5. Explicitly assign both source scores for each technique participating in the calculation. Keep unknown values distinct from `0` until their handling is defined.

### 2. Create a Native Formula Layer

1. Open **Navigator → Create layer from score formula…** and verify the source names mapped to `a` and `b`.
2. In **Formula and scope**, enter a result name and `a * (1 - b)`. For this example keep **Calculation mode: Studio**, choose **Formula syntax**, then **Selected TTP union from referenced sources** or **Entire matrix**. Use the mode comparison above when deliberately choosing Navigator rules.
3. The default **Missing scores** policy preserves unknowns: missing/disabled referenced scores leave that result unscored. Select the zero policy only when this interpretation is intentional.
4. Optionally choose individual source layers in **Inherit properties**, then click **Create result layer**. Background progress shows 1/5 validation, 2/5 snapshot reading, 3/5 calculation/inheritance, 4/5 result validation and 5/5 completion. A separate result tab opens.
5. Check the three example cases and configure a 0–1 gradient with result `1` colored red through **Layer settings…**.

The following scope/missing-policy paragraphs describe **Studio calculation mode**. Calculations use stored Score values per technique/tactic; displayed parent aggregates are separate. In the default **Selected TTP union** scope, only occurrences selected in referenced sources are targets. Unused variables do not introduce missing inputs or targets. Constant formulas use all listed sources' selected union. An inheritance-only source does not add targets.

**Entire matrix** targets all active mapped techniques, sub-techniques and tactics, including collapsed, disabled and platform/search-filtered cells. To initialize everything to 50: open any compatible layer, enter `50`, choose **Entire matrix**, leave inheritance at its defaults, then create. No source selection is required. Filters inherited afterward change visibility, not coverage.

The default missing policy checks **every variable mentioned**, including unchosen conditional branches; any missing/disabled input makes that cell unscored. Choose the zero policy intentionally if unknowns should count as zero. A genuine zero result stays scored/included. Within the target scope, stored source scores can contribute independently of source checkbox inclusion. Scored results are included even if their inherited Enabled state is false; missing results are disabled unless an explicit state source overrides that default.

### Independent Property Inheritance

Each dropdown may use a different source. For example, calculate `(a+b)/2`, inherit **Comments** from `a`, **Manual colors** from `b`, and retain the automatic gradient for new scores.

| Property | What is copied |
| --- | --- |
| Score gradient | Exact source colors/bounds override Automatic gradient mode; without a source, follow the chosen Studio/Navigator policy |
| Manual colors / Comments | Exact tactic annotation, or global-row fallback; colors override score colors |
| Links / Metadata | Technique lists plus layer-level lists, preserving dividers and extension fields |
| Enabled states | Source state per tactic; absent source rows default to Enabled |
| Filters / hide disabled | Platform filters and hide-disabled flag; calculations still cover the selected scope |
| Legend | Source layer legend entries |

All properties except the automatic gradient default to **Do not inherit**. An absent property produces no synthetic annotation; there is no parent/child inheritance. Studio uses exact tactic rows with the native whole-row global fallback; Navigator uses the file-order projection described above. Reserved source selection markers are removed. Formula provenance remains in `x_ttp_studio_formula` even when layer metadata is inherited. Source names, scores, colors, inclusion and save state remain unchanged. Combined-color mode is switched off to show the result.

### 3. Export and Exchange with the Official Tool

1. Export a Navigator Layer JSON through the existing file export controls, or use **Navigator → Export all open layers…** for sources/results. Choose an existing folder, or create `examples` before saving `examples/layers.navigator.json`.
2. The application reports absolute final/temporary paths before validation, writing and publication.
3. **Navigator → Open ATT&CK Navigator website** opens the official tool for loading the exported JSON. Scalar scores and inherited standard properties are available there; Studio formula provenance is an extension, not an instruction to recompute the formula.
4. Import external result layers through **File → Import Navigator Layer**.

Formula inputs and outputs are in memory and are announced as **Input files: None / Output files: None** before processing. Use **Save / Save As** for complete Studio JSON and a separate export for Navigator JSON/CSV; those operations show absolute final/temporary paths before stage progress. Studio JSON, Navigator JSON and recovery retain scores, inherited properties and formula provenance; CSV contains selected TTP annotations rather than the entire layer configuration. See [Studio Files](studio_files_en.md) and [Aggregation and Matrix Exports](aggregation_and_exports_en.md).

The parser accepts at most 512 characters, 128 tokens and 24 nesting levels. Numeric values must be real, finite and within ±1e300; exponent magnitude is limited to 10000, and min/max accept at most 32 arguments. Unknown variables/functions, unsupported syntax, division by zero, Studio `%` by zero and domain/overflow errors stop the operation without creating a partial layer. Navigator remainder with zero divisor returns the dividend. **Cancel / Close** interrupts at worker checkpoints. On failure, correct the input and retry; sources remain unchanged.

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
