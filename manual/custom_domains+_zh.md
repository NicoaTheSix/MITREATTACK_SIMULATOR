# 自訂 Domain 與資料模型

## 載入操作範例

1. 選 **File → Load layer URL / custom STIX…**，再選 **Custom STIX Bundle / Collection**。
2. 瀏覽專案目錄下的 `manual/examples/custom_domain_bundle.json`（[範例說明](examples/README.md)），填備用版本 **1.0**，再按 **Load and validate preview**。
3. 選 **Research Lab**；預覽會顯示來源／雜湊、技術／Tactic／平台數及兩份 Matrix 名稱，再按 **Open as a new document**。
4. 從 TTP 側欄開啟矩陣，可看到 **Observe**、**Review** 兩欄。展開結構父項、勾選 `LAB-001.child`；其父技術 ID 為 `LAB-001`。
5. 使用既有技術編輯或批次操作新增註解、顏色、分數。以 Studio JSON 儲存完整文件，也可匯出所選 TTP JSON／CSV、Navigator JSON、SVG 或 Excel。

範例只描述目錄條目，不執行技術行為。原本 Ctrl+N／新增圖層仍建立官方 Enterprise 文件；請透過自訂 Bundle 建立自訂領域文件。

Bundle 含多個領域時，來源預覽會提供有有效技術的領域。右鍵點檔案分頁 → **ATT&CK Domain**，可在同一驗證資料集中切換；每個領域各自保留選取、註記與封存。不可用的官方領域維持停用，不借用官方資料或其他 Bundle。

## 在 Bundle 定義領域

於 Bundle 頂層加入 `x_ttp_studio_domains`，與 `objects` 並列：

```json
"x_ttp_studio_domains": [
  {
    "id": "research-lab",
    "name": "Research Lab",
    "kill_chain_name": "research-chain",
    "reference_source": "research-kb"
  }
]
```

各欄位分開定義，不必採同一字串：

| 欄位 | 意義 |
| --- | --- |
| `id` | 領域的正式識別值，供 `x_mitre_domains` 與 Navigator `domain` 使用。 |
| `name` | 來源選單、檔案右鍵選單、側欄、矩陣及匯出的顯示名稱。 |
| `kill_chain_name` | 技術 `kill_chain_phases[].kill_chain_name` 的精確名稱，其 phase 對應 Tactic。 |
| `reference_source` | 決定外部 ID 的 `external_references[].source_name`；其他參照保留原樣，不覆蓋身分。 |

領域 ID 長 1–64 字元，以 ASCII 小寫字母開頭，其餘限小寫字母／數字／連字號；`mitre-enterprise`、`mitre-mobile` 保留為舊圖層別名。名稱、Kill Chain、參照來源須為非空白純文字、最多 128 字元，不接受控制字元或角括號。定義不能重複，最多 32 筆，宣告／定義的領域識別值聯集也最多 32 個。

未明確定義的自訂領域，只有在有效技術共同提供唯一 Kill Chain 與唯一外部 ID 來源時才能推導，顯示名稱預設為 ID。缺少或不明確就須補定義，不在無關參照中猜測。Enterprise／Mobile／ICS 保留官方預設；自訂定義只屬於該 Bundle，不修改全域官方清單。

## 技術、Tactic 與關係

相關物件的 `x_mitre_domains` 應包含領域 ID；提供短名稱唯一的 `x-mitre-tactic`、`tactic_refs` 可解析的 `x-mitre-matrix`，以及含名稱和有效領域 Kill Chain 對應的 `attack-pattern`。Tactic 短名稱以字母開頭，最多 128 個字母／數字／底線／連字號。

明確設定或唯一推導外部參照來源後，技術 ID 可使用 `LAB-001`、`LAB-001.child`、`RESEARCH_A` 等識別字串：以 ASCII 字母開頭，僅含 ASCII 字母／數字／底線／連字號／點，最多 128 字元。未另設來源的官方領域 Bundle，仍保留 `T####／T####.###` 規則；沒有自訂來源／資料集的官方 Navigator 圖層也維持官方 ID 格式。

有效技術須從指定來源取得唯一、不歧義的外部 ID。同領域中不同 STIX 技術不能重用此 ID；不同領域或資料集可有相同外部 ID，不會合併。共用 STIX 物件亦可透過不同領域定義解析出不同 ID 與 Kill Chain 對應。其他參照與自訂物件屬性維持原樣。

子技術以 `x_mitre_is_subtechnique: true`，加上明確 `subtechnique-of` 關係，指向同領域唯一的有效父技術；不靠 ID 標點推測階層。循環、多層子技術、跨領域或缺少父項會被拒絕。未另設來源的官方領域保留父子格式一致性檢查。Group／Software／Campaign／Mitigation、偵測與 Asset 等既有來源仍依精確 STIX 關係解析，沒有新增任意瀏覽分類。

關係若有 `x_mitre_domains`，只套用至列出的領域；沒有該欄位時，依各領域可用的端點解析。共用子技術可透過明確範圍關係分別擁有不同父項，但任一關係都不能指向該領域有效資料以外的父項。

## 多份 Matrix

一個領域可有多份有效 Matrix；各自須有非空白、不重複，且可在該領域解析的 Tactic 參照。每個有效技術映射的 Tactic，至少須出現在一份 Matrix 中。

文件顯示單一**有序聯集**：依原 Bundle 的 Matrix 順序，再按各 Matrix 的 `tactic_refs` 順序，保留每個 Tactic 首次出現的位置；其餘未使用的標頭依短名稱排序。技術依原領域 Kill Chain 映射，不因多份 Matrix 重疊而重複選取。此行為避免只採第一份 Matrix 而遺失後續欄位。完整 Matrix 物件仍保留於資料模型及原始內容，來源預覽會列出其名稱；本功能沒有另加單一 Matrix 篩選／編輯器。

## 身分隔離與檔案交換

資料集身分仍是原始 Bundle 位元組的 SHA-256。不同 Bundle 可以有相同領域 ID、版本與 STIX ID，但不同名稱、Kill Chain 或參照映射；仍按雜湊隔離，載入後者不改寫前者定義。公式、疊色與選取比較維持精確的領域／版本／資料集檢查；跨來源搬移請走升級審查。

Studio 儲存／重開與工作階段復原，會從確切快取 Bundle 重建定義並保留自訂領域封存。CSV 記錄正式領域、自訂技術／父技術／Tactic ID、來源／雜湊與註記。Navigator 匯出保留自訂 ID／Domain、`customDataURL`、`x_ttp_studio_dataset`；非官方領域另含 `x_ttp_studio_domain` 定義。匯入／重新開啟時，記錄的定義須符合確切 Bundle。SVG、Excel 使用相同已解析模型。

MITRE Python SDK 只接受官方領域與 T 開頭 ID，因此程式先自行驗證自訂識別與定義，再用獨立副本讓 SDK 驗證共通 Layer 結構；副本替換不會改寫匯出 ID 或原始 JSON。官方網頁版 Navigator 不保證認得 Studio 的自訂定義；交換時需提供接收端支援的 Bundle 與映射。

本功能仍是 ATT&CK 相容目錄流程：需要 STIX UUID、具名技術、Tactic、Matrix 與既有支援的關係，不是任意 STIX 圖編輯器或通用知識模型工具。STIX／TAXII 複製保留原物件字典，不輸出 Python 紀錄檢視額外的解析資訊。

## 檔案、進度與驗證

處理前顯示 Bundle／快取輸入的絕對路徑或 URL，以及輸出／快取絕對路徑；純記憶體操作明確顯示沒有檔案。沿用來源階段：**讀取 → 解析 → 驗證定義／物件與各領域投影 → 快取有效位元組**；各領域的程序／來源關聯索引亦回報進度。領域切換為 **解析 → 還原該領域狀態 → 重建樹狀與矩陣**，不寫交換檔。儲存、匯入、匯出各自保留原有分段進度及原子發布。

在專案環境設定 `QT_QPA_PLATFORM=offscreen` 後，執行 `python -B audit_custom_domains.py`。測試先顯示絕對輸入／輸出，使用隔離設定／快取，於 `<project-root>/artifacts/custom-domains` 產生 Bundle、Studio／Navigator／復原／CSV 範例、SVG／XLSX、雙語截圖與 `audit.json`。涵蓋自訂／推導／共用領域、同版本不同來源、ID 衝突、Matrix 聯集／錯誤參照、父子隔離、介面切換／搜尋、批次編輯、來源選取、公式與往返；不需公網下載。

[範例說明](examples/README.md) · [全部手冊](README.md) · [customDataURL 取得](custom_data_url_import+_zh.md) · [多圖層開啟](navigator_bundle_import+_zh.md)
