# Linux / WSL2 Verification Artifacts

These artifacts were produced in the isolated Kali WSL2 project at `/home/kali/.local/share/ttp-selection-studio-wsl-test/project` and exported to this directory on 2026-10-20. The original Windows settings/recovery files were excluded from that copy.

Read [the human-readable report](../../LINUX_WSL2_TEST_REPORT.md) and [verification.json](verification.json) first. The final verification uses the most recent targeted result for each of 31 audit programs. Initial failures are intentionally preserved; a FAIL in an earlier run does not by itself describe the final result. `attempt_history` identifies the sequence.

| Artifact | Meaning |
| --- | --- |
| `offscreen/audit.json` and logs | Initial full Linux Qt offscreen sweep: 21/31 passes. |
| `rechecks`, `color-rechecks`, `version-recheck`, `source-path-final` | Targeted repair/recheck evidence; the final latest results pass all 31 programs. |
| `xcb/audit.json` and logs | Final real WSLg/X11 GUI checks: Manual and custom-source workflows. |
| `manual-link-results.json` | 15 feature links in English and zh_TW, 30 cases total. |
| `startup-xcb`, `startup-wayland`, `startup-default` logs/images | Successful visible Linux GUI smoke checks using each startup route. |
| `manual-en.png`, `manual-zh-TW.png` | Final actual xcb/WSLg bilingual Manual previews. |
| `custom-source-results.json` | Final Linux source workflow assertions. |
| `windows-custom-data-regression.log` | 70 passing Windows assertions for the same source-path change. |
| `pip-freeze-linux.txt` | Installed Linux package versions. |

Workflow: native Linux audit programs announce absolute inputs/outputs → run feature assertions with stage progress → publish per-run JSON/logs → export existing evidence → validate that every expected program's latest result passes, all pointer checks pass, GUI/manual results pass and Windows source regression passes → publish `verification.json`. Export/summary operations report their source and output directories and three-stage progress. The export retains earlier evidence and does not rerun tests or delete destination files. If validation fails, no successful summary is published. Absolute Linux log paths inside original reports describe the native workspace; `exported_log` in the final verification points to the Windows copy.

To reproduce in an isolated Linux source copy, use `scripts/audit_linux.py` as documented in [scripts/README.md](../../scripts/README.md#linux--wsl2-feature-audits). Full feature coverage is primarily offscreen; actual xcb GUI coverage is narrower and Wayland coverage is startup only. External system-browser launch and other Linux distributions/desktops were not verified.
