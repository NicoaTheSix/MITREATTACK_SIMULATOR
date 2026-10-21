# Studio 文件儲存與工作階段復原操作手冊

## 開啟與儲存

| 操作 | 選單／快捷鍵 | 行為 |
| --- | --- | --- |
| 新文件 | File → New File／Ctrl+N | 建立獨立分頁，預設 Enterprise |
| 開啟 Studio JSON | File → Open Studio JSON…／Ctrl+O | 還原完整文件，開啟後為已儲存狀態 |
| 儲存 | File → Save／Ctrl+S | 第一次選擇位置；之後使用該文件的 Studio JSON 路徑 |
| 另存新檔 | File → Save As…／Ctrl+Shift+S | 選擇新位置，更新分頁名稱與儲存路徑，保留原檔 |
| 匯入 Navigator | File → Import Navigator Layer…／Ctrl+Alt+O | 使用原有 Navigator 版本／ID 預覽流程 |

Studio JSON 與 Navigator Layer JSON 是不同格式。Studio 使用 `schema_version: "1.0"`，保留文件 UUID、建立時間、所選 TTP、獨立啟用狀態、全域／Tactic 註解、顏色、分數、Links、Metadata、排版與領域／版本／搬移封存。選取偏好、搜尋欄位與部分 Tactic 選取也會保存，詳見[選取與搜尋手冊](selection_and_search+_zh.md)。已有的 Studio 1.0 匯出檔也可以開啟；新檔額外保存 `navigator_import_selected` 供精確還原。

**範例：** 新增文件，選取 T1053.005，設定分數、註解並停用。按 Ctrl+Shift+S，選擇 `<project-root>/examples/research.json`（資料夾須先存在）。修改後分頁出現 `*`；按 Ctrl+S 後星號消失。關閉該分頁，再按 Ctrl+O 選擇此檔，確認所選 TTP、停用狀態及註解仍在。開啟同一路徑會切換至既有分頁；不同路徑若有相同文件 UUID，會要求先關閉既有文件，避免混淆。

Save 會保留在程式中重新命名後的名稱；Save As 使用新檔名作為文件名稱。兩者都保留 UUID／建立時間。Save 使用上次儲存檔案的 SHA-256 檢查外部變動；檔案若已被其他程式修改，會停止覆寫，請另選 Save As 路徑或關閉後重新開啟。不能覆寫另一個開啟分頁的儲存路徑，也不能將文件儲存到本程式使用中的復原檔路徑。

CSV、Navigator JSON、SVG、Excel 是交換／報表輸出，不能取代完整 Studio 儲存，也不會清除尚未保存的修改。既有 Export → Studio JSON 因為保存完整文件，也會建立 Studio 儲存路徑與基準。每個分頁的提示會分別顯示儲存路徑及最後匯出路徑。

## 資料集與舊版本

開啟時使用檔案記錄的確切 ATT&CK 領域與版本，包含封存中的版本；不套用目前分頁的版本。官方快照必須已在本機快取，缺少時先使用 Version 下載對應版本，再重試。自訂資料使用 SHA-256 驗證 `<project-root>/data/attack/custom/<sha256>.json`；缺少時先載入相同的 STIX Bundle。跨電腦搬移時，請一併提供自訂 Bundle，並在目的電腦準備相關官方版本。

開啟不會自動存取 JSON 內的來源網址，也不會修改官方 `active.json`／`latest.json`。格式錯誤、未知版本、失效／不一致的選取 ID 或無法解析的封存會顯示錯誤，整份文件不會部分開啟或靜默丟棄 TTP。Studio／復原 JSON 上限 64 MiB，自訂 Bundle 快取上限 128 MiB。

## 關閉與退出

關閉有修改的分頁，或 File → Exit／Ctrl+Q／關閉主視窗時，會詢問 **Save／Discard／Cancel**。

- Save：將列出的修改存成完整 Studio JSON；未有路徑的文件逐一詢問位置。
- Discard：捨棄這次關閉範圍的修改。
- Cancel：保留文件與程式。

取消儲存對話框、驗證失敗或寫入失敗，都會停止關閉。退出儲存多份文件時，若第一份成功、第二份取消，第一份已儲存的結果仍保留，所有分頁繼續開啟。

**退出時選 Discard 會清空整個工作階段復原清單**，避免被捨棄的草稿下次重新出現；已儲存的 Studio JSON 原檔仍在，之後可自行開啟。關閉單一分頁則只從下一個復原檢查點移除該分頁。

## 自動檢查點與復原

一般啟動預設使用 `<project-root>/data/workspace-session.json`，另有同路徑加 `.lock` 的執行個體鎖。啟動會先顯示絕對路徑。同一復原檔同時僅由一個執行個體使用，其他執行個體仍可手動開啟／儲存文件。

修改穩定約 1.5 秒後，以背景工作原子寫入檢查點，不自動覆寫 Studio 原檔。檢查點保存最多 50 個分頁的順序、目前分頁、完整內容、未儲存草稿、儲存路徑／基準、領域與版本封存，以及主要頁面、側邊分類、疊色與顏色顯示選擇；不保存精確捲動位置或搜尋文字。

下次啟動，程式會在背景驗證整個檢查點，**直接自動還原，不再詢問是否復原**。所有分頁、已儲存／未儲存狀態、目前文件與支援的工作區設定皆會還原。工作區／矩陣完成載入後，下方 **Output 操作紀錄** 會自動顯示，提醒已還原的分頁數、含未儲存變更的分頁數，以及復原檔絕對路徑；提醒文字依介面語言顯示。沒有復原檔時開啟新工作區；空檢查點會提示沒有分頁可還原。驗證失敗或取消時保留原檢查點、暫停覆寫，且不顯示成功還原訊息。

手動選擇 **File → Restore last session…** 時，仍會先確認是否取代目前已開啟的工作區：

- Yes：還原所有分頁及各自的已儲存／未儲存狀態。
- No：使用目前工作區，開始新的檢查點。
- Cancel：保留原復原檔；暫停覆寫它。

可透過 **File → Restore last session…** 重試。復原失敗或取消時，原檔與目前工作區保留，程式不會自動覆蓋舊檢查點；要放棄舊內容並改用目前工作區，請選 **Start new recovery session…**。退出前已全部儲存時，下次仍可復原乾淨的分頁；非正常中止則使用最後成功的檢查點，尚未完成該次檢查點的最新輸入可能不在其中。

檢查點含有文件內容與絕對路徑，只存本機。預設復原檔及鎖已排除於 Git。儲存檔若在程式外被修改或移除，復原草稿會標為未儲存，仍保留檔案衝突檢查。

停用自動工作階段（退出提示與手動儲存仍有效）：

```powershell
.\.venv\Scripts\python.exe -B .\main.py --no-session
```

指定其他復原位置：

```powershell
.\.venv\Scripts\python.exe -B .\main.py --session-file .\data\my-workspace.json
```

## 進度、失敗保護與驗證

Open：顯示絕對輸入路徑／無輸出 → 讀取 → 解析確切資料集 → 驗證文件及所有封存 → 成功後新增分頁。Save：顯示輸入／輸出與暫存檔絕對路徑 → 檢查外部修改 → 序列化並寫入同目錄暫存檔 → 原子取代成功後才更新路徑與已儲存基準。儲存開始後等待完成，不接受中途取消，以確保磁碟內容與文件基準一致；失敗仍可關閉錯誤提示並繼續編輯。

Session：擷取記憶體草稿 → 顯示復原檔／暫存檔絕對路徑 → 建立含 checksum 的快照 → 背景原子發佈。寫入失敗保留上個檢查點；退出檢查點失敗時保留主視窗，顯示原因。所有階段均可在 Output、狀態列與終端查看。

在專案根目錄驗證：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -B .\audit_studio_lifecycle.py
```

輸入為已快取的官方資料（含 v11.3）；絕對輸出目錄為 `<project-root>/artifacts/studio-lifecycle`，包含範例文件、獨立檢查點、畫面及 `audit.json`。測試使用隔離的工作階段／設定，檢查往返、取消／失敗、外部修改、退出、多分頁及復原，不變更使用者的官方指標。其他操作見 [README](../README.md) 與[批次手冊](batch_operations+_zh.md)。
