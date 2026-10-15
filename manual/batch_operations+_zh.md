# 獨立啟用狀態與批次操作手冊

## 納入輸出與啟用狀態

勾選框代表「將此 TTP 納入選取清單匯出」；Enabled 控制圖層顯示、分數彙總／公式參與，以及 Hide disabled 啟用時的可見性。兩者獨立：已勾選但停用的 TTP 仍會匯出；未勾選但啟用的 TTP 可以保留並顯示圖層註解。改變勾選不會重寫啟用狀態或自動產生顏色。

矩陣 **State… → Enable selected／Disable selected／Toggle selected states**、Selected Techniques 的狀態選單，以及 Navigator 的 Enable／Disable 動作，作用於已納入 TTP 的所有有效範圍。技術右鍵也提供整個技術或 **Enable／Disable in this tactic**，未勾選的技術也可操作。單筆註解編輯器的 Include 與 Enabled 分開，Enabled 只修改目前選擇的註解範圍；特定 Tactic 列優先於全域列。停用／重新啟用會保留顏色、分數、註解、Links 與 Metadata。所有圖層檢視中，其他啟用圖層仍可能提供顏色；狀態操作只修改目前圖層。

範例：勾選 T1053.005、加入註解與分數後停用，勾選不會取消、資料也不會刪除。Studio JSON／CSV 的選取列包含全域 `enabled` 與依 Tactic 排序的 `tactic_enabled`；Navigator JSON 保存實際啟用旗標與程式的選取 Metadata，重新匯入可分別還原「停用」與「已納入」。Navigator 圖層包含已自訂或已選取項目；Studio／CSV 的選取清單只列已納入 TTP。

## 批次選取

打開矩陣，選擇 **Selection scope**：

- **Platform scope · includes hidden**：目前平台聯集中的技術，包含收合的子技術及被隱藏的停用技術，忽略搜尋文字。
- **Search matches · excludes hidden**：直接比對名稱／ID，不分大小寫、可輸入空格，排除隱藏的停用技術；不會自動勾選僅供祖先脈絡的父技術。
- **Visible / expanded cells**：篩選後顯示的矩陣格，包含已展開子技術；不是只計算捲動視窗內的像素。

可再限定一個 Tactic。純分組用途、未映射到範圍的父技術不會被勾選。按 **Select…**：

- Select all in scope：加入此範圍，保留範圍外選取。
- Select only this scope：用此範圍取代整份選取清單。
- Deselect scope：只取消此範圍。
- Invert scope：只反轉此範圍的勾選。
- Select annotated only／Select unannotated only：用範圍內已註解／未註解的子集合取代整份選取清單。

「已註解」指非空註解／顏色／Links、有分數（包括零）、使用者 Metadata／分隔線，或停用狀態。程式維護的選取 Metadata 與展開偏好不計入。限定單一 Tactic 時檢查該範圍的有效註解；所有 Tactic 時任一有效範圍有註解即符合。Tactic 標題右鍵也可加入、取消或反轉該平台／Tactic 範圍。選取仍以技術 ID 跨 Tactic 同步，不改變註解或啟用狀態。

## 批次編輯

使用矩陣 **Batch edit selected…**、Selected Techniques 的 **Batch edit included TTPs…** 或 **Navigator → Batch edit selected TTPs…**。目標是目前文件全部已納入 TTP，包括矩陣篩選外的項目。開啟時每個欄位都預設 **Keep unchanged**。

範圍可選 **Entire technique · all mapped scopes**，或顯示受影響數量的單一 Tactic；不映射到該 Tactic 的 TTP 會略過。各欄位獨立選擇設定或清除：

目標清單會列出確切技術 ID／名稱；滑鼠停留可先檢查目前全域或指定 Tactic 的值。切換範圍時，受影響與略過數量也會更新。

| 欄位 | Set / replace | Clear / reset |
| --- | --- | --- |
| Enabled state | 啟用、停用、逐範圍反轉 | 恢復預設啟用 |
| Comment | 文字，可包含換行 | 移除註解 |
| Score | 有限數字，零有效 | 恢復未評分 |
| Color | `#RRGGBB` | 移除明確顏色，分數漸層可能仍存在 |
| Links | 取代標籤／HTTP(S) 網址／分隔線清單 | 移除使用者連結 |
| Metadata | 取代文字名稱／值／分隔線清單 | 移除使用者資料，保留程式的選取 Metadata |

範例：選取 20 個 TTP，將 Comment 設為 `Validated in lab`、Score 設為 `0`，其他保持 Keep，套用只修改這兩欄。再選單一 Tactic 編輯，只影響映射到該 Tactic 的項目。建立新的 Tactic 列時會先複製目前全域註解，保留未修改欄位；既有範圍覆寫保持獨立。

**Clear all selected annotations…** 會開啟六個欄位都選 Clear 的草稿；確認目標與範圍後 Apply。它重設啟用狀態、移除已知註解欄位，保留勾選、排版偏好與未知擴充欄位。若要保留顏色／分數，先把相應欄位改回 Keep。無法映射的歷史註解範圍仍會保留。

## 處理進度與保存

執行前 Output 顯示輸入／輸出都在記憶體，不寫檔；進度依序為驗證、逐項修改草稿、完整驗證。批次編輯使用背景工作，成功後才一次套用；無效分數／顏色／URL、取消或中斷都不改變原文件。狀態與選取操作也會顯示階段。直到 Export 才寫檔，屆時先顯示輸出與暫存檔的絕對路徑。

修改只屬於目前文件／領域／版本／資料集，複製圖層及記憶體領域／版本封存會保留獨立狀態。Session 復原與 Studio JSON 重開仍是另外的未完成功能；需要完整註解及封存時，關閉前請匯出 Studio JSON。啟動與驗證命令見 [README](../README.md)。
