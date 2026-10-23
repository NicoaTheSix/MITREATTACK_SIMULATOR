# Independent sidebar groups

Windows verification, 2026-10-21. The menu now has three independent checkboxes, **ATT&CK**, **ATLAS**, **CAR**. Fresh settings enable all three. Workplace always remains visible, including with every family off.

| Run | Passing checks |
| --- | ---: |
| Eight combinations, fresh defaults, labels, restart and migration; Qt offscreen | 147 |
| Same scenarios plus real catalogs, active-explorer fallback and document preservation; Qt offscreen | 154 |
| Real catalogs with native Windows Qt; hidden test windows/menus | 148 |
| Existing library navigation contract | 32 |
| Existing workspace/case/recovery/protected-file checks | 121 |
| Total | 602 |

Logs: [initial group audit](run.log), [loaded audit](loaded.log), [native Windows](windows-loaded.log), [library regression](library-regression.log), [workspace regression](workspace-regression.log). Reports: [default audit](audit.json), [latest loaded audit](audit-loaded.json), [static checks](static.json). The native run preceded the extra six active-explorer checks; its 148-check result is retained in the Windows log. The latest loaded report records the subsequent 154-check offscreen run.

Inspected previews: [ATT&CK alone](groups-1.png), [its three-switch menu](groups-1-menu.png), [CAR alone](groups-4.png), [all off with Workplace retained](groups-0.png). [All three enabled menu](groups-7-menu.png). Right-side reference pages intentionally remain open when their rail family is disabled; these switches control navigation visibility, not document data.

The audit uses real menu mouse events for every combination in both label layouts. It asserts exact independent checked state, actual visibility, exclusion from the rail, resistance to later show requests, canonical order and restart for each state. Migration fixtures cover old both/Only settings, unknown modes, malformed new JSON, an empty group list and CAR alone. Settings are isolated under this directory and production recovery is disabled. The workspace regression's user settings/recovery/dataset-pointer preservation check passed.

`audit_sidebar_groups.py` announces absolute input/settings/report/preview paths before defaults/menu → combinations/restart → migration/validation → report. Native Windows tests use `--native-hidden` so their windows and menus do not appear on the user's desktop. `audit_sidebar_visibility.py` remains a compatibility entry point to the same audit; the Linux runner does not execute a duplicate. Runtime read/apply/save flow is in the [root README](../../README.md#independent-attck--atlas--car-sidebar-switches), with bilingual workspace guides.

Old `both` preferences migrate to all three. Old ATT&CK-only or ATLAS-only preferences migrate to that single family, including CAR off. New or invalid preferences default to all three. A user change writes `navigation/families` as an enabled-family JSON list and removes the legacy key. An empty list is a valid all-off choice. No production preferences were reset during tests. Fully exit/restart the application to load the new menu.
