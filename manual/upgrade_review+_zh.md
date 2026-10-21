# 圖層升級前的完整技術逐項審核

升級前後完整並排內容、歷史版本頁驗證連結與既有目標註記編輯，請見[升級內容與目標註記手冊](upgrade_content+_zh.md)；這些功能已加入下述分類審核流程。

開啟 **Navigator → Review and upgrade layer…（審閱並升版圖層）**，選取已快取的官方版本，或目前開啟且領域相同的自訂資料集，按 **Load target and compare**。其他官方版本請先透過 Version 下載。本流程建立新文件，來源文件仍保持開啟。

## 完整分類

**Technique review（技術逐項審核）**涵蓋來源與目標的所有有效技術 ID 聯集，以及來源註記中無法解析的 ID；沒有註記的技術也會列入。每個 ID 只屬於一類：

| 分類 | 意義 |
| --- | --- |
| Added／新增 | 目標有效技術中存在，來源有效技術中不存在。 |
| Changed／變更 | 兩邊皆有效，但任一 STIX 欄位不同，版本與時間戳變更也算。 |
| Removed／移除 | 目標不再有效，包含沒有唯一有效替代關係的 revoked／deprecated 技術；無法解析的匯入註記 ID 也歸此類。 |
| Replaced／替代 | 舊 ID 不再有效，且明確、有效的 `revoked-by` 指向一個目標有效技術。多個替代候選須手動指定。 |
| Unchanged／未變更 | 同 ID 在兩邊皆有效且完整記錄一致；來源範圍也有效時，預設已審。 |

新替代 ID 本身仍有 Added 列，舊 ID 則是 Replaced：以 ID 分類互斥，同時保留新目標的審核入口。不會依相似名稱猜測替代。

## 篩選與逐項審核

選擇 **All categories（所有分類）**或個別分類，可搭配 **Only annotated techniques（只顯示有註記的技術）**與 **Show only rows requiring review**。畫面顯示每一完整分類及全體的「已審／總數」；篩選不會改變分母與必要審核集合。沒有符合項目時會顯示空狀態。

Comment、零分、顏色、停用狀態、Links 與具名 Metadata 都算註記；單獨的內部選取標記、分隔線及展開設定不算。Added 草稿中新增的有效註記也會納入篩選。

檢查差異與映射後，勾選單項 **Reviewed**，或按 **Mark visible decisions reviewed**，確認目前可見技術及其來源註記列。隱藏但尚未審核的項目仍會阻擋建立。Added 沒有草稿或明確選取時，審核後記錄為 **Skip added**，不會自動選取。Unchanged 預設已審。

## 來源註記搬移決策

**Annotation mappings（註記搬移決策）**保留每個來源註記列，包含沒有另加註記的已選技術。選擇 **Copy** 並指定有效目標技術及 Tactic，或明確 **Drop**。來源 Tactic 被移除時，必須指定有效目標範圍。同技術可能有多個來源列，每列都必須完成決策。更改映射或取消來源列審核，會使該技術回到待審狀態，處理後須重新確認。

尚未處理的分數／顏色等純量衝突會阻擋搬移；可按「審核搬移衝突」選用來源值、自訂值或清除欄位，也可調整映射／草稿。相容的 Comment、Links、Metadata 可以合併。[一對多映射與欄位衝突解決](upgrade_mapping+_zh.md)已可使用；最後提交與返回操作見[摘要及略過理由手冊](upgrade_summary+_zh.md)。

## 完成前編輯新增技術

選取 Added 列，按 **Annotate added target…（編輯新增技術註記）**，可編輯 Tactic 範圍、Comment、Score、Color、Enabled、Links 與 Metadata。**Include this TTP in the document** 預設不勾選。儲存只更新記憶體草稿，不會修改來源；明確勾選才加入指定 Tactic 的技術，單獨加註不會選取。取消保留先前已存的草稿。

儲存修改後會清除該項已審狀態，請檢查後再次確認。切換篩選保留草稿；更換／重新載入目標，或關閉審核則清除。替代技術也可能經由另一筆已審 Copy 決策繼承來源選取，這是明確的搬移行為。

## 建立、保存與復原

**檢視最後摘要… → 提交升級** 會驗證全部技術審核及來源決策，包含被篩選隱藏者，再建立目標分頁。失敗會回復可編輯狀態，不安裝半成品；取消不改變來源。Studio JSON 的 `migration_archives` 保存完整來源；`x_ttp_studio_upgrade` 保存分類計數、每個 ID 的審核、Added 草稿／選取與來源映射決策。Save／重開及工作階段復原保留這些資料。Navigator JSON 保留審核擴充與結果註記；來源封存由 Studio JSON 保存。

審核／建立使用記憶體中的不可變來源及目標資料，不直接寫檔。執行前會明示此輸入／輸出狀態，再依比較分類 → 已審映射與 Added 草稿驗證 → 新文件完成顯示進度。載入快取版本／自訂資料時會列出實際絕對路徑；後續 Save／Export 另行顯示絕對輸入／輸出路徑與進度。參閱[文件儲存與復原](studio_files+_zh.md)。

## 範例與驗證

假設舊 A 被新 B 替代：在 Replaced 審核 A，決定是否把註記 Copy 到 B；在 Added 明確審核 B，可留空略過額外新增註記，也可先編輯草稿。另一新技術 C 即使已審，未明確選取仍不會被選取；隱藏但未審的 C 仍阻擋建立。

在專案根目錄安裝相依套件，並快取官方 v11.3 與目前版本後執行：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& '.\.venv\Scripts\python.exe' -B '.\audit_upgrade_review.py'
```

七階段稽核先列絕對輸入／輸出路徑，在 `artifacts/upgrade-review` 建立固定來源／目標測例與獨立快取，再驗證分類 → 決策驗證 → Added 草稿 → 原生介面／失敗／取消 → Studio／session／Navigator → 真實歷史版本聯集 → `audit.json`。介面截圖為 `artifacts/upgrade-review/review.png`，不連線外部伺服器。

參照[官方 v5.3.2 升級手冊](https://github.com/mitre-attack/attack-navigator/blob/v5.3.2/USAGE.md#upgrading-a-layer-to-the-current-version)；本程式的完整 ID 分母與嚴格審核規則以上述說明為準。[手冊索引](README.md)。
