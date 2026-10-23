# ATLAS mitigation navigation evidence

Windows Qt offscreen, 2026-10-21:

- **16** real-catalog mouse/keyboard/Workplace-action checks passed: [run log](run.log), [report](audit.json).
- **116** existing ATLAS integration checks passed: [regression log](atlas-regression.log).
- **132 total**; source compilation, locale-key uniqueness and changed-guide link checks passed: [static report](static.json).

[Inspected Workplace screenshot](workplace-choice.png) shows the separate **Open ATLAS Mitigation Details** action and chosen ID/name.

`audit_mitigation_navigation.py` announces absolute source/settings/report/screenshot paths before loading → actual navigation/item clicks → explicit Workplace opening/reference retention → keyboard/filter/translation checks → document switch/stale-action checks → report. Settings are isolated in this directory and recovery is disabled. The audit preserves document content while browsing. It tests that neither the rail action nor an item click creates a closed Details tab, and that choosing another item leaves an open reference unchanged until the Workplace button is used.

Runtime/module flow is in the [root README](../../README.md#atlas-mitigation-selection-through-workplace) and bilingual workspace guides. The pending choice is transient, bound to the active document/catalog, and excluded from saves/recovery. Linux runner registration is provided without claiming a native Linux pass.
