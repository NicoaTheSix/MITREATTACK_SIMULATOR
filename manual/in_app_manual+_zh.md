# Fusion Studio 操作手冊

*A community toolkit for MITRE ATT&CK® and ATLAS*

從 **Info → Manual** 或 **F1** 開啟本頁。Manual 與檔案名稱、Technique Details 位於同一排分頁；可自由切換、關閉並重新開啟。重複點擊 Manual 會回到同一個手冊分頁。

左側「大綱與條目」可直接跳到章節。頁面內的指南連結會在這個分頁內開啟，並更新左側大綱；「開啟功能」連結會前往程式目前文件的實際操作入口。上方可回手冊首頁、瀏覽全部指南，或搜尋目前頁面文字。

預設介面與手冊為英文。使用 **設定 → 語言 → 繁體中文（臺灣）** 即時切換全程式介面與手冊，選擇 **English** 可切回英文，重新啟動後仍會保留選擇。語言切換不會變更文件名稱、選取、註記、分數、公式、來源 ID 或已儲存的檔案；ATT&CK 原始內容與官方日誌摘錄保留來源語言。

## 1. 建立、開啟與儲存文件

1. 使用 **File → New File** 建立獨立文件。
2. 使用 **File → Open Studio JSON…** 開啟既有完整 Studio 文件。
3. 使用 **Save / Save As…** 保存選取、註記、圖層與來源版本。
4. 每個檔案分頁各自保存；名稱後的 `*` 表示尚未儲存。

一般啟動會自動還原上次有效工作階段，不再詢問。載入完成後，下方 Output 操作紀錄會提醒已還原分頁數、含未儲存變更的分頁數與復原檔路徑。

[完整操作：文件儲存、關閉與復原](studio_files+_zh.md) · [English](studio_files_en.md)

[開啟功能：選擇 Studio 文件](studio://open-file)

## 2. 選擇資料版本與領域

目前預設使用 **ATT&CK v20.0**，涵蓋 Enterprise、Mobile、ICS。舊文件仍採用其儲存的資料版本；開啟舊文件不會自動升版。

點擊上方 **Version (vX.Y)** 可選版本。檔案分頁的右鍵選單可切換 ATT&CK Domain。首次使用未下載版本需要網路，已驗證的本機快照可離線讀取。

[開啟功能：資料版本選擇器](studio://versions) · [完整操作：資料與文件](studio_files+_zh.md#_2)

## 3. 搜尋與選取 TTP

在左側 **TTP** 類別搜尋名稱或 ID；**TTP search fields…** 可指定 Description、Data Sources、Detection Strategy 等欄位。勾選技術即可加入目前文件。矩陣中的一般點擊與 Ctrl / Shift 點擊有不同選取行為。

選取偏好可設定跨戰術連動、父子技術家族連動與僅選可見項目。切換偏好會影響之後的操作，不會自動擴大先前的選取。

[開啟功能：TTP 搜尋](studio://search) · [開啟功能：已選技術清單](studio://selected)

[完整操作：選取偏好與進階搜尋](selection_and_search+_zh.md) · [矩陣互動與來源複製](detection_interaction+_zh.md)

## 4. 瀏覽組織、軟體與偵測資料

左側可切換 Groups、Software、Campaigns、Mitigations、Assets、Detections。Group／Software／Campaign／Mitigation／Asset／Detection Strategy／Data Component／Data Source 支援關聯選取及結果聯集批次，Analytics 仍僅供瀏覽。滑過下拉／完成清單的來源結果，可暫時標示對應矩陣技術。側欄的 **Show matrix preview（顯示矩陣預覽）** 可保留來源列表並在右側預覽；移開後還原，不更動選取或註記。

[完整操作：來源搜尋與右鍵動作](navigator_parity_controls+_zh.md) · [English](navigator_parity_controls_en.md)

[來源結果批次操作](source_relationship_selection+_zh.md) · [懸停預覽手冊](source_hover_preview+_zh.md)

## 5. 矩陣顯示與圖層設定

**Open ATT&CK Matrix** 開啟原生矩陣，可使用 Flat / Side / Mini 版面、平台篩選與技術家族展開。**Navigator → Layer settings…** 可編輯名稱、說明、漸層、圖例、顯示設定與自訂右鍵網址。

[開啟功能：ATT&CK 矩陣](studio://matrix) · [開啟功能：圖層設定](studio://layer-settings)

[完整操作：Navigator 進階流程](advanced_navigator+_zh.md) · [矩陣標籤與註記提示](matrix_display+_zh.md) · [可見選取與展開](visibility_expansion_presets+_zh.md)

## 6. 註記、分數與批次編輯

技術可以有 Comment、Score、Color、Links、Metadata 與 Enabled 狀態。技術是否被選取，與其 Enabled 狀態是獨立概念。依操作範圍可編輯全部戰術或特定戰術的技術出現位置。

先選取技術，再使用 **Navigator → Batch edit selected TTPs…**。對話框內確認範圍，套用才會提交；取消會保留原有內容。

[完整操作：獨立狀態與批次操作](batch_operations+_zh.md) · [English](batch_operations_en.md)

[開啟功能：批次編輯已選技術](studio://batch-edit)（需先選取技術，且文件版本支援 Navigator。）

## 7. 公式分析、聚合與比較

分數公式可組合多份開啟文件的資料，建立新的分析圖層。**公式語法**預設 Navigator scalar，支援常數、三角函式、容差比較與連續比較；選 Studio scalar 可保留舊有捨入及運算子規則，完整手冊另說明差異與 Studio 專用的 nthRoot 擴充。計算模式預設 Studio；改選 Navigator 可採空變數常數探測、缺分補零、全部缺分略過，並納入停用來源的既有分數；此時語法固定，Studio 政策控制停用。使用前另行確認屬性繼承，自動漸層預設跟隨計算模式：Navigator 使用實際結果上下限、0–1 透明白／藍色階，常數／空結果保留 0–100。仍可選 Studio，指定 Score gradient 來源則優先於自動設定。Parent / sub-technique 聚合是分析設定，不會自動加入技術選取。

[開啟功能：分數公式](studio://formula) · [開啟功能：比較文件](studio://compare) · [開啟功能：比較 ATT&CK 版本](studio://compare-versions)

[完整操作與範例：圖層分數公式](layer_score_formulas+_zh.md) · [聚合與匯出](aggregation_and_exports+_zh.md)

[完整操作：SVG 紙張尺寸與方向](svg_paper+_zh.md)

[完整操作：SVG 淺色／深色匯出主題](svg_themes+_zh.md)

## 8. Navigator、自訂資料與版本遷移

Studio 文件用於完整保存本工具狀態；Navigator Layer 用於與支援該格式的工具交換圖層。CSV 是選取資料交換，無法還原所有畫面設定。

**Import Navigator Layer… / Ctrl+Alt+O** 可一次開啟含 1–20 層的 JSON 陣列，預設勾選全部，也可自行選子集合。各層獨立使用領域、版本、來源與選取規則；全部勾選圖層就緒才一次開啟，保留既有文件。

[完整操作：多圖層 JSON 與缺少來源的處理](navigator_bundle_import+_zh.md)

自訂來源缺少或不明確時，可在匯入預覽按 **解析自訂資料…**，取得指定網址、驗證本機 Bundle／快取或選擇 Collection Index 版本。確認確切雜湊、領域及版本後才綁定該層；資料集變更須明確同意取代。單純開啟來源視窗不會下載。

[完整操作：customDataURL 取得與來源變更檢視](custom_data_url_import+_zh.md)

自訂資料需是 ATT&CK-compatible STIX Bundle 或 Collection Index。匯入後先確認來源、領域與版本。升版請使用逐項審閱遷移，檢查被撤銷、替代或無法對應的技術。

自訂 Bundle 現可加入額外領域，分別設定顯示名稱、Kill Chain 與外部 ID 來源。先在來源預覽選領域，再透過檔案分頁右鍵 **ATT&CK Domain** 在同一資料集中切換。多份 Matrix 使用有序聯集；Studio、Navigator、CSV 與復原均保留自訂識別及各領域狀態。

[完整操作與可載入範例：自訂 Domain](custom_domains+_zh.md)

[完整操作：升級最後摘要、略過理由與返回未完成項目](upgrade_summary+_zh.md)

[開啟功能：匯入 Navigator Layer](studio://import-layer) · [開啟功能：URL／自訂 STIX](studio://sources) · [開啟功能：審閱圖層升版](studio://upgrade)

[完整操作：自訂資料與審閱升版](advanced_navigator+_zh.md)

## 9. 匯出與分享

**File → Export… / Export CSV… / Export Navigator Layer…** 匯出交換資料。**Navigator → Export matrix SVG… / Export matrix Excel…** 匯出矩陣成果；多圖層 Excel 可將每份開啟文件輸出為個別工作表。

[開啟功能：匯出 SVG 設定](studio://export-svg) · [開啟功能：匯出 Excel 設定](studio://export-excel)

[完整操作：匯出範圍、聚合與範例](aggregation_and_exports+_zh.md)

Navigator JSON 匯出會檢視各圖層隱藏但已修改的註記格子。**只匯出可見技術的註記** 預設不勾選，完整保留全部註記。作用中矩陣依篩選／搜尋／展開判定可見性，其他圖層依各自保存的畫面設定。精簡副本仍保留 Studio 納入標記、完整圖層屬性與選取範圍。取消不寫檔，原註記、名稱及未儲存狀態均不變。

[完整操作：JSON 註記匯出選項與隱藏範圍提醒](json_annotation_export+_zh.md)

## 10. 進度、錯誤與復原

檔案操作會先顯示輸入／輸出絕對路徑，並於各階段顯示進度。請等候完成訊息。儲存／匯出失敗時先閱讀下方 Output，不要把未完成檔案當成成功結果。

Session checkpoint 可協助復原工作階段，但仍應主動儲存 Studio 文件。手冊為唯讀參考分頁，不會加入選取集合或成為匯出圖層；其開啟狀態不另存入 Studio 文件。

[完整操作：Session 復原與失敗保護](studio_files+_zh.md)

## 11. 作者與官方資源

**Info** 內可查看作者資訊、MITRE 簡介、ATT&CK 簡介與版本更新紀錄。滑鼠懸停 **Version update history** 可展開版本列表；點擊版本閱讀短摘錄，再由網址開啟完整官方更新日誌。

[全部中英文操作指南](README.md) · [安裝與啟動說明](../README.md) · [MITRE ATT&CK 官方網站](https://attack.mitre.org/)

## CAR 研究內容

CAR 分析、CAR 資料模型與 CAR 感測器導覽圖示只開側邊清單；選好後透過 **Workplace → 開啟 CAR 完整介面** 開啟完整頁。分析可獨立納入目前 Workplace；請用 Studio JSON 與預設勾選的 CAR 內容選項完整保存。Navigator 僅保存 TTP。[CAR 操作手冊](car_integration+_zh.md)。

## 工作區頁籤與側邊欄顯示

ATLAS 案例詳細頁位於上層參考頁籤，搜尋／清單位於左側。**Workplace → 開啟 ATLAS 緩解措施詳細資料** 不需先選項目；點緩解措施圖示／清單不切換右頁。Settings → 側邊欄顯示提供 ATT&CK、ATLAS、CAR 三個獨立開關，預設全開，Workplace 永遠保留。全部收合選取清單時，摘要與控制列維持正常高度。 [操作說明](workspace_layout+_zh.md).

**CAR 瀏覽器** 與 **Technique Details** 並列為上層獨立參考頁籤，可用 × 或右鍵關閉，再由 Workplace 開啟；Recovery 保存頁籤是否開啟、目前頁面及類別。另見[工作區操作說明](workspace_layout+_zh.md#car-瀏覽器)。
