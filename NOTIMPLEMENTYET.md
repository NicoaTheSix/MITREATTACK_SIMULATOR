# 尚未實作／尚未完全對齊的功能

這是 **Fusion Studio** 對照官方 MITRE ATT&CK Navigator 的追蹤清單，盤點日期為 **2026-10-19**。實際操作與程式流程見 [README.md](README.md)，雙語手冊見 [manual/README.md](manual/README.md)。保留固定 ID、來源與驗收條件，避免每次比較重新把已完成功能算成缺項。

## 比較基準及狀態

- 官方 Latest 目前指向 **Navigator v5.3.2**，release commit 顯示 `76bf61f`：[官方發行頁](https://github.com/mitre-attack/attack-navigator/releases/tag/v5.3.2)。交換格式基準為 [Layer 4.5](https://github.com/mitre-attack/attack-navigator/blob/master/layers/spec/v4.5/layerformat.md)。程式版本、Layer 格式與 ATT&CK 資料版本須分開看。
- 本次讀取的官方文件／程式多為 **master**；該分支仍有 release 之後的提交。以下標示 master 的細節，表示主線程式存在該能力，**不代表已逐項證明 v5.3.2 都具有**。初次盤點未能取得相同路徑的 release-tag 原始碼；後續 NAV-018～020 已取得並記錄 v5.3.2 的 package、公式 service、Gradient、ViewModel、TechniqueVM 與 tabs 來源雜湊，用於這三項的固定對照。其他路徑精確釘版仍列 CHECK-008，不把 master 日期當發行日期。
- **未實作**：沒有完整入口與資料路徑；**部分實作**：有基礎但缺列出的細節；**實作中**：本輪準備開發，尚未完成驗證；**待核實**：證據不足，不當成確定缺項；**桌面替代／範圍差異**：須依桌面產品決定，不照搬瀏覽器架構。
- 每項程式、驗證、README、中英文手冊完成後才改為「已完成」，並記錄測試產物。清單完整度限於本次讀取的官方文件／程式及本機檔案，不包含未發行 PR 或逐像素一致性承諾。本機證據是盤點時狀態，同一工作階段可能隨實作更新。

## 已完成，不再列為缺項

Enterprise／Mobile／ICS、歷史版本、平台聯集、Flat／Side／Mini、四種排序、名稱／ID 開關、Tactic 背景、獨立 Enabled、批次選取／註記、跨 Tactic／家族／visible-only 偏好、TTP Description／Data Sources／Detection Strategy 搜尋、Groups／Software／Mitigations Description 搜尋、全域與個別父技術展開保存、Ctrl／Cmd／Shift 點選、手動色、透明漸層與六組預設、分數與四種彙總、Links／Metadata／來源 Notes、有限純量公式與屬性繼承、版本比較與審核式搬移、URL／自訂 Bundle／Collection Index、Navigator JSON 陣列讀取、單層及全部開啟圖層 JSON 匯出、SVG 進階設定／預覽、單層及多工作表 Excel、Studio Open／Save／Save As／未存檔提醒／復原、來源 STIX 與本機 TAXII envelope 懸停預覽及複製。

特別釐清：`main.py::export_all_layers` 與 `navigator_integration.py::export_layers` **已存在**；不能再說缺少全部圖層 JSON 匯出。`navigator_visuals.py::COLOR` 已允許漸層與 Legend 的 `#RRGGBBAA`，不能泛稱缺少透明色。TAXII envelope 複製是本機包裝，**不是 TAXII 伺服器連線**。

**已完成：NAV-001～026、NAV-030，共 27 項。** 本輪完成 NAV-026；下方保留固定 ID 與驗收範圍供追溯，不再當成待辦。其餘 **8 項**仍分別標示未實作／部分實作／桌面範圍差異，另外保留 8 項待核實與 7 項非 Navigator 產品待辦。完整升級審核見[中文手冊](manual/upgrade_review+_zh.md)／[英文手冊](manual/upgrade_review_en.md)，並排內容與目標編輯見[中文手冊](manual/upgrade_content+_zh.md)／[英文手冊](manual/upgrade_content_en.md)，一對多映射與衝突見[中文手冊](manual/upgrade_mapping+_zh.md)／[英文手冊](manual/upgrade_mapping_en.md)，最後摘要與理由見[中文手冊](manual/upgrade_summary+_zh.md)／[英文手冊](manual/upgrade_summary_en.md)，SVG 主題見[中文手冊](manual/svg_themes+_zh.md)／[英文手冊](manual/svg_themes_en.md)，SVG 紙張與方向見[中文手冊](manual/svg_paper+_zh.md)／[英文手冊](manual/svg_paper_en.md)；純量公式見[中文手冊](manual/layer_score_formulas+_zh.md)／[英文手冊](manual/layer_score_formulas_en.md)與[固定參考測例](scripts/formula-reference/README.md)。自訂領域見[中文手冊](manual/custom_domains+_zh.md)／[英文手冊](manual/custom_domains_en.md)與[可載入範例](manual/examples/README.md)，自訂來源取得見[來源手冊](manual/custom_data_url_import+_zh.md)，多圖層開啟見[開啟手冊](manual/navigator_bundle_import+_zh.md)，JSON 註記匯出見[匯出手冊](manual/json_annotation_export+_zh.md)，來源選取見[批次操作手冊](manual/source_relationship_selection+_zh.md)。完成本組不代表全部 Navigator 功能已對齊。

## P1：搜尋、選取與視覺控制

### NAV-001 — 來源搜尋的欄位開關

- **狀態：已完成（2026-10-19）。** `selection_workspace.py` 提供獨立 Source search fields，`ttp_search.py` 依選定欄位投影，側欄所有 library 與矩陣八種來源一致；至少一欄，舊檔預設三欄。設定存入每圖層 `x_ttp_studio_source_search_fields`，重開／復原保留。
- **要補：** Groups／Software／Mitigations 可選 Name／ID／Description，至少一欄；側欄與可輸入來源選單一致；設定保存還原；TTP 專用控制不得漏到 library。
- **驗收：** Description 專有字只在該欄開啟時匹配；ID-only／Name-only、空格、大小寫、無結果、重開、舊檔預設均測試，不改變選取。
- **依據：** [官方搜尋元件（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/search-and-multiselect/search-and-multiselect.component.ts)。

### NAV-002 — 已註記子技術的數量

- **狀態：已完成（2026-10-19）。** `attack_matrix.py::family_label`／`matrix_presentations.py` 在 Flat／Side 收合時顯示註記數及映射總數，展開後保留總數；三版面 Tooltip 可讀註記數，Mini 維持小格。計數包含目前平台／Tactic 家族內隱藏的 Disabled，不受指示線開關影響；Notes／零分算，divider／選取標記／展開旗標不算。SVG／Excel 保持既有標籤與集合，不另增加列或計數。
- **要補：** 父項標籤／tooltip 顯示逐 Tactic 的「註記子數／總數」；定義平台、隱藏 Disabled、Notes、展開旗標與 Studio 選取 metadata 的計數邊界。
- **驗收：** 加註／清除即更新；零分算註記，純 divider／內部選取標記不算；不同 Tactic 可不同數量；三版面與匯出不重複計數。
- **依據：** [官方更新紀錄](https://github.com/mitre-attack/attack-navigator/blob/master/CHANGELOG.md)、[ViewModel（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/classes/view-model.ts)。

### NAV-003 — 三種背景色獨立開關

- **狀態：已完成（2026-10-19）。** Layer settings → Colors / indicators 分別控制三種背景，`LayerAppearance.cell` 依手動→啟用彙總→啟用原始分數回退；Disabled 保持暗色，設定不刪資料。Overlay 各來源依自己的背景開關貢獻；偏好使用可保存的原生延伸欄位。
- **要補：** manual background、original score、aggregate score 各自開關；定義回退優先序；只改顯示、不刪原註記；Disabled 仍依規則顯示。
- **驗收：** 全部開關組合、零分、無分數、透明度、Overlay、清色、保存還原、SVG／Excel 一致。
- **依據：** [官方 `customize_features`](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/assets/config.json)。

### NAV-004 — Comment／Metadata／Links 指示線各自設定

- **狀態：已完成（2026-10-19）。** 三類各有開關與 RGB 色碼，Notes 歸 Comment，同色合併提示線。`indicator_style` 與 `marker_colors` 共用於三版面、SVG、單／多層 Excel；Overlay 使用作用中圖層的指示線偏好。保留舊版 Comment／Metadata 黃、Links 藍預設；這與官方 master config 的 Metadata 紫色預設不同，但已可自行設定。
- **要補：** 三類獨立顯示／顏色、Notes 歸屬規則、多提示同時顯示；保存設定，不改資料內容。
- **驗收：** 逐項清除、三類共存、無背景色、Disabled、Mini、Overlay、SVG／Excel 均可辨識且無殘線。
- **依據：** [官方 indicator 顏色與 underline 設定](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/assets/config.json)。

### NAV-005 — 技術右鍵的完整選取指令

- **狀態：已完成（2026-10-19）。** 技術右鍵加入只選／加入／移除／反選、本 Tactic 全選／取消，以及矩陣全選／取消／反選／已註記／未註記；沿用既有偏好與平台範圍。僅分組父項維持不可選，右鍵不改勾選。
- **要補：** 只選這項、加入、移除、反選、全選、全不選、已註記／未註記、本 Tactic 全選／取消；使用既有跨 Tactic／家族／可見偏好。
- **驗收：** 已選／未選、結構父節點、收合／篩選、跨 Tactic 正確；右鍵本身不意外清除其他選取。
- **依據：** [官方右鍵選取操作](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#selecting-with-the-mouse)。

### NAV-006 — View technique／View tactic 網站入口

- **狀態：已完成（2026-10-19）。** 右鍵提供原生 View technique details，並從點擊技術／目前 Tactic 的確切 external reference 提供 Open reference；缺合法 HTTP(S) 網址就不顯示該入口。使用者點擊才開系統瀏覽器並顯示兩階段結果，不推測自訂或歷史來源網址。
- **要補：** 取確切點擊物件的 external reference，正確處理子技術、Tactic、歷史／自訂資料及缺少 URL；不沿用上一項 URL。
- **驗收：** 三 Domain、子技術、無來源、無 Tactic 都把正確 URL 傳給系統瀏覽器，缺資料時停用或提示。
- **依據：** [官方右鍵操作](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#selecting-with-the-mouse)。

### NAV-007 — 自訂右鍵網址模板

- **狀態：已完成（2026-10-19）；相依 NAV-006。** `context_templates.py` 提供原生每圖層的 Label／URL／sub-technique URL 編輯、官方替換參數、解析後 URL Tooltip 及點擊開啟。值作 URL 編碼，缺父／Tactic 停用，未知／不成對 placeholder、動態主機、非 HTTP(S)／帳密會拒絕儲存。存於 `x_ttp_studio_context_menu`，不修改上游 config.json；全組織設定仍屬 NAV-033／034。
- **要補：** label、URL、subtechnique_url；替換技術／Tactic／父技術／子技術的 ATT&CK ID、STIX ID、名稱 slug、suffix；新增／刪除／測試／保存，不執行任意程式。
- **驗收：** 特殊字元編碼、未知 placeholder、缺父／Tactic、無效協定、取消、重開正確；使用者點擊才開網址。
- **依據：** [官方模板參數](https://github.com/mitre-attack/attack-navigator#adding-custom-context-menu-options)。

### NAV-008 — 全部來源搜尋結果一次加入／移除

- **狀態：已完成（2026-10-19）；相依 NAV-001。** 側欄與矩陣皆有 Add all results／Remove all results、來源／去重技術／映射 Tactic 數；`change_sources_ttps` 先驗證完整來源集合，再一次套用聯集及選取偏好。側欄限作用中文件 Domain，矩陣限當前類型；空查詢取全部支援來源，精確選中單項則矩陣批次限該項。空結果不變更，無效或過期資料集整批拒絕；完成訊息列實際變動格子數。無額外確認視窗，關閉／取消搜尋不執行選取。
- **要補：** 取得目前來源查詢結果，計算技術聯集後一次 Add／Remove，顯示來源數、去重技術數、Tactic 影響。
- **驗收：** 重疊去重、空結果、exact dataset、visible-only／家族／跨 Tactic 與取消一致。
- **依據：** [搜尋元件 `selectAll`／`deselectAll`（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/search-and-multiselect/search-and-multiselect.component.ts)。

### NAV-009 — Asset 作為選取來源

- **狀態：已完成（2026-10-19）；master 已確認，release-tag 歸屬仍依 CHECK-008 核實。** `ttp_sources.py` 反向索引有效 technique `targets` asset，加入矩陣 Asset、來源結果聯集及原生詳情表／Add／Remove。拒絕 Asset→Technique 的反向錯誤邊及 uses 代替 targets；已用真實 ICS 與三 Domain fixture 對照。
- **要補：** 依實際 Asset 關聯建 exact-catalog 索引，加入來源 picker／Details 批次操作；不靠名稱推論。
- **驗收：** ICS／自訂 fixture、無關聯、停用關聯、跨版本隔離與 Add／Remove 往返。
- **依據：** [Asset 類別（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/classes/stix/asset.ts)、[來源元件](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/search-and-multiselect/search-and-multiselect.component.ts)。

### NAV-010 — Detection Strategy 作為選取來源

- **狀態：已完成（2026-10-19）；master 已確認來源操作。** 矩陣 Detection Strategy、Detections 詳情與結果批次使用有效直接 detects；同名不同 ID 不混淆，沒有策略的歷史版本維持空列表。原 TTP Detection Strategy 搜尋仍獨立存在。
- **要補：** 顯示策略 active detects 對應、Add／Remove，配合 NAV-008 作來源結果聯集。
- **驗收：** 同名不同 ID、revoked／deprecated、無策略歷史版本、不同 Domain／dataset 不誤連結。
- **依據：** [DetectionStrategy 類別（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/classes/stix/detection-strategy.ts)、[來源元件](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/search-and-multiselect/search-and-multiselect.component.ts)。

### NAV-011 — Data Source／Component 結果分組及選取

- **狀態：已完成（2026-10-19）。** 矩陣提供 Data Component／Data Source；元件標籤依真實 parent ref 顯示 Source : Component，碰撞加 STIX ID。元件支援舊直接 detects 及新 Strategy→Analytic→Component 明確參照，Data Source 取所屬元件聯集。Detections 新增 Data Sources、詳情表／來源連結及 Add／Remove；衍生映射與原始邊分開標示，保留 route refs。舊版只有字串、沒有可解析物件的資料來源仍供 TTP 搜尋，不靠名稱虛構來源；另列的來源懸停高亮 NAV-012 現已完成。
- **要補：** 舊 Data Source: Component 及新資料格式的分組、關聯技術、來源頁連結、單組／全部結果操作。
- **驗收：** 新舊 release、重複名稱、無映射、撤銷關聯、直連／間接規則清楚，不回填其他版本資料。
- **依據：** [搜尋元件 `stixDataComponents`（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/search-and-multiselect/search-and-multiselect.component.ts)。

### NAV-012 — 懸停來源結果時預覽矩陣關聯

- **狀態：已完成（2026-10-19）。** `source_preview.py` 監聽矩陣下拉／完成清單及側欄的實際 MouseMove，依 STIX ID 查同一 catalog 映射；`attack_matrix.py`／`matrix_presentations.py` 只在畫面繪製青色外框。側欄有 Show matrix preview，可保留分類／查詢並開矩陣；hover 本身不切頁。實線為實際相關格子，虛線父項提示可顯示但收合的相關子項，不新增父技術／不自動展開。範圍為平台內實際映射 Tactic，不受家族／跨 Tactic／visible-only 選取偏好擴張，原本搜尋／Hide disabled 仍控制可見性。
- **完成邊界：** leave、popup hide／Escape、鍵盤瀏覽、滾輪、查詢／分類、矩陣篩選重建、文件／資料集切換及隱藏／退出皆清除；owner 隔離避免另一視窗遲到的 leave 清掉新預覽。空結果／其他 Domain 不沿用舊高亮。三版面及 Overlay 保留原有色彩／選取／註記／dirty／展開與原始畫面像素；SVG／Excel／JSON／CSV／復原不含暫時狀態。來源事件監聽器先判斷事件類型再存取 viewport，已修正 Qt 原生銷毀階段的非法存取，並加入子程序退出回歸。
- **要補：** hover／leave 獨立 highlight，不更改選取／分數／顏色／dirty；家族與跨 Tactic 高亮規則明確。
- **驗收：** 快速移動、關閉選單、切文件、無關聯、Overlay 都完全還原且無殘色。
- **依據：** [搜尋元件 `mouseEnter`／`mouseLeave`（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/search-and-multiselect/search-and-multiselect.component.ts)。

### NAV-013 — Campaign／Asset 等其他來源的 Description 搜尋

- **狀態：已完成（2026-10-19）。** 全部 library 葉項共用選定來源欄位，包含 Campaign／Asset；八種矩陣來源完成清單亦支援 Description。NAV-009～011 現已另外完成來源選取，Analytics 仍僅供瀏覽。
- **要補：** 其他有描述的來源類別一致使用選定欄位；瀏覽能力不能當成描述搜尋已完成。
- **驗收：** 各類描述專有字／空描述／同名／欄位開關與 exact catalog 測例。
- **依據：** [來源搜尋 `stixTypes`（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/search-and-multiselect/search-and-multiselect.component.ts)。

## P2：格式交換與公式

### NAV-014 — JSON 可見註記輸出與隱藏註記提醒

- **狀態：已完成（2026-10-19）。** `json_annotation_export.py` 凍結實際矩陣邏輯格子，解析全域／Tactic 註記；`json_export_dialog.py` 在單層／全部開啟圖層 Navigator JSON 匯出提供每次預設不勾選的「只匯出可見技術的註記」。逐層顯示隱藏但已修改的技術／Tactic 格子數、不重複技術 ID 數及唯讀明細，包含未知 ID／無映射列。預設保持 `document_layer` 完整 payload；原名稱、註記、選取、儲存基準、dirty 不變，成功單層匯出只記住交換檔名／格式。
- **完成邊界：** 平台聯集／未知平台投影、搜尋暫時展開、Hide disabled、收合子技術、結構性父技術、Flat／Side／Mini 均驗證。作用中用目前矩陣，不受捲動、分頁顯示、填色／提示開關或 hover 影響；其他層用各自保存的平台與展開，不套用作用中搜尋。只輸出可見時，全域註記拆為明確 Tactic 列，隱藏已選取項目只保留 Studio 納入標記，選取範圍仍精確；圖層屬性仍完整，因此不是機密資料去識別工具。Studio JSON／CSV／復原／SVG／Excel 規則不變。取消不寫檔，失敗保持舊目標並清暫存；選項不持久化。
- **驗證證據：** [專項報告](artifacts/json-annotation-export/audit.json) 124 項；Navigator IO 64、圖層 69、Studio lifecycle 104、Navigator controls 97，共 458 項通過。舊 Navigator／Layers 固定 v19.2 測例使用 `artifacts/*-nav14-v19.2-pointer.json`，不變更目前 v20.0 指標；舊 UI 測試改用具名顏色動作並接受新增匯出檢視。專項原生截圖與範例位於 `artifacts/json-annotation-export`，回歸記錄為 `artifacts/audit_*-nav14-regression.log`。
- **要補：** 隱藏但修改的技術數提醒，選擇完整或只匯出可見註記；區分 Studio 選取與 Navigator 註記列，不默默遺失資料。
- **驗收：** 平台／Disabled／收合／搜尋／部分 Tactic 計數正確，預設完整保留，源圖層不變。
- **依據：** [ViewModel `modifiedHiddenTechniques`／`serialize`（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/classes/view-model.ts)。

### NAV-015 — 多圖層 JSON 一次完整開啟

- **狀態：已完成（2026-10-20）。** `ImportLayerDialog` 提供預設全選的 1–20 層清單、全選／取消全選、逐層 Domain／版本／資料集／錯誤及技術預覽。每層獨立保存選取規則；已記錄版本固定，未記錄版本可個別選擇。`navigator_import.py` 自動解析確切已載入／快取的官方版本與 SHA-256 自訂 Bundle；只有 URL 時要求唯一相符已載入來源／版本／Domain。按 Load selected versions / Preview 可明確準備缺少官方版本，不更動官方指標；缺少／不明確自訂來源逐列阻擋，不改用官方資料。
- **完成邊界：** 任一勾選圖層未就緒時整批不能開啟，只有明確取消勾選才排除；全部草稿在背景驗證後，由 `main.install_imported_documents` 一次加入，依原陣列順序並啟用第一個新分頁。同名保持獨立 UUID，既有文件不變；50 份文件上限整批檢查，插入分頁失敗回滾全部新增項目。取消延後讀檔／解析／草稿、格式壞一層、缺版本／來源均不留下部分安裝。未知技術列保留註記並統計，不自動選取；官方低於 v4 的 Navigator 來源預覽即阻擋，自訂版本不套用該官方歷史限制。內嵌自訂 URL 引導取得已於 NAV-016 完成，詳見下一項。
- **驗證證據：** [專項報告](artifacts/navigator-bundle/audit.json) **93 項**，涵蓋真實混合官方 v20.0／v11.3 與自訂 v19.2／v20.0、UTF-16、全選／子集、個別版本／規則、同名、自訂快取雜湊、URL 不明確、取消、整批回滾、Studio／Navigator／Session 往返及指標保持。Navigator IO 64、圖層 70、進階／自訂來源 138、NAV-014 124，共 **489 項**通過；舊固定 v19.2 測例用 `artifacts/*-nav15-v19.2-pointer.json`，不切換目前資料版本。截圖、範例與報告在 `artifacts/navigator-bundle`，記錄為 `artifacts/audit_*-nav15-regression.log`。
- **要補：** 陣列多選／全選，逐層處理 Domain／version／customDataURL，整批安裝，失敗不默默少層。
- **驗收：** 混合 Domain／版本、同名、壞一層、自訂來源、取消與逐層進度／原子安裝。
- **依據：** [官方 Tabs 載入（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/tabs/tabs.component.ts)。

### NAV-016 — customDataURL 的連貫解析流程

- **狀態：已完成（2026-10-20）。** `ImportLayerDialog` 加入「解析自訂資料…」，由 `custom_data_dialog.py`／`custom_data_import.py` 在同一匯入流程內取得網址、選本機 Bundle／快取或選 Collection Index 版本。轉址後來源、預期／實際雜湊、領域／版本、輸出快取與選取／未解析統計皆可檢視；不自動下載內嵌網址。
- **完成邊界：** 本機相對參照依 JSON 目錄，遠端相對參照依轉址後的圖層／Index 網址。HTTP(S) 轉址驗證、20 秒 socket timeout、128 MiB／200,000 物件／1,000 Index 選項上限；格式錯誤、錯版本／領域或快取檔名與實際雜湊不符均拒絕。內容變更預設不能接受，須明確確認取代；URL-only 已解析來源也以其確切雜湊比較。接受才快取並綁定該圖層，保留其他圖層來源、原輸入、官方指標及原雜湊快取；註記不遺失，未知技術保留未解析列。記錄確切 digest 與來源／取代同意，Studio、Navigator、工作階段往返保留。取消及關閉程式會中止並等待背景來源工作，延遲結果不綁定、不開啟部分圖層；已完成有效快取可能保留。跨版本搬移仍走升級審查，自訂 Domain 擴充已於 NAV-017 完成。
- **驗證：** `audit_custom_data_url.py` **66 項通過**；隔離本機 HTTP 測轉址／迴圈／404／格式與大小限制、相對 URL、Index 明確選擇、雜湊變更確認、快取／取消／關閉程式、多層獨立來源及 Studio／Navigator／復原。既有回歸：Bundle 93、Navigator 64、Layers 70、Advanced 138、JSON Export 124、Lifecycle 113，合計本輪 **668 項**。報告／截圖在 `artifacts/custom-data-url/`，記錄在 `artifacts/*nav16*.log`，雙語手冊與 README 同步。
- **驗收：** 失效 URL、redirect、過大 Bundle、快取、來源改變與取消不載錯圖層。
- **依據：** [Tabs `newLayerFromURL`（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/tabs/tabs.component.ts)。

### NAV-017 — 自訂 Domain 與擴充資料模型

- **狀態：已完成（2026-10-20）。** `domain_model.py` 提供資料集範圍內的 DomainDefinition／CatalogRecord；Bundle 頂層 `x_ttp_studio_domains` 分別設定 ID、顯示名稱、Kill Chain 及外部 ID 來源。未知領域只有單一不歧義來源／鏈時可推導，否則須明確設定。自訂外部 ID 支援有界識別字串；未另設來源的官方領域維持官方規則，全域官方清單不變。
- **完成邊界：** SourceDialog／檔案右鍵領域選單／側欄／矩陣／來源關聯與搜尋／註記、批次、公式、選取比較／審閱搬移／Studio、CSV、Navigator、SVG、Excel、復原皆接入同一模型。多 Matrix 依原順序合併 Tactic 首次出現的有序聯集；拒絕空／壞參照及未覆蓋的有效技術 Tactic，不再只用第一份。外部 ID 在同領域不能衝突；同版本／同領域 ID 但不同雜湊完全隔離，共用 STIX 物件可分別解析來源及鏈，明確範圍父子關係可各自保留。Studio／Navigator 記錄的領域定義須符合確切 Bundle；原始 STIX／TAXII JSON 不含衍生 Python 檢視資訊。需要 ATT&CK 相容技術／Tactic／Matrix 與既有關係，不宣稱通用 STIX 圖編輯；沒有新增單一 Matrix 篩選器。官方 SDK 只驗證替代副本的共通 Layer 結構，原 Domain／ID 不改寫，接收工具仍需支援相應映射。
- **驗證：** `audit_custom_domains.py` **77 項通過**，包含可直接載入的 `manual/examples/custom_domain_bundle.json`、同版本不同來源、推導／明確設定、共用物件及各領域父項、ID／Matrix 錯誤、原生 UI 與中英文 Manual、批次／公式／選取比較／審閱搬移、三種往返及 SVG／Excel。來源取得 68、Bundle 93、Advanced 138、Source Selection 1219、Lifecycle 113、Batch 74、JSON Export 124，加上專項共 **1906 項通過**。報告／截圖在 `artifacts/custom-domains/`，回歸在 `artifacts/*nav17*.log`。82 份 Python 語法、文件／範例連結與翻譯鍵檢查通過；README、雙語手冊、範例說明與程式內索引同步。
- **驗收：** 非三大 Domain 最小 Bundle 往返、同版本來源隔離、多 Matrix 行為及 ID 衝突。
- **依據：** [Tabs.validateInput](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/tabs/tabs.component.ts)、[DataService](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/services/data.service.ts)。

### NAV-018 — 更多有限純量公式相容項

- **狀態：已完成（2026-10-20，經確認的有限純量子集）。** 新公式視窗預設 Navigator scalar，提供 Studio scalar 保留先前算術；Python API 預設仍為 Studio。`scalar_math.py` 與 `score_expression.py` 新增 pi／e／tau／phi／true／false、三角／反三角／雙曲／反雙曲、atan2、log2／log10／log1p／expm1、cbrt／sign／fix／mod。Navigator 模式比照官方整式轉小寫、比較容差、相鄰連續比較與短路、中綴 mod、負數／零除數取餘及遠離零捨入，精度 0–15。Studio 保留 round／not／%／精確比較規則，並新增區分大小寫的 nthRoot；官方轉小寫後的 nthroot 未定義，不冒稱為 Navigator 相容。圖層 e 優先於自然常數，exp(1) 可避免歧義。
- **要補：** 先建官方實際可返回有限實數／布林的對照，再按需增加常數、函數、運算子；pi/e、三角、mod/nthRoot、大小寫、chained comparison 等均先取 golden 結果。
- **驗收：** 同來源逐格與官方比對，每項正常／邊界／錯誤測例，保留運算量限制。不要求 assignment、任意執行、Matrix／Unit／Complex／物件等全部 mathjs：官方也僅接受 number／boolean。
- **完成證據：** 固定 Navigator v5.3.2 來源與 mathjs 15.2.0，121 式 × 3 組同值來源，共 363 筆 golden（270 筆有限結果另經完整逐格圖層計算），專項 971 項通過；舊進階公式 127、分數／彙總／匯出 87、自訂 Domain 77，共 1262 項通過。語法欄、背景失敗重試、來源不變、Studio／Navigator／復原與舊紀錄保存均已驗證。保留 512 字元／128 token／24 層／±1e300／指數上限與 allowlist，未知語法、非有限／非實數結果拒絕。報告：`artifacts/formula-compatibility/audit.json`；重現見 [reference README](scripts/formula-reference/README.md)。**NAV-019 缺值／範圍與 NAV-020 自動漸層均已完成**；本項不是整套 layerOperation 或全部 mathjs 語法的相容承諾。
- **依據：** [官方公式服務與型別限制](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/services/viewmodels.service.ts)。

### NAV-019 — 公式的官方缺值／範圍模式

- **狀態：已完成（2026-10-20）。** `calculate_layer(..., mode="navigator")` 與原生 Calculation mode 提供官方缺值／範圍規則；預設保留 Studio。Navigator 模式固定 Navigator scalar，先做空變數常數／短路探測，成功就初始化所有有效映射格子；否則逐 Technique／Tactic 使用參照來源的分數聯集，部分缺分補零、全部缺分略過，真正零分及停用來源的既有分數仍參與。勾選、平台／搜尋／隱藏／收合不縮小範圍；未使用或只供繼承的來源不增加分數目標。未評分結果預設啟用，明確 Enabled 繼承可覆蓋；允許合法空結果。
- **要補：** 保留 Studio 模式，新增明確 Navigator 相容模式；規範 disabled 但有分、部分缺分、全部缺分、常數與逐 Tactic。
- **驗收：** 同一來源與公式，逐 technique/tactic 比對；a+b 單例不代表全部相容。
- **完成證據：** `generate-scope.cjs` 檢查固定 v5.3.2 官方 service 的 SHA-256，移除 TypeScript 註記後執行原函式，搭配有限模型 stub／載入後常數初始化及 mathjs 15.2.0，產生 31 案例／124 個逐格 golden。專項 `audit_formula_scope.py` 401 項通過：來源不變、逐 Tactic、列順序覆寫、常數 e／來源 e、空結果、繼承、失敗／取消、三官方 Domain、自訂 Domain、介面切換／繁中／小視窗捲動及 Studio／Navigator／復原／舊紀錄保存。原有純量相容 971、公式進階 127、分數／聚合／匯出 87、自訂 Domain 77 也通過，共 1663 項；報告 `artifacts/formula-scope/audit.json`。`x_ttp_studio_formula` 保存 mode／實際 scope／missing／evaluation，缺 mode 的舊結果維持 Studio 意義而不重算。原生計算限於有效映射格子，來源未解析列保留；有限數值／語法限制不放寬。**NAV-020 自動漸層已完成**，不宣稱整個 Angular UI／全部 mathjs／所有 layerOperation 行為一致。
- **依據：** [固定 v5.3.2 官方 layerOperation](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/services/viewmodels.service.ts)。

### NAV-020 — 公式結果的自動漸層模式

- **狀態：已完成（2026-10-20，自動初始化政策）。** Formula and scope 的 Automatic gradient mode 提供 Follow calculation mode／Studio／Navigator；預設跟隨計算模式。Navigator 使用官方紅／黃／綠，結果有範圍時採實際 min/max，恰為 0–1（可含小數）則採 #ffffff00 → #66b1ffff；常數、單一／同分及無結果保留官方 0–100 預設。不將近零誤判為零。Studio 保留來源配色及舊範圍政策；指定 gradient 來源完整保留原色／上下限／透明度，優先於自動政策。手動色及停用顯示沿用原規則；分數、選取與來源不變。
- **要補：** 在相容模式使用結果實際範圍及二元色階，顯式繼承漸層時尊重指定。
- **驗收：** 正／負／二元／常數／無結果／顯式繼承的色階與分數都對照。
- **完成證據：** `generate-gradient.cjs` 驗證固定 v5.3.2 service／Gradient 來源雜湊，使用固定 TypeScript 5.8.3、mathjs 15.2.0、tinycolor2 1.6.0、tinygradient 2.0.1，實際執行官方方法及 Gradient 類別，產生 24 組漸層／96 逐格 golden。專項 335、缺值／範圍 401、純量 971、公式進階 127、分數／聚合／匯出 87、自訂 Domain 77，共 1998 項通過。涵蓋正負／常數／空結果／精確與近似二元範圍、極端有限值、優先繼承、原生矩陣、SVG 像素及 Excel 填色、背景取消、三 Domain、來源／官方指標不變及 Studio／Navigator／復原往返。`gradient_mode` 記錄解析後自動政策，`inheritance.gradient` 優先；舊紀錄缺此欄保留實際儲存漸層，不重算。報告 `artifacts/formula-gradient/audit.json`；重現見 `scripts/formula-reference/README.md`。官方初始化的序列化顏色／上下限已對照，原生連續 RGBA 與官方 100 點 RGB 繪製差異仍記於 CHECK-006，不宣稱逐像素一致。
- **依據：** [固定 v5.3.2 官方公式漸層初始化](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/services/viewmodels.service.ts)、[Gradient 類別](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/classes/gradient.ts)。

## P3：版本升級審核

### NAV-021 — 新增技術與完整分類逐項審核

- **狀態：已完成（2026-10-20）。** `upgrade_review.py` 分類有效來源／目標 ID 聯集及未解析來源註記 ID；`upgrade_review_dialog.py` 提供完整五類技術清單、每類及全體已審／總數、分類／有註記／待審篩選與空狀態。原註記搬移表獨立保留；修改映射會重新要求審核。Added 可先編輯完整註記，加入預設不勾選；空 Added 明確審核記為 Skip added。`migrate_layer` 同時驗證完整技術審核及每列 Copy／Drop，隱藏待審不能繞過，新增草稿不覆蓋衝突純量。Studio／session 保留原圖層封存與完整審核；Navigator JSON 保留審核擴充。取消、失敗及關閉後延遲完成不安裝部分結果。分類按 ID 互斥；新替代目標亦有獨立 Added 列，歧義 revoked-by 不自動猜測。Changed 涵蓋任一 STIX 欄位變化（含時間戳），Unchanged 預設已審。
- **要補：** Added／Changed／Removed／Replaced／Unchanged 清單，審核新項並可在完成前加目標註記，支援只看有註記。
- **驗收：** 每類總數／已審數／空狀態；新增不自動選取；未審明確阻擋或明確略過。
- **驗證：** 專項 67、Advanced Navigator 138、自訂 Domain 77，共 282 項；固定五類測例、真實 v11.3→v20.0 全部 719 個 ID、原生編輯／取消／失敗／雙語切換及 Studio／session／Navigator 往返。99 份 Python、501 個本地文件連結與 708 個唯一翻譯鍵／占位符檢查通過。報告 `artifacts/upgrade-review/audit.json`，英／中截圖 `review.png`／`review-zh.png`；本機靜態檢查見 `artifacts/nav21-static-checks.json`。流程與範例見[中文手冊](manual/upgrade_review+_zh.md)／[英文手冊](manual/upgrade_review_en.md)。
- **依據：** [官方升級](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#upgrading-a-layer-to-the-current-version)、[LayerUpgrade 程式](https://github.com/mitre-attack/attack-navigator/tree/master/nav-app/src/app/layer-upgrade)。

### NAV-022 — 升級前後完整內容與註記編輯

- **狀態：已完成（2026-10-20）。** `upgrade_comparison.py` 提供可調整空間的雙欄完整內容，技術與來源映射列皆可檢視名稱／描述／Tactic／Platform／精確版本、完整 STIX 與註記；Raw differences 保留原差異。`upgrade_content.py` 使用兩側官方資料集的主版本封存 URL，點擊時背景驗證同版本／技術後才開瀏覽器，404／錯誤／跨版本或最新版轉址不開啟，不把網站主版本當精確 patch；自訂資料與缺記錄停用官方頁面。既有來源列可編輯目標 Comment／Score／Color／Enabled／Links／Metadata，鎖定映射範圍與選取，草稿隨明確重新映射攜帶，修改後重新審核；無來源列的既有目標也能加註而不選取。取消保留上次草稿，結果與編輯補丁隨 Studio／session／Navigator 保存，原圖層與來源封存不變。
- **要補：** 前／後完整技術及註記並排、來源版本頁入口，審核中直接改目標 comment/score/color/links/metadata。
- **驗收：** 名稱／描述／Tactic 變更、舊頁不存在、已撤銷與自訂資料不誤開最新版。
- **驗證：** `audit_upgrade_content.py` 專項 64、NAV-021 分類審核 67、Advanced Navigator 138、自訂 Domain 77，共 346 項通過；涵蓋原生並排、編輯／取消／清除／重新映射、缺頁與錯誤版本轉址、關閉後回應及三種資料往返。102 份 Python、521 個本地 Markdown 連結及 733 個唯一翻譯鍵／占位符通過靜態檢查。報告及雙語截圖在 `artifacts/upgrade-content`，靜態紀錄 `artifacts/nav22-static-checks.json`；版本 HTTP／瀏覽器使用替身驗證，不宣稱已實測所有公開封存可連線。流程與範例見[中文手冊](manual/upgrade_content+_zh.md)／[英文手冊](manual/upgrade_content_en.md)。
- **依據：** [官方 Mapping Annotations](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#mapping-annotations)。

### NAV-023 — 一對多 Tactic 搬移與衝突解決

- **狀態：已完成（2026-10-21）。** `upgrade_mapping.py` 支援每來源列 1～100 個明確技術／Tactic 目標，包含跨技術、任意 Tactic 子集合與個別目標補丁；拒絕重複、失效與同一來源內 All tactics／個別 Tactic 重疊。`upgrade_mapping_dialogs.py` 提供新增／移除目標及逐欄衝突介面，`upgrade_comparison.py` 可切換目標檢視／編輯。衝突可選來源候選、自訂有限 JSON 值或清除欄位，每欄須審核，型別與所有候選先驗證。註解、Links、Metadata 多源去重，內部選取標記不重複；只搬移指定選取範圍。後端以完整貢獻列的 SHA-256 綁定決策，修改映射／註記後舊決策失效；無關、重複、未審或不合法決策不可建立結果。Studio／session／Navigator 保存展開映射、部分選取與 schema 2 衝突紀錄；原檔及來源封存完整保留。新增／移除清單為拖放的桌面等效操作，沒有新增拖曳手勢。
- **要補：** 一源多目標 Tactic、新增映射／拖放等效；多源同目標 scalar 衝突可審核解決，不僅能 Drop。
- **驗收：** 1→1／1→多、Tactic 移除、合併衝突、comment/links/metadata 合併、內部標記不重複。
- **驗證：** 專項 `audit_upgrade_mapping.py` 74、完整分類審核 67、內容／目標編輯 64、Advanced Navigator 138、自訂 Domain 77，共 420 項。涵蓋三 Tactic 子集合、不同目標技術、目標別註記、三來源去重、候選／自訂／清除、未審／過期／無關決策、原生取消／重開／雙語介面、背景預覽鎖定／失敗重試及三種資料往返。產物 `artifacts/upgrade-mapping/audit.json`、`mapping-en.png`／`mapping-zh.png`、`conflicts-en.png`／`conflicts-zh.png`；手冊：[中文](manual/upgrade_mapping+_zh.md)／[英文](manual/upgrade_mapping_en.md)。
- **靜態檢查：** 105 份 Python 語法、543 個本地 Markdown 連結、761 個唯一翻譯鍵及占位符、變更檔案 whitespace 均通過；紀錄 `artifacts/nav23-static-checks.json`。
- **依據：** [Mapping Annotations](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#mapping-annotations)、[ViewModel.copyAnnotations](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/classes/view-model.ts)。

### NAV-024 — 升級分類進度及最後摘要

- **狀態：已完成（2026-10-21）。** 「檢視最後摘要…」以背景工作彙整完整分類的已審／總數／略過數、Copy／Drop、輸出列、選取範圍與衝突狀態。零項、未完成、整類略過與已完成均明示；篩選不縮小分母。略過理由可針對 Drop 來源列及空白 Added 新增註記編輯，支援多列套用、4096 字 Unicode／換行及選填空白；取消回復先前草稿，返回保留，未作用的 Copy 理由不輸出。略過 Added 新增註記不取消映射至該技術的 Copy。
- **提交與返回：** 所有未審確認、無效映射／草稿／名稱及衝突列入未完成表；可雙擊、返回選取或第一項。返回清除分類／註記／待審篩選，定位技術、確切來源列、名稱或目標／範圍／衝突欄位。摘要以輸入指紋阻擋過期提交，後端再次驗證完整計畫。成功建立獨立結果，失敗／取消不安裝半成品，原文件與來源封存不變。
- **保存：** `x_ttp_studio_upgrade.final_summary`（摘要 schema 1、外層 review schema 2）保存來源／目標識別、分類及輸出數、有效略過理由；對應 Drop／Added 審核亦有 `skip_reason`。Studio／session／Navigator 往返保留；未提交的升級視窗草稿不做 session 復原，重載目標或關閉即捨棄。
- **要補（已完成的驗收範圍）：** 各類已審／總數／略過理由；提交前回到未完成項，保留來源與決策。
- **驗證：** 專項 `audit_upgrade_summary.py` 86、映射衝突 74、完整分類 67、內容編輯 64、Advanced Navigator 138、自訂 Domain 77，共 **506 項**。涵蓋完整分母、空分類／全部 Drop、無效／重複／未審／過期決策、理由編輯／上限／多列／取消、原生返回／隱藏列揭露／衝突定位、提交／失敗重試／晚到結果取消、中英文與三種保存往返。報告 `artifacts/upgrade-summary/audit.json`、`artifacts/*nav24*.log`，截圖 `pending-en.png`／`summary-en.png`／`summary-zh.png`；已登錄 Linux runner，本輪未另宣稱原生 Linux 通過。
- **靜態檢查：** 108 份 Python 語法、575 個本地 Markdown 連結與 805 個唯一翻譯鍵／占位符通過，變更檔案 whitespace 通過；報告 `artifacts/nav24-static-checks.json`。
- **文件與流程：** [中文](manual/upgrade_summary+_zh.md)／[英文](manual/upgrade_summary_en.md)、既有升級指南、程式內索引與 README 同步。計算前明示記憶體輸入／無輸出檔，摘要三階段、理由套用兩階段與既有提交三階段皆報進度；檔案操作另列絕對路徑。
- **依據：** [官方升級流程](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#upgrading-a-layer-to-the-current-version)。

## P4：匯出及介面

### NAV-025 — SVG Light／Dark

- **狀態：已完成（2026-10-21）。** SVG 設定新增深色／淺色，預設維持深色、僅套用本次匯出視窗。畫布、標頭、無色格、停用格及 Legend 使用對應配色；手動不透明色／指定 Tactic 色及可讀前景保留。`navigator_visuals.py` 提供唯讀原始 RGBA，`svg_themes.py` 對主題底色合成分數／彙總／每個疊圖來源，保持等權重及零透明度排除。Legend alpha 對實際面板底色合成，淺色加色票邊框與指示襯線；深色 SVG 停用字調亮。三版面皆可用，進階 Mini 保留選取框。圖層 JSON、儲存標記、選取、原生矩陣／程式配色及 Excel 不變。
- **要補（已完成的驗收範圍）：** SVG 獨立主題、透明混色基底、文字／Legend 可讀，不改技術色資料。
- **驗證：** `audit_svg_themes.py` 專項 **146**、進階匯出 **87**、矩陣顯示 **74**、疊圖 **52**、圖層分析 **87**、公式漸層 **335**，共 **781 項**。涵蓋實際 Qt SVG 像素、雙主題三排版、黑白／透明色、文字對比、停用／隱藏、Legend／Tactic、彙總／疊色、Mini 選取框、雙語原生設定、預覽／輸出位元組完全一致、切回深色無殘色、失敗／取消保護原輸出及真實 Enterprise／Mobile／ICS。報告 `artifacts/svg-themes/audit.json`、`artifacts/*nav25*.log`；SVG／PNG 雙主題範例及設定／預覽截圖位於同目錄。
- **靜態檢查：** 110 份 Python 語法、601 個本地 Markdown 連結、810 個唯一翻譯鍵及占位符與變更檔案 whitespace 通過；報告 `artifacts/nav25-static-checks.json`。
- **流程與文件：** [中文手冊](manual/svg_themes+_zh.md)／[英文手冊](manual/svg_themes_en.md)、進階匯出指南、程式內索引、README 及 Linux runner 同步；本輪沒有另宣稱原生 Linux 通過。預覽先報記憶體輸入／無輸出檔並顯示三階段；匯出先列最終／暫存檔絕對路徑，再顯示四階段與實際主題。NAV-026 紙張／方向也已完成，NAV-027 字級控制及 NAV-028 應用主題仍分開待辦。
- **依據：** [官方 SVG UI（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/svg-export/svg-export.component.html)。

### NAV-026 — SVG 紙張尺寸及方向預設

- **狀態：已完成（2026-10-21）。** SVG 設定加入 Custom、US Letter（8.5×11）、US Legal（8.5×14）、11×17／18×24／24×36 英吋及直式／橫式。預設紙張鎖定寬高，依 px／cm／in 換算，後端亦驗證並解析。自訂仍預設 Auto，保留獨立寬高／方向草稿；寬高皆指定時可切換方向交換，任一 Auto 時停用方向；返回 Custom 可跨單位還原。標頭／圖例長度與其他設定保留，採標準實際長度避免累積誤差及單位換算時靜默截短，上限維持每長度 100000 邏輯像素。
- **要補（已完成的驗收範圍）：** 預設轉換與 Custom，保留 header／legend 設定。
- **驗證：** `audit_svg_paper.py` 專項 **266**、SVG 主題 **146**、進階匯出 **87**、圖層分析 **87**、矩陣顯示 **74**，共 **660 項**。涵蓋五紙張×雙方向×三單位的實際 root 尺寸／viewBox／Qt rendering、標準化冪等、自訂／單軸 Auto、內容超界、雙主題三排版、原生鎖定／重複換算／草稿還原／上限／雙語、預覽與檔案完全一致、取消／原子失敗及來源／儲存標記保留。報告 `artifacts/svg-paper/audit.json`、`artifacts/*nav26*.log`；30 份紙張 SVG、原生設定與預覽截圖在同目錄。
- **靜態檢查：** 112 份 Python 語法、627 個本地 Markdown 連結、825 個唯一翻譯鍵／占位符及變更檔案 whitespace 通過；報告 `artifacts/nav26-static-checks.json`。
- **流程與文件：** [中文手冊](manual/svg_paper+_zh.md)／[英文手冊](manual/svg_paper_en.md)、既有匯出／主題指南、程式內索引、README 與 Linux runner 同步。Preview 明示記憶體輸入／無輸出檔並顯示三階段，Export 先列最終／暫存檔絕對路徑並顯示四階段。單位控制值為 px／cm／in，紙張及方向翻譯不改標準 ID。設定僅限本次視窗，不寫圖層；本輪未另宣稱原生 Linux 通過。
- **依據：** [官方 SVG UI（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/svg-export/svg-export.component.html)。

### NAV-027 — SVG 字級、自動適字、溢位警示

- **狀態：部分實作。** 有 font family，DEFAULT_SVG 沒有 fontSize/autofit，基礎 renderer 固定字級折行。
- **要補：** 手動字級、autofit、文字超界提示，不能無聲裁字。
- **驗收：** 長名稱、雙語、極窄輸出與三版面預覽／檔案一致。
- **依據：** [官方 SVG 字型設定（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/svg-export/svg-export.component.html)。

### NAV-028 — 應用程式 Light／Dark

- **狀態：未實作。** main.py 固定深色 stylesheet；官方 Tabs 有 userTheme 路徑。
- **要補：** 全窗／對話框／tooltip／JSON popup／輸入框一致、保存偏好，與 SVG／圖層色分離。
- **驗收：** 切換不改圖層，重開保留，disabled/selection/hover 對比正確。
- **依據：** [Tabs.handleUserThemeChange（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/tabs/tabs.component.ts)。

### NAV-029 — 程式內 Help／版本說明

- **狀態：部分實作（範圍已修正）。** 已有 Info → Manual／F1 雙語手冊、程式內指南／例子、Info 介紹及離線版本歷史，不能再列為缺少 Help。尚缺完整 Studio 自身更新紀錄，以及集中呈現程式版本、Layer 格式、授權與上游來源的完整資訊入口。
- **要補：** 在既有手冊／Info 基礎上補完整 Studio Changelog，以及版本／格式／授權／上游資訊整合；延續離線導覽。
- **驗收：** 移動安裝位置仍找得到相對資源，中英文連結均有效且閱讀不改文件。
- **依據：** [Tabs.openDialog（master）](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/tabs/tabs.component.ts)。

### NAV-030 — Legend 獨立開關與 Clear all

- **狀態：已完成（2026-10-19）。** Colors / indicators → Show matrix legend 可在保留技術色下隱藏 Legend，設定隨文件保存。Legend → Clear all legend items 清草稿，Save 確認／Cancel 還原；保留既有折行顯示及 alpha 色碼。SVG 有獨立的匯出 Show legend 設定，不受矩陣開關覆寫。
- **要補：** 不關技術色即可收合 Legend，整批清除／確認，大量項目可讀。
- **驗收：** 空／大量／alpha、取消、保存還原與其他圖層獨立。
- **依據：** [官方 Legend 操作](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#legend-bar)。

## P5：資料連線、組織配置、分享部署

### NAV-031 — TAXII Collection 讀取

- **狀態：未實作。** read_source 僅讀單份 HTTP／本機 JSON，stix_clipboard 僅本機 envelope。
- **要補：** API root／Discovery／Collection、TAXII2.1 Accept、more/next 分頁、取消／錯誤／快取，形成隔離 catalog。官方列2.0但已預告淘汰，先2.1；2.0另決定。
- **驗收：** 可重現 fixture、跨頁去重／物件版本、空 Collection、失敗不安裝半套資料。本項僅讀取，不授權發佈；認證／權限／秘密管理另定產品要求。
- **依據：** [官方 TAXII 讀取設定](https://github.com/mitre-attack/attack-navigator#loading-content-from-a-taxii-server)。

### NAV-032 — 組織資料來源清單與多 Bundle

- **狀態：部分實作。** 有官方發現、單獨 Bundle／Index；沒有統一管理多 Index、多 Bundle 的持久設定。
- **要補：** 名稱／版本／Domain／URL／本機 paths／enabled；多 Bundle 按 ID+modified 選版、衝突拒絕，隔離官方目錄。
- **驗收：** 來源 union、同版本不同源、物件衝突、離線 cache、刪設定不刪原檔。
- **依據：** [官方 versions.entries.domains.data](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/assets/config.json)、[DataService](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/services/data.service.ts)。

### NAV-033 — 可配置的功能隱藏／白名單

- **狀態：未實作。** 無完整 customize_features/features；NAV-003/004 僅視覺子集。
- **要補：** tabs/header/search/selection/layer settings/export/filters/sorting/color setup/hide disabled/subtechniques/state/score/comment/links/metadata/clear annotations 等群組及子項配置；關控制不刪已載資料。
- **驗收：** 選單／按鈕／快捷鍵／右鍵同步；舊檔註記保留，壞設定可回預設。
- **依據：** [官方 feature 設定樹](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/assets/config.json)。

### NAV-034 — 啟動預設圖層、Banner、可攜配置

- **狀態：未實作。** session recovery 不等於組織啟動配置。
- **要補：** 預設圖層／URL、標語、功能與資料來源設定；定義與 recovery 的優先序；不分享秘密。
- **驗收：** 首次／離線／壞URL／重複檔／未存變更／復原有確定規則。
- **依據：** [官方 default_layers/banner](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/assets/config.json)。

### NAV-035 — Web 客製網址／分享／iframe

- **狀態：桌面替代／範圍差異。** PySide6 沒有 Web 前端、layerURL 分享產生器、iframe。
- **要補：** 決定內嵌官方或獨立網站，再做 layerURL／多層／功能配置、跨來源與敏感資料規則；純桌面可用啟動設定檔替代，不稱 iframe 已實作。
- **驗收：** 分享入口重建相同圖層與設定，失效不載錯，接收連結不靜默上傳／匯出。
- **依據：** [官方客製](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#customizing-the-navigator)、[嵌入](https://github.com/mitre-attack/attack-navigator#embedding-the-navigator-in-a-webpage)。

## 待核實：先取得對照證據，不當成確定缺項

| ID | 精確核實範圍 | 本機證據／下一步 | 官方依據 |
| --- | --- | --- | --- |
| CHECK-001 | manual/header alpha、CSS 色名／短 HEX 支援範圍 | manual/header 限#RRGGBB；gradient/legend已alpha。規格 color:string 不保證全CSS；先用釘版 picker/deserialize 實測再立修補項。 | [TechniqueVM](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/classes/technique-vm.ts)、[Layer4.5](https://github.com/mitre-attack/attack-navigator/blob/master/layers/spec/v4.5/layerformat.md) |
| CHECK-002 | 彙總是否計入 disabled／平台隱藏／跨Tactic／全部unscored | LayerAppearance.aggregate 已有四種彙總，排除disabled；同fixture逐格比對再確認政策差異。 | [ViewModel](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/classes/view-model.ts) |
| CHECK-003 | locale排序、同分tie-break、round/mod/浮點/比較 | NAV-018 已用 mathjs 15.2.0 golden 核對所列純量 round/mod/浮點/比較，明確保留 Studio 差異。locale 排序、同分 tie-break 與未列運算仍待核實，不能因此關閉整項。 | [公式服務](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/services/viewmodels.service.ts)、[ViewModel](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/classes/view-model.ts) |
| CHECK-004 | Layer3.x/4.0–4.4完整預設與升版 | 已接受版本並保留欄位，仍需sample corpus驗證alias、缺attack版、row fallback、空platforms、extensions/dividers；受理版本號不等於全相容。 | [規格目錄](https://github.com/mitre-attack/attack-navigator/tree/master/layers/spec) |
| CHECK-005 | 無tactic與scoped列並存、重複row、未知ID | 本機保留raw並用最後索引顯示；釘版確認拒絕／提示／覆寫政策，再測往返。 | [TechniqueVM](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/classes/technique-vm.ts)、[ViewModel.deserialize](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/classes/view-model.ts) |
| CHECK-006 | Mini/Side分組、符號、空列、SVG/Excel精確資訊差異 | 三版面及符號已存在；不要求Qt/Excel逐像素複製，先測可讀性／資訊遺漏。NAV-020 已對照漸層初始化參數；原生連續 RGBA／官方 100 點 RGB 的中間顏色繪製仍有差異，不能以該項完成宣稱 renderer 完全相同。 | [資料表UI](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/datatable/data-table.component.html)、[SVG UI](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/svg-export/svg-export.component.html) |
| CHECK-007 | 色盤／Legend色票捷徑／hover pin等細節 | 有QColorDialog/Legend/tooltip；先重現官方操作，不把不同控制元件都算缺功能。 | [ViewModel](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/classes/view-model.ts)、[資料表UI](https://github.com/mitre-attack/attack-navigator/blob/master/nav-app/src/app/datatable/data-table.component.html) |
| CHECK-008 | master能力屬v5.3.2或後續 | 取得release commit檔案SHA與diff及runtime版本，補足釘版證據，保留未確認標記。 | [release](https://github.com/mitre-attack/attack-navigator/releases/tag/v5.3.2) |

## 桌面等效與非缺項

- **Sticky toolbar：** 桌面矩陣工具列已在捲動區外固定；無須加一個無作用的網頁pin開關。[官方 toolbar](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#toolbar-controls)
- 瀏覽器相容、CORS、Angular／Docker是Web部署事項，不直接算Qt缺項；需要Web時歸NAV-035。
- Save／Save As／退出／復原已完成；沒有依據把通用STIX authoring、TAXII寫入當Navigator必要能力。
- Undo／Redo、recentfiles、拖放、regex、installer、Linux CI、更新、翻譯、協作等，不因這次比較就宣稱官方有而本機缺；分列產品待辦。

## Studio 產品待辦：非已確認 Navigator 差距

| ID | 待辦 | 驗收方向 |
| --- | --- | --- |
| PROD-001 | General Undo／Redo | 選取／註記／設定交易歷史與版本切換邊界；失敗交易不入列。 |
| PROD-002 | Recent files／拖放 | 僅記成功路徑，遺失提示，拖入仍走驗證，不自動寫檔。 |
| PROD-003 | 復原細節／歷史 | scroll/search/activepanel、checkpoint歷史／清理；不覆蓋外部變更。 |
| PROD-004 | 進階查詢 | regex/Boolean須明確語法、限制、錯誤提示，保留literal模式。 |
| PROD-005 | 來源選取provenance | 某來源移除時保留其他來源共用TTP；現Remove是集合運算。 |
| PROD-006 | 發行／跨平台 | installer/portable、Linux實測/CI、依賴/授權、版本簽章、更新、產品條款。 |
| PROD-007 | 原始模擬器構想 | 語言偵測、模組參數、排序、dry-run、synthetic event/timeline/reports在目前文件產品範圍外，須另定義。 |

## 實作順序與完成紀錄

1. **已完成 NAV-001～007，並完成 NAV-013／030：** 來源欄位、數量、色彩／指示線、右鍵／連結／模板、全部 library 描述搜尋及 Legend 草稿。已驗證三版面、生命週期及匯出。
2. **已完成 NAV-008～012：** 來源結果全集、Asset／策略／元件／Data Source 關聯、追溯與暫時懸停預覽均已完成；不靠名稱推測關聯，不把預覽寫入註記。
3. **已完成 NAV-018～020；接續 CHECK-001～005：** 公式純量、官方缺值／範圍與自動漸層已有固定 golden；繼續核實其他交換相容細節，多圖層整批開啟 NAV-015、customDataURL 引導取得 NAV-016、自訂 Domain／模型 NAV-017 已完成。
4. **已完成 NAV-021～024：** 完整分類、並排內容／版本連結／目標編輯、一對多映射／逐欄衝突，以及最後摘要／略過理由／提交前返回未完成項目均已驗證。NAV-025 SVG Light／Dark 也已完成。
5. **已完成 NAV-025～026；下一階段 NAV-027～029、CHECK-006～007：** 字級／自動適字、應用主題與完整程式版本資訊。NAV-029 的手冊及 Info 基礎已存在，僅補剩餘整合；NAV-030 已先完成。
6. **NAV-031～035：** TAXII讀取、組織來源／啟動；Web分享先選部署架構；持續完成CHECK-008。

每階段先報輸入／輸出絕對路徑，純記憶體操作明示無檔案；讀取／解析／驗證／套用／匯出顯示進度，長作業背景執行，取消／失敗保留原文件。完成一項同步更新所在程式目錄README與雙語手冊，記可重現測試，不以「寫完程式碼」代替驗證。

| 日期 | 範圍 | 狀態／驗證 |
| --- | --- | --- |
| 2026-10-21 | NAV-026 SVG 紙張尺寸與方向預設 | 專項 266、SVG 主題 146、進階匯出 87、圖層分析 87、矩陣顯示 74，共 660 項。五紙張／雙方向／三單位實際 SVG 尺寸與 Qt rendering、Custom 草稿／Auto／鎖定／換算／上限、原生雙語預覽／檔案一致、取消／失敗保護與來源／標記保留均通過。README、雙語新／既有指南、索引與 runner 同步；112 份 Python、627 個本地連結及 825 個翻譯鍵／占位符亦通過；報告 `artifacts/svg-paper/audit.json`、`artifacts/nav26-static-checks.json`；下一階段 NAV-027。 |
| 2026-10-21 | NAV-025 SVG 獨立 Light／Dark 主題 | 專項 146、進階匯出 87、矩陣顯示 74、疊圖 52、圖層分析 87、公式漸層 335，共 781 項。實際像素、雙主題三排版、透明分數／彙總／疊圖、停用／Legend／Mini、原生雙語預覽／檔案一致、取消／原子失敗及來源／儲存標記保留均通過。README、雙語新／既有指南、程式內索引與 runner 同步；另修正 NAV-029 已有 Help／Info 的過時描述。110 份 Python、601 個本地連結及 810 個翻譯鍵／占位符亦通過；報告 `artifacts/svg-themes/audit.json`、`artifacts/nav25-static-checks.json`；下一階段 NAV-026。 |
| 2026-10-21 | NAV-024 升級最後摘要、略過理由與返回未完成項目 | 專項 86 加五組回歸 420，共 506 項通過；完整分類分母、空／全略過結果、全部未完成檢查、理由多列／取消／上限、返回揭露隱藏列及衝突欄位、過期摘要阻擋、失敗／關閉安全與 Studio／session／Navigator 均驗證。README、中英文新／既有手冊與程式內索引同步。108 份 Python、575 個本地連結及 805 個翻譯鍵／占位符亦通過；報告 `artifacts/upgrade-summary/audit.json`、`artifacts/nav24-static-checks.json`；下一階段 NAV-025。 |
| 2026-10-21 | NAV-023 一對多 Tactic 搬移與欄位衝突解決 | 專項 74、完整分類 67、內容編輯 64、Advanced Navigator 138、自訂 Domain 77，共 420 項；105 份 Python、543 個本地文件連結與 761 個翻譯鍵／占位符通過。原生多目標與個別註記、部分選取、逐欄候選／自訂／清除、三來源去重、指紋失效、取消／重開、預覽鎖定／失敗重試、雙語及三種保存往返均驗證。README、雙語新／既有指南與程式內索引同步；報告 `artifacts/upgrade-mapping/audit.json`、`artifacts/nav23-static-checks.json`。下一階段 NAV-024。 |
| 2026-10-20 | NAV-022 升級完整並排內容、版本頁與目標註記編輯 | 專項 64、完整審核 67、Advanced Navigator 138、自訂 Domain 77，共 346 項；102 份 Python、521 個本地文件連結及 733 個翻譯鍵／占位符通過。HTTP／瀏覽器替身驗證同封存連結、缺頁／錯誤版本不開最新版；精確本機快照與網站主版本區別明示。原生中英文比較、目標草稿／清除／取消／重新映射及 Studio／session／Navigator 往返通過。README、雙語新／既有指南與程式內索引同步；產物在 `artifacts/upgrade-content`。下一階段 NAV-023。 |
| 2026-10-20 | NAV-021 完整技術分類與逐項審核 | 專項 67、Advanced Navigator 138、自訂 Domain 77，共 282 項通過；完整分類涵蓋真實 v11.3→v20.0 的 719 個 ID。原生篩選、Added 草稿、取消／失敗／延遲完成、雙語切換與三種保存往返驗證完成。99 份 Python、501 個本地連結及 708 個翻譯鍵／占位符通過靜態檢查。README、雙語新／既有指南及程式內索引同步；報告 `artifacts/upgrade-review/audit.json`、`artifacts/nav21-static-checks.json`。下一階段 NAV-022，NAV-023／024 保留其未完成範圍。 |
| 2026-10-19 | NAV-001～035、CHECK-001～008、PROD-001～007盤點 | 來源／相依／驗收及路線已建立；主線與發行版證據區分，非已確認缺項另外列出。 |
| 2026-10-19 | NAV-001～007、NAV-013、NAV-030 | 程式、README 與雙語操作手冊完成；`audit_navigator_parity.py` 97 項通過，產物在 `artifacts/navigator-parity/`。原生偏好用 x_ttp_studio 延伸保存，官方 Navigator 可能在重新輸出時丟棄。 |
| 2026-10-19 | 既有流程回歸 | Matrix 3104、Selection/Search 99、Visibility/Presets 117、Detection/Interaction 110、Advanced Navigator 138、Matrix Display 74、Export Options 87 項通過；加上新測試共 3826 項。60 份 Python 語法、163 個本地 Markdown 連結與 git diff whitespace 檢查通過。 |
| 2026-10-19 | NAV-008～011 來源批次／關聯 | `audit_source_selection.py` 1219 項通過，包含三 Domain fixture、當前官方快取原始 STIX 獨立對照、舊 v11.3、同名、撤銷／錯誤路徑、過期資料集拒絕、偏好及 Studio／Navigator／CSV／復原。產物：`artifacts/source-selection/`，操作見 README 與新增雙語來源手冊。 |
| 2026-10-19 | 本輪來源流程回歸 | Related TTPs 3442、Matrix Actions 72、Matrix 3139、Selection/Search 99、Navigator Parity 97、Detection/Interaction 110、Visibility/Presets 117、Advanced Navigator 138；加上新測試共 8433 項通過。64 份 Python 語法、199 個本地 Markdown 連結及 git diff whitespace 檢查通過。測試改用實際載入版本及命令名稱，避免舊的 19.2／選單位置假設。 |
| 2026-10-19 | NAV-012 懸停預覽 | `audit_source_preview.py` 123 項通過，程序正常退出；包含獨立原生退出子程序、實際 dropdown/completion/sidebar mouse move、三版面像素還原、收合父項、wheel／Escape／close／文件重建、空與同名結果、資料集隔離、Overlay、隱藏色彩、繁中控制及匯出隔離。README、新增雙語手冊、程式內手冊與索引同步，產物在 `artifacts/source-preview/`。 |
| 2026-10-19 | 懸停階段回歸 | Source Selection 1219、Matrix 3139、Matrix Display 74、Navigator Parity 97，加上新測試共 4652 項通過；Qt viewport 銷毀錯誤有修正前原生失敗／修正後正常退出的可重現子程序測例。68 份 Python 語法、265 個本地 Markdown 連結、翻譯 JSON 唯一鍵與 git diff whitespace 檢查通過。 |
| 2026-10-20 | NAV-016 自訂來源完整取得與檢視 | 專項 66、Bundle 93、Navigator 64、Layers 70、Advanced 138、JSON Export 124、Lifecycle 113，共 668 項通過。涵蓋本機 HTTP 轉址／限制／相對參照、快取、變更確認、取消與退出背景工作、批次獨立來源及三種往返。79 份 Python 語法、文件連結及 644 個翻譯鍵／占位符檢查通過；詳見 `artifacts/custom-data-url/audit.json`、`artifacts/nav16-static-checks.json`。README、雙語新手冊與既有相關指南、程式內索引同步。 |
| 2026-10-20 | NAV-017 自訂 Domain 與擴充資料模型 | 專項 77、來源取得 68、Bundle 93、Advanced 138、Source Selection 1219、Lifecycle 113、Batch 74、JSON Export 124，共 1906 項通過。資料集範圍定義、非官方 ID、共用物件／範圍關係、多 Matrix 聯集、隔離、原生 UI／Manual 與交換／搬移封存均已驗證。原始 STIX 及官方指標不變。82 份 Python 語法、文件／範例連結與 644 個翻譯鍵檢查通過；詳見 `artifacts/custom-domains/audit.json`、`artifacts/nav17-static-checks.json`。README、雙語手冊與可載入範例同步。 |
| 2026-10-20 | NAV-018 更多有限純量公式相容項 | 專項 971（363 筆固定參考、270 筆完整圖層計算）、既有進階公式 127、分數／彙總／匯出 87、自訂 Domain 77，共 1262 項通過。84 份 Python 語法、372 個本地 Markdown 連結、648 個翻譯鍵／占位符、原生繁中公式控制與 Node 語法／diff whitespace 檢查通過。明確保留 Studio 語意並記錄 Navigator scalar 語法；來源與官方指標不變。README、雙語公式手冊、程式內手冊與固定參考工作流程同步；詳見 `artifacts/formula-compatibility/audit.json`、`artifacts/nav18-static-checks.json`。下一階段 NAV-019。 |
| 2026-10-20 | NAV-019 公式的官方缺值／範圍模式 | 專項 401（31 案例／124 逐格 golden）、純量相容 971、公式進階 127、分數／聚合／匯出 87、自訂 Domain 77，共 1663 項通過。85 份 Python、374 個本地 Markdown 連結、653 個翻譯鍵／占位符、繁中模式控制、LF 固定測例、Node 語法及 whitespace 檢查通過。官方缺值／分數聯集、空範圍常數、停用來源分數與舊 Studio 模式分開；五階段進度、來源保留與三種往返均驗證。README、雙語操作／程式內手冊與重現工作流程同步；詳見 `artifacts/formula-scope/audit.json`、`artifacts/nav19-static-checks.json`。下一階段 NAV-020。 |
| 2026-10-20 | NAV-020 公式結果的官方自動漸層模式 | 專項 335（24 漸層／96 逐格 golden）、範圍 401、純量 971、公式進階 127、分數／聚合／匯出 87、自訂 Domain 77，共 1998 項通過。88 份 Python、384 個本地 Markdown 連結、660 個翻譯鍵／占位符、繁中控制、固定 LF／參考依賴、Node 語法及 whitespace 檢查通過。官方實際上下限、0–1 透明白／藍、常數／空結果預設與指定來源優先均驗證；原生矩陣、SVG 像素、Excel 填色與三種往返通過。README、雙語操作／程式內手冊及重現工作流程同步；詳見 `artifacts/formula-gradient/audit.json`、`artifacts/nav20-static-checks.json`。下一階段 NAV-021；繪製器差異仍記於 CHECK-006。 |
