# Navigator 進階操作手冊與範例

獨立的 **Show names／Show IDs**、**Tactic background／Header color…**、**Expand annotated**、彩色註記提示線及唯讀來源 Notes，詳見[矩陣顯示與註記提示](matrix_display+_zh.md)。這些設定使用標準圖層欄位，不會改變已選 TTP。

跨 Tactic／父子連動偏好、Description／Data Sources 搜尋與 Mitigation 加入／取消，詳見[選取與搜尋手冊](selection_and_search+_zh.md)。

## 矩陣排版、排序與多平台

從 TTP 側邊欄打開矩陣，在 Platform 旁選擇 **Flat／Side／Mini**。Flat 是可展開的直向技術樹；Side 把父技術放在子技術清單旁；Mini 把父子技術排成一組小色塊。點擊選取、雙擊看詳細資料、滑鼠停留看名稱／分數／註解，右鍵開啟技術操作。小箭頭及 Expand／Collapse all 控制子技術展開。

**Name ↑／↓** 按名稱排序，**Score ↑／↓** 按分數排序。啟用彙總時使用顯示的父子技術彙總分數，否則使用技術自己的分數；無分數視為零。排序不修改分數或選取狀態。按 **Multiple…／Platforms (…)…** 勾選多個平台，結果取聯集；全部取消時矩陣為空。一般 Platform 下拉選单仍可快速切換單一平台或所有平台，搜尋會與平台篩選同時生效。

這些設定屬於目前圖層，會寫入 Navigator JSON 的 `layout.layout`、`sorting`、`filters.platforms`，Studio JSON 的完整圖層也會保留。切換圖層會恢復各自設定。匯入資料中的未知平台名稱保留於 JSON，但不會產生矩陣項目。Show all layers 只混合相同領域、版本及資料集身分的圖層。

所有圖層的顏色同時顯示時，排序仍使用目前圖層的分數／彙總；混色不產生合併分數。

SVG 依照排版、平台聯集、搜尋、排序與顏色匯出，進階設定可調單位、尺寸、字型、標頭、圖例、框線與全部／目前展開／不顯示子技術，並提供記憶體預覽。單圖層 Excel 保持直向矩陣與 Techniques／Layer Info；**Export all open layers to Excel…** 則依各層已保存篩選建立每層一張工作表。Excel 不模仿 Mini 色塊或 Side 欄位。詳見[分數彙總與矩陣匯出](aggregation_and_exports+_zh.md)。

## 技術／圖層的 Links 與 Metadata

獨立啟用／停用及多技術批次編輯見 [獨立狀態與批次操作](batch_operations+_zh.md)。納入輸出與 Enabled 分開，勾選也不會再自動產生預設藍色。

技術右鍵選 **Edit technique annotation…**，指定 Tactic scope 後使用 **Links／Metadata** 分頁。Links 填標籤與 URL；Metadata 填名稱與文字值。可以新增、刪除或加入分隔線，最後 Save。每個範圍的草稿請先儲存再切換；Cancel 捨棄目前草稿。Include 勾選框獨立控制是否選取該 TTP。

例如新增標籤 `Investigation`、網址 `https://example.org/case/123`，Metadata 填 `Owner = Detection team` 與 `Confidence = High`。Metadata 會顯示於技術提示文字；可開啟的連結顯示於右鍵的 **Open: …**。新增或修改網址須使用不含帳密的完整 HTTP(S) URL。匯入檔原有的其他協定仍保留，但本程式不開啟它們。

圖層層級資料在 **Layer settings… → Layer links／Layer metadata**。無效資料不會覆寫圖層；原有欄位擴充與分隔線會保留。程式的選取狀態 Metadata 自動維護，不出現在技術編輯器。Navigator／Studio JSON 保留完整全域或 Tactic 註解、Links、Metadata 與擴充欄位。CSV 仍是選取 TTP 報表，包含註解與資料集來源；完整結構請匯出 JSON。

## URL 圖層與自訂 STIX

選 **File → Load layer URL / custom STIX…**。Navigator URL 模式輸入直接提供 JSON 的 HTTP(S) 網址，按 **Load and validate preview**。開啟後接續既有匯入預覽，選擇圖層、選取政策並解析指定 ATT&CK 版本。一般網頁的 HTML 不是圖層 JSON。

自訂資料選 **Custom STIX Bundle / Collection**，貼網址或 Browse 選本機 JSON。Collection Index 會列出版本；選取後再按 Load，才下載該版本 Bundle。包含 `x-mitre-collection` 的 Bundle 可直接載入。只有參照清單的單獨 Collection 物件，需要先與被參照物件一起封裝成 Bundle。此功能載入 ATT&CK 相容資料集，並非通用 STIX 檢視器。

Bundle 的有效技術需要每個領域唯一的外部 ID、名稱、正確領域的 Kill-chain phase、`x-mitre-tactic`、`x-mitre-matrix` 與一致的 `x_mitre_domains`。官方預設使用 `T####／T####.###`；[自訂領域定義](custom_domains+_zh.md)可分別設定顯示名稱、Kill Chain 與 ID 來源，並採用 `LAB-001.child` 等有界識別。多份 Matrix 以有序 Tactic 聯集合併，不遺失後續欄位。子技術須透過明確範圍關係指向有效且僅一層的父技術。相同 STIX ID 採用 `modified` 最新版本；同版內容衝突、無效欄位或重複外部 ID 會拒絕載入。版本採 Collection 的版本資訊，沒有時填數字備用版本。預覽中選可用領域，再按 **Open as a new document**。可直接載入的範例見[examples](examples/README.md)。

執行前顯示輸入檔案絕對路徑或 URL、快取目錄，依序顯示讀取、解析、驗證與快取進度。驗證完成後原始資料原子寫入 `<project-root>/data/attack/custom/<sha256>.json`；官方資料與 `active.json／latest.json` 保持完整。Navigator 限 10 MiB／20 圖層，自訂資料限 128 MiB／200,000 物件。HTTP(S) Socket 逾時為 20 秒，重新導向只能使用 HTTP(S)。取消於處理檢查點停止，失敗不會安裝不完整的文件。

Studio JSON 記錄自訂來源與 SHA-256；CSV 加入來源／雜湊欄位；Navigator JSON 加入 `customDataURL` 與 `x_ttp_studio_dataset`。本機來源使用絕對路徑，跨電腦需攜帶 Bundle，先載入相同內容或提供經相同雜湊驗證的快取；官方網頁版 Navigator 只能直接使用網路 URL。自訂圖層不會套用官方同版本資料；確切已載入資料與雜湊驗證快取可離線解析。缺少或不明確的來源，現可在匯入預覽按 **解析自訂資料…**，明確下載網址、選本機 Bundle／快取或選 Collection Index 版本。接受前驗證領域／版本／雜湊，內容變更須明確確認取代；相對網路參照以轉址後圖層網址解析，不自動下載內嵌網址。詳見[來源解析手冊](custom_data_url_import+_zh.md)與[多圖層 JSON 手冊](navigator_bundle_import+_zh.md)。官方文件可用 Version 切換官方版本；其他自訂版本請分別載入或使用升級審查流程。Ctrl+N 一律建立官方 Enterprise 文件。

## 舊圖層升級與註解搬移

選 **Navigator → Review and upgrade layer…**，挑選已快取的官方版本或目前開啟、相同領域的自訂資料集。若需要其他官方版本，先在官方文件透過 Version 下載。按 **Load target and compare** 後，技術逐項審核列出全部 Added／Changed／Removed／Replaced／Unchanged，包含無註記技術；註記搬移決策保留來源註記與已選 TTP，來源 ID 懸停可看原註記。分類／有註記／待審篩選不改變完整計數與必要審核集合。Added 可在完成前編輯註記，預設不選取，須明確勾選加入。詳見[完整升級審核手冊](upgrade_review+_zh.md)。

未變更項目預設已審查。技術變更、Tactic 消失、失效 ID 與替代項目需要確認。替代建議只依 STIX 的 `revoked-by` 關係；沒有此關係的失效／棄用 ID 不猜替代技術。選 **Copy**，用可搜尋的下拉選單指定技術與目標 Tactic（或 All tactics），再勾 Reviewed；**Drop** 明確捨棄該來源註解列。可用 **Show only rows requiring review** 篩選，以及 **Mark visible decisions reviewed** 批次確認目前顯示的決策；建立前仍會逐項驗證。

選取來源列後，**Content comparison（內容並排比較）**顯示升級前後完整記錄與註記，包含名稱、描述、Tactic 與 STIX 擴充欄位；**Raw differences** 保留原始 JSON 差異。官方兩側各提供經檢查的網站主版本連結，不自動改開最新版。指定有效 Copy 目標／範圍後，可按「編輯目標註記」於搬移前修改，修改後須重新審核。網站封存限制、清除欄位、獨立目標草稿與保存規則詳見[內容／編輯手冊](upgrade_content+_zh.md)。

例如已撤銷的技術有 `comment = Lab observation`、分數、顏色、Links 與 Metadata。確認替代技術意義後 Copy 到該技術與有效 Tactic，新圖層會保留這些註解及選取狀態。多列映射到同一技術／範圍時，相容資料合併、不同註解保留、Links／Metadata 去重；不同分數、顏色或啟用旗標等衝突須透過「審核搬移衝突」選用來源值、自訂值或清除欄位，也可重新映射或 Drop。消失的 Tactic 不會默默改成 All tactics。

**檢視最後摘要… → 提交升級** 要求每列都已審查，且 Copy 的技術與範圍有效。完成後新增目標版本分頁，原文件保持完整；新文件包含來源圖層封存及 `x_ttp_studio_upgrade` 決策紀錄。進度依序顯示比較、映射與完成。文件可透過 Save／Export 明確保存，自動工作階段檢查點也會保存草稿；Studio JSON 保存封存，Navigator JSON 保存新圖層與決策。請用 Save／Save As 保存完整文件及封存。Studio JSON 重開與工作階段復原請見[文件操作手冊](studio_files+_zh.md)。

啟動與驗證方式見 [專案 README](../README.md)；交換欄位見 [官方 Navigator 圖層格式](https://github.com/mitre-attack/attack-navigator/blob/master/layers/spec/v4.5/layerformat.md)。

自訂版本號代表該資料集自己的版本：現代自訂 STIX 的 `1.0` 版本仍可操作 Navigator。v4 之前的限制針對歷史官方 ATT&CK 資料。來源封存保存於 Studio JSON 的 `migration_archives`，帶有來源領域、版本與資料集身分，不會透過 Version 切換自動恢復到另一個資料集。

最後提交會先經過[完整摘要、選填略過理由及返回未完成項目](upgrade_summary+_zh.md)。
