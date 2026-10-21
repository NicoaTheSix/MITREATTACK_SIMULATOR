# 偵測策略搜尋、個別展開保存與原始資料複製

## 用 Detection Strategy 尋找技術

在側欄 **TTP search fields…** 或矩陣 **Search fields…**，開啟 **Detection Strategy · Name / ID / Description**。預設關閉，Name／ID 維持原有預設。若只想查策略內容，開啟此欄位、關閉其他欄位；至少保留一個。

**範例：** 開啟近期 ATT&CK 版本，只啟用 Detection Strategy，輸入資料中實際存在的策略 ID，例如 `DET0001`，或策略標題／描述中的片語。結果是該版本中由符合策略直接偵測的技術。各領域／版本的 ID 與可用資料不同。支援空格、字面標點、不分大小寫；僅在比對時忽略外圍空白。沒有策略物件的舊版本不會有結果，也不會借用新版資料。

索引使用有效 `x-mitre-detection-strategy` 的直接 `detects` 關聯，排除撤銷／棄用策略與關聯。查詢策略自己的名稱、ID、Description，不只查 analytic 日誌來源名稱。既有 Data Sources 欄位保持獨立。側欄、Flat／Side／Mini、Select… → Search matches，以及篩選後 SVG／Excel 共用欄位偏好。Save／重開、複製、Navigator 擴充與工作階段復原都會保留。Detections 分類搜尋也包含 Description；圖書分類仍隱藏 TTP 專用欄位控制。

## 保存個別父技術展開狀態

點父技術箭頭，開啟或關閉某一 Tactic 下的子技術，現在會保存 `showSubtechniques` 並讓文件待儲存，不會勾選技術，也不會改註記或 Enabled。

**範例：** 先 Expand all，再關閉 Execution 下的一個父技術。下拉選單變成 **Per-technique · saved**，只有該父技術的 Execution 家族關閉，其他 Tactic 與家族保持原狀。切換 Flat → Side → Mini、搜尋後清空、Save 後重開，都會還原個別開關。

離開全域 all／none／annotated 模式時，程式先記錄每個父技術／Tactic 的狀態，包括平台篩選外的家族，再只修改被點擊的家族，避免切模式時讓無關家族一起關閉。需要新增 Tactic 列時會先複製繼承的全域註記，保留註解、分數、顏色、Links、Metadata 與 Enabled。純分組父節點仍不能被當成可選技術。

搜尋可以暫時開啟命中家族，這種自動展開不會保存或標記待儲存，清空搜尋後還原。搜尋期間手動點箭頭是明確編輯，會保存該家族，但不會把其他搜尋自動展開一起記錄。Mini 也遵守明確收合旗標，沒有逐項旗標時才使用舊有預設展開。全域 Expand all／Collapse all／Expand annotated 仍可切換整體政策；選 Per-technique 則回到已存逐項設定。

切換圖層、複製、Studio／Navigator 交換、復原都會保留旗標。SVG 僅展開項目匯出會採畫面快照，沒有快照時讀取保存的個別狀態。預設 SVG／Excel 仍匯出全部符合篩選的子技術。

## Ctrl／Cmd／Shift 滑鼠多選

| 矩陣操作 | 結果 |
| --- | --- |
| 左鍵點名稱／格子 | 以該技術及偏好要求的連動格子取代原選取 |
| Ctrl／Cmd／Shift＋左鍵 | 在原選取中加入／移除該技術及連動格子 |
| Flat 的核取方塊，不按修飾鍵 | 保留原有累加勾選方式 |
| 父技術分支箭頭 | 只修改展開狀態 |
| 連點兩下 | 開啟詳情 |

Shift 是切換是否納入，不是選取字母排序區間。依被點擊格子的狀態決定整組連動目標要加入或移除，移除已選父技術不會反過來加入未選子技術。跨 Tactic、父子連動、只選可見偏好仍會套用；只選可見開啟時，連動不會加入收合／被篩選的成員。顏色、分數、註解、Enabled 不變。TTP 側欄及鍵盤核取方塊操作維持原有方式。

**範例：** 點 A，再 Ctrl 點 B，保留 A、B；Shift 點 B 可移除 B。普通點 C 會取代為 C。關閉跨 Tactic 時，操作只針對被點擊的 Tactic 格子。

## 懸停預覽與複製 STIX／TAXII JSON

開啟技術、子技術、實際 Tactic 或圖書條目的詳情頁，上方會有：

- **Copy STIX JSON**：複製完整的原始來源物件。
- **Copy TAXII envelope**：將同一筆物件放入本機產生的 TAXII 2.1 包裝後複製。

滑鼠停在按鈕上約 300 毫秒，會出現小型唯讀 JSON 視窗，顯示 STIX ID、領域與版本。移入小視窗可以捲動長內容；按裡面的 **Copy complete JSON**，或原本按鈕，即可貼到文字編輯器或其他工具。離開按鈕與小視窗後會稍候關閉；換條目／頁面會清除預覽及快取，避免誤複製上一筆。視窗位置限制在可用螢幕範圍內，不會啟用新的編輯視窗。

**範例：** 瀏覽一項技術，懸停 Copy STIX JSON，檢查 `external_references`、`kill_chain_phases` 及 `x_mitre_*` 欄位。點擊後貼入文字編輯器。即使格式化詳情頁未顯示所有欄位，完整來源仍會被複製；Studio 註解／顏色與目前選取不會被混入。

TAXII 模式的格式如下：

```json
{
  "objects": [
    { "type": "attack-pattern", "id": "attack-pattern--...", "name": "..." }
  ],
  "more": false
}
```

上例縮寫物件，剪貼簿會包含完整內容。包裝依 [TAXII 2.1 envelope 規格](https://docs.oasis-open.org/cti/taxii/v2.1/os/taxii-v2.1-os.html)，由已載入的本機快照產生，不是從 TAXII 伺服器下載的回應。只包含一個版本的該物件，不包含獨立關聯、標記或其他相依物件，不是完整相依 Bundle。其他服務可能需要認證、權限、相依資料或不同匯入格式。此操作不會上傳資料或同步 TAXII。

複製依瀏覽條目的領域／版本，也支援跨領域連結。平台、索引、圖書分組標題與合成的舊版 Tactic 沒有原始 STIX 物件，會隱藏按鍵。Unicode、巢狀內容、參照、自訂屬性都會保留。預覽／複製不修改來源 Bundle 或目前文件。

## 進度與驗證

搜尋、滑鼠選取、展開、預覽與複製都先回報記憶體輸入／無直接檔案輸出，再顯示階段進度。展開修改會驗證完整草稿後才替換圖層；JSON 序列化失敗會保留原剪貼簿文字。Save／Export／Session 沿用原子發佈與寫入前的最終／暫存檔絕對路徑回報。

安裝相依套件後，在專案根目錄執行：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -B .\audit_detection_interaction.py
```

七階段檢查涵蓋真實官方／隔離策略映射、三種排版的實際滑鼠點擊、個別展開與繼承註記、懸停／捲動／剪貼簿／貼上，以及 Studio／Navigator／Session／SVG／CSV 往返。先列出輸入與輸出絕對路徑；範例資料、檔案、畫面及 `audit.json` 位於 `<project-root>/artifacts/detection-interaction`，並檢查官方資料指標未改變。啟動與程式流程見 [README](../README.md)，另見[選取與搜尋](selection_and_search+_zh.md)、[矩陣顯示](matrix_display+_zh.md)、[文件儲存／復原](studio_files+_zh.md)。
