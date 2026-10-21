# 圖層分數公式操作手冊與範例

本手冊說明圖層分數公式的用途、分數定義，以及如何在 Fusion Studio 產生分析圖層，或與官方 ATT&CK Navigator 交換資料。

## 目前支援範圍

使用 **Navigator → Create layer from score formula…**，最多 26 份來源快照對應變數 `a`–`z`，須使用相同領域、版本與資料集。支援官方 ATT&CK v4 以上及相容的自訂資料。視窗分為 **Formula and scope**（公式與範圍）及 **Inherit properties**（屬性繼承）兩頁。開啟視窗與計算本身不寫入檔案。

| 表達式 | 範例 | 意義 |
| --- | --- | --- |
| 四則運算與次方 | `(a+b)/2`、`a%2`、`a^2` | 平均、餘數、次方 |
| 比較 | `a>b`、`a>=75`、`a==b`、`a!=b` | 成立為數字 1，否則為 0 |
| 布林 | `(a>b) and (a>=75)`、`a or b`、`a xor b`、`not a` | 非零為真，結果為 1／0 |
| 條件式 | `a>b ? 25 : 10` | 依條件選擇分數 |
| 函式 | `max(a,b)`、`sqrt(abs(a-b))`、`round(a/3,2)` | 使用允許的數學函式 |

次方使用 `^`，從右往左結合，且優先於正負號：`2^3^2` 為 512，`-2^2` 為 -4。`and`／`or` 與條件式只計算需要的算術分支。建立結果前先選 **Formula syntax（公式語法）**。視窗預設 **Navigator scalar**；若要重現先前 Studio 的計算規則，選 **Studio scalar**。既有已儲存圖層維持原本的結果，不會自動重算。

### 純量語法與函式（NAV-018）

兩種純量語法皆提供常數 `pi`、`e`、`tau`、`phi`、`true`、`false`。在 Studio 計算模式中，若來源表列出圖層 `e`，它優先代表該圖層；自然常數請改寫成 `exp(1)`。Navigator 計算模式會先以空變數環境嘗試常數，詳見下節。

| 函式類型 | 支援函式與參數 |
| --- | --- |
| 原有算術 | `abs(x)`、`min(...)`、`max(...)`、`sqrt(x)`、`pow(x,y)`、`log(x[,base])`、`exp(x)` |
| 捨入 | `round(x[,digits])`、`floor(x)`、`ceil(x)`；Navigator 的 floor／ceil 也可指定 digits |
| 三角，角度使用弧度 | `sin(x)`、`cos(x)`、`tan(x)`、`asin(x)`、`acos(x)`、`atan(x)`、`atan2(y,x)` |
| 雙曲 | `sinh(x)`、`cosh(x)`、`tanh(x)`、`asinh(x)`、`acosh(x)`、`atanh(x)` |
| 對數與微小值 | `log2(x)`、`log10(x)`、`log1p(x)`、`expm1(x)` |
| 實數工具 | `cbrt(x)`、`sign(x)`、`fix(x[,digits])`、`mod(x,y)` |
| Studio 擴充 | 區分大小寫的 `nthRoot(x[,root])`；預設二次根，負數 x 須使用奇整數根，負根次取倒數 |

`log(x)` 是自然對數。`fix` 向零截斷並修正捨入誤差，`cbrt(-8)` 為 -2，`sign` 回傳 -1／0／1。仍限制在實數定義域：`asin(2)`、`acosh(.5)`、`atanh(1)`、零根次都會失敗。新增的 `fix` 在兩模式都限制精度為 0–15；`mod` 函式在兩模式皆採 Navigator 規則。

| 行為 | Navigator scalar（新視窗預設） | Studio scalar（舊有算術／Python API 預設） |
| --- | --- | --- |
| 大小寫 | 整份公式轉小寫；`SIN(PI/2)` → 1 | 區分大小寫，寫 `sin(pi/2)` |
| 中間值捨入 | `round(2.5)` → 3、`round(-2.5)` → -3 | 取偶數：分別為 2、-2 |
| 小數精度 | round／floor／ceil／fix 須為 0–15 整數，含誤差修正 | round 可用 ±100 整數；floor／ceil 僅一個參數 |
| 比較 | 相對容差 1e-12、絕對容差 1e-15；`.1+.2==.3` → 1 | 精確浮點比較；該例為 0 |
| 連續比較 | 相鄰值比較，短路求值；`3>2>1` → 1、`(3>2)>1` → 0 | 明確寫成 `(a<b) and (b<c)` |
| `not` 優先序 | 與一元運算同級；`not 0>1` → 0 | 沿用舊規則；`not 0>1` → 1 |
| 餘數 | `%`、中綴 `mod`、`mod(x,y)` 用向下取整商數；`5 mod -3` → -1、`3%0` → 3 | `%` 沿用舊規則且拒絕零除數；可用新增的 `mod(x,y)` |
| n 次根 | 拒絕：官方轉小寫會將 `nthRoot` 變成未定義的 `nthroot` | `nthRoot(-8,3)` → -2、`nthRoot(16,-2)` → .25 |

Navigator 範例：`0<=a<=100 ? round(a,2) : 0`、`max(0, sin(pi/2)*a)`、`mod(a,10)`。當 a=80 時，結果分別是 80、80、0。語法記錄在 `x_ttp_studio_formula.syntax`；舊有紀錄缺此欄代表歷史 Studio 語意。Studio／Navigator JSON 與工作階段復原皆保留此欄；匯出結果不會要求官方 Navigator 重新執行公式。

本次以 [Navigator v5.3.2 的轉小寫／運算流程](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/services/viewmodels.service.ts) 與 mathjs 15.2.0 比對，詳見[可重現的參考測例](../scripts/formula-reference/README.md)。這是有限純量子集：隱式乘法、階乘、後綴百分比、賦值、任意函式、陣列／矩陣、單位、複數、物件均拒絕。NAV-019 提供官方缺值／範圍模式，NAV-020 另加入下述自動漸層政策。

### 計算模式：缺值與範圍（NAV-019）

**Calculation mode（計算模式）**與**公式語法**分開。每次新開視窗仍預設 **Studio · 使用指定範圍與缺值政策**。若要採官方來源分數規則，改選 **Navigator · 官方缺值與範圍規則**；此時固定使用 Navigator 純量語法，Studio 的**計算範圍**與**缺少分數**控制停用。切回 Studio 會還原先前選項；小視窗可捲動設定與說明。

| 規則 | Studio 計算模式（預設） | Navigator 計算模式 |
| --- | --- | --- |
| 計算目標 | 已選來源聯集或整張矩陣 | 參照來源中至少有一份分數的有效 Technique／Tactic 格子 |
| 勾選與可見性 | 已選範圍跟隨勾選；整張矩陣忽略顯示篩選 | 勾選、平台／搜尋篩選、隱藏／停用及收合狀態不縮小計算範圍 |
| 部分參照輸入缺分 | 維持未評分，或明確選擇補零 | 缺分補零 |
| 全部參照輸入缺分 | 依 Studio 選定政策 | 保持未評分，不產生人造零分；可建立空結果圖層 |
| 停用來源的既有分數 | 視為缺失 | 仍採用原分數 |
| 真正已儲存的零分 | 是分數 | 是分數，足以讓該格成為計算目標 |
| 常數公式 | 使用所選範圍 | 先嘗試空變數環境，成功則初始化所有有效映射矩陣格子 |
| 未評分結果狀態 | 預設停用，可明確繼承覆蓋 | 預設啟用，可明確繼承覆蓋 |

例如 `(a+b)/2`，a=80、b 缺分時，Navigator 模式結果為 **40**；來源 TTP 即使未勾選或停用也相同。若 a、b 都缺分，結果維持未評分。未使用來源有分數不會擴大目標；只用來繼承的來源可以複製註記／狀態，但不提供計算分數。分數逐 Technique／Tactic 計算，同一技術的 execution／persistence 可有不同結果；父技術彙總顯示不是公式輸入。

空變數探測也遵守短路求值：`0 ? a : 50` 不讀取 a，直接將整張矩陣設為 50。此模式的單獨 `e` 會先解析為自然常數，即使來源表有圖層 e；`e+a` 因空變數探測無法完成，之後逐格運算則使用來源 e（缺分補零）。`exp(1)` 永遠明確代表自然常數。非常數公式的所有來源都未評分時，可產生合法的空結果圖層。

Navigator 模式依來源 JSON 列的順序投影：全域列先展開到映射 Tactic，後面的列會取代該格較早的整列。較晚的精確 Tactic 列若沒有 Score，就清除該格較早全域列的分數；較晚的全域列也能取代較早的精確列。Studio 保留既有精確列／全域後備規則。計算限定目前資料集的有效映射格子；未解析／失效列不成為新增計算目標，原來源仍保留。

操作流程：確認相容來源 → 選 Navigator 計算模式 → 輸入公式與結果名稱 → 選**自動漸層模式**或明確指定繼承來源 → **建立結果圖層** → 核對分數 → 另行儲存／匯出。五階段進度會先宣告輸入／輸出皆在記憶體，再驗證模式／常數探測、讀取快照、計算／繼承、完整驗證並一次新增獨立頁籤。錯誤／取消不發布部分結果，也不改來源。

`x_ttp_studio_formula` 記錄 `mode`、`syntax`、實際 `scope: "navigator"`、`missing: "zero-if-any-score"`、`evaluation: "constant"` 或 `"scored-union"`；Studio 則記錄所選範圍／缺值政策。Studio JSON、Navigator JSON 與工作階段復原保留這些欄位。歷史紀錄缺少 `mode` 代表 Studio 行為，保留原結果而不重算。CSV 保存選取結果 TTP 的註記，並非整份公式設定。

### 公式結果的自動漸層（NAV-020）

在**公式與範圍**頁面的**自動漸層模式**可選**跟隨計算模式**（預設）、**Studio · 來源配色與包含零／一的範圍**、**Navigator · 官方結果範圍與二元色階**。跟隨模式會在 Studio 計算時沿用 Studio 漸層，在 Navigator 計算時採官方漸層；也可獨立選擇色階政策，不改變分數／範圍規則。

| 計算分數 | Navigator 自動漸層 |
| --- | --- |
| 有差異的正分或負分，例如 20／40／80、-80／-20 | 實際最小／最大值，官方紅／黃／綠配色 |
| 範圍恰為 0–1，例如 0／1、0／.25／1 | 透明白 `#ffffff00` → 藍色 `#66b1ffff`，上下限為 0–1 |
| 只有一個分數、全部同分或常數公式 | 預設紅／黃／綠，上下限保留 0–100 |
| 沒有計算分數 | 預設紅／黃／綠與 0–100，不自行新增分數或填色 |
| 明確指定 **Score gradient** 來源 | 完整保留來源漸層，含上下限與透明度，優先於自動政策 |

官方預設配色為 `#ff6666ff`、`#ffe766ff`、`#8ec843ff`。0–1 特例依實際上下限精確判斷，允許中間有小數；全部為零或全部為一因沒有分數範圍，仍採預設配色。最小值若為 `1e-16`，不會誤判為 0–1。常數 200 保留 0–100，顯示上界顏色，但儲存分數仍為 200。Studio 則保留第一個參照來源的配色，範圍包含零且上界至少為一。

範例操作：將兩個 Tactic 格子設為 20、80 → 選 Navigator 計算模式 → 保留**自動漸層模式：跟隨計算模式** → 建立，結果上下限為 20–80。若結果是 0、1 的成員指標，零分透明、一分藍色。若要保留來源配色／上下限，到**繼承屬性 → Score gradient → 指定來源**；自動選單會停用但保留原選項，取消來源後重新啟用。手動色仍優先於分數色；明確停用的結果仍顯示停用樣式。分數先計算再繼承 Enabled，因此被繼承停用的結果分數仍參與自動上下限。

切換政策建立獨立結果，不改來源分數、勾選、啟用狀態或註記。`x_ttp_studio_formula.gradient_mode` 記錄解析後的自動政策（`studio`／`navigator`），`inheritance.gradient` 記錄優先採用的來源。Studio JSON、Navigator JSON 與工作階段復原保留結果漸層及紀錄。舊檔若沒有 `gradient_mode`，包含 NAV-020 前建立的 Navigator 計算結果，都保留當時儲存的漸層，不自動重算。CSV 仍是選取 TTP 的註記匯出，不含完整圖層設定。

固定參考測例實際執行 v5.3.2 的[公式服務](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/services/viewmodels.service.ts)與 [Gradient 類別](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/nav-app/src/app/classes/gradient.ts)，使用固定版開發依賴，比對序列化配色／上下限及分數。原生矩陣、疊圖與 SVG／Excel 沿用既有連續 RGBA 插值及合成，並非逐像素複製官方 100 點 RGB 繪製器。重現步驟及七階段離線漸層檢查見[參考工作流程](../scripts/formula-reference/README.md)，包含原生顏色、SVG 像素及 Excel 填色；應用程式本身不需要 Node／TypeScript 套件。

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
3. 在「威脅技術」圖層中，可利用矩陣的 **TTPs from → Group／Software／Campaign／Mitigation** 加入相關技術。加入清單後仍須設定分數；勾選或顏色不會自動成為分數。
4. 使用 **Score selected…** 或個別 TTP 的註解編輯器設定 Score。以範例的定義建立 `0`／`1` 評分，並在 Comment 紀錄資料來源、驗證方式與日期。
5. 對準備參與計算的每個技術明確填入兩份圖層的分數。未知值保持與 `0` 區別，先釐清處理方式。

### 2. 在程式內建立公式圖層

1. 開啟 **Navigator → Create layer from score formula…**，核對表格中 `a`、`b` 對應的來源檔案名稱。
2. 在 **Formula and scope** 輸入結果圖層名稱及 `a * (1 - b)`；本範例保留 **計算模式：Studio**，再選 **Formula syntax（公式語法）**及 **Selected TTP union from referenced sources**（參照來源已選 TTP 聯集）或 **Entire matrix**（整張矩陣）。若要採官方規則，先參考上方模式對照表。
3. **Missing scores** 預設保留未知：任一參照分數缺失／停用時，該結果維持未評分。只有明確決定將缺失值當成 0 時，才改選零值處理。
4. 視需要在 **Inherit properties** 分別指定各項屬性的來源，再按 **Create result layer**。背景工作依序顯示 1/5 驗證、2/5 讀取快照、3/5 計算與繼承、4/5 驗證完整結果、5/5 完成，然後開啟獨立的新圖層。
5. 核對上表的三種情況。在 **Layer settings…** 設定 0–1 的漸層，讓 `1` 顯示紅色。

以下範圍／缺值段落說明 **Studio 計算模式**。公式逐個 Technique／tactic 使用原始 Score；父子彙總顯示不是公式輸入。預設的 **Selected TTP union** 只計算公式參照來源已勾選的 tactic 範圍。未使用的變數不影響缺失值或計算目標；常數使用所有列出來源的勾選聯集。只提供繼承屬性的來源不擴大計算目標。

**Entire matrix** 計算所有有效技術、子技術及其映射 tactic，包括目前收合、停用或被平台／搜尋篩選的格子。一次全部設成 50 的操作：開啟任一相容圖層 → 輸入 `50` → 選 **Entire matrix** → 保留預設繼承選項 → 建立。來源完全沒有勾選 TTP 也能使用。後續繼承的篩選只影響顯示，不縮小計算範圍。

預設缺失值規則檢查**公式提到的所有變數**，包含未採用的條件分支；任一輸入缺失／停用，該格維持未評分。只有明確決定未知值視為零時才選零值政策。真正的零分仍會評分並納入選取。在計算目標內，來源原始分數是否參與計算與來源勾選狀態分開處理。有計算分數的結果即使繼承停用狀態也仍被選取；未評分結果預設停用，但明確指定的狀態來源可以覆蓋預設值。

### 各項屬性分別繼承

每個下拉選單都可以選不同來源。例如計算 `(a+b)/2`，**Comments** 選 `a`，**Manual colors** 選 `b`，漸層保留自動設定。

| 屬性 | 複製內容 |
| --- | --- |
| Score gradient | 指定來源就完整保留顏色／上下限，優先於自動漸層模式；未指定時依所選 Studio／Navigator 政策 |
| Manual colors／Comments | 精確 tactic 註記，沒有時取技術全域列；手動顏色會覆蓋分數色 |
| Links／Metadata | 技術及圖層層級清單，保留分隔列與擴充欄位 |
| Enabled states | 逐 tactic 狀態；來源沒有對應列時預設啟用 |
| Filters／hide disabled | 平台篩選與隱藏停用設定；不改變公式涵蓋範圍 |
| Legend | 來源圖層圖例 |

除了自動漸層，其他預設為 **Do not inherit**。缺少的屬性維持空白，不會自行產生顏色或父子繼承；Studio 精確 tactic 列／全域整列後備規則和原生矩陣一致，Navigator 則採上方的來源列順序投影。來源的保留選取標記會移除。即使繼承圖層 Metadata，公式來源紀錄仍保留在 `x_ttp_studio_formula`。來源名稱、分數、顏色、勾選與儲存狀態都不改變；結果會關閉疊色模式以顯示自身。

### 3. 匯出與官方工具交換

1. 用既有檔案匯出功能選擇 Navigator Layer JSON，或用 **Navigator → Export all open layers…** 匯出來源與結果圖層。目的資料夾須存在，例如先建立 `examples` 再儲存 `examples/layers.navigator.json`。
2. 寫入前會顯示最終／暫存檔的絕對位址，並顯示驗證、寫入及發布進度。
3. 可用 **Navigator → Open ATT&CK Navigator website** 開啟官方工具，載入匯出的 JSON。計算分數與標準繼承屬性可使用；Studio 的公式來源擴充欄位是紀錄，不會指示官方工具重新計算。
4. 外部產生的結果可用 **File → Import Navigator Layer** 載回桌面程式。

公式輸入與輸出都在記憶體，運作前會顯示 **Input files: None／Output files: None**。完整 Studio JSON 請用 **Save／Save As**；Navigator JSON／CSV 另行匯出，寫檔前會顯示最終與暫存檔的絕對位址及分階段進度。Studio JSON、Navigator JSON 與工作階段復原保留分數、繼承屬性與公式來源紀錄；CSV 保存選取 TTP 的註記，不是完整圖層設定。詳見[文件儲存手冊](studio_files+_zh.md)與[分數彙總及矩陣匯出](aggregation_and_exports+_zh.md)。

公式上限為 512 字元、128 個語法 token、24 層巢狀。數值須為 ±1e300 內的有限實數，指數絕對值上限 10000，min／max 最多 32 個參數。未知變數／函式、不支援的語法、除以零、Studio `%` 的零除數及數學定義域／溢位錯誤會中止，不建立部分圖層。Navigator 取餘數遇到零除數會回傳被除數。**Cancel／Close** 會在背景工作的檢查點取消。失敗後可修正並重試，來源維持不變。

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
