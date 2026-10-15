# 圖層分數公式操作手冊與範例

本手冊說明圖層分數公式的用途、分數定義，以及如何在 TTP Selection Studio 產生分析圖層，或與官方 ATT&CK Navigator 交換資料。

## 目前支援範圍

TTP Selection Studio 現已支援 **Navigator → Create layer from score formula…**。支援數字、圖層變數 `a`–`z`、`+`、`-`、`*`、`/`、正負號及括號，最多 26 份相同領域／版本的來源圖層，限 ATT&CK v4 以上。比較、布林、函式等其他表達式尚未加入；需要時仍可在[官方 ATT&CK Navigator](https://mitre-attack.github.io/attack-navigator/)使用其較完整的公式介面。

## 公式與分數代表什麼

公式將來源圖層中同一個 Technique 的分數，計算成新圖層的分數。例如 `a` 是圖層 A、`b` 是圖層 B，某個技術的分數分別為 80 與 60，使用 `(a+b)/2` 後，其結果為 70。分數含義需要先由使用者定義；本手冊以下的數據皆為假設範例。

## 範例：找出偵測缺口

先定義兩份圖層的評分規則：

- **a：威脅技術清單**。納入這次威脅分析的技術設為 `1`，其餘設為 `0`。
- **b：偵測能力**。已驗證能偵測的技術設為 `1`，已確認沒有偵測能力的技術設為 `0`。

使用公式：

```text
a * (1 - b)
```

| Technique | a：威脅技術 | b：能偵測 | 計算結果 | 解讀 |
| --- | ---: | ---: | ---: | --- |
| 技術甲 | 1 | 0 | 1 | 這次分析中的偵測缺口 |
| 技術乙 | 1 | 1 | 0 | 已有偵測能力 |
| 技術丙 | 0 | 0 | 0 | 不在這次威脅分析範圍 |

結果 `1` 可以用紅色標示，協助安排補強工作；它是這套評分規則下的缺口標記，不能直接解讀為攻擊發生機率。尚未測試的技術應標示為未知，先決定是否排除或另外處理，再納入運算。

## 操作流程

### 1. 在桌面程式準備來源圖層

1. 依[專案 README](../README.md)啟動程式。
2. 用 **Navigator → New layer** 建立兩份檔案，分別重新命名為「威脅技術」與「偵測能力」。確認兩份檔案使用相同 ATT&CK 領域及版本。
3. 在「威脅技術」圖層中，可利用矩陣的 **Add from → Group／Software／Campaign** 加入相關技術。加入清單後仍須設定分數；勾選或顏色不會自動成為分數。
4. 使用 **Score selected…** 或個別 TTP 的註解編輯器設定 Score。以範例的定義建立 `0`／`1` 評分，並在 Comment 紀錄資料來源、驗證方式與日期。
5. 對準備參與計算的每個技術明確填入兩份圖層的分數。未知值保持與 `0` 區別，先釐清處理方式。

### 2. 在程式內建立公式圖層

1. 開啟 **Navigator → Create layer from score formula…**，核對表格中 `a`、`b` 對應的來源檔案名稱。
2. 輸入結果圖層名稱及 `a * (1 - b)`。兩份來源必須使用相同領域及 ATT&CK 版本。
3. **Missing scores** 預設保留未知：任一參照分數缺失／停用時，該結果維持未評分。只有明確決定將缺失值當成 0 時，才改選零值處理。
4. 按 **Create result layer**。背景工作會顯示 1/4 驗證、2/4 讀取快照、3/4 計算、4/4 完成，然後開啟獨立的新圖層。
5. 核對上表的三種情況。在 **Layer settings…** 設定 0–1 的漸層，讓 `1` 顯示紅色。

公式逐個 Technique／tactic 使用原始 Score 計算，範圍是公式參照來源中已勾選 TTP 的聯集；未使用的來源變數不會影響缺失值判定。常數公式如 `50` 使用表格中所有來源的勾選聯集。結果保留公式與來源名稱／UUID，來源檔案不會被修改。圖層的父子彙總顯示不是公式的輸入。

### 3. 匯出與官方工具交換

1. 用既有檔案匯出功能選擇 Navigator Layer JSON，或用 **Navigator → Export all open layers…** 匯出來源與結果圖層。目的資料夾須存在，例如先建立 `examples` 再儲存 `examples/layers.navigator.json`。
2. 寫入前會顯示最終／暫存檔的絕對位址，並顯示驗證、寫入及發布進度。
3. 可用 **Navigator → Open ATT&CK Navigator website** 開啟官方工具，載入匯出的 JSON。若需較進階表達式，再透過其 **Create Layer from Other Layers** 與 **Score Expression** 操作。
4. 外部產生的結果可用 **File → Import Navigator Layer** 載回桌面程式。

輸入是記憶體中的來源快照，公式結果是新圖層；只有另外匯出時才寫入檔案。公式不會繼承來源手動色，以免覆蓋新分數的漸層。除以零、未知變數、非有限結果與不支援的語法會顯示錯誤，並且不建立部分結果。SVG／Excel 操作見[分數彙總與矩陣匯出手冊](aggregation_and_exports+_zh.md)。

## 其他可用的分析例子

| 用途 | 分數定義 | 公式 | 結果代表 |
| --- | --- | --- | --- |
| 比較改善前後 | a＝改善後、b＝改善前，使用相同 0–100 評分標準 | `a-b` | 正值表示評分提升 |
| 整合兩組評估 | a、b 使用相同指標與尺度 | `(a+b)/2` | 兩組評估的平均值 |
| 統計多個威脅的共同技術 | a、b、c 各以 0／1 標示是否納入該清單 | `a+b+c` | 有幾份清單包含該技術 |
| 找出兩份清單共同技術 | a、b 各使用 0／1 | `a*b` | 1 表示兩份清單都包含該技術 |

## 檢查重點

- 來源圖層須使用相同領域及 ATT&CK 版本，並確認公式中的變數對應。
- 先記錄評分定義、尺度、證據及未知值的處理方式；空白分數與 `0` 不相同。
- 公式逐項計算 Technique；具有不同 tactic 註解的同一技術，可能產生不同結果。
- 「Show all layers」是視覺疊色；本手冊的公式會產生帶有計算分數的新圖層。
- 使用少量已知資料核對結果後，再套用到完整清單。

## 參考資料

- [官方圖層公式說明](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#creating-layers-from-other-layers)
- [官方分數說明](https://github.com/mitre-attack/attack-navigator/blob/master/USAGE.md#scoring-techniques)
- [官方 Navigator GitHub 專案](https://github.com/mitre-attack/attack-navigator)
- [English manual](layer_score_formulas_en.md)
