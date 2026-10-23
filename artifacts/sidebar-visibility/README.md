# Sidebar visibility enforcement

Windows Qt offscreen, 2026-10-21. The fix keeps framework exclusions authoritative when a later Qt `Show` event requests an excluded rail button.

The original clean-window Settings action, language/label changes and restart probes passed before the change. The targeted replay then called `show()` on excluded ATLAS buttons after selecting ATT&CK only; this failed before the guard ([red log](red.log)). The exact caller responsible for the previously running user's window was not identified; this is a visibility-invariant fix verified through event replay, not a claim that the original caller was reproduced.

Final targeted checks:

- **17** with catalog loading paused: [green log](green.log), [report](audit.json).
- **18** with real catalogs loaded, actual menu mouse clicks and document-content preservation: [loaded green log](loaded-green.log).
- **35 total**. Syntax checks for changed modules passed.

Run `audit_sidebar_visibility.py`, then `audit_sidebar_visibility.py --loaded`, using the project Python and `QT_QPA_PLATFORM=offscreen`, `PYTHONUTF8=1`. Each announces absolute input/settings/output paths before the three-stage menu/events → labels → restart/report workflow. Settings are isolated in this directory; the session is disabled. The default run overwrites `audit.json` and the screenshot after the loaded run.

The broader [workspace regression](workspace-regression.log) completed 120 functional checks, then failed its final production-file preservation guard because the live `data/workspace-session.json` changed during the run. This is not counted as a full workspace-suite pass. No production rollback was performed. Its isolated settings/recovery fixtures remain under `artifacts/workspace-layout/`.

[Inspected sidebar screenshot](attack-only-guarded.png). The runtime/module flow is in the [root README](../../README.md#workspace-tabs-and-sidebar-visibility). Linux registration is included without claiming a native Linux pass.
