# Navigator JSON Annotation Export

## Choose complete or visible annotations

1. Arrange the active matrix's platforms, search and expanded sub-techniques as desired.
2. Choose **File → Export Navigator Layer…**, or **Navigator → Export all open layers…** for a JSON array of 1–20 layers.
3. Choose the output filename. The next review shows its absolute path, hidden modified cell counts, distinct technique IDs per layer and a read-only list of affected ID/tactic scopes.
4. Leave **Export annotations on visible techniques only** unchecked to retain everything. This is the default every time.
5. Check it only to omit hidden technique annotations from this exchange copy, then click **Export JSON**. **Cancel** writes nothing and preserves an existing target.

In this review “modified” means different from the default technique state, rather than edited since the last Save. It includes a score (zero counts), manual color, disabled state, comment, Links, user Metadata, `showSubtechniques: true`, and custom technique-row fields. Imported annotations count too. Studio inclusion-only metadata and read-only source STIX Notes do not count. Each affected technique/tactic occurrence counts once; a second column counts distinct technique IDs. Unresolved imported ID/tactic rows are hidden and listed separately by their scope text.

## What is visible

The active layer uses the actual logical matrix cells after platform union, search, **Hide disabled**, saved/global expansion and temporary search expansion. A collapsed child is hidden even if its parent is visible. A parent displayed as a family heading is visible. Scrolling off-screen, closing/switching away from the matrix tab, hiding fills/markers, and temporary source-hover outlines do not remove annotations. An active layer still building uses the same platform/search controls and saved expansion projection.

For an all-layer export, inactive layers independently use their saved platform filters, enabled states and expansion settings, with no active-layer search. Combined overlay annotations are never copied into another layer. Names, sorting, layer Description, gradient, legend, layer Links/Metadata and other layer properties remain complete.

Global annotations are expanded to explicit tactic rows in a visible-only copy. This prevents a visible tactic's global comment/color from reappearing in a hidden tactic when imported. Existing tactic rows take precedence as whole rows, matching the matrix. Hidden selected techniques retain only identity and the reserved Studio inclusion marker, so they may still appear in the JSON without comments, colors, scores, links or user metadata. Selection scopes stay intact; visibility does not deselect TTPs. Omitting a hidden disabled-state annotation means that exchange copy no longer disables that occurrence.

This option controls technique annotations; it is not a confidential-data redaction tool. Complete layer properties remain, including custom extensions. **Studio JSON Save / Save As / Export**, CSV, session recovery, SVG and Excel are unaffected. Keep a Studio save when you need all domains, version archives and an editable original.

## Worked example

Give `T1053.005 Scheduled Task` a comment and score, collapse `T1053 Scheduled Task/Job`, and export a Navigator JSON layer. With the default complete option, the hidden child's annotations remain and the review lists its hidden tactic occurrences. With visible-only checked, those child annotations are absent. If the child was selected, its Studio inclusion-only rows still restore that selection when imported into Studio. Reopen the review: complete export is selected again.

If a technique has one global comment but only one visible tactic occurrence, the reduced copy contains the comment only on that tactic row. The original layer retains its global annotation and all selected scopes.

## Files, progress and failure behavior

Input is the open document, exact cached catalog and frozen matrix controls in memory; no network download occurs. Before processing, Output lists the absolute target path. Preview reports **1/3 validate → 2/3 resolve technique/tactic rows → 3/3 hidden count**. Export reports the chosen preservation policy, then absolute output/temporary paths and **1/3 serialize → 2/3 write UTF-8 → 3/3 atomic publish**. A cancelled review creates no output or temporary file; a failed publish preserves the previous target and cleans its temporary file.

Source names, annotations, selections, save baselines and clean/unsaved states remain unchanged. Single-layer export remembers its exchange filename/format; all-layer export leaves that bookkeeping alone. The checkbox is per export and is not a layer/session preference. Explicit programmatic `visible_only=True` uses the same projection; omitted options preserve all annotations and log hidden counts.

Verification: run `audit_json_annotation_export.py` using the project's Python with `QT_QPA_PLATFORM=offscreen`. It announces resolved paths before creating isolated fixtures, example exports, Studio data, screenshots and `audit.json` under `<project-root>/artifacts/json-annotation-export`.

[All guides](README.md) · [Studio files](studio_files_en.md)
