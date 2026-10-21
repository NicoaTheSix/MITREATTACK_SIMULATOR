# Navigator 搜尋、顯示與右鍵操作

這份手冊說明對照官方 Navigator 後完成的原生桌面操作。完整差異及後續順序見 [NOTIMPLEMENTYET.md](../NOTIMPLEMENTYET.md)。[English](navigator_parity_controls_en.md)

## 來源搜尋欄位

側邊欄選 Groups、Software、Campaigns、Mitigations、Assets 或 Detections，再開 **Source search fields…**。Name、ATT&CK ID、Description 可獨立勾選，至少保留一欄；舊文件預設三欄都開啟。設定屬於每份圖層，與 TTP 搜尋欄位獨立。

矩陣的同名按鍵控制 **TTPs from** 八類完成清單：Campaign、Software、Group、Mitigation、Asset、Detection Strategy、Data Component、Data Source。更改欄位會清除待執行的來源選擇，請重新選定完整 ID／名稱才按單筆 Add／Remove，或使用「加入搜尋結果的所有 TTP」／「取消選取搜尋結果的所有 TTP」。來源文字搜尋不更動 TTP 勾選。詳見[來源批次操作](source_relationship_selection+_zh.md)；Analytics 仍僅供瀏覽。

**範例：** 關閉 Name 與 ID，只留 Description，輸入描述中的連續片語；支援空格及大小寫差異。標題相符但描述不符的項目不會命中。名稱或 ID 即使出現在描述內，仍會作為描述文字命中。

側欄在 library 分類只顯示來源控制；回到 TTP 則顯示 TTP 專用控制。

## 分別控制背景與註記提示

開啟 **Layer settings… → Colors / indicators**：

| 控制 | 作用 |
| --- | --- |
| Show manually assigned technique colors | 顯示已指定的手動色 |
| Show original score gradient colors | 顯示原始分數的漸層 |
| Show aggregate score gradient colors | 顯示父子彙總分數的漸層 |
| Show comment / source Note indicators | 註解與有效來源 Note 的提示線 |
| Show metadata indicators | 使用者 Metadata 提示線 |
| Show link indicators | Links 提示線 |
| Show matrix legend | 在保留技術色的情況下顯示／隱藏 Legend |

優先序為手動色 → 啟用的彙總分數色 → 啟用的原始分數色 → 無註記背景。只有先啟用彙總分數運算並有有效結果時，才有彙總色。關閉開關保留原始數值與色碼；停用技術仍用暗色呈現。**Show layer colors** 仍可整體隱藏矩陣背景色。

三種提示線分別接受 `#RRGGBB`。為相容舊畫面，Comment 與 Metadata 預設黃、Links 預設藍；相同色合併為一條線。指定三個不同顏色時可同時顯示三條。Flat／Side／Mini／SVG 使用相同投影；Excel 對應下／右／上框線。全部圖層檢視使用作用中圖層的提示線偏好，各來源背景仍依來源自己的色彩開關混合。

**範例：** 技術有手動紅色及分數 50，關閉手動色後顯示 50 的漸層。再關閉原始分數色後，沒有彙總結果的技術回到一般底色；分數與手動紅色仍保留。重新開啟即還原。這與刪除手動色是不同操作。

**Legend → Clear all legend items** 只清空草稿；Save 套用、Cancel 放棄。SVG 的 Show legend 是匯出專用設定，與矩陣的 Legend 顯示開關分開。

## 父技術的已註記子數

Flat／Side 收合時顯示例如 `Parent [2 annotated] (5)`；展開後只保留總數。Tooltip 仍提供「2 annotated / 5」。Mini 不增加文字標籤，透過 Tooltip 查看。

計數依目前平台／Tactic 的映射子技術去重，包含該家族被隱藏的停用子項。分數含零、Comment、使用者 Metadata、Links、手動色、停用狀態、有效來源 Note 都算註記；只有 divider、內部勾選 metadata 或展開旗標不算。關閉提示線不會改計數。子技術總數是映射數，不是勾選數。數量提示只供矩陣介面，不增加匯出的 TTP 或改寫 SVG／Excel 的標籤格式。

## 技術右鍵與自訂網址

右鍵技術可加入／移除／只選此項／反選，也有本 Tactic 與矩陣的批次命令。它們沿用跨 Tactic、家族連動及只選可見偏好；右鍵本身不改選取。View technique details 開原生詳情；有有效來源網址時，Open technique/tactic reference 才出現。

開 **Layer settings… → Context actions**，新增 Label、URL template、可選 Sub-technique URL。例如：

```text
Label: Internal reference
URL: https://example.org/techniques/{{technique_attackID}}?tactic={{tactic_attackID}}
Sub-technique URL: https://example.org/techniques/{{parent_technique_attackID}}/{{subtechnique_attackID_suffix}}
```

可用參數為 `technique_*`、`tactic_*`、`parent_technique_*`、`subtechnique_*`，各支援 `attackID`、`stixID`、`name`，另有 `subtechnique_attackID_suffix`。Name 轉小寫、空格轉連字號，再對代入值作 URL 編碼。沒有父技術、Tactic 或所需識別資料時停用該動作。Save 後在技術右鍵 **Custom actions** 檢查；滑鼠停留顯示解析後 URL，實際點擊才開系統瀏覽器。

僅允許固定主機的 HTTP(S) URL；未知 placeholder、不成對括號、內嵌帳密與其他協定會阻擋儲存並保留草稿。模板不執行程式。這些是每圖層原生設定，不是修改官方 Navigator 的部署 config.json。

## 儲存、進度與驗證

純記憶體操作先顯示沒有輸入／輸出檔案，再報建立索引、驗證、套用及完成。設定草稿只有 Save 後才更動文件；取消或失敗保留原文件。實際寫檔使用既有 Save／Save As，先顯示解析後的輸入／輸出絕對路徑，分階段驗證及原子寫入。

來源欄位、視覺偏好及網址模板以 `x_ttp_studio_*` 欄位保存在 Studio、Navigator JSON、複製及工作階段復原中。官方 Navigator 不支援這些原生延伸，可能在重新匯出時丟棄。CSV 保留選取／註記交換格式，不還原顯示偏好。

從專案根目錄執行：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_navigator_parity.py'
```

七階段檢查會先列出 `<project-root>/data/attack` 及 `<project-root>/artifacts/navigator-parity` 的絕對位址，再產生隔離 fixture、Studio、復原範例、SVG、Excel、截圖及 `audit.json`。包含全部背景／提示線開關組合、欄位隔離、收合計數、右鍵分派、錯誤及取消保護、重開／復原與匯出。檢查不連網、不變更官方資料指標。
