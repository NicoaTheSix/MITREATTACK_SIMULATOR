# 來源搜尋結果的矩陣懸停預覽

[English](source_hover_preview_en.md) · [來源批次操作](source_relationship_selection+_zh.md) · [功能追蹤](../NOTIMPLEMENTYET.md)

## 矩陣下拉清單與搜尋結果

1. 開啟 ATT&CK Matrix，在 **TTPs from** 選來源類型。
2. 打開下拉清單，或輸入片語讓完成清單出現。
3. 將滑鼠移到結果列；矩陣會以青色外框暫時標示該來源對應的技術。
4. 移開清單或按 Escape，原畫面即還原。若要實際加入，仍需按既有 Add techniques／加入搜尋結果的所有 TTP。

支援 Campaign、Software、Group、Mitigation、Asset、Detection Strategy、Data Component、Data Source。識別依實際 STIX ID，名稱相同也不會混淆。無對應技術的來源會清除前一筆預覽，不沿用前一筆高亮。

**範例：** 在 Group 搜尋含同一片語的兩個來源，依序滑過結果。外框跟著目前那筆來源切換；即使快速移動也不會把兩筆預覽累加。移到清單外，全部暫時外框消失。

## 從來源側欄預覽

在 Groups／Software／Campaigns／Mitigations／Assets／Detections 側欄輸入查詢後，按 **Show matrix preview（顯示矩陣預覽）**。左側保留分類與查詢，右側顯示目前文件的矩陣；待矩陣 Ready 後，直接滑過左側結果即可預覽。

懸停不會自動切換右側頁面。若目前正在看詳情頁，請先按上述按鍵。分類標題、Analytics、其他 Domain 的來源與不支援的列不會預覽目前文件。按來源項目仍依原本行為開詳情；這與移入預覽分開。

## 外框與範圍

| 顯示 | 含意 |
| --- | --- |
| 青色實線 | 該技術／Tactic 格子直接屬於來源映射 |
| 父項青色虛線 | 此 Tactic 有相關子技術，但目前收合 |
| 沒有外框 | 沒有來源映射，或該格子不在目前可見投影內 |

Flat、Side、Mini 都支援。父項虛線只是提示，不會把父技術當成來源技術、不會勾選、不會自動展開。展開／收合仍由原有控制處理，滑過前後保留狀態。

預覽依該來源的確切資料集／Domain／版本及實際技術映射，涵蓋技術有效映射的所有 Tactic，並限制在目前平台投影。搜尋與 Hide disabled 仍控制可見性；被隱藏的停用子項不會在父項產生誤導的提示。只有在相關子項本身可顯示但收合時才提示父項。

**家族連動、跨 Tactic、只選可見是選取偏好，不改變預覽映射。** 預覽描述來源關聯；實際 Add／Remove 才按偏好計算選取。來源沒有特定 Tactic 限制，因此預覽可同時出現在技術的多個有效 Tactic 欄。

**範例：** 一個來源只對應某子技術。在 Collapse all 下，只有該子技術對應 Tactic 的父項顯示虛線；其他 Tactic 的父項不會跟著亮起。滑過不會展開家族或加入父技術。

## 圖層與還原

預覽是獨立的畫面繪製標記，覆蓋在現有底色上；註記提示線繼續顯示。**Show all layers** 下的混色、單層色碼、分數、註解、Links／Metadata、停用狀態及選取都不變。關閉 Show layer colors 後，來源外框仍可顯示。

以下情況清除預覽：移出結果區、關閉下拉／完成清單、Escape 或鍵盤瀏覽、滾輪捲動、更改查詢／來源類型／側欄分類、矩陣重建或篩選、切換文件／Domain／版本／資料集、隱藏矩陣及退出。不同清單分別管理自己的預覽；舊清單較晚送出的移開事件，不會清除新清單的當前預覽。

這些動作不改文件 dirty 狀態或註記，不建立新的圖層，也不執行加入／移除命令。預覽不寫入 Studio、Navigator、CSV、SVG、Excel 或復原資料；螢幕截圖則可以保留當下外框。

## 程式流程與驗證

每次開始預覽先明示無輸入／輸出檔案，接著顯示兩階段：解析記憶體中的來源映射、繪製暫時外框。移開時清空預覽狀態並重繪原本格子，顯示還原完成。沒有下載或寫檔。顯示矩陣入口也先明示無檔案，再報開啟與完成；若需建立欄位則沿用矩陣既有進度。

從專案根目錄執行：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_source_preview.py'
```

檢查先印出 `<project-root>/data/attack`、自身測試程式及 `<project-root>/artifacts/source-preview` 的絕對路徑。七階段涵蓋獨立子程序退出、實際滑鼠移動、三版面像素前後比較、父項提示、完成清單／側欄、快速切換、捲動／關閉、空結果、其他 Domain、檔案切換、Overlay、匯出隔離及資料指標保留。

輸出有 `audit.json`、隔離 fixture、Studio 範例、懸停期間的 SVG 與前後截圖；不下載資料、不改官方 pointer。`--lifecycle-only` 可單獨檢查 Qt 原生視窗銷毀，不讀寫檔案。事件監聽器先判斷是否為滑鼠移動，再讀取 viewport，避免在視窗部分銷毀時存取它。
