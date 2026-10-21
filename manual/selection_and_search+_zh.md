# 選取偏好、進階搜尋與 Mitigation 批次操作

## 選取行為偏好

從矩陣 **Selection behavior…** 或 **Navigator → Selection behavior** 設定。三個選項屬於目前文件，切換分頁會還原各自設定：

| 選項 | 預設 | 行為 |
| --- | --- | --- |
| Select techniques across tactics | 開 | 勾選／取消一個技術時，同步其全部已映射 Tactic |
| Select parent, children and siblings together | 關 | 開啟後，選父技術會連動子技術；選子技術會連動父技術與兄弟子技術 |
| Select visible techniques only | 關 | 在連動後，僅保留操作來源畫面中邏輯可見的技術／Tactic 格子 |

關閉跨 Tactic 同步時，只修改點擊的 Tactic；父子連動也只包含映射到該 Tactic 的成員，不會勾選僅用於分組的父節點。跨 Tactic 與父子連動開啟、只選可見關閉時，可納入整個家族，包括平台／搜尋下不可見的成員。開啟只選可見，會在連動之後排除收合子項、隱藏停用列與被篩選格子；矩陣／來源批次依矩陣，側欄勾選依側欄。捲動後可見的列仍符合條件。偏好改變只影響後續操作，不回溯擴大或清除既有勾選，也不改顏色、分數、註解或 Enabled。詳見[可見選取與保存展開範例](visibility_expansion_presets+_zh.md)。

**範例：** 關閉跨 Tactic 同步，在 Execution 勾選 T1053.005。它在 Persistence／Privilege Escalation 不會跟著勾選。Selected Techniques 仍只列一筆 T1053.005，下方新增 Selected tactics；同一 Tactic 在其他平台的重複分支保持同步。再開啟跨 Tactic 同步不會立即改動既有選取，下次勾選才套用同步設定。

矩陣 Select… 的加入、取代、取消、反選及 Tactic 標題操作也遵守偏好。已註解／未註解的選取在跨 Tactic 同步開啟時以技術為單位分類；關閉時可區分各個 Tactic 的有效註解。父子連動可讓操作包含額外的家族成員。篩選只影響操作的初始範圍，不會清除範圍外已選內容，除非使用取代選取的功能。

有部分 Tactic 選取時，Batch edit 預設為 **Selected tactic occurrences only**，批次顏色、分數、狀態動作也只改已選格子。編輯器仍可明確選 **Entire technique · all mapped scopes** 或指定 Tactic；右鍵整個技術的動作維持其明示範圍。勾選與 Enabled 分開，取消勾選不會刪除註解或停用技術。

## Description 與 Data Sources 搜尋

TTP 側邊欄按 **TTP search fields…**，矩陣按 **Search fields…**。兩處共用目前文件的搜尋欄位偏好，但保有各自搜尋文字：

- Name、ATT&CK ID：預設開啟。
- Description：搜尋技術描述。
- Data Sources / Components / Log Sources：搜尋版本內可解析的資料來源、元件與日誌名稱／通道。
- Detection Strategy：沿有效直接 `detects` 映射，搜尋策略 Name／ID／Description。預設關閉，不會替舊資料借用新版策略，詳見[偵測策略範例](detection_interaction+_zh.md)。

至少保留一個欄位；查詢在任何已開啟欄位包含該文字即符合。比對不分大小寫，使用字面子字串，不使用正規表示式。可輸入空格，外圍空白僅在比對時計算，輸入框內容與游標不會被改寫。側邊欄按 Enter 或停頓約 180 毫秒後搜尋；矩陣同時支援直接搜尋符合項目的批次選取。

**範例一：** 開啟 Description，關閉 Name／ID，輸入 `PowerShell`，尋找描述提及它的技術，不限技術標題。只顯示符合的分支，保留必要的父節點作為脈絡。

**範例二：** 只開啟 Data Sources，於新資料集搜尋 `Sysmon` 或 `WinEventLog:Security`；舊版可搜尋 `Process Creation`。實際結果依該領域與版本提供的欄位而定，沒有關聯資料時不推測補上。

舊版使用技術的 `x_mitre_data_sources`，以及資料元件的 `detects` 關聯與來源參照。新版可從有效 detection strategy → analytic → log source／data component 參照建立索引；已撤銷的 detects 關聯與已停用的策略／analytic 不參與。來源名稱／通道取自同一快照，不混入其他領域、版本或自訂資料集。

搜尋命中父技術時，其子項仍可作為脈絡顯示；**Search matches** 批次範圍只採用直接符合的技術，不會因父子脈絡而額外勾選（父子連動偏好另行套用）。SVG／Excel 使用相同搜尋欄位。切換圖書分類時，TTP 搜尋及其欄位按鍵會隱藏。Groups、Software、Mitigations、Detections 獨立搜尋 Name／ID／Description，其他分類維持 Name／ID。

## 透過 Mitigation 加入／取消 TTP

兩種入口的結果一致：

1. 左側 **Mitigations** 開啟與目前文件相同領域的項目，按 **Add all TTPs (N)** 或 **Remove all TTPs (N)**。
2. 矩陣 **TTPs from → Mitigation**，展開下拉清單並在同一空格輸入名稱／ID，例如 `M1047`；選中完整清單項目後按 **Add techniques (N)**／**Remove techniques (N)**。

Campaign、Software、Group 也提供相同的取消功能。四種來源下拉搜尋皆預設 Name／ID／Description，可由 **Source search fields…** 個別控制，與 TTP 欄位獨立。結果仍顯示並填入 ID／名稱，滑鼠停留可讀 Description。部分輸入文字只用於尋找項目，不會執行先前項目。沒有有效對應技術的項目不能操作；其他領域的詳情頁按鍵會停用。詳見[來源搜尋控制](navigator_parity_controls+_zh.md)。

Mitigation 僅使用目前文件快照中的有效、直接 `mitigates` 關聯；其他來源使用 `uses`。去除重複目標，不包含撤銷／棄用邊，不推測間接關聯。N 是直接映射的技術 ID 數；實際選取可能因父子連動較多，或因可見限制較少。來源按鍵先採全部已映射 Tactic，再套用父子／只選可見偏好；旁邊 Selection scope／Tactic 選單控制的是 Select…。

**範例：** 先勾選一項不屬於該 Mitigation 的技術，再按 Add。原有勾選仍保留；再按 Remove，只移除該來源目標（含開啟偏好要求的家族）。若同一技術也由另一來源加入，Remove 仍會移除它：來源選取是集合操作，沒有來源所有權追蹤。取消不會改動 Enabled、註解、顏色或分數。

## 儲存、匯出與進度

Studio JSON 新增選取偏好、搜尋欄位及部分 `selection_scopes`，完整保存／重開與 Session 復原均可還原。CSV 的 `selected_tactics` 是每筆技術實際納入的 Tactic 清單，與原有全部映射 `tactics`／`tactic_enabled` 分開。Navigator JSON 使用標準選取偏好旗標、逐 Tactic 的選取 Metadata，以及 Studio 擴充；外部工具可能移除擴充，跨工具回存後請確認選取範圍。早期 Studio 檔缺少新欄位時採相容預設。

複製圖層會獨立複製偏好及範圍；分數公式與已審查的搬移也保留 Tactic 選取邊界。領域封存會保存部分範圍；切換版本時只保留仍有效的 Tactic，不會將失效的部分選取放大為全部技術。

上述操作先顯示記憶體輸入／無直接檔案輸出，再顯示選取、索引或來源解析的階段進度。Save／Export／Session 寫入沿用各自的絕對輸出／暫存路徑及原子發佈流程；搜尋查詢本身不修改勾選，偏好變更會標記文件待儲存。

在專案根目錄驗證：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -B .\audit_selection_search.py
```

使用已快取官方資料（含 v11.3）與程式建立的隔離 STIX 範例；輸出絕對目錄為 `<project-root>/artifacts/selection-search`，包含 Studio／CSV／Session 範例、畫面及 `audit.json`。六階段檢查涵蓋偏好、舊新資料來源、三排版、Mitigation 加入／取消、編輯與儲存往返，並驗證官方指標不變。啟動見 [README](../README.md)，保存與復原見[文件手冊](studio_files+_zh.md)。
