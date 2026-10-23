# Workspace tabs and sidebar visibility

## CAR Browser

**CAR Browser** is an independent upper reference tab beside **Technique Details** and filenames. Open it from **Workplace → Open CAR Browser** or an explicit CAR information/link action; rail icons still open the sidebar only. All CAR categories and internal links reuse this tab. Switching between reference tabs preserves the current CAR content, query and filters.

Click **×** or right-click **Close CAR Browser**. Closing changes no included analytics, TTPs, annotations or save status. Workplace reopens the retained view unless a different sidebar choice/category is requested. The two reference tabs close independently. Recovery remembers CAR tab visibility, active page and category, restoring the category list after restart; individual detail navigation is transient. Older checkpoints default to no CAR tab.

## ATLAS Case Studies Details

**ATLAS Case Studies Details** is an upper reference tab beside **Technique Details** and document filenames. The matrices remain inside the document workspace. It has moved out of the left activity rail. Open it using **View → ATLAS Case Studies Details**, **Open ATLAS Case Studies** above the selection lists, or the workspace context menu.

Search names, IDs or descriptions in the left Explorer list. Search and results are outside the reference page; the reference tab contains only the selected case details. Click a result to read its native description, case type, dates, references and steps. The step links open internal technique details; reopen the case-study tab to return to its retained query and entry. Title/Description copy buttons and STIX JSON/TAXII envelope copy controls remain available, including the existing source-content hover previews.

**Add all ATLAS TTPs** and **Remove all ATLAS TTPs** use the displayed case's exact official relationships. Repeated steps are deduplicated. Removal retains annotations and unrelated selections. Browsing alone does not include techniques. The controls resolve against the active Workplace's exact ATLAS dataset; obsolete actions cannot modify another document or source.

Click its **×**, or right-click the Case Studies tab and choose **Close Case Studies**. Closing removes this reference tab and retains its list/detail state and document selections. Reopen it using View, the workplace button or context menu. Both reference pages close independently. Automatic recovery saves its visibility, query, selected case and active page alongside the existing matrix states.

## ATLAS mitigations: open details through Workplace

1. Click **ATLAS Mitigations** in the left rail. It opens the sidebar and retains the current right-hand page.
2. Click a mitigation row to open its Details immediately, or select it with the arrow keys and press Enter.
3. Click **Workplace**. Its **Open ATLAS Mitigation Details** button shows the chosen entry's ID/name beside it.
4. Click that button to open the selected mitigation's Details, including copy controls and related-TTP actions.

The Workplace button remains available when catalog loading finishes, including without a prior choice: it displays the first available mitigation and shows the sidebar. Searching and returning to the library retain the choice. After closing Details, click the same row or use the button to reopen it. Arrow keys alone only change the choice; clicking or pressing Enter opens it. Browsing changes no included TTPs, annotations or save status. Changing documents or the exact ATLAS dataset clears the choice. The choice is not restored from Studio/recovery files.

## Settings → Sidebar content

Check or uncheck **ATT&CK**, **ATLAS** and **CAR** independently. All three default to enabled for fresh settings. This supports eight combinations: any single family, any pair, all three, or all off. **Workplace** always remains available. For ATT&CK alone, keep ATT&CK checked and uncheck ATLAS and CAR.

ATT&CK controls its technique and library icons. ATLAS controls its TTP/mitigation icons. CAR controls Analytics, Data Model and Sensors. Excluded buttons leave the rail layout and are kept under a hidden parent; enabling them restores the original order. Icon-only and labeled navigation use the same switches.

Each combination survives restart. Turning off the active family moves its explorer to Workplace while preserving the right-hand page. Saved TTPs, CAR inclusion, annotations, documents and export scope stay unchanged. Fresh/invalid settings show all three. Older ATT&CK-only or ATLAS-only preferences migrate to that family alone, with CAR off; the old both-frameworks preference enables all three. The first change writes the new family-list setting.

## Collapsed selections

ATT&CK, ATLAS TTP and CAR Analytics expand independently. When all three are collapsed, the summary and buttons stay compact at the top; a bottom spacer absorbs the unused height. Expanded lists receive the available space. Collapsing does not change counts, selections, comments, scores or colors. Recovery preserves all three expansion states; older checkpoints default missing states to expanded.

## Files and progress

Tab opening/closing and source operations announce memory-only inputs/no immediate file outputs and staged progress. Sidebar preference reading announces the absolute settings path, then read/validate; changes announce the absolute output path, then validate → update → save. Recovery uses the existing absolute final/temporary paths and atomic writes. These are interface preferences, not Studio document edits.

The isolated audit `audit_workspace_layout.py` reports all actual inputs and outputs under `artifacts/workspace-layout/`. Its fast `--collapse-only` mode pauses catalog loading and checks real Qt geometry in seconds; the full run checks all expansion combinations, actual menu/row/button actions, persistence, bilingual controls and protected user files. See the [root workflow](../README.md#workspace-tabs-and-sidebar-visibility) and [guide index](README.md).

## Collapse matrix controls

Above the ATT&CK matrix, click the arrow beside **Matrix controls**. All configuration rows collapse together; the summary remains visible and the matrix gains space. Click again to reopen. Layer, platform/search, display settings, source lookup/preferences/results, colors/scores and batch actions stay available inside this panel.

Queries and filters remain active while hidden. Collapse does not change selected TTPs, annotations or save status. Temporary source hover outlines clear. Automatic recovery retains the expanded/collapsed state independently of the active reference tab; older checkpoints default to expanded. This is separate from **Collapse all**, which controls child-technique expansion.

Runtime reports memory-only inputs/no immediate output files, then update visibility → ready. The existing recovery checkpoint reports its absolute final/temporary paths before writing. Run `audit_matrix_controls.py` for isolated native geometry/reference/bilingual checks, and `audit_workspace_layout.py` for real-catalog/session/legacy checks. See the [root workflow](../README.md#collapsible-matrix-controls-and-reference-tabs).

## CAR sidebar and full page

Click **CAR Analytics**, **CAR Data Model** or **CAR Sensors** to show that category's searchable list in the Explorer. Click a row, or select it with arrow keys and press Enter, to open its complete content in the shared CAR Browser reference tab. **Workplace → Open CAR Browser** also opens the chosen entry; without a choice it opens the full category browser. Changing documents clears stale choices and does not open a cached CAR detail automatically. Inclusion, sorting, related links and code copying remain available in the full page.
