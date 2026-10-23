# Workspace tabs, sidebar scope and collapsed-layout evidence

All settings, test sessions, screenshots and reports for the new audit use this directory. Existing suite logs are collected here; their fixtures remain in the suites' isolated artifact directories. User settings/session files and official active/latest pointers are checked for preservation.

The original regression was reproduced without catalog/session loading: at 1200 × 1200, the collapsed summary was **574 pixels high**. Fixing only its size policy reduced its height to 17 pixels but left a 64-pixel top offset. A bottom expanding spacer produced the intended **17-pixel height at y=9**. The production spacer now passes all eight group expansion combinations at two sizes, retaining all document content. Temporary probe options have been removed from the audit; the fast `--collapse-only` mode tests the production behavior.

Run from the project root with `QT_QPA_PLATFORM=offscreen` and `PYTHONUTF8=1`:

```powershell
.\.venv\Scripts\python.exe -B audit_workspace_layout.py
```

The program announces absolute source/settings/output paths, then verifies compact geometry → real Settings visibility actions/persistence → actual Case Studies tab/search/source actions/copying/navigation/close/reopen → session view restoration/bilingual controls/protected files. Root README documents the program modules and runtime IO/progress flow.

Evidence: [audit.json](audit.json), [final run](run-final.log), [collapsed large](collapsed-1100.png), [collapsed small](collapsed-950.png), [Case Studies English](case-studies-en.png), [Case Studies Chinese](case-studies-zh.png). ATLAS Case Studies now shares the upper reference-tab level with Technique Details; matrices remain inside document workspaces. The latest hierarchy/control regression evidence is in ../matrix-controls/. Shared Workplace/CAR icons remain available in both sidebar framework modes.

Regression logs: [ATLAS](atlas-regression.log), [CAR](car-regression.log), [Studio lifecycle retry](studio-regression-retry.log), [reference tabs](reference-regression.log), [manual/language retry](manual-regression-retry.log). The first lifecycle attempt encountered a transient OS file-write error in its invalid-JSON fixture; the unchanged suite was rerun to completion. Its initial log is retained as `studio-regression.log`.

Windows Qt offscreen evidence only; registration in the Linux runner is available but no Linux pass is claimed. No production session was used as a test fixture.

Completed Windows Qt offscreen results (2026-10-21):

| Suite | Passing checks |
| --- | ---: |
| Workspace layout / scope / case-study tab | 116 |
| ATLAS regression | 116 |
| CAR regression | 133 |
| Studio lifecycle | 113 |
| Independent reference tabs | 48 |
| Total | 526 |

Manual/language regression additionally passed 30 feature/language cases on its isolated retry; the initial concurrent run timed out during the final window's catalog loading and is retained as `manual-regression.log`. The unchanged manual suite completed when run alone. [Query limit](query-limit.log) confirms the native maximum query can round-trip through recovery. [Static results](static-checks.json) report 123 compiled Python sources, 891 unique translation keys/placeholders and 515 checked local links. Targeted whitespace checks passed; the temporary diagnosis branches/instrumentation are removed.
