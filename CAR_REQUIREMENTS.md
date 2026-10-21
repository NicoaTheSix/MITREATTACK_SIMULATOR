# Fusion Studio：CAR 整合需求規格

日期：2026-10-21。規格版本：1.0。需求提出者：專案使用者。實作負責對話：**工程部門**。狀態：已派工，工程對話已啟動執行；本文不代表功能已完成。

產品名稱：**Fusion Studio**。副標：*A community toolkit for MITRE ATT&CK® and ATLAS*。

## 1. 目標與優先順序

將 CAR 原生分析、技術關聯、資料模型及感測器整合到目前的桌面工作區，讓使用者瀏覽、排序、互相導覽，並把 **CAR Analytic 本身**納入目前 Workplace。使用者稱 workspace，本文指現有 Workplace 文件與其工作區介面，不新增另一套互不相通的專案管理系統。

本規格為這次實作的驗收依據。優先順序是：本次使用者明確需求 → 本規格的具體操作決策 → `CAR_INTEGRATION_PLAN.md` 的架構建議 → `CAR_UPSTREAM_RESEARCH.md` 的上游調查。若舊計畫只描述「由 CAR 加入對應 TTP」，必須以本規格補上「選取分析本身」。

**本次必做：**固定來源資料、Analytics 六欄排序介面、依技術瀏覽、三種詳細頁互通、左側 Data Model／Sensors 獨立入口與圖示、分析納入 Workplace、文件儲存／讀入／復原、雙語與必要驗收。

**後續另案：**環境部署管理、SIEM 查詢執行、自動測試命令執行、CALDERA 連接、完整 Detection Plan 證據評分及 ATLAS 間接偵測推論。不得以後續功能尚未完成為由漏掉本次分析選取與持久化。

## 2. 需求與來源

| 使用者需求 | 對應需求 |
| --- | --- |
| Analytics 具有 ID、Name、Submission Date、ATT&CK Techniques、Implementations、Applicable Platforms，且皆可排序 | CAR-002 |
| ATT&CK Technique／ATT&CK Sub-technique(s)／CAR Analytic(s) 之間能互通，遵循 CAR 對應方法 | CAR-003、CAR-004 |
| Data Model 與 Sensors 放在最左側，各有自己的 Icon | CAR-005 |
| Analytics 各項可以選取並放進 workspace | CAR-006、CAR-007 |

官方閱讀介面來源：[Analytics](https://car.mitre.org/analytics/)、[Analytics by technique](https://car.mitre.org/analytics/by_technique)、[Data Model](https://car.mitre.org/data_model/)、[Sensors](https://car.mitre.org/sensors/)。

官方原始資料固定基準：`mitre-attack/car@1b922fe1527d956e222a99473472e594f10f610b`。若工程取得更新 commit，必須記錄新版本、差異與對應方式重新驗證的結果，不能將網站最新輸出與舊 YAML 混成一個快照。[固定來源](https://github.com/mitre-attack/car/tree/1b922fe1527d956e222a99473472e594f10f610b)

## 3. CAR-001：資料來源與獨立身分

1. 匯入原生 `analytics/*.yaml`、`data_model/*.yaml`、`sensors/*.yaml`，保存原始欄位及未知欄位；衍生索引與原始資料分開。
2. 本地來源 manifest 必須含 repository URL、commit、檔案相對路徑與 SHA-256；隨附適用 LICENSE／NOTICE。正常開啟應用程式與文件只使用本地快照，不自動連網。
3. CAR ID 與 ATT&CK `x-mitre-analytic`、TTP STIX ID、ATLAS AML ID 分開，不按名稱合併。分析參照以 CAR ID＋來源快照身分定位。
4. schema 容許缺少 coverage、platforms、implementations、code、unit_tests、data_model_references；不完整但有效的分析仍可瀏覽及選取。缺值不等於沒有資料需求或已驗證。
5. 保留多個 implementation；同一工具的多個實作不可因 type 相同而合併遺失。只有連結的實作顯示來源連結，不捏造 query。
6. schema／資料損壞應提出診斷，不發布半完成索引；CAR 載入失敗不影響 ATT&CK／ATLAS 基本操作。

依據：[analytic schema](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/scripts/analytic_schema.yaml)、[含多種實作的 YAML](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/analytics/CAR-2013-05-009.yaml)。

## 4. CAR-002：Analytics 六欄清單與排序

左側新增 **CAR Analytics** 入口；主要內容區提供 **Analytics** 與 **By ATT&CK Technique** 切換。Analytics 採原生 Qt 表格，呈現以下六個屬性，順序與官方一致。可以另加獨立的納入核取欄，但不得取代任一屬性。

| 欄位 | 內容 | 本專案排序規則 |
| --- | --- | --- |
| ID | 原始 `id` | 依 CAR ID 的年／月／序號自然排序 |
| Name | 原始 `title` | 名稱文字排序，不區分大小寫 |
| Submission Date | 原始 `submission_date`，可讀日期格式 | 按實際年月日排序，不按月份字串排序 |
| ATT&CK Techniques | coverage 父技術 ID 與名稱；可進入精確子技術關聯檢視 | 以所顯示的技術名稱清單文字為排序鍵，ID 為次鍵，不改為數量排序 |
| Implementations | 工具 type 的顯示摘要；完整實作保留在詳細頁 | 按顯示的工具類型清單文字排序，不按實作數量 |
| Applicable Platforms | 原始 platforms 的顯示摘要 | 按顯示的平台清單文字排序 |

以上六欄及點標頭排序來自使用者／官方頁面；具體缺值、次鍵與穩定性是本規格的產品決策，並非宣稱官方網站採取同一演算法。

操作規則：

- 點擊任一屬性欄標頭，在升冪／降冪間切換，顯示方向；預設 ID 升冪。排序作用於全部目前篩選結果。
- 多值欄先建立確定且一致的顯示摘要，再依其文字比較；同值以 CAR ID 升冪作穩定次鍵。缺值在兩方向皆置底，不因切換語言或排序而改寫原始資料。
- 支援名稱／ID 搜尋；提供平台、工具篩選及「只看已納入分析」。搜尋、篩選與排序只改顯示，不修改納入狀態。
- 單次點擊列為反白，Ctrl／Shift 可多選；核取方塊或明確「加入 Workplace」操作才改變納入狀態。提供檢視資訊的明確按鈕、ID 連結或右鍵選項。
- 列的身分使用 CAR ID＋快照，不能依視覺 row index 記錄選取；在排序後勾選或批次加入必須命中正確分析。
- 窄視窗可水平捲動、欄寬可調；多值內容可換行或透過提示／詳細頁完整檢視，不只顯示不可操作的省略文字。

依據：[官方六欄可排序清單](https://car.mitre.org/analytics/)。

## 5. CAR-003：官方父／子技術關聯語意

**By ATT&CK Technique** 必須保留三欄：

| ATT&CK Technique | ATT&CK Sub-technique(s) | CAR Analytic(s) |
| --- | --- | --- |
| 父技術 ID＋名稱 | 明列子技術 ID＋名稱，或 technique-only 狀態 | 對應範圍內的分析 ID＋名稱 |

1. 讀取原生 coverage 的 `technique`、`subtechniques`、`tactics` 與 `coverage` 原值，以父技術分組，分開呈現直接父技術關聯與指定子技術關聯。
2. coverage 未列子技術時，放在該父技術的 **N/A — technique only** 範圍；列明子技術時，放入各指定子技術的範圍。沒有明列的兄弟／子技術不得繼承該分析。
3. 父技術詳細頁可提供「此父技術及明列子技術的分析」彙總，但必須標出來自父層或哪個子技術；子技術詳細頁預設只顯示其精確對應。不得把彙總當作父層直接關聯。
4. 索引應以官方 native coverage 與同版 `generate_analytics.py` 所產生的 by-technique 分組為核對基準，工程必須閱讀該生成邏輯並建立案例。**不可用 Navigator generator 的父層視覺 entry 代替 by-technique 語意。** 若固定版生成結果與網站當下不同，記錄版本差異，以固定快照一致性為準。
5. 重複 coverage 可在顯示端依父／子範圍＋CAR ID 去重，但保留各原始 coverage 與來源路徑供追溯。無 coverage 的分析仍存在於 Analytics 清單與 Workplace，關聯頁顯示未提供。
6. 以當前 ATT&CK dataset／domain／版本解析外部 ID，保留成功、缺失、棄用／撤銷及戰術不符等狀態，不依名稱猜測或自動升版。技術名稱優先顯示目前 Catalog 名稱，原始映射 ID 不變。
7. CAR 的 `Moderate` 等描述不換算成實測百分比。CAR Data Model 名稱不等於 ATT&CK Data Component ID；ATLAS 不自動建立直接 CAR 映射。

驗收案例：`CAR-2013-05-009` 在 `T1036.003` 範圍可找到；`T1036` 的父層彙總可顯示它並註明子技術來源，但不能因此宣稱 `T1036.005` 也適用。`CAR-2013-05-002` 則核對 technique-only 的 `T1036` 範圍。另以 `T1021` 同時含 technique-only 與多個子技術關聯驗證分組。

依據：[官方三欄關聯表](https://car.mitre.org/analytics/by_technique)、[分析生成邏輯核對位置](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/scripts/generate_analytics.py)、[原始範例 coverage](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/analytics/CAR-2013-05-009.yaml)。

## 6. CAR-004：三種頁面雙向互通

三欄每個項目均提供內部導覽連結或明確按鈕。互通是 Fusion Studio 內的詳細頁，不只是開啟外部網頁。

| 從哪裡 | 必須能到哪裡 |
| --- | --- |
| 父技術詳細頁 | 子技術詳細頁、範圍明確的相關 CAR 分析詳細頁 |
| 子技術詳細頁 | 父技術詳細頁、精確相關 CAR 分析詳細頁 |
| CAR 分析詳細頁 | 對應父技術／明列子技術詳細頁、所引用 Data Model 物件／欄位 |
| Analytics 清單／By Technique／Workplace 已納入分析 | 同一 CAR 分析詳細頁 |

- 既有 ATT&CK 技術詳細頁補「Related CAR Analytics」區塊；保留原有 ATT&CK Detections 與原始內容。
- 技術無法在當前 Catalog 解析時，保留原始 ID、說明狀態並提供「開啟官方來源」。不得悄悄改變文件版本、domain 或已選資料。
- 提供返回來源清單的操作，至少保留來源視圖、搜尋、篩選、排序與可還原的捲動／定位；導覽本身不勾選或取消任何分析／TTP。
- CAR 詳細頁顯示原始描述、日期、平台、coverage、各 implementation（工具／code／外部連結／前提）、data model、適用 sensor 候選、來源 commit。測試說明只顯示，不執行。
- 若加入「加入／移除對應 ATT&CK TTP」沿用既有計畫功能，必須是與「加入／移除分析」不同的按鈕，清楚顯示目標範圍，不能互相替代或偷偷連動。

## 7. CAR-005：最左側 Data Model／Sensors 與圖示

1. 最左側活動導覽列新增三個可識別入口：**CAR Analytics**、**CAR Data Model**、**CAR Sensors**；後兩者必須各有自己的圖示，不合併到同一入口。
2. 圖示延續目前 ATLAS 的黑白、透明背景風格，使用專案自有 SVG：建議 Data Model 為欄位格／資料結構，Sensors 為感測節點／訊號。圖示在深底與互動選取狀態要可辨識；保留標籤、tooltip、無障礙名稱及現有導覽文字開關。
3. 工程部門負責交付可用 SVG 與載入整合。本次不另行派工「美術設計」，避免同檔案平行修改；可在後續另案美術優化。
4. Data Model 提供 Object／Actions／Fields 清單與說明。由分析的 `object/action/field` 可定位相應項目；從物件／欄位可查看精確引用它的分析。
5. Sensors 依工具與版本分開顯示，保留 mappings、notes、來源；可導覽到對應 Data Model 與有資料欄位交集的分析候選。
6. Sensor→Analytic 的候選採官方交集語意；顯示「候選／部分欄位匹配」與實際交集，不標成資料齊備或已驗證。缺資料需求的分析顯示未知，不當成需求為空且已滿足。
7. 欄位列舉不可任意把所有 action 與所有 field 做全組合並宣稱感測器支援；優先呈現原始 sensor mapping 的 object/action/fields 與 notes。

依據：[官方 Data Model](https://car.mitre.org/data_model/)、[官方 Sensors](https://car.mitre.org/sensors/)、[sensor 生成邏輯](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/scripts/generate_sensors.py)。

## 8. CAR-006：分析選取與 Workplace

1. Analytics 表格每列可獨立勾選／取消，支援對反白多列「加入 Workplace」「從 Workplace 移除」。重複加入同一快照分析不重複計數。
2. Workplace 的目前選取介面新增可收合 **CAR Analytics (n)** 區塊，與 ATT&CK、ATLAS TTP 區塊平行；CAR 是內容類型，不宣稱是第三個 ATT&CK 矩陣。無項目時仍顯示區塊與零計數。
3. 保留 ATT&CK／ATLAS TTP 原有計數。CAR 分析計數另外顯示，不把分析加進 TTP 總數；必要時把共同頁面稱為 **Workspace Selections／工作區選取**，並同步所有選單與手冊文字。
4. 已納入分析顯示 ID、Name；可反白、Ctrl／Shift 多選；單次點擊只反白，右鍵「查看分析資訊」「移除選取的 Analytics」。取消右鍵選單不改文件。
5. 取消納入只移除分析的 inclusion，不刪既有分析註記／未來評估資料，不影響任何 TTP 選取、TTP 註記、分數、顏色或另一框架。
6. 切換 Workplace，各文件的分析選取獨立；複製文件採獨立複本。關閉／切換 CAR 瀏覽視圖、排序、搜尋或關閉矩陣均保留選取。
7. 表格勾選、詳細頁加入／移除、Workplace 清單與數量同步；排序／篩選後不把勾選套到其他分析。失效或跨文件的舊右鍵 action 不得操作新文件。

## 9. CAR-007：文件、讀入／輸出與復原

1. 原生 Studio 文件以有版本的可選 CAR 擴充保存分析選取、CAR 快照身分及必要顯示快照（至少 ID／名稱）。建議 `car_workspace`，最終 schema 由工程說明；不要借用 `atlas_document` 或 TTP ID 集合。
2. 舊 Studio 文件未含 CAR 時仍可開啟，建立空的 CAR 選取。選取變更納入 dirty tracking、Save／Save As、複製、關閉／退出檢查與自動 recovery；單純反白、排序、導覽不設 dirty。
3. 原生讀寫選項保留 ATT&CK／ATLAS 各自預設是，新增獨立的「包含 CAR Analytics」選項，預設是。可只讀寫 CAR；有效條件為至少選一種內容，不要求一定含威脅框架。
4. 未選 CAR 時，輸出不得殘留其 ID、註記或快照內容；讀入時不解析略過的 CAR dataset。部分輸出不把完整文件標成已儲存。自動 recovery 固定保存所有內容，不問框架範圍。
5. 缺少精確 CAR 快照時，仍保存已納入分析 ID／名稱／原始 commit，顯示未解析狀態，不靜默刪除、套用最新快照或自動下載。只有 CAR 的文件應能在獨立內容 envelope 或等效格式還原；略過 ATT&CK 時不因其磁碟資料缺失而阻擋 CAR 還原。
6. JSON 保留完整原生結構。CSV 明確區分 ATT&CK TTP、ATLAS TTP、CAR Analytic 行類型與 ID；現有 CSV 格式若不適合混排，可交付有說明的獨立 CAR CSV／多檔選項。不得把 CAR ID 放進 `technique_id` 冒充 TTP，或聲稱 CSV 可完整復原。
7. Navigator 格式無法完整表示 CAR 分析選取。Navigator 匯出只投影使用者明確選取的 TTP，或另行選擇且清楚標示的 CAR 映射圖層；不得把 CAR 分析轉成偽技術、偷偷加入對應 TTP，或把 Navigator 輸出當完整 CAR 儲存。偵測到 CAR 內容時，匯出介面說明保留限制。
8. 未納入本次實作的可攜快照封裝或額外報告須明確列為後續，不影響原生 Save／Open／recovery 的本次驗收。

## 10. CAR-008：操作進度、路徑與錯誤隔離

遵守使用者專案規則：程式處理前先顯示所有實際輸入／輸出檔案的**絕對路徑**；各階段顯示運算進度；程式所在目錄 README 必須同步記錄流程。

- CAR 載入：來源／manifest／雜湊驗證 → YAML 解析 → 技術／資料模型／sensor 索引 → 發布至 UI。需背景處理，UI 不長時間凍結。
- 納入／移除：宣告輸入為記憶體、無立即檔案輸出 → 解析精確 ID 與文件身分 → 修改 inclusion → 同步視圖／dirty／checkpoint。延後 recovery 寫入沿用既有絕對路徑與進度流程。
- 儲存／匯出：宣告最終及暫存絕對路徑 → 擷取不可變快照與內容範圍 → 序列化／驗證 → 原子發布。失敗或取消保留原檔與原文件。
- 圖示載入：先列 SVG 絕對路徑及記憶體輸出，再報分階段進度；缺圖示可退回可讀標籤。
- 純排序／反白等高頻 UI 動作不需每列輸出大量日誌；涉及耗時索引／重建時顯示彙總進度，狀態不暗示寫檔。

## 11. 模組責任與依賴

| 建議模組／既有位置 | 責任 |
| --- | --- |
| `car_catalog.py` | native YAML、來源 manifest、驗證及不可變索引；不依賴 Qt |
| `car_mapping.py` | CAR coverage 及官方分組語意→指定 ATT&CK Catalog 的可追溯關聯；不自行修改文件 |
| `car_workspace.py`／獨立 view 模組 | Qt 六欄清單、排序／篩選、By Technique、詳細頁與 Data Model／Sensors |
| CAR 文件擴充模組 | 文件選取身分、內容快照、序列化驗證；與 UI 分開 |
| `ttp_documents.py`、`studio_files.py`、`framework_io.py` | 保存、選擇性讀寫、複製、dirty／recovery；不直接解析 YAML |
| `main.py`、既有詳細頁與最左導覽 | 入口、頁面路由及工作區連動；不要把 CAR parser 與排序比較器全部堆入主視窗 |

資料流：固定 CAR 本地快照 → CAR Catalog／官方語意索引 → 六欄清單／By Technique／詳細頁 → 明確加入命令 → 文件 CAR inclusion → 工作區同步 → Studio 保存／復原。ATT&CK Catalog 僅用來解析及展示技術關聯，不是 CAR ID 的存放位置。

## 12. 分階段工程任務與交付

| 階段 | 必須交付 | 對應需求 |
| --- | --- | --- |
| A | 固定資料、manifest／授權、解析／索引、官方 by-technique 語意案例 | CAR-001、003 |
| B | 六欄排序清單、雙向詳細頁、Data Model／Sensors 導覽與可用 SVG | CAR-002、004、005 |
| C | 分析本身納入 Workplace、同步／多選／移除、完整原生儲存／復原與選擇性 IO | CAR-006、007 |
| D | 失敗／取消處理、進度日誌、雙語介面／手冊、必要回歸與完整驗收報告 | CAR-008 及全部需求 |

工程可以分批提交／報告，但**本次完成定義是 A～D 全部交付**。不得只做唯讀瀏覽器即回報整合完成；不得自行跳回 NAV-027 而擱置這份需求。

## 13. 驗收清單

- [ ] 六個屬性欄逐一升／降冪驗證；包括日期跨月／年、同名、缺值、多值、排序後選取正確與語言切換。
- [ ] Native coverage 與同快照 by-technique 生成語意一致；`T1036`／`.003`／`.005` 與 `T1021` 案例不發生父層擴張或兄弟關聯污染。
- [ ] 父技術、子技術、CAR 分析三種詳細頁可雙向導覽；返回保留來源狀態；導覽不改 inclusion。
- [ ] 最左側 Data Model、Sensors 各有自己的可辨識圖示、標籤、tooltip／無障礙名稱；小視窗與標籤開關正常。
- [ ] Data Model 引用與 sensor 版本／notes 保留，sensor 部分交集僅顯示候選，不誤標齊備／驗證。
- [ ] Analytics 勾選、排序、搜尋、多列加入與已納入區同步；無 coverage／無 code 的分析仍可選。
- [ ] Workplace 含獨立 CAR Analytics 區塊與計數；Ctrl／Shift／右鍵移除只影響目標分析，保留所有 TTP 與註記。
- [ ] 多文件隔離、文件複製、舊右鍵 action、重複加入／移除、關閉視圖再開皆正確。
- [ ] 原生 JSON／Save／Open／Save As／recovery 能往返還原 CAR 選取、快照及必要顯示資訊；舊文件仍可用。
- [ ] 三種內容預設都包含；ATT&CK／ATLAS／CAR 各種範圍、CAR-only、略過缺失快照、部分輸出 dirty 與取消均驗證。
- [ ] Navigator／CSV 不混淆 CAR 與 TTP，不靜默丟失原生儲存內容；來源版本差異及失效技術有可見診斷。
- [ ] 實際 Qt 控制項互動測試、代表性解析與關聯案例、文件生命週期回歸通過；不要只驗證函式存在或硬編碼樣本。
- [ ] 每階段進度、所有實際檔案絕對路徑、原子失敗保護符合規則；中英文 README／手冊及來源聲明同步。
- [ ] 保留 Fusion Studio 名稱、副標與目前既有功能；使用隔離 settings／session／artifacts 驗證，不覆寫使用者工作階段與未提交變更。

交付證據放在 `artifacts/car-integration/`，至少有分項結果／日誌、Analytics 清單（兩種排序）、By Technique、Data Model、Sensors、Workplace CAR 區塊及中英文代表性截圖，並在根 README 記錄實際操作入口、資料流程、測試方式與已知限制。

## 14. 工程交接與後續範圍

交接對話：**工程部門**，工作目錄：`D:\MITREATTACK_SIMULATOR`。工程開始時先閱讀本規格、`CAR_INTEGRATION_PLAN.md`、`CAR_UPSTREAM_RESEARCH.md`、目前 README 與適用專案規範；現有工作樹包含其他對話已完成但未提交的更動，必須保留。

派工紀錄：2026-10-21，已將完整工程指令傳送至對話 `01a1200d-92ae-7c42-8038-700f04cfe496`；派工後狀態確認為 active／inProgress。工程實際完成與測試證據由工程部門後續填寫，不以派工成功代替功能驗收。

本規格的模組名稱與欄位名可在符合行為及相容性的前提下調整，但工程須在 README 記錄實際責任與格式。任何必做項目無法達成時，應具體列出阻礙與受影響的驗收項，不能默默降為後續。
