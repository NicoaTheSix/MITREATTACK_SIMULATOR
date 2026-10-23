# Fusion Studio Operating Manual

*A community toolkit for MITRE ATT&CK® and ATLAS*

Open **Info → Manual** or press **F1**. Manual is a reference tab alongside your file names and Technique Details. Opening it again focuses the same tab; switching or closing it retains your current document.

Use the outline on the left to jump to sections. Guide links open inside this tab and update the outline. **Open feature** links open the actual control for the active document. The toolbar opens the home page or guide index and searches the current page.

English is the default. Choose **Settings → Language → 繁體中文（臺灣）** to switch the interface and manual immediately. Choose **English** to switch back. Your choice is remembered after restart. Language changes preserve document names, selections, comments, scores, formulas, source IDs and saved file contents. Original ATT&CK content and official release excerpts retain their source language.

## 1. Create, open and save documents

1. Use **File → New File** to create an independent document.
2. Use **File → Open Studio JSON…** to restore a complete Studio document.
3. Use **Save / Save As…** to save selections, annotations, layer settings and dataset identity.
4. Files save independently; an asterisk after a name indicates unsaved changes.

Normal startup automatically restores the last valid session without a confirmation question. The bottom Output panel reports the restored tab and unsaved-tab counts and checkpoint path when loading completes.

[Guide: Studio files, closing and recovery](studio_files_en.md) · [Open feature: choose a Studio document](studio://open-file)

## 2. Choose an ATT&CK version and domain

The current default is **ATT&CK v20.0**, with Enterprise, Mobile and ICS data. Existing documents keep their recorded dataset; opening an old document does not upgrade it automatically.

Use **Version (vX.Y)** to select a release. Right-click a file tab to change its ATT&CK Domain. Uncached releases need a download; verified local snapshots remain available offline.

[Open feature: version picker](studio://versions) · [Guide: datasets and historical releases](studio_files_en.md#datasets-and-historical-releases)

## 3. Search and select TTPs

Search by name or ID in the TTP sidebar. **TTP search fields…** also offers Description, Data Sources and Detection Strategy. Check techniques to include them in the active document. Ordinary matrix clicks and Ctrl / Shift clicks have different selection behavior.

Selection preferences control cross-tactic linking, parent/child family linking and visible-only eligibility. Changing a preference affects later gestures rather than expanding an existing selection.

[Open feature: TTP search](studio://search) · [Open feature: selected techniques](studio://selected)

[Guide: selection preferences and extended search](selection_and_search_en.md) · [Guide: matrix interaction and source copying](detection_interaction_en.md)

## 4. Browse groups, software and detection content

Use Groups, Software, Campaigns, Mitigations, Assets and Detections in the left rail. Group / Software / Campaign / Mitigation / Asset / Detection Strategy / Data Component / Data Source support related-technique selection and result-union batches; Analytics remain browse-only. Hover dropdown/completion results to temporarily outline mapped techniques. In the sidebar, **Show matrix preview** keeps source results beside the matrix. Moving away restores the original display without editing selection or annotations.

[Guide: source search and context actions](navigator_parity_controls_en.md)

[Guide: source result batches](source_relationship_selection_en.md) · [Guide: hover preview](source_hover_preview_en.md)

## 5. Matrix display and layer settings

**Open ATT&CK Matrix** opens the native Flat / Side / Mini views with platform filters and saved family expansion. **Navigator → Layer settings…** edits the description, gradient, legend, display preferences and custom context URLs.

[Open feature: ATT&CK matrix](studio://matrix) · [Open feature: layer settings](studio://layer-settings)

[Guide: advanced Navigator workflows](advanced_navigator_en.md) · [Guide: labels and annotation indicators](matrix_display_en.md) · [Guide: visible selection and expansion](visibility_expansion_presets_en.md)

## 6. Annotations, scores and batch editing

Techniques support Comment, Score, Color, Links, Metadata and Enabled state. Inclusion and Enabled are independent. Editing may apply to all tactics or selected tactic occurrences.

Select techniques before opening **Navigator → Batch edit selected TTPs…**. Check the scope before applying. Cancelling leaves the original content intact.

[Open feature: batch-edit selected techniques](studio://batch-edit) — requires a selection and a Navigator-compatible document.

[Guide: independent states and batch operations](batch_operations_en.md)

## 7. Formulas, aggregation and comparisons

Score formulas combine source layers into a new result. **Formula syntax** defaults to Navigator scalar, with constants, trigonometric functions, tolerant comparisons and chained comparisons. Choose Studio scalar to retain earlier rounding and operator rules; the full guide explains the differences and the Studio-only nthRoot extension. Calculation mode defaults to Studio. Choose Navigator mode for empty-scope constants, missing inputs as zero, all-missing cells skipped and stored disabled scores included; its syntax is fixed and Studio policy controls are inactive. Check independent property inheritance separately. Automatic gradient mode follows the calculation mode by default: Navigator uses actual result bounds and a transparent-white/blue 0–1 preset, with default 0–100 for constant/empty results. Studio remains selectable, and a chosen Score gradient source always overrides automatic settings. Family aggregation does not automatically change the selected techniques.

[Open feature: score formula](studio://formula) · [Open feature: compare documents](studio://compare) · [Open feature: compare ATT&CK versions](studio://compare-versions)

[Guide and examples: score formulas](layer_score_formulas_en.md) · [Guide: aggregation and exports](aggregation_and_exports_en.md)

[Guide: SVG paper sizes and orientation](svg_paper_en.md)

[Guide: SVG Light/Dark export themes](svg_themes_en.md)

## 8. Navigator, custom sources and reviewed upgrades

Studio JSON preserves the complete native document. Navigator Layers exchange compatible layer data. CSV exchanges selected techniques and cannot restore all presentation settings.

**Import Navigator Layer… / Ctrl+Alt+O** can open an entire 1–20-layer JSON array. All layers are checked by default; use the checkboxes to choose a subset. Each has its own domain, release, source and selection policy. The batch opens only when every checked layer is ready, preserving existing documents.

[Guide: multi-layer JSON opening and blocked-source handling](navigator_bundle_import_en.md)

For a missing or ambiguous custom layer source, **Resolve custom data…** in the import preview can fetch its URL, validate a local Bundle/cache or offer Collection Index versions. Review the exact hash/domain/release and explicitly approve any changed dataset before binding it to that layer. Opening the source review does not fetch automatically.

[Guide: customDataURL acquisition and changed-source review](custom_data_url_import_en.md)

Custom data must be an ATT&CK-compatible STIX Bundle or Collection Index. Confirm its source, domain and version. Use reviewed migration to handle revoked, replaced or unresolved techniques.

Custom Bundles can now define additional domains with separate display names, Kill Chains and external-ID sources. Choose a domain in the source preview, then switch within that dataset through the filename's **ATT&CK Domain** context menu. Multiple matrices form one ordered union; Studio, Navigator, CSV and session recovery preserve custom identities and domain state.

[Guide and loadable example: custom domains](custom_domains_en.md)

[Guide: final upgrade summary, skip reasons and unfinished-item return](upgrade_summary_en.md)

[Open feature: import Navigator Layer](studio://import-layer) · [Open feature: URL or custom STIX](studio://sources) · [Open feature: reviewed layer upgrade](studio://upgrade)

[Guide: custom data and reviewed migration](advanced_navigator_en.md)

## 9. Export and share

Use **File → Export… / Export CSV… / Export Navigator Layer…** for exchange files. **Navigator → Export matrix SVG… / Export matrix Excel…** creates matrix artifacts. The all-layer workbook creates a separate worksheet for each open layer.

[Open feature: SVG export settings](studio://export-svg) · [Open feature: Excel export settings](studio://export-excel)

[Guide: export scope, aggregation and examples](aggregation_and_exports_en.md)

Navigator JSON exports review hidden modified annotation cells per layer. **Export annotations on visible techniques only** is unchecked by default, preserving all annotations. The active matrix's filters/search/expansion define visibility; inactive layers use their own saved view. A reduced copy retains Studio inclusion markers, complete layer properties and exact selection scopes. Cancel writes nothing; source annotations, names and unsaved states are unchanged.

[Guide: JSON annotation export options and hidden-scope warnings](json_annotation_export_en.md)

## 10. Progress, errors and recovery

File operations announce absolute input/output paths and staged progress. Wait for completion. If an operation fails, inspect Output before treating a file as a finished result.

Session checkpoints help recover work but do not replace deliberate Studio saves. The Manual is read-only reference content; it is excluded from TTP selections and exported layers. Its open state is not saved in Studio files.

[Guide: session recovery and failure protection](studio_files_en.md)

## 11. Information and official resources

Info contains author information, official MITRE and ATT&CK introductions, and version history. Hover over **Version update history** to see the release list. Select a version for a short source excerpt and a link to the full official changelog.

[All operating guides](in_app_index_en.md) · [Installation and startup](../README.md) · [Official MITRE ATT&CK website](https://attack.mitre.org/)

## CAR research content

Use the CAR Analytics, CAR Data Model and CAR Sensors activity icons to open sidebar lists. Select an entry, then use **Workplace → Open CAR Browser** for its full page. Include analytics independently in the current Workplace; use Studio JSON for complete preservation and the default-on CAR content option. Navigator stores TTPs only. [CAR operating guide](car_integration_en.md).

## Workspace tabs and sidebar visibility

ATLAS case details use an upper reference tab with search/results in the left sidebar. **Workplace → Open ATLAS Mitigation Details** also works without a prior choice; mitigation rail/item clicks retain the current right page. Settings → Sidebar content independently toggles ATT&CK, ATLAS and CAR, with all three on by default; Workplace always remains. Collapsed selection groups keep the summary and controls compact. [Guide](workspace_layout_en.md).

**CAR Browser** opens beside **Technique Details** as an independent upper reference tab. Close it with × or its context menu; Workplace reopens it. Recovery retains tab visibility, active page and category. See the [workspace guide](workspace_layout_en.md#car-browser).
