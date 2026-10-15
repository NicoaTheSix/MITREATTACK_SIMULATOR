# Navigator 進階操作手冊與範例

## 矩陣排版、排序與多平台

從 TTP 側邊欄打開矩陣，在 Platform 旁選擇 **Flat／Side／Mini**。Flat 是可展開的直向技術樹；Side 把父技術放在子技術清單旁；Mini 把父子技術排成一組小色塊。點擊選取、雙擊看詳細資料、滑鼠停留看名稱／分數／註解，右鍵開啟技術操作。小箭頭及 Expand／Collapse all 控制子技術展開。

**Name ↑／↓** 按名稱排序，**Score ↑／↓** 按分數排序。啟用彙總時使用顯示的父子技術彙總分數，否則使用技術自己的分數；無分數視為零。排序不修改分數或選取狀態。按 **Multiple…／Platforms (…)…** 勾選多個平台，結果取聯集；全部取消時矩陣為空。一般 Platform 下拉選单仍可快速切換單一平台或所有平台，搜尋會與平台篩選同時生效。

這些設定屬於目前圖層，會寫入 Navigator JSON 的 `layout.layout`、`sorting`、`filters.platforms`，Studio JSON 的完整圖層也會保留。切換圖層會恢復各自設定。匯入資料中的未知平台名稱保留於 JSON，但不會產生矩陣項目。Show all layers 只混合相同領域、版本及資料集身分的圖層。

所有圖層的顏色同時顯示時，排序仍使用目前圖層的分數／彙總；混色不產生合併分數。

SVG 依照排版、平台聯集、搜尋、排序與顏色匯出，所有符合篩選的子技術會展開。Excel 保持有名稱的直向矩陣，使用相同的篩選與排序；Layer Info 記錄原本排版，Techniques 包含 Links／Metadata JSON。Excel 不模仿 Mini 色塊或 Side 欄位。

## 技術／圖層的 Links 與 Metadata

獨立啟用／停用及多技術批次編輯見 [獨立狀態與批次操作](batch_operations+_zh.md)。納入輸出與 Enabled 分開，勾選也不會再自動產生預設藍色。

技術右鍵選 **Edit technique annotation…**，指定 Tactic scope 後使用 **Links／Metadata** 分頁。Links 填標籤與 URL；Metadata 填名稱與文字值。可以新增、刪除或加入分隔線，最後 Save。每個範圍的草稿請先儲存再切換；Cancel 捨棄目前草稿。Include 勾選框獨立控制是否選取該 TTP。

例如新增標籤 `Investigation`、網址 `https://example.org/case/123`，Metadata 填 `Owner = Detection team` 與 `Confidence = High`。Metadata 會顯示於技術提示文字；可開啟的連結顯示於右鍵的 **Open: …**。新增或修改網址須使用不含帳密的完整 HTTP(S) URL。匯入檔原有的其他協定仍保留，但本程式不開啟它們。

圖層層級資料在 **Layer settings… → Layer links／Layer metadata**。無效資料不會覆寫圖層；原有欄位擴充與分隔線會保留。程式的選取狀態 Metadata 自動維護，不出現在技術編輯器。Navigator／Studio JSON 保留完整全域或 Tactic 註解、Links、Metadata 與擴充欄位。CSV 仍是選取 TTP 報表，包含註解與資料集來源；完整結構請匯出 JSON。

## URL 圖層與自訂 STIX

選 **File → Load layer URL / custom STIX…**。Navigator URL 模式輸入直接提供 JSON 的 HTTP(S) 網址，按 **Load and validate preview**。開啟後接續既有匯入預覽，選擇圖層、選取政策並解析指定 ATT&CK 版本。一般網頁的 HTML 不是圖層 JSON。

自訂資料選 **Custom STIX Bundle / Collection**，貼網址或 Browse 選本機 JSON。Collection Index 會列出版本；選取後再按 Load，才下載該版本 Bundle。包含 `x-mitre-collection` 的 Bundle 可直接載入。只有參照清單的單獨 Collection 物件，需要先與被參照物件一起封裝成 Bundle。此功能載入 ATT&CK 相容資料集，並非通用 STIX 檢視器。

Bundle 的有效技術需要每個領域唯一的 `T####／T####.###` 外部 ID、名稱、正確領域的 Kill-chain phase、`x-mitre-tactic`、`x-mitre-matrix` 與一致的 `x_mitre_domains`。子技術須有有效且僅一層的父技術。相同 STIX ID 採用 `modified` 最新版本；同版內容衝突、無效欄位或重複外部 ID 會拒絕載入。版本採 Collection 的版本資訊，沒有時填數字備用版本。預覽中選可用領域，再按 **Open as a new document**。

執行前顯示輸入檔案絕對路徑或 URL、快取目錄，依序顯示讀取、解析、驗證與快取進度。驗證完成後原始資料原子寫入 `<project-root>/data/attack/custom/<sha256>.json`；官方資料與 `active.json／latest.json` 保持完整。Navigator 限 10 MiB／20 圖層，自訂資料限 128 MiB／200,000 物件。HTTP(S) Socket 逾時為 20 秒，重新導向只能使用 HTTP(S)。取消於處理檢查點停止，失敗不會安裝不完整的文件。

Studio JSON 記錄自訂來源與 SHA-256；CSV 加入來源／雜湊欄位；Navigator JSON 加入 `customDataURL` 與 `x_ttp_studio_dataset`。本機來源使用絕對路徑，跨電腦需攜帶 Bundle 並先載入相同內容；官方網頁版 Navigator 只能直接使用網路 URL。自訂圖層不會自動套用同版本的官方資料，須先載入匹配 Bundle 再匯入；檔案內的自訂 URL 不會自動下載。官方文件可用 Version 切換官方版本；其他自訂版本請分別載入或使用升級審查流程。Ctrl+N 一律建立官方 Enterprise 文件。

## 舊圖層升級與註解搬移

選 **Navigator → Review and upgrade layer…**，挑選已快取的官方版本或目前開啟、相同領域的自訂資料集。若需要其他官方版本，先在官方文件透過 Version 下載，再進入此流程。按 **Load target and compare** 列出所有來源註解列與未附註解的已選 TTP。滑鼠停在來源 ID 可看完整原註解。目標版本新增 ID 另外列出，不會自動被選取。

未變更項目預設已審查。技術變更、Tactic 消失、失效 ID 與替代項目需要確認。替代建議只依 STIX 的 `revoked-by` 關係；沒有此關係的失效／棄用 ID 不猜替代技術。選 **Copy**，用可搜尋的下拉選單指定技術與目標 Tactic（或 All tactics），再勾 Reviewed；**Drop** 明確捨棄該來源註解列。可用 **Show only rows requiring review** 篩選，以及 **Mark visible decisions reviewed** 批次確認目前顯示的決策；建立前仍會逐項驗證。

選取來源列後，下方唯讀區會顯示完整欄位變更前後值及原註解。比較涵蓋資料集的所有欄位，因此描述、映射或擴充欄位變更也會要求審查；匯出的決策紀錄包含變更欄位名稱。

例如已撤銷的技術有 `comment = Lab observation`、分數、顏色、Links 與 Metadata。確認替代技術意義後 Copy 到該技術與有效 Tactic，新圖層會保留這些註解及選取狀態。多列映射到同一技術／範圍時，相容資料合併、不同註解保留、Links／Metadata 去重；不同分數、顏色或啟用旗標等衝突會停止建立，須重新映射或 Drop 一列。消失的 Tactic 不會默默改成 All tactics。

**Create migrated layer** 要求每列都已審查，且 Copy 的技術與範圍有效。完成後新增目標版本分頁，原文件保持完整；新文件包含來源圖層封存及 `x_ttp_studio_upgrade` 決策紀錄。進度依序顯示比較、映射與完成。匯出前不寫檔；Studio JSON 保存封存，Navigator JSON 保存新圖層與決策。程式尚無 Session 復原／Studio JSON 重開功能，離開前請匯出重要資料。

啟動與驗證方式見 [專案 README](../README.md)；交換欄位見 [官方 Navigator 圖層格式](https://github.com/mitre-attack/attack-navigator/blob/master/layers/spec/v4.5/layerformat.md)。

自訂版本號代表該資料集自己的版本：現代自訂 STIX 的 `1.0` 版本仍可操作 Navigator。v4 之前的限制針對歷史官方 ATT&CK 資料。來源封存保存於 Studio JSON 的 `migration_archives`，帶有來源領域、版本與資料集身分，不會透過 Version 切換自動恢復到另一個資料集。
