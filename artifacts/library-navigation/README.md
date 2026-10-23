# Library navigation and sidebar evidence

Windows verification, 2026-10-21. The real-catalog contract failed before implementation: mitigation opening depended on a prior choice, CAR activity buttons immediately replaced the full page, and Case Studies results were embedded in its reference page. [Original failure](red.log).

Final checks:

| Suite | Passed |
| --- | ---: |
| Integrated library navigation / ownership / source queries | 32 |
| CAR acceptance and IO/recovery | 136 |
| ATLAS integration | 116 |
| Workspace geometry / case interactions / recovery / protected files | 121 |
| Mitigation selection and Workplace opening | 16 |
| Sidebar scope, Qt offscreen | 17 |
| Sidebar scope, native Windows Qt | 17 |
| Total | 455 |

Logs: [integrated contract](green.log), [CAR](car-regression.log), [ATLAS](atlas-regression.log), [workspace](workspace-regression.log), [mitigations](mitigation-regression.log), [sidebar offscreen](sidebar-fast.log), [sidebar Windows](sidebar-windows.log). Reports: [contract](audit.json), [static checks](static.json). Static checks compiled 129 Python sources, validated 905 unique locale keys, and checked 255 local documentation links at that point in the run.

Inspected screenshots: [Case Studies sidebar and independent details](case-sidebar.png), [CAR sidebar retaining the Workplace page](car-sidebar.png), [mitigation sidebar and opened native record](mitigation-details.png). Later summary-label cleanup replaces stale Workplace counts with the source version/status.

Scope tests verify hidden icons, actual membership outside the rail, canonical restoration, live menu actions, label modes, restart and subsequent show requests. The initial clean-window hide flags already worked; structural exclusion is additional enforcement, not a claim that the exact caller behind the previous user's display was identified. An intermediate replay failed after reparenting because Qt sends `ShowToParent` when a hidden-parent child receives a show request; the final guard handles both `Show` and `ShowToParent`, and the final native/offscreen logs above pass. `sidebar-regression.log` retains that intermediate failure. Native Windows tests used the Windows Qt platform, with test windows/menus marked `WA_DontShowOnScreen` to avoid disrupting the user's desktop.

All audits announce absolute input/settings/output paths and staged progress before processing. They use local catalogs, isolated settings/recovery fixtures and no network acquisition. The workspace audit's production settings/recovery/pointer preservation checks passed. No production rollback or application shutdown was performed.

Runtime flow is documented in the [root README](../../README.md#sidebar-libraries-and-explicit-workplace-pages), bilingual workspace and CAR guides. Linux registration is included without claiming a native Linux pass. The running application must be fully exited and restarted to import the updated source.
