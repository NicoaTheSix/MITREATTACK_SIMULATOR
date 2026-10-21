# 可見技術選取、展開模式保存與漸層預設

## 只選取可見技術

在 **Selection behavior…** 開啟 **Select visible techniques only**。每份文件獨立保存，預設關閉。此限制在跨 Tactic 與父子／兄弟連動之後套用，連動不會額外選到不可見的格子。

矩陣點擊、Select… 批次、Tactic 標題操作，以及 Group／Software／Campaign／Mitigation 的 Add／Remove，使用目前矩陣的平台、搜尋、隱藏停用與子技術展開狀態。側欄勾選則依側欄自己的篩選與展開分支。「可見」是邏輯上顯示的列，包含捲動後可見的內容，不只目前螢幕的像素範圍。僅作分組的父標題不能選取。矩陣正在重建或沒有對應資料集時，此偏好下的來源操作沒有可選目標；請先開啟矩陣並等候 Ready。

**範例：** 選 Windows、Collapse all，開啟父子連動與只選可見。勾選父技術後，只納入可見的父技術 Tactic 格子，不包含收合的子技術或僅支援 Linux 的成員。Expand all 後再勾選，才會納入可見子技術；Hide disabled 也會排除被隱藏的停用列。

開啟偏好不會清除先前已選的隱藏項目。Remove／Invert 只處理符合可見條件的目標；Replace、已註記／未註記選取仍以符合條件的結果取代整份選取集合。明確指定範圍的顏色、分數、狀態與註記編輯維持原有範圍。來源按鍵數字是直接映射 ID 數，實際變更數可能因可見限制較小，也可能因家族連動較大。

## 保存與還原展開模式

使用 **Expand annotated** 旁的下拉選單，或以下按鍵：

| 操作 | 保存的 `layout.expandedSubtechniques` |
| --- | --- |
| Collapse all | `none` |
| Expand all | `all` |
| Expand annotated | `annotated` |
| Per-technique · saved | 移除全域欄位，使用已保存／匯入的父技術／Tactic 逐項設定 |

三種模式皆支援 Flat、Side、Mini。按 Save 儲存 Studio 文件後才會保存到磁碟。切換圖層、複製、重開、Navigator 交換與工作階段復原都會還原模式。模式變更會讓文件成為待儲存，但不改技術勾選或註記。

Annotated 會展開具有已註記映射子技術的家族：註解、使用者 Metadata、Links、已設定分數（含零）、明確顏色、停用狀態與有效來源 Note 都算註記。只有父技術有註解不符合。展開仍保留其他符合篩選的兄弟子技術。搜尋可暫時展開命中家族，清空後還原保存狀態。個別箭頭現在會保存父技術／Tactic 的 `showSubtechniques`，保留其他家族並切到 Per-technique 模式。Mini 也遵守明確收合旗標，沒有旗標時才使用舊有預設展開。詳見[個別展開與滑鼠範例](detection_interaction+_zh.md)。

**範例：** 替一個子技術新增註解，選 Expand annotated，再 Save。重開後該家族展開，沒有子技術註記的家族維持收合。之後修改註記時會重新計算 Annotated 模式。

SVG 的 **Show children expanded when export opened** 擷取實際畫面；沒有畫面快照時，僅展開項目的投影依保存模式。預設 SVG／Excel 匯出仍包含全部符合篩選的子技術。CSV 不含矩陣顯示設定。

## 來源 Description 搜尋

來源側欄與矩陣 **TTPs from** 八種類別皆預設搜尋 Name、ID、Description，可由 **Source search fields…** 個別控制，與 TTP 搜尋欄位選單獨立。Campaign 也支援 Description。詳見[來源搜尋控制](navigator_parity_controls+_zh.md)與[來源批次操作](source_relationship_selection+_zh.md)。

**範例：** 在 Mitigations 輸入描述中的一句話，即使標題不含該句也能找到。矩陣來源類型切換 Mitigation，輸入同一句話；完成清單仍顯示簡短 ID／名稱，滑鼠停留可讀 Description。必須選定完整結果才能 Add／Remove，部分輸入文字不會執行上一個項目。支援空格及字面標點、不分大小寫，比對忽略外圍空白。搜尋只讀取目前載入的資料，不會抓取其他版本。圖書分類中仍隱藏 TTP 專用控制。

## 漸層預設組合

開啟 **Layer settings… → Gradient preset**。開啟視窗時保留現有漸層，選單從 Custom 開始；選取預設會填入色碼與分數上下限：

| 預設 | 範圍 | 色碼順序 |
| --- | --- | --- |
| Red / Yellow / Green | 0–100 | `#ff6666`、`#ffe766`、`#8ec843` |
| Green / Yellow / Red | 0–100 | `#8ec843`、`#ffe766`、`#ff6666` |
| White / Blue | 0–100 | `#ffffff`、`#007acc` |
| Blue / White / Red | −100–100 | `#2166ac`、`#ffffff`、`#b2182b` |
| Purple / White / Orange | −100–100 | `#762a83`、`#ffffff`、`#e66101` |
| Transparent / Blue | 0–100 | `#007acc00`、`#007accff` |

**範例：** 給技術 −50、0、50 的分數，選 Blue／White／Red 後 Save，分別呈現偏藍、白色中點、偏紅。若表示覆蓋程度，可選 White／Blue，分數越高越藍。顏色沒有固定風險意義，應自行定義並記錄分數尺度。

手動修改後選單回到 Custom，仍支援 2–32 個 RGB／RGBA 色點及有限、遞增的上下限。Save 驗證並套用草稿，Cancel 放棄。選預設不會替技術新增分數、手動顏色或勾選。技術的手動顏色優先於分數漸層，Clear color 後會顯示該分數應有顏色。透明色會與矩陣背景混合。Studio／Navigator JSON 和復原保存實際色碼與範圍；帶色 SVG／Excel 使用這些值。CSV 保持選取技術／註記格式。

## 進度與驗證

操作先顯示記憶體輸入／無直接輸出檔案，再顯示選取、來源／索引、展開及預設填入的階段進度。Save、Export 與復原快照會在原子發佈前顯示最終／暫存檔絕對路徑。取消或設定錯誤保留原文件。

安裝相依套件後，在專案根目錄執行：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -B .\audit_visibility_presets.py
```

七階段檢查會先列出輸入、輸出絕對路徑，再建立隔離 STIX 範例，檢查三種排版、可見與家族／Tactic／來源操作、Description 字面完成及實際輸入、每組漸層與取消、舊檔相容、Studio／Navigator／Session 往返及 SVG／XLSX／CSV 輸出。範例、畫面及 `audit.json` 位於 `<project-root>/artifacts/visibility-presets`，並檢查官方資料指標未變動。

啟動與流程見 [README](../README.md)，另見[選取與搜尋](selection_and_search+_zh.md)、[矩陣顯示](matrix_display+_zh.md)、[文件與復原](studio_files+_zh.md)。
