# CAR Browser upper reference tab

Windows Qt offscreen verification, 2026-10-21:

| Suite | Passing checks |
| --- | ---: |
| Upper reference lifecycle, document ownership, recovery and bilingual title | 25 |
| Existing CAR acceptance / IO / recovery | 136 |
| Existing copyable/collapsible CAR code blocks | 36 |
| Total | 197 |

Logs: [reference tab](run.log), [CAR regression](car-regression.log), [code panels](code-regression.log). [Reference report](audit.json), [static report](static.json). [Inspected upper-tab preview](car-reference.png) shows filenames, Technique Details and CAR Browser in the same bar.

The tab audit uses actual Qt button/tab/context events, analytic/model/sensor links and real document insertion/closure. It verifies one stable CAR reference, independent closure, retained in-memory content/query, current-document binding, active/inactive reference recovery, legacy defaults and localized title. A fresh MainWindow automatically reads the isolated recovery file and restores the CAR reference with its owning document and category. Category lists restore after restart; individual detail navigation remains transient.

Inputs and all absolute settings/session/report/preview paths are printed before the four-stage lifecycle → closure/link/document → recovery/language → report flow. Settings and recovery files are isolated under this directory. Existing CAR regression fixtures use their own artifact directory. No production recovery checkpoint is used.

Runtime open/close and reveal routing are documented in the [root README](../../README.md#car-browser-reference-tab) and bilingual CAR/workspace guides. Linux audit registration is included without claiming a native Linux pass. Restart the running application to import the changed source.
