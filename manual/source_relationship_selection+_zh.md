# 來源搜尋結果批次操作與關聯技術選取

[English](source_relationship_selection_en.md) · [完整功能追蹤](../NOTIMPLEMENTYET.md)

## 從搜尋結果整批加入／移除

側欄開啟 Groups、Software、Campaigns、Mitigations、Assets 或 Detections，用 **Source search fields…** 選 Name／ID／Description，再輸入字面查詢。新摘要顯示目前文件 Domain 中符合的來源數、去重技術數與映射 Tactic 格子數。

- **加入搜尋結果的所有 TTP**：將結果來源的技術聯集一次加入，保留其他選取。
- **取消選取搜尋結果的所有 TTP**：一次取消選取同一聯集，保留其他選取。
- 空查詢代表目前分類中所有支援的來源；沒有映射的結果不會更動文件。
- 其他 Domain 的項目仍可瀏覽，但不納入這份文件的批次。Detections 的 Analytics 僅供瀏覽，不作為批次來源。

**範例：** 兩個 Group 都對應 T1059，其中一個另有 T1059.001。搜尋結果有兩個來源、兩個去重技術。「加入搜尋結果的所有 TTP」只加入兩個 ID 一次；原先勾選的其他技術保留。「取消選取搜尋結果的所有 TTP」取消這兩個 ID 的選取。若另一個來源也曾加入相同 ID，仍會取消；目前不追蹤來源所有權。

更改文字、選來源或關閉下拉框都不會更動 TTP；只有按加入／移除才套用。按鍵立即執行，不額外開確認視窗。來源失效、資料集已切換或整批包含無效 ID 時，整批拒絕，避免只套用一部分。

## 矩陣來源選單

**TTPs from** 現在支援八類：Campaign、Software、Group、Mitigation、Asset、Detection Strategy、Data Component、Data Source。

1. 選來源類型，打開列表或輸入名稱／ID／描述查詢；大小寫不敏感、支援空格。
2. 選定完整結果，使用 **Add techniques / Remove techniques** 處理單一來源。
3. 尚在輸入部分文字時，可用 **加入搜尋結果的所有 TTP / 取消選取搜尋結果的所有 TTP** 處理目前所有命中來源；單筆按鍵此時維持停用。
4. 清空文字代表該類所有來源；選定完整結果後，結果批次縮小為該一筆。
5. **View source** 開原生詳情與對應技術表，該頁也有 Add all TTPs／Remove all TTPs。

Data Component 的標籤顯示 `Data Source : Component`，有確切來源參照時才分組。相同顯示名稱會加完整 STIX ID 區分。來源欄位搜尋同時考慮元件及其確切父來源；例如只留 Name，輸入 Data Source 名稱可找到所屬元件。Detections 側欄另有 Data Sources 分類可瀏覽。

**範例：** 切 Detection Strategy，只開 Description，輸入描述中的片語。摘要統計所有命中策略的技術聯集。若要只處理一項，從完成清單選完整結果後再按 Add techniques。

## 關聯的實際含意

來源下拉／完成清單及側欄現在可懸停預覽矩陣。青色實線表示映射格子，父項虛線表示相關子技術收合。側欄按 **Show matrix preview（顯示矩陣預覽）** 可保留來源列表並在右側顯示矩陣。移開後還原，不更動選取、註記或 dirty 狀態。詳見[懸停預覽手冊](source_hover_preview+_zh.md)的範圍與清除規則。

| 來源 | 取技術方式 |
| --- | --- |
| Group／Software／Campaign | 有效來源 `uses` 技術 |
| Mitigation | 有效來源 `mitigates` 技術 |
| Asset | 由技術 `targets` 該資產反向查找 |
| Detection Strategy | 有效策略 `detects` 技術 |
| Data Component | 舊版直接 `detects`；或由策略的 Analytic 日誌來源參照回推 |
| Data Source | 合併以 `x_mitre_data_source_ref` 明確參照此來源的元件技術 |

新版元件路徑為：Strategy `detects` Technique，Strategy 的 `x_mitre_analytic_refs` 指向 Analytic，再由 `x_mitre_log_source_references[*].x_mitre_data_component_ref` 指向 Component。詳情頁用 **Explicit reference path (derived mapping)** 區分衍生映射與原始 STIX 關聯，並提供策略／Analytic／元件／來源的本地連結。

只使用目前文件的資料集、Domain、版本。撤銷或棄用的來源、技術、關聯、Analytic，以及缺少或型別錯誤的參照都不會提供映射。不同名稱相同的物件不會自動連結；只有舊版技術文字欄位的資料來源仍可由 TTP Data Sources 搜尋找到，但不靠該文字虛構來源 ID 或關聯。沒有某種物件的歷史版本顯示空列表。這些關聯表示參考資料映射，不代表已部署或驗證偵測效果。

## 選取偏好與計數

來源操作從技術全部有效映射 Tactic 開始，再沿用家族連動、跨 Tactic 與只選可見偏好。摘要是套用偏好前的來源映射數；完成訊息另列實際變動的 Tactic 格子數。平台篩選、矩陣技術搜尋與子技術收合，會在只選可見開啟時限制資格。Select… 的範圍控制不限制來源按鍵。

**範例：** Windows、Collapse all、開啟家族連動及只選可見，再加入某元件的結果。收合子項與只支援 Linux 的技術不會被額外選入；原本已勾選的其他項目不會清除。

Enabled 狀態與納入清單獨立。來源加入／移除不改分數、手動色、註解、Links、Metadata 或停用狀態。選取可照既有功能保存到 Studio、Navigator JSON、CSV 與工作階段復原；來源關聯本身由對應快取 Bundle 重新建立，不變成 CSV 裡的來源所有權。

## 程式流程與檔案

載入時先顯示 Bundle／pointer 的絕對路徑，再由既有背景工作依序建立直接關聯、策略／Analytic／元件路徑及來源聯集，顯示進度。查詢使用記憶體索引。按批次按鍵先顯示沒有輸入／輸出檔案，再顯示解析／驗證整批、套用偏好、完成三階段；失敗保留原文件。選取本身不寫匯出檔。

Save／Save As 及匯出仍先顯示實際輸入／輸出絕對路徑，驗證後原子寫入。未儲存文件遵循既有關閉提醒與復原流程。

從專案根目錄檢查：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_source_selection.py'
```

七階段檢查先列印 `<project-root>/data/attack` 與 `<project-root>/artifacts/source-selection` 的絕對路徑，再讀取既有官方快取及三 Domain 隔離 fixture，驗證原始 STIX 對照、重疊聯集、同名、錯誤／撤銷參照、可見／家族偏好、過期來源拒絕、Studio／Navigator／CSV／復原往返。輸出包含 `audit.json`、範例與截圖；不下載資料、不變更官方 pointer。
