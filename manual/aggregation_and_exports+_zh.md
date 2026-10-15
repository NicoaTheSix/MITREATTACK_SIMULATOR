# 父子技術分數彙總與矩陣匯出

本手冊適用於 TTP Selection Studio 的 ATT&CK v4 以上圖層。啟動與環境設定見[專案 README](../README.md)，公式建立新圖層見[圖層分數公式手冊](layer_score_formulas+_zh.md)。

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
4. 在匯出視窗按 **Export SVG／Export XLSX**，等待背景工作完成。

寫入前會顯示輸出檔案及暫存檔的絕對位址，並依序顯示 **1/4 投影、2/4 繪製、3/4 寫入、4/4 發布**。驗證／寫入失敗或在發布前取消時，既有輸出不會被覆蓋，暫存檔會清除。

輸入是目前圖層與已驗證目錄的記憶體快照；輸出是 SVG 或 XLSX。匯出會展開全部符合條件的子技術，包含畫面捲動範圍以外的內容。平台、搜尋、隱藏停用項、色彩顯示與同領域／版本疊色會反映在輸出中。關閉色彩顯示時，輸出也會呈現中性色。

**SVG** 是可縮放的向量圖，包含技術 ID／名稱、原始與彙總分數、漸層／圖例，並在滑鼠提示中保留註解。子技術以 `>` 與縮排標示。

**Excel** 包含三個工作表：

| 工作表 | 內容 |
| --- | --- |
| Matrix | 各 tactic 的彩色矩陣、分數、註解，並凍結標題列 |
| Techniques | 技術／父技術 ID、勾選與停用狀態、原始分數、彙總、顏色與註解，可篩選 |
| Layer Info | 領域、版本、平台、搜尋、公式來源及圖例 |

名稱與註解以文字保存，開頭為 `=` 也不會變成 Excel 公式。Excel 單一儲存格上限為 32,767 字元，超長文字會使匯出明確失敗；需要保存完整長篇註解時請使用 JSON。

SVG／Excel 是展示及分析輸出，不會重新命名檔案或把完整專案狀態標記為已儲存。保存原始分數、註解與跨領域／版本紀錄時，另匯出 Studio JSON；與官方工具交換目前圖層時使用 Navigator Layer JSON。

## 範例檔案與驗證

- [SVG 範例](../artifacts/layer-analysis-example.svg)
- [彩色 Excel 範例](../artifacts/layer-analysis-example.xlsx)
- [SVG 預覽](../artifacts/layer-analysis-svg-preview.png)
- [英文手冊](aggregation_and_exports_en.md)

專案根目錄的 `audit_layer_analysis.py` 驗證運算、介面、SVG 像素、Excel 顏色與數值、失敗／取消處理及來源資料不變；執行方式見專案 README。
