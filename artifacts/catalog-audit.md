# ATT&CK Catalog Audit: PASS

Snapshot: v19.2

Scope: downloaded artifact integrity and structural validation for Enterprise, Mobile, and ICS; full UI mapping, metadata, search, detail rendering, parent relationships, and checkbox interactions for Enterprise. All six library sections are checked across Enterprise, Mobile, and ICS; Mobile/ICS TTP matrix views are not implemented.

## Results

- snapshot_artifacts_verified: 5
- source_active_records: 697
- source_parent_relationships: 475
- expected_platform_tactic_technique_mappings: 2285
- procedure_example_counts: {'enterprise-attack': 17136, 'mobile-attack': 1478, 'ics-attack': 271}
- ui_mappings: 2285
- missing_mappings: 0
- extra_mappings: 0
- structural_parent_rows: 12
- platforms: 11
- tactic_branches: 122
- active_record_interactions_verified: 697
- navigation_category_counts: {'Mitigations': 109, 'Assets': 18, 'Detections': 3155, 'Groups': 210, 'Software': 974, 'Campaigns': 67}
- title_description_clipboard_verified: True

## Scheduled Task/Job

| ID | Name | Platforms | Windows / Execution |
| --- | --- | --- | --- |
| T1053.002 | At | Windows, Linux, macOS | Mapped |
| T1053.003 | Cron | Linux, macOS, ESXi | Other platform |
| T1053.005 | Scheduled Task | Windows | Mapped |
| T1053.006 | Systemd Timers | Linux | Other platform |
| T1053.007 | Container Orchestration Job | Containers | Other platform |

The Windows branch correctly shows At and Scheduled Task. Other children are available under their own mapped platforms. The detail panel lists the full active family. Revoked/deprecated records are excluded by design.

## Findings

No missing or extra mappings, parent links, or descriptions were found by these checks.

Selected text uses explicit white foreground colors and a dark Qt palette. See `scheduled-job-preview.png` for the rendered At selection and all five active sibling sub-techniques. See `navigation-preview.png` for the rail and ICS asset browser; `procedure-preview.png` shows Procedure Examples and native copy buttons.
