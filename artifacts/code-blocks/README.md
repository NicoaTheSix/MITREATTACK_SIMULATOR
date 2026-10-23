# Collapsible CAR code-panel verification

Inputs: verified local `data/car/source.json` / source members and in-memory Qt fixtures. Outputs: screenshots, logs and reports in this directory. The dedicated panel audit creates no production MainWindow, settings or session; the CAR regression uses its existing isolated artifact settings/session and checks user files for preservation.

Run from the project root with `QT_QPA_PLATFORM=offscreen` and `PYTHONUTF8=1`:

```powershell
.\.venv\Scripts\python.exe -B audit_code_blocks.py
```

The audit reports absolute inputs/outputs, then **1/4** native default-collapse / exact clipboard / geometry → **2/4** bilingual state / empty and long text / re-entry → **3/4** actual CAR analytic implementations / metadata / native record / model / sensor → **4/4** content/source preservation and report.

Windows Qt offscreen results on 2026-10-21: **36 panel checks** and **133 existing CAR checks**, **169 total**, passed. Original native text is stored separately from the read-only editor; tests include CRLF, tabs, indentation, trailing spaces, escaped paths, Unicode, literal HTML, empty code, a 12,000-character line, copied JSON validity and real source code. Native query code is copied without JSON string escaping. All blocks default collapsed when entries change; language changes preserve expansion and code.

- [Panel checks](audit.json) · [panel log](run.log) · [CAR regression](car-regression.log)
- [Collapsed native analytic](analytic-collapsed.png) · [expanded native implementation](analytic-expanded.png)
- [Narrow collapsed panels](collapsed-en.png) · [expanded English](expanded-en.png) · [expanded Chinese](expanded-zh.png)

Internal rich-text links still forward to the existing CAR router. The native model and sensor JSON use the same collapsed component. Code operations do not edit Workspace inclusion, dirty baselines, source records or files. Linux audit registration is available, but these results are Windows-only.

Program flow and copy/visibility progress reporting are in the [root README](../../README.md#collapsible-car-code-blocks), with [English](../../manual/car_integration_en.md#collapsible-code-and-json-panels) and [Chinese](../../manual/car_integration+_zh.md#可收合的程式碼與-json-區塊) operating instructions.
