# Pinned formula references (NAV-018/NAV-019/NAV-020)

These development-only runners compare the selected finite real/boolean subset with mathjs **15.2.0** and official gradient initialization with TypeScript **5.8.3**, tinycolor2 **1.6.0** and tinygradient **2.0.1**. The desktop application uses its Python allowlisted interpreter and native color projection; it requires none of these Node packages. Python audits use checked-in goldens offline.

The [Navigator v5.3.2 dependency declaration](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/package.json) declares mathjs `^15.2.0`. Its [formula service](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/services/viewmodels.service.ts) lowercases the entire expression before evaluating. This runner pins one version within that range; it does not claim every possible dependency resolution or future release is identical. `golden.json` records the tag URLs and SHA-256 hashes of the two upstream files inspected.

## Inputs, outputs and progress

- Input: [cases.json](cases.json), trusted developer-authored expressions. Each is evaluated with the same three explicit a/b/c source maps: **121 expressions / 363 reference cells**.
- Output: [golden.json](golden.json), with the exact case-file SHA-256, pinned version/configuration, scopes and normalized results. Booleans become 1/0; finite real numbers within ±1e300 are retained; nonfinite/complex/out-of-bound results and errors are classified separately.
- `generate.cjs` prints resolved absolute input/output file paths before **1/3 runtime/fixture checks → 2/3 evaluate with expression-count progress → 3/3 publish**. It overwrites the named development output after evaluating all cases; errors exit visibly. Run only against these trusted cases. Arbitrary mathjs evaluation is never exposed in the application.

Navigator cases use the actual lowercase pipeline. Studio cases test the new case-sensitive nthRoot extension against raw mathjs, outside that pipeline. Previous Studio rounding/operator semantics are checked separately by Python. The scalar comparison supplies identical numeric inputs per cell. NAV-019 has the separate scope reference below; NAV-020 has the real Gradient-class reference at the end of this guide.

## Regenerate and verify

From the project root with Node/npm available:

```text
npm --prefix scripts/formula-reference ci --ignore-scripts
node scripts/formula-reference/generate.cjs scripts/formula-reference/cases.json scripts/formula-reference/golden.json
```

The lockfile pins transitive reference dependencies. node_modules and the local npm cache are ignored. Installing reference packages may need network access. Regeneration does not download ATT&CK datasets or change application dependencies or source layers.

Run the offline application audit with your project's Python environment and cached ATT&CK data:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.venv\Scripts\python.exe -B audit_formula_compatibility.py
```

On Linux use `QT_QPA_PLATFORM=offscreen .venv/bin/python -B audit_formula_compatibility.py`. The audit prints absolute reference/catalog inputs and every output path before six stages: reference integrity/scalars → earlier arithmetic/bounds → per-cell layer calculation → Studio/Navigator/recovery → native UI/default/retry/worker → report. Finite numbers use relative tolerance 1e-13 and absolute tolerance 1e-14 for platform math-library rounding; comparisons remain 0/1. Expression limits remain enforced.

The report is `artifacts/formula-compatibility/audit.json`, beside example Studio/session JSON and the native syntax screenshot. Golden files are evidence: review mismatches and runtime/source changes before deliberately regenerating them, rather than rewriting expectations after a failing application test.

See the [English manual](../../manual/layer_score_formulas_en.md), [中文手冊](../../manual/layer_score_formulas+_zh.md) and [project workflow](../../README.md).

## Official missing-score/scope reference (NAV-019)

[scope-cases.json](scope-cases.json) defines 31 cases over four mapped Technique/Tactic cells; [scope-golden.json](scope-golden.json) records 124 results. Inputs include disabled scores, missing/zero values, independent tactics, unused sources, global/exact row order, constant/lazy expressions, empty results and the Euler/source-e collision. The directory's `.gitattributes` fixes fixture JSON/JavaScript to LF so exact-byte hashes remain stable across Windows/Linux checkouts.

`generate-scope.cjs` reads three explicit paths: trusted case JSON, the original reviewed official service source, and the golden destination. Before processing it prints both absolute input paths and the absolute output path. Stages: **1/3 check mathjs 15.2.0 and official SHA-256 → 2/3 evaluate every case with count progress → 3/3 publish**. It runs the exact v5.3.2 `layerOperation` method after removing its TypeScript annotations, using minimal score/enabled ViewModel/TechniqueVM stubs and post-load constant initialization. The source must match SHA-256 `b973f8ef52435c256f30b32766f4a40811ddf32ea35eced03b172df8e85576e9`; arbitrary source files are rejected. This execution is development-only, never part of the desktop application or its formula parser. The trusted fixtures also use mathjs only in development.

Obtain the original bytes of the [official service](https://raw.githubusercontent.com/mitre-attack/attack-navigator/v5.3.2/nav-app/src/app/services/viewmodels.service.ts), save them as `artifacts/formula-compatibility/navigator-viewmodels.service.ts` (create the directory first), then run from the project root:

```text
node scripts/formula-reference/generate-scope.cjs scripts/formula-reference/scope-cases.json artifacts/formula-compatibility/navigator-viewmodels.service.ts scripts/formula-reference/scope-golden.json
```

The reviewed context is the same tag's [ViewModel initialization/deserialization](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/classes/view-model.ts), [TechniqueVM defaults](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/classes/technique-vm.ts) and [referenced-variable mapping](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/tabs/tabs.component.ts); their hashes are recorded in the golden metadata. The scope reference tests that method and these limited model behaviors, rather than the complete Angular interface or unbounded mathjs values. Missing/invalid number strings are not imported as native score fields: native source validation already requires finite numeric scores. Unresolved/inactive catalog rows are retained in source documents but are outside native active-matrix calculation targets. The separate NAV-020 reference below exercises the real Gradient class and automatic initialization.

The offline Python audit needs neither Node nor the upstream source download:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.venv\Scripts\python.exe -B audit_formula_scope.py
```

On Linux use `QT_QPA_PLATFORM=offscreen .venv/bin/python -B audit_formula_scope.py`. Absolute reference/data inputs and report/fixture/Studio/session/screenshot/cache outputs are announced before **1/7 provenance/custom fixture → 2/7 per-tactic goldens → 3/7 independence/inheritance/earlier behavior/fail/cancel → 4/7 three official domains → 5/7 file/recovery → 6/7 native controls/language/worker → 7/7 report**. Outputs live under `artifacts/formula-scope/`; a separate isolated cache protects official pointers. The audit compares score/state/inclusion and source immutability, not just a successful expression evaluation. Both English and Chinese previews are included. See the bilingual manuals linked above for operation-mode rules and examples.

## Official automatic-gradient reference (NAV-020)

[gradient-cases.json](gradient-cases.json) defines 24 cases; [gradient-golden.json](gradient-golden.json) records 24 gradients and 96 Technique/Tactic cells. Cases cover positive, negative, mixed, exact 0–1, fractional 0–1, near-binary, all-zero/all-one, equal/single scores, empty results, constants, tiny/large finite bounds, exact inherited gradients, inherited disabled states and manual colors.

`generate-gradient.cjs` reads trusted fixture JSON plus the original v5.3.2 service and [Gradient source](https://raw.githubusercontent.com/mitre-attack/attack-navigator/v5.3.2/nav-app/src/app/classes/gradient.ts). It prints all three absolute input paths and the absolute output before **1/3 verify dependency/source pins → 2/3 execute each case with count progress → 3/3 publish**. The service SHA-256 is the value used above; the Gradient SHA-256 must be `4e48d69a52ffaa221a8aaeedba7c1b3d31948ff14e4af5e0fd15e4e9b0650ec3`. Changed source bytes are rejected before execution.

The runner transpiles the actual official `layerOperation` and full Gradient class with TypeScript, then executes them with the pinned tinycolor2/tinygradient packages. Only score/enabled ViewModel/TechniqueVM and constant post-load initialization use minimal stubs. Source-gradient serialization/deserialization and preset/color operations use the real class. Arbitrary upstream files and application code are not accepted. This is development-only execution, separate from the bounded Python application parser.

Run `npm --prefix scripts/formula-reference ci --ignore-scripts` as described above. Save the original service bytes at the earlier path, and the original Gradient bytes at `artifacts/formula-gradient/navigator-gradient.ts` (create that directory first). Then run:

```text
node scripts/formula-reference/generate-gradient.cjs scripts/formula-reference/gradient-cases.json artifacts/formula-compatibility/navigator-viewmodels.service.ts artifacts/formula-gradient/navigator-gradient.ts scripts/formula-reference/gradient-golden.json
```

The golden records input SHA-256, both upstream hashes, all four runtime pins, complete serialized gradients and scores/states. `officialRGB` is the actual official 100-sample RGB output for evidence; the native continuous RGBA renderer is checked separately, not asserted pixel-identical. Six/eight-digit inherited hex colors are compared after equivalent alpha normalization, while the application preserves the exact selected source gradient. Native global palette presets are unchanged by this formula-specific policy.

Run the application audit without Node or downloaded upstream sources:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.venv\Scripts\python.exe -B audit_formula_gradient.py
```

On Linux use `QT_QPA_PLATFORM=offscreen .venv/bin/python -B audit_formula_gradient.py`. It announces absolute inputs/outputs before **1/7 pins/custom fixture → 2/7 official gradients/scores/states → 3/7 independent policies/inheritance/fail/cancel/three domains → 4/7 save/import/recovery/historical preservation → 5/7 actual native controls/colors → 6/7 SVG pixels and Excel fills → 7/7 report**. The isolated report/cache, example Studio/session files, English/Chinese dialog previews, native matrix screenshot and SVG/PNG/XLSX exports are in `artifacts/formula-gradient/`. It publishes PASS after all assertions and checks unchanged source documents and official dataset pointers. The Linux audit runner registers this audit alongside the previous formula audits.
