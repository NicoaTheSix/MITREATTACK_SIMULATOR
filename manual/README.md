# Manuals and Examples

This directory contains operating guides and worked examples for Fusion Studio. Chinese guides use the requested `+_zh.md` suffix; English guides use `_en.md`.

The application subtitle is *A community toolkit for MITRE ATT&CK® and ATLAS*. Both in-app home pages use the Fusion Studio name; **Info → About Fusion Studio** displays the same identity. Guide filenames and `studio://` feature links stay stable. Manual loading retains its existing absolute-path and staged progress reporting; the root [branding workflow](../README.md#application-name-and-startup-flow) documents the shared name.

`installation_en.md` and `installation+_zh.md` cover Windows and Linux/WSL2 startup. Keep their Linux system packages, separate-venv instructions and Bash launcher flags aligned with the root README. They describe the same resolve inputs → validate environment/imports → launch → dataset loading workflow; package and application commands display absolute input/output paths and stage progress. Linux tests use an isolated source copy so existing Windows settings and recovery documents are not overwritten.

The installation guides also describe `setup-ttpselecter.sh`: validate the installed Linux application → preflight command/profile ownership → install a user wrapper and backed-up Bash/Zsh PATH blocks → verify forwarding. Reopen the terminal before using bare `ttpselecter`; repeat setup after moving the project. Keep these steps aligned with `scripts/install_linux_command.py` and the root command-setup instructions.

Open **Info → Manual** or **F1** for the [in-app operating manual](in_app_manual_en.md). It appears beside file tabs, with a clickable heading outline, links to the guides below, page search, and explicit feature links that open existing application controls. Reading does not edit TTP documents; the Manual tab can be closed and reopened. Feature links in this guide are handled by the desktop's fixed `studio://` action list, rather than by a web browser.

The default in-app manual is [English](in_app_manual_en.md), with an [English guide index](in_app_index_en.md). **Settings → Language → 繁體中文（臺灣）** switches the interface and [Traditional Chinese manual](in_app_manual+_zh.md) / [index](in_app_index+_zh.md) together. Keep both home pages' `studio://` feature IDs aligned. Original source content and authored user data retain their source language.

| Topic | Traditional Chinese | English |
| --- | --- | --- |
| Dataset-scoped custom domains, external-ID sources, ordered Matrix unions and a loadable Bundle example | [自訂 Domain 與資料模型](custom_domains+_zh.md) | [Custom Domains and Catalog Models](custom_domains_en.md) |
| In-import customDataURL acquisition, relative references, Bundle validation and changed-source review | [解析圖層的 customDataURL](custom_data_url_import+_zh.md) | [Resolve a Layer's customDataURL](custom_data_url_import_en.md) |
| Open all/subsets of Navigator arrays with independent versions/sources and atomic installation | [一次開啟多個 Navigator JSON 圖層](navigator_bundle_import+_zh.md) | [Open Multiple Navigator JSON Layers](navigator_bundle_import_en.md) |
| Complete/visible-only Navigator JSON, hidden modified annotation warnings and inclusion preservation | [Navigator JSON 註記匯出](json_annotation_export+_zh.md) | [Navigator JSON Annotation Export](json_annotation_export_en.md) |
| Temporary source-result hover outlines, collapsed-child hints and restoration | [來源搜尋結果的矩陣懸停預覽](source_hover_preview+_zh.md) | [Matrix Preview on Source Result Hover](source_hover_preview_en.md) |
| Source-result batches and Asset / Detection Strategy / Data Component / Data Source mappings | [來源搜尋結果批次操作與關聯技術選取](source_relationship_selection+_zh.md) | [Source Result Batches and Related Technique Selection](source_relationship_selection_en.md) |
| Source search switches, independent fills/markers, annotated child counts and context URL actions | [Navigator 搜尋、顯示與右鍵操作](navigator_parity_controls+_zh.md) | [Navigator Search, Display and Context Controls](navigator_parity_controls_en.md) |
| Detection Strategy search, saved individual expansion, Ctrl/Shift selection and hover STIX/TAXII copying | [偵測策略搜尋、矩陣操作與原始資料複製](detection_interaction+_zh.md) | [Detection Search, Matrix Interaction and Source JSON](detection_interaction_en.md) |
| Visible-only selection, saved expansion, source Description search and six gradient presets | [可見選取、展開模式與漸層預設](visibility_expansion_presets+_zh.md) | [Visible Selection, Expansion and Gradient Presets](visibility_expansion_presets_en.md) |
| Independent names/IDs, tactic header colors, annotated expansion and annotation/source-Note indicators | [矩陣顯示與註記提示](matrix_display+_zh.md) | [Matrix Display and Annotation Indicators](matrix_display_en.md) |
| Cross-tactic/family selection, Description/Data Sources search and Mitigation add/remove | [選取偏好與進階搜尋](selection_and_search+_zh.md) | [Selection Preferences and Extended Search](selection_and_search_en.md) |
| Studio JSON opening, Save/Save As, close/exit and session recovery | [文件儲存與工作階段復原](studio_files+_zh.md) | [Studio Files and Session Recovery](studio_files_en.md) |
| Navigator/Studio syntax, missing-score/scope and automatic-gradient modes, independent inheritance and worked examples | [圖層分數公式操作手冊與範例](layer_score_formulas+_zh.md) | [Layer Score Formulas: Manual and Examples](layer_score_formulas_en.md) |
| SVG paper presets, portrait/landscape, physical units and Custom restoration | [SVG 紙張尺寸與方向](svg_paper+_zh.md) | [SVG Paper Sizes and Orientation](svg_paper_en.md) |
| SVG Light/Dark export themes, alpha composition and identical preview/file output | [SVG 淺色與深色主題](svg_themes+_zh.md) | [SVG Light and Dark Themes](svg_themes_en.md) |
| Parent/sub-technique aggregation, advanced SVG settings/preview and one-sheet-per-layer Excel export | [分數彙總與矩陣匯出](aggregation_and_exports+_zh.md) | [Aggregation and Matrix Exports](aggregation_and_exports_en.md) |
| Side/Flat/Mini, sorting, platform unions, Links/Metadata, URL/custom STIX and reviewed upgrades | [Navigator 進階操作手冊與範例](advanced_navigator+_zh.md) | [Advanced Navigator Workflows](advanced_navigator_en.md) |
| Final upgrade summary, optional skip reasons and return-to-unfinished controls | [升級最後摘要與略過理由](upgrade_summary+_zh.md) | [Final Upgrade Summary and Skip Reasons](upgrade_summary_en.md) |
| Complete upgrade categories, individual acknowledgement, Added drafts and hidden-pending validation | [升級技術完整分類與逐項審核](upgrade_review+_zh.md) | [Complete Upgrade Technique Review](upgrade_review_en.md) |
| Complete paired upgrade content, checked version-page links and target annotation editing | [升級內容並排比較與目標註記](upgrade_content+_zh.md) | [Upgrade Content and Target Annotation Editing](upgrade_content_en.md) |
| Explicit one-to-many tactic destinations, per-destination editing and reviewed field conflict resolution | [一對多 Tactic 搬移與衝突審核](upgrade_mapping+_zh.md) | [One-to-Many Tactic Migration and Conflict Review](upgrade_mapping_en.md) |
| Independent enabled states, batch selection and atomic batch annotation editing | [獨立狀態與批次操作](batch_operations+_zh.md) | [Independent States and Batch Operations](batch_operations_en.md) |

These guides describe native desktop formulas, full-matrix calculations, per-property inheritance, family aggregates and SVG/XLSX exports, and explain exchange with the official ATT&CK Navigator. Formulas support bounded scalar arithmetic, comparisons, boolean operators, conditional expressions and the documented mathematical functions; they do not execute the entire mathjs language.

Documentation workflow: add the operating guide and its examples here, maintain equivalent Chinese/English versions, update this index, and link the index from the project README. Use project-relative example locations rather than a specific user's computer paths. Describe actual file inputs/outputs and progress wherever a guide includes file operations.

For installation and startup, see the [project README](../README.md).
