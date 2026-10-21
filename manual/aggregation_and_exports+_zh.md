# 父子技術分數彙總與矩陣匯出

本手冊適用於 Fusion Studio 的 ATT&CK v4 以上圖層。啟動與環境設定見[專案 README](../README.md)，公式建立新圖層見[圖層分數公式手冊](layer_score_formulas+_zh.md)。

## 設定父／子技術分數彙總

1. 開啟要分析的檔案與矩陣，替父技術或子技術設定 Score。
2. 選 **Navigator → Layer settings…**。
3. 勾選 **Show parent/sub-technique aggregate scores**。
4. 選擇 **Average／Maximum／Minimum／Sum**，需要時勾選 **Count enabled unscored family members as zero**。
5. 儲存後，滑鼠停在父技術可看到原始 **Score** 與衍生 **Aggregate score**。父技術的漸層使用彙總分數；其手動指定色仍優先。

例如，同一 tactic 中父技術分數為 20，兩個子技術為 40、0，其他子技術未評分，且未啟用零值計數：

| 函數 | 計算 | 結果 |
| --- | --- | ---: |
| Average | `(20+40+0)/3` | 20 |
| Maximum | `max(20,40,0)` | 40 |
| Minimum | `min(20,40,0)` | 0 |
| Sum | `20+40+0` | 60 |

真實的 0 會參與計算。缺失值預設省略；啟用零值計數後，未評分但啟用的成員會以 0 參與所有函數，包括最小值。整個家族都未評分時仍維持未知。明確停用的成員不計入；同一技術的不同 tactic 各自計算。範圍是目錄中對應該 tactic 的完整家族，平台／搜尋只限制畫面，不會改變彙總結果。

原始 Score 與勾選狀態保持不變。設定會保存於圖層的 `layout` 欄位，隨檔案的領域／版本紀錄保存。加總可能超過既有漸層上限，必要時提高 **Maximum score**，以免多個不同數值都顯示成相同的上限顏色。

## 匯出 SVG 或彩色 Excel 矩陣

1. 在矩陣選擇平台、搜尋條件與是否顯示圖層色彩。需要疊色時勾選 **Show all layers**。
2. 選 **Navigator → Export matrix SVG…** 或 **Export matrix Excel…**。
3. 選擇已存在的目的資料夾，例如先建立 `examples`，再選 `examples/matrix.svg` 或 `examples/matrix.xlsx`。
4. SVG 可先調整 **Settings** 並使用 **Preview SVG · no file written** 預覽；Excel 維持單圖層匯出視窗。按 **Export SVG／Export XLSX**，等待背景工作完成。

寫入前會顯示輸出檔案及暫存檔的絕對位址，並依序顯示 **1/4 投影、2/4 繪製、3/4 寫入、4/4 發布**。驗證／寫入失敗或在發布前取消時，既有輸出不會被覆蓋，暫存檔會清除。

輸入是目前圖層與已驗證目錄的記憶體快照；輸出是 SVG 或 XLSX。預設展開全部符合條件的子技術，包含畫面捲動範圍以外的內容；SVG 也可改成目前展開或不顯示子技術。平台、搜尋、隱藏停用項、色彩顯示與同領域／版本／資料集疊色會反映在輸出中。關閉色彩顯示時，輸出也會呈現中性色。

**SVG** 是可縮放的向量圖，包含技術 ID／名稱、原始與彙總分數、漸層／圖例，並在滑鼠提示中保留註解。子技術以 `>` 與縮排標示。

**單圖層 Excel** 包含三個工作表：

| 工作表 | 內容 |
| --- | --- |
| Matrix | 各 tactic 的彩色矩陣、分數、註解，並凍結標題列 |
| Techniques | 技術／父技術 ID、勾選與停用狀態、原始分數、彙總、顏色與註解，可篩選 |
| Layer Info | 領域、版本、平台、搜尋、公式來源及圖例 |

名稱與註解以文字保存，開頭為 `=` 也不會變成 Excel 公式。Excel 單一儲存格上限為 32,767 字元，超長文字會使匯出明確失敗；需要保存完整長篇註解時請使用 JSON。

SVG／Excel 是展示及分析輸出，不會重新命名檔案或把完整專案狀態標記為已儲存。保存原始分數、註解與跨領域／版本紀錄時，另匯出 Studio JSON；與官方工具交換目前圖層時使用 Navigator Layer JSON。

## SVG 進階設定與預覽

選 **Navigator → Export matrix SVG…**、指定目的檔案後，在 **Settings** 調整。設定只屬於這次匯出視窗，不會改變圖層儲存資料。

| 設定 | 使用方式 |
| --- | --- |
| SVG 主題 | 深色（初始預設）或淺色，僅影響本次輸出呈現；切換後請重新預覽 |
| 紙張尺寸 | 自訂、Letter、Legal、11×17、18×24、24×36 英吋；預設紙張鎖定寬高 |
| 方向 | 預設紙張可選直式／橫式；自訂寬高皆指定時切換會交換兩軸 |
| Units | px、cm 或 in；切換單位時保持實際尺寸，以每英吋 96 邏輯像素換算 |
| Image width／height | 0 為自動；指定尺寸時完整矩陣會縮放至畫布內，不裁切 |
| Header height | 0 為自動；指定高度時標頭內容會縮放至指定範圍 |
| Font | sans-serif、serif、monospace，套用於標頭、圖例及矩陣 |
| Header sections | 分別顯示／隱藏整個標頭、名稱與說明、領域與版本、平台與搜尋文字 |
| Cell border | 六位十六進位色碼，例如 `#808080` |
| Sub-techniques | 全部符合條件的子技術、開啟匯出視窗時已展開的子技術、或不顯示 |
| Legend | 顯示／隱藏；固定於標頭或獨立定位，以目前單位指定 X／Y／寬／高；高度 0 為自動 |

目前展開模式會逐父技術／tactic 擷取 Flat／Side／Mini 的實際狀態。矩陣仍在建立時，視窗會先等待，完成後才啟用預覽／匯出。擷取後的展開狀態固定；平台、搜尋、隱藏項目仍依該次匯出篩選處理。

獨立定位的圖例可以刻意覆蓋矩陣，且隱藏標頭時仍保留；圖例必須放在畫布內，超出會要求調整位置、尺寸或畫布。固定於標頭的圖例隨標頭一起隱藏。圖例標籤會換行，指定圖例高度時會縮放內容。較小的圖片／標頭／圖例尺寸會讓文字縮小，不會自行刪掉資料列。數值上限為 100000 邏輯像素，圖片至少寬 80 像素，標頭下方須保留至少 40 像素的矩陣空間。

範例：選 **cm**，寬 `20`、高 `25`、標頭高 `2`、字型 **serif**、框線 `#808080`，子技術選 **Show children expanded when export opened**，再預覽。矩陣很大時，增加寬度或縮小平台／搜尋範圍以保持可讀性。Qt 預覽會配合視窗縮放；輸出 SVG 保留指定的實際單位及尺寸。

**Preview SVG · no file written** 會先顯示記憶體輸入／輸出，再依序顯示 **1/3 驗證 → 2/3 繪製 → 3/3 完成**，於 **Preview** 分頁呈現向量圖。錯誤數值可修正後重試。真正匯出時才顯示最終／暫存檔的絕對位址及四階段發布進度。處理中設定暫時鎖定；取消或失敗保留原本輸出。完成後修改設定即可再次匯出至指定位置。

SVG 明暗與程式介面主題獨立。不透明手動色／Tactic 色維持原值；透明分數／彙總及疊色會對所選主題底色重新合成。圖例文字／面板及停用格子隨主題變化，淺色增加可讀指示襯線及色票邊框；進階 Mini 匯出保留選取框。主題不寫入圖層 JSON，也不影響 Excel；重開匯出視窗預設深色。詳見[SVG 主題範例與驗證](svg_themes+_zh.md)。

[紙張尺寸與方向手冊](svg_paper+_zh.md)說明五種預設、實際單位換算、自訂草稿還原及上限。改紙張／方向保留標頭與圖例尺寸；獨立圖例超界時須明確調整。

## 所有開啟圖層匯出至同一份 Excel

1. 開啟要輸出的文件，分別設定各層已保存的平台篩選、顏色、分數與啟用狀態。
2. 選 **Navigator → Export all open layers to Excel…**，指定例如既有 `examples` 資料夾內的 `all-layers.xlsx`。
3. 核對完整圖層清單與領域／版本欄，再按 **Export all layers XLSX**。
4. 等待 **1/4 驗證 → 2/4 逐層投影與繪製 → 3/4 寫入整份活頁簿 → 4/4 原子發布**。運作前顯示輸出與暫存檔絕對位址，輸入是不可變的記憶體快照。

結果**每份開啟文件各佔一個工作表**，依頁籤順序，最多 50 份。Enterprise／Mobile／ICS、相容版本及自訂資料集可混合，各自獨立。每張表使用該層已保存的平台篩選、排序、隱藏停用設定與顏色，展開全部符合條件的子技術；不套用目前頁面的暫時搜尋、隱藏色彩或疊色開關。未勾選 TTP 仍會匯出該層矩陣；明確選空的平台篩選會保留一張標示無符合項目的表。

第 1 列保留完整名稱，第 2 列顯示領域／版本／平台，第 3 列為 tactic 標頭。彩色格子包含技術 ID／名稱及分數；Excel 註解保留勾選／啟用狀態、註記、Links 與 Metadata。矩陣下方列出說明、圖層 Metadata／Links／公式 JSON 與圖例。凍結位置為 A4。此模式不另建 Techniques／Layer Info；單圖層 Excel 才有原本的三張表。

工作表名稱會替換 Excel 不接受的字元、截斷至 31 個 UTF-16 單位，大小寫相同的重名加上如 `Assessment (2)` 的後綴，保留字 `History` 也會改名；第 1 列仍保存原名。以 `=` 開頭的內容仍是文字。無效控制字元、超過 32,767 字元的文字／註解、不支援的 v4 以前歷史圖層或後續任一圖層失敗，會明確中止整份活頁簿。取消／寫入失敗保留原檔並清除暫存檔。來源、選取與儲存標記不變；完整可編輯狀態仍請保存 Studio JSON。

## 範例檔案與驗證

- [SVG 範例](../artifacts/layer-analysis-example.svg)
- [彩色 Excel 範例](../artifacts/layer-analysis-example.xlsx)
- [SVG 預覽](../artifacts/layer-analysis-svg-preview.png)
- [進階 SVG 範例](../artifacts/export-options/advanced.svg)
- [所有圖層 Excel 範例](../artifacts/export-options/all-layers.xlsx)
- [英文手冊](aggregation_and_exports_en.md)

專案根目錄的 `audit_layer_analysis.py` 驗證既有運算、SVG 像素及單圖層 Excel。`audit_export_options.py` 驗證進階選項／單位、實際向量像素、三種子技術模式、工作表命名／領域隔離、空篩選、失敗／取消，以及原生預覽與匯出操作；七階段開始前會顯示輸入／輸出絕對位址，範例、截圖與 `audit.json` 位於 `artifacts/export-options`。設定 `QT_QPA_PLATFORM=offscreen` 後執行 `.venv\Scripts\python.exe -B audit_export_options.py`；環境設定見專案 README。
