# Matrix controls and reference hierarchy evidence

Windows Qt offscreen verification, 2026-10-21. Run audits from the project root with `QT_QPA_PLATFORM=offscreen` and `PYTHONUTF8=1` using the project virtual environment.

| Suite | Passed |
| --- | ---: |
| Matrix controls / reference hierarchy | 22 |
| Real workspace / case studies / recovery | 121 |
| Existing reference-tab lifecycle | 48 |
| ATLAS integration | 116 |
| Studio Save/Open/exit/recovery lifecycle | 113 |
| Total | 420 |

Logs: [controls](run.log), [workspace](workspace-regression.log), [reference tabs](reference-regression.log), [ATLAS](atlas-regression.log), [Studio lifecycle](studio-regression.log). Structured results: [controls](audit.json), [workspace](../workspace-layout/audit.json), [static checks](static-checks.json).

Inspected native screenshots: [real matrix collapsed](../workspace-layout/matrix-controls-collapsed.png), [upper case reference, English](../workspace-layout/case-studies-en.png), [Traditional Chinese](../workspace-layout/case-studies-zh.png). Small-window geometry is also checked in [collapsed-1000.png](collapsed-1000.png).

The audits announce absolute input/settings/output paths and staged progress before processing. Controls checks pause catalog loading while exercising actual Qt widgets; the workspace suite uses real catalogs, source relationships and isolated recovery fixtures. Production settings/recovery and dataset pointers are checked for preservation. One intermediate run detected protected data changing during the test and correctly failed its preservation guard; that log is retained as `workspace-protected-file-interference.log`. The final rerun passed the full guard. No rollback of production user data was performed.

Runtime flow is documented in the [root README](../../README.md#collapsible-matrix-controls-and-reference-tabs) and the bilingual workspace guides. Linux audit registration is included; this evidence does not claim a native Linux test pass.
