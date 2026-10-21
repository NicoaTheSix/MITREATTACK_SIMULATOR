# 矩陣顯示與註記提示

啟動方式見[專案 README](../README.md)。本功能適用於 Enterprise、Mobile、ICS 與自訂 ATT&CK 資料集中的相容 Navigator 圖層。

## 名稱與 ID 獨立開關

1. 開啟文件，從 TTP 側邊欄開啟矩陣。
2. 分別切換 **Show names** 與 **Show IDs**。預設顯示名稱，不顯示 ID。
3. 兩者都開啟時顯示 ID 與名稱；都關閉時，技術格子與 tactic 標頭不顯示名稱／ID，勾選、顏色與滑鼠提示仍可使用。
4. 切到 **Mini** 時，暫時隱藏文字與自訂 tactic 背景，並停用工具列開關；回到 Flat／Side 就恢復原設定。

這是顯示選項，不改變選取、註記或分數。完整 ID／名稱仍保留在提示文字、詳細資料及選取 TTP 的 JSON／CSV。名稱與 ID 開關也會套用到 tactic 標頭。

## Tactic 標頭背景色

勾選 **Tactic background**，再用 **Header color…** 選顏色。選色會一併啟用背景顯示，文字會自動調整對比。取消勾選只隱藏背景，保留已選的顏色。

也可透過 **Navigator → Layer settings… → Display** 一次編輯顯示開關與六位 `#RRGGBB` 色碼。Save 會驗證後套用；Cancel 或無效色碼不改變文件。Mini 模式仍可在此分頁預先設定，但畫面會暫時隱藏這些選項的效果。

| 保存欄位 | 意義 |
| --- | --- |
| `layout.showName` | 顯示技術／tactic 名稱 |
| `layout.showID` | 顯示技術／tactic 的 ATT&CK ID |
| `showTacticRowBackground` | 在 Flat／Side 顯示共用 tactic 標頭色 |
| `tacticRowBackground` | 標頭顏色，預設 `#dddddd` |

每層各自保存設定。切換頁籤、複製、Studio 儲存／重開、Navigator 交換、跨領域／版本紀錄與工作階段復原都會保留。修改後須儲存 Studio 文件，才算保存完整編輯狀態。

## Expand annotated

按 **Expand annotated** 會展開具有已註記子技術的家族，並收合其他家族。範圍依目前平台投影，逐 tactic 判定。註解、使用者 Metadata、Links、已設定分數（包含 **0**）、手動顏色、明確停用狀態與有效來源 Notes 都算註記。只有父技術有註解，不會讓未註記的子技術符合條件。

這個操作展開的是**家族**：展開後，其他兄弟子技術仍依既有搜尋／隱藏停用篩選顯示，不會被刪除，也不會因此加入選取清單。例如父技術有五個子技術，只有一個有註解，該家族會展開；另一個家族只有父技術有註解，就維持收合。

Expand annotated、Expand all、Collapse all 分別保存 `layout.expandedSubtechniques` 為 `annotated`、`all`、`none`，會讓文件待儲存，並在圖層切換、Save／重開、Navigator 交換及復原時還原。個別箭頭現在會保留其他家族，保存逐 Tactic 的標準 `showSubtechniques`，選單切換為 **Per-technique · saved**；Mini 也遵守明確收合旗標。搜尋可暫時展開命中家族，清空後還原保存狀態，不會保存自動展開。勾選與註記不變。SVG 選 **Show children expanded when export opened** 可匯出畫面。詳見[個別展開範例](detection_interaction+_zh.md)、[全域模式](visibility_expansion_presets+_zh.md)與[SVG／Excel 匯出](aggregation_and_exports+_zh.md)。

## 註記視覺提示

| 顯示 | 意義 |
| --- | --- |
| 黃色底線 | 非空註解、使用者 Metadata 或來源 STIX Note |
| 藍色底線 | 已指定 Links |
| 同時兩條線 | 兩類註記都存在 |
| 單純勾選沒有提示線 | 保留選取標記與只有分隔列的清單不算註記 |

Flat／Side／Mini 都會顯示提示，包括被選取、被停用或關閉 **Show layer colors** 的格子。只有分數／顏色／狀態時，可參與已註記家族判定，但不會單獨產生註解／連結線。清除最後一份相關註記後，重新繪製就會移除提示；若來源 Notes 或其他 Metadata 仍存在，清除可編輯註解後黃色線仍可能保留。

滑鼠提示會保留完整識別資訊、註解、Metadata、Links 與來源 Notes。Notes 來自精確領域／版本／資料集內，透過 `object_refs` 參照該技術的有效 STIX `note` 物件；撤銷、棄用或無關的參照不顯示。Notes 是唯讀來源內容，不會變成可編輯 Comment 或 CSV 的使用者註解欄。自訂 Bundle 的 Note 不必有 `name`，使用 `abstract` 與 `content`。

**Show all layers** 會合併相容圖層的提示，不依賴該來源是否有顏色；滑鼠提示會列出來源圖層的註記文字。名稱／ID 與標頭色仍使用目前編輯圖層的設定。

## 匯出與運作流程

SVG 套用已保存的名稱／ID、Flat／Side 標頭色，以及黃／藍底線；Mini SVG 維持小格子、註記／狀態符號及提示。兩種 Excel 都依已保存開關產生直向標籤矩陣，即使原生畫面是 Mini 也是如此。標頭填色保留設定，黃色下框線代表註解／Metadata，藍色右框線代表 Links；Excel 註解保留完整識別資訊與來源 Notes。詳細資料工作表及 JSON／CSV 的 ID／名稱不受顯示開關影響。

顯示設定在 **1/2 驗證 → 2/2 套用** 前會顯示 **Input files: None／Output files: None**；已註記家族展開會在 **1/2 解析 → 2/2 更新欄位** 前標示沒有檔案輸入／輸出。儲存、匯出與復原仍會先顯示最終／暫存檔絕對位址，再顯示原有階段進度；讀取目錄時會顯示絕對輸入路徑。繪圖或閱讀 Notes 不會寫入 Bundle，無效設定或取消會保留原狀態。

## 驗證

設定 `QT_QPA_PLATFORM=offscreen` 後執行 `.venv\Scripts\python.exe -B audit_matrix_display.py`。測試會顯示絕對位址及七階段進度，檢查實際提示線像素與清除、tactic 範圍／選取獨立性、Mini／Side、來源 Notes、文件／復原往返，以及 SVG／Excel 讀回。範例與 `audit.json` 位於 `artifacts/matrix-display`。

- [SVG 範例](../artifacts/matrix-display/matrix.svg)
- [Excel 範例](../artifacts/matrix-display/matrix.xlsx)
- [English manual](matrix_display_en.md)
