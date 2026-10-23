# CAR 分析、資料模型與感測器

Fusion Studio 隨附 MITRE Cyber Analytics Repository（CAR）的固定本地快照。CAR 分析是每個 Workplace 的獨立研究內容，與 ATT&CK、ATLAS TTP 並存。納入分析不會自動選取其對應技術。

## 瀏覽、排序與篩選

完整 **CAR Browser（CAR 瀏覽器）** 位於與 **Technique Details** 同層的上方參考頁籤。可用 **×** 或右鍵「關閉 CAR 瀏覽器」獨立關閉；分析／模型／感測器連結共用該頁籤。Workplace 可重開保留於記憶體的畫面；Recovery 會保存頁籤開啟狀態、目前頁面及類別，重啟後回到類別清單，不還原個別詳細頁導覽。關閉頁籤不修改納入狀態或註記。

從最左側選擇 **CAR 分析（CAR Analytics）** 會開啟可搜尋的側邊清單，點選項目或選取後按 Enter 即可在 CAR 瀏覽器開啟分析詳細頁。也可透過 **Workplace → 開啟 CAR 完整介面** 開啟所選分析；沒有選項目時會開啟完整類別瀏覽介面。分析表格依序呈現納入核取方塊，以及官方六個屬性：ID、名稱、提交日期、ATT&CK 技術、實作、適用平台。點欄位標頭可切換排序方向。日期依實際年月日排序，名稱不區分大小寫，同值以 CAR ID 升冪排列，缺值在兩方向都置底。多值欄依顯示摘要文字排序，不按數量。可調整欄寬或水平捲動查看完整內容。

搜尋名稱或 ID，可同時套用平台、實作工具及「只看已納入分析」。這些操作不改變納入狀態。點列只反白，Ctrl／Shift 可多選；勾選納入或按「將反白分析加入 Workplace」「從 Workplace 移除反白分析」才會修改文件。雙擊、按「查看分析資訊」或使用右鍵選單可開啟詳細頁。所有原生實作都會保留，包括相同工具的多份實作與只有參考連結的實作。

## 技術關聯與導覽

「依 ATT&CK 技術瀏覽」有父技術、子技術範圍、CAR 分析三欄。**N/A：僅父技術**表示原生 coverage 未指定子技術。對應 `T1036.003` 不代表也對應兄弟技術 `T1036.005`。父技術頁可彙總相關分析，但逐項標示真正來源範圍。分組遵循固定版 `generate_analytics.py`；同一分析重複列出父技術時，分組使用第一次 coverage，完整原生紀錄仍可查閱。

父技術、子技術、分析連結均在 Fusion Studio 內導覽。技術詳細頁提供「相關 CAR 分析」及返回連結。「返回 CAR 結果」保留原搜尋、篩選、排序及清單頁籤。導覽不改 inclusion。技術 ID 依目前文件的 Domain、版本與 dataset 解析；缺失、撤銷、棄用及 Tactic 不符狀態保留在解析資訊中，不自動切換版本。ATLAS 不會被推定有直接 CAR 關聯。

## 資料模型與感測器

最左側的 **CAR 資料模型（CAR Data Model）**、**CAR 感測器（CAR Sensors）**各有自己的圖示、標籤與提示，點擊先開側邊欄，再點選條目或按 Enter 開啟內容，也保留 **Workplace → 開啟 CAR 完整介面** 按鈕。完整介面的資料模型可展開物件的動作及欄位；詳細頁以精確 object/action/field 範圍反查引用分析，並保留原始描述及完整紀錄。

感測器按工具／版本分開呈現，保留 native mappings 與 notes。分析的資料需求與感測器原始映射只要有一個精確 `object/action/field` 交集，即列為候選，符合固定版生成邏輯；頁面同時列出交集欄位。部分交集不表示遙測完整或偵測已驗證。缺少資料需求時明示未知，不把動作與欄位任意全組合成宣稱支援的映射。

## 納入 Workplace

**Workplace → 工作區選取**有可收合的 **CAR 分析（n）**，與 ATT&CK／ATLAS TTP 分開計數。可 Ctrl／Shift 反白多列，再右鍵查看資訊或移除選取分析。取消選單不修改文件。移除只清除 inclusion，保留原生分析快照與已儲存註記；重複加入不重複計數。每個文件獨立，複製圖層會獨立複製 CAR 狀態，失效的舊文件選單不能修改另一份文件。

## 保存、重新開啟、匯出與復原

原生讀寫選項包含 ATT&CK、ATLAS、「包含 CAR 分析」，預設全部勾選。至少選一種內容，允許 CAR-only。**Save／Save As** 與 **Open Studio JSON** 保留 `car_workspace` schema 1：以 dataset SHA-256 加 CAR ID 為鍵，每項保存名稱、repository、commit、原生分析、inclusion 與註記欄位。取消選取的項目也保留供未來使用；沒有此擴充的舊文件會以空 CAR 選取開啟。

只有保存全部三種內容才建立完整已儲存基準。部分輸出仍將完整 Workplace 標為未儲存。不勾 CAR 時，輸出不含其 ID／快照；讀入時略過 CAR 區塊的解析。CAR-only 文件即使沒有 ATT&CK 磁碟資料仍可重新開啟。缺少精確 CAR 快照時保留分析與來源，以「未解析快照」標示；不下載或靜默替換新版。

自動 recovery 固定保留所有內容，沿用啟動自動還原與下方 Output 提示。未儲存星號、關閉／退出檢查與複製也包含 CAR 變更。排序、反白及導覽不造成 dirty。

CSV 以 `content_type` 區分 `attack_ttp`、`atlas_ttp`、`car_analytic`。CAR 列使用 `car_id`、`car_snapshot`、`car_commit`、`car_analytic_json`，`technique_id` 留空。CSV 是交換報告，不能當完整重新開啟格式。Navigator 與矩陣 Excel 僅投影明確選取的 TTP，不能保存 CAR inclusion；完整保存請用 Studio JSON。CAR-only Navigator／矩陣匯出會提示限制，不產生偽技術。

## 來源、進度與限制

固定來源為 `mitre-attack/car@1b922fe1527d956e222a99473472e594f10f610b`，含 102 份分析、13 個模型物件、7 份感測器紀錄。`data/car/source.json` 記錄逐檔 SHA-256，保留原 Apache 2.0 LICENSE 及 NOTICE。見[來源說明](../data/car/PROVENANCE.md)。

啟動先顯示 manifest／來源檔案絕對路徑，再由背景工作執行驗證 → 解析 → 索引 → 發布。CAR 載入失敗另行提示，ATT&CK／ATLAS 仍可操作。納入／移除先聲明記憶體輸入與無立即檔案輸出，再回報身分驗證 → inclusion 修改 → 視圖／recovery 同步。保存先列實際輸入、最終及暫存檔絕對路徑，再序列化及原子發布；失敗保留原檔。測試設定、session 與範例均隔離於 `artifacts/car-integration/`。

CAR 的測試及命令只供閱讀。本次不部署查詢、不執行 SIEM 或上游 unit tests、不驗證感測器完整性，也不推論偵測有效性。可攜來源封裝、部署管理及證據評分留待後續。

另見[文件保存與復原](studio_files+_zh.md)及[手冊索引](README.md)。

## 可收合的程式碼與 JSON 區塊

實作程式碼、coverage JSON、完整原生紀錄及 Data Model／Sensor JSON 都會顯示為獨立框框，每次開啟條目時預設收起。點箭頭／標題可展開；標頭的「複製」按鈕在收起時也能使用，會完整複製原文並保留換行、縮排、跳脫字元與 Unicode。實際實作程式碼與中繼資料 JSON 分開，方便直接複製。內容唯讀、使用等寬字體，長行可水平捲動；複製後短暫顯示「已複製」。切換條目會重設為收起，切換語言則保留目前展開狀態及原始程式碼。這些操作不修改選取、註記或檔案，程式會宣告記憶體輸入／無檔案輸出並顯示更新／複製進度。
