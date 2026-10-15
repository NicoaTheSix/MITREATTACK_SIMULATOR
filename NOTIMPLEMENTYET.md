# Not Implemented Yet

The current product is **TTP Selection Studio**, focused on creating TTP selection documents and exchanging Studio JSON, CSV and Navigator Layers. Implemented features and operation flows are documented in [README.md](README.md).

## Remaining Document and Export Features

| Area | Implemented foundation | Remaining extension |
| --- | --- | --- |
| New documents | File → New File / Ctrl+N; independent tabs/selections; Navigator Layer import / Ctrl+O with version/ID preview | Reopen/import the Studio's own JSON schema |
| JSON/CSV/Navigator export | Selected TTPs, parent IDs/names, individual annotations, global/scoped comments in JSON/CSV, Navigator Layer round trips, full matrix SVG and colored Excel export | A dedicated Save action and Studio JSON reopening |
| Document lifecycle | Untitled/export names, changed-content markers, right-click rename/close/domain choice, independent closable reference page, and pre-close export/discard/cancel | Application-exit prompts for unexported changes and session recovery |
| Search | Literal, case-insensitive ID/name matching | Description search |
| Filtering | Platform/tactic tree navigation, saved matrix platform unions, name/score sorting and Side/Flat/Mini layouts | Dedicated tactic filters and additional tree filtering controls |
| Batch operations | Independent global/tactic enabled states; scoped add/replace/remove/invert and annotated/unannotated selection; atomic state/comment/score/color/Links/Metadata batches and reviewed annotation clearing | Configurable across-tactic/parent-child selection behavior, richer search fields and relation-based select/deselect beyond the existing sources |
| Domain selection | Enterprise/Mobile/ICS TTP trees, matrices, selection and JSON/CSV/Navigator exchange; per-file right-click domain choice and in-memory domain archives | Reopen domain archives from Studio JSON and recover them across application sessions |
| Dataset workflow | Official versions, custom ATT&CK-compatible STIX Bundles/Collection Indexes, URL layer loading, isolated custom catalogs, SDK differences and guided annotation migration | General-purpose STIX browsing, authenticated TAXII synchronization and session recovery for custom sources |
| Navigator workflow | Native layers, colors/gradients/legends, RGB overlays, scoped comments/Links/Metadata editors, safe arithmetic score formulas, average/max/min/sum family aggregates, SVG/XLSX matrices, reviewed annotation migration and selection comparisons | Embedded Navigator web UI; comparison/boolean/function expressions and configurable inheritance of other layer properties |
| Distribution | Runs in the existing Python/PySide6 environment | Tested installer/portable release, dependency/license inventory, product EULA and release/update documentation |

Future Studio JSON reopening must preserve document identity and recorded ATT&CK versions, resolve each version's catalog, and restore annotation archives. Navigator import already resolves its recorded version and reports unknown/inactive IDs and tactic mismatches. Studio JSON persists data/annotations on disk, but reopening that particular schema is not implemented.

## Processing and Documentation Requirements

Each new operation must show absolute input/output paths before processing and visible stage progress, including completion, cancellation and failure. Use background work for lengthy file/catalog operations. Update README.md in each program's own directory with operation flow, inputs, outputs, run commands and failure handling when implementing a feature. Remove or revise the relevant entry here after implementation and verification.

## Previous Simulator Ideas Outside the Current Product Scope

The earlier proposal included programming-environment discovery, execution ordering and module parameters, dependency/platform compatibility validation, dry-run behavior modules, synthetic events, an event timeline and simulation research reports. Those ideas are outside the current selected-TTP document/export scope and are not requirements for completing this product. A simulation engine, executable behavior generation, a graph editor and interface localization would require a separate product decision.


