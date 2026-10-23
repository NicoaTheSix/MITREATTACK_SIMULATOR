# Fusion Studio：資安工作流程與 CLI 需求研究

研究日期：2026-10-22。方法：核對本地最新 README，以及 MITRE、CISA、NIST、Sigma 官方文件與原始碼。本次沒有訪談資安人員，不能以文件研究宣稱市場需求已驗證。下文區分「官方證據」、「設計推論」與「待驗證假說」，未修改程式。

## 現況基線

[README](README.md#car-integration) 已記錄 ATT&CK、ATLAS 與 CAR 整合。CAR 包含 Analytics、Data Model、Sensors、工作區獨立納入、`car_workspace` schema 1、快照身份及原始記錄保存、選擇性讀寫、CSV、復原、雙語與原文查詢閱讀。README 同時將 SIEM 執行與環境／證據評估列為未來範圍。因此下一步的重點應是把現有資料轉成工作成果，無須重新規劃一次 CAR 基本瀏覽器。

## 官方資料反映的工作需求

| 工作角色 | 官方證據 | 對 Fusion Studio 的設計推論 |
| --- | --- | --- |
| SOC／事件應變 | NIST SP 800-61r3 的 DE.AE-03/07 要求關聯多來源資訊並納入 CTI／環境脈絡；RS.AN-03 關注事件序列及資產，RS.AN-06/07 關注調查與資料來源及完整性。[NIST，印刷頁 25–29](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r3.pdf) | 使用者需要把 TTP 查詢結果連到案件觀察、資產、證據及下一步，並產出可交接的內容。現有知識瀏覽器可作參考入口，但不能直接替代 SIEM 或完整案件系統。 |
| CTI 分析 | CISA ATT&CK mapping 指引要求理解行為、保留足夠脈絡並說明情報缺口；MITRE 官方 roadmap 重述查閱原始報告、技術細節及脈絡的步驟。[CISA mapping 指引](https://www.cisa.gov/sites/default/files/2023-01/Best%20Practices%20for%20MITRE%20ATTCK%20Mapping.pdf)、[MITRE roadmap](https://attack.mitre.org/docs/attack_roadmap_2024_april.pdf) | 映射應附來源、原文位置、具體行為與理由。原文摘錄、觀察時間、信心與人工審核欄位是本產品提案，不能宣稱這些欄位名稱或分數是 CISA 強制 schema。 |
| 偵測工程 | Sigma 區分 detection、logsource 與 metadata；`falsepositives` 用於分析人員判斷，不會自動轉成排除條件。Processing Pipelines 用來適配資料欄位及環境。[Sigma Rules](https://sigmahq.io/docs/basics/rules.html)、[Processing Pipelines](https://sigmahq.io/docs/digging-deeper/pipelines.html) | 需要知道「適用什麼資料、缺什麼欄位、怎麼轉換、怎麼驗證」，不只列規則或複製查詢。工具應保留原生規則、版本、logsource 與轉換設定。 |
| 紅／紫隊 | MITRE 的 Adversary Emulation Library 提供根據實際 TTP 的防禦測試計畫；Attack Flow 則描述技術如何組合與排序。[Emulation Library](https://github.com/center-for-threat-informed-defense/adversary_emulation_library)、[Attack Flow overview](https://center-for-threat-informed-defense.github.io/attack-flow/overview/) | 從選取 TTP 進一步形成可追蹤的測試案例：程序、前置條件、環境、預期遙測、執行紀錄、偵測結果與待改善事項。時間順序不能由矩陣欄位順序自動推定。 |

以上只證明這些工作流程有官方依據；不能據此推定每一類人員都會選用 Fusion Studio，或 CLI 一定比現有工具快。

## 最實用的五個需求

### 1. 不必開 GUI 的快速查詢與批次補充資料

**設計推論：**在 terminal、筆記或腳本裡查 ID、名稱、description 與關聯資料，並可將一份 ID 清單批次補成可引用結果。重點是少切換畫面，以及把結果送回既有流程。

建議 MVP 提供 `show`、`search`、`related`、`batch`；輸出 text／JSON／Markdown，明確附 framework、domain、版本、來源 URI、快照識別、物件版本與 revoked/deprecated 狀態。ATT&CK、ATLAS、CAR ID 維持獨立命名空間。以下只是待實作的介面示意：

```text
fusion show T1059.001 --framework attack --domain enterprise --format json
fusion show AML.T0015 --framework atlas --format md
fusion related T1059.001 --framework attack --kind car --format json
fusion batch --input D:\cases\technique-ids.txt --format json
```

這些命令名稱尚未實作。CLI 應使用與 GUI 相同的本地 catalog 與明確版本，避免各自取得不同的「最新」內容。正常查詢只讀本地資料；更新資料是獨立顯式動作。`stdout` 只放結果；絕對輸入／輸出路徑、分階段進度與診斷寫到 `stderr`，兼顧專案規範及 shell pipe。沒有輸出檔時應寫明結果送往 stdout，不要編造檔案路徑。

**待驗證：**每日查詢頻率、常用 shell／OS、是否有離線需求、主要貼入 Markdown 還是 JSON、批次清單來源。只有查 description 的最小功能可以先做，但長期差異不在重複一個查 ID 的 API。

### 2. 有證據的 TTP 映射與人工審核

**設計推論：**新增 Case Evidence：來源 URL／檔案、原文片段與位置、具體觀察行為、時間、資產、候選 TTP、映射理由、信心及 reviewer。把「報告聲稱」、「本地觀察」、「分析推論」分開，不因某 actor 常使用某 TTP，就推定本事件一定發生。

信心應針對該筆映射及其依據，與威脅嚴重度、技術優先序及偵測能力分開。可以先使用有文字準則的低／中／高與 unknown，避免顯示沒有校準依據的精確百分比。原文、脈絡與信心欄位的具體模型屬產品設計，不是已確認的官方統一格式。CISA 的 Decider 已提供 guided mapping、搜尋及結果匯出；Fusion 可利用已有工作區承接證據及後續工作，不必先重做完整問答樹。[CISA Decider](https://github.com/cisagov/Decider)

**待驗證：**分析人員願意補多少欄位、哪類來源最常用、是否需雙人 review、哪些證據能存本地、報告可否包含原文。

### 3. 能說明缺口的遙測與偵測能力評估

**官方證據：**MITRE Get Started 明確提醒不要追求所有技術的 100% coverage，也不要因知道單一實現方法就把整個技術格子塗綠；應優先處理與組織相關的威脅。[MITRE Get Started](https://attack.mitre.org/resources/)

**設計推論：**以 Telemetry Profile 記錄平台、產品／版本、可收集 event／欄位、收集設定及狀態日期。把 CAR／Sigma 需求對到已知資料，分別顯示滿足、缺少、未知。再用獨立狀態記錄候選分析、已適配、已部署、已測試、觀察到告警；沒有證據時維持未知。資料具備不等於規則有效，規則存在不等於已部署，單次測試成功也不代表所有實現方式均被偵測。

既有 CAR sensor 關聯只能作候選，不能直接當完整 readiness。詳細上游限制見 [CAR_UPSTREAM_RESEARCH.md](CAR_UPSTREAM_RESEARCH.md)。

**待驗證：**使用者能否取得真實 log／欄位樣本、環境資料是否可攜出、優先支援哪一個 SIEM／EDR、狀態更新由誰負責。

### 4. 可交接的分析報告與有理由的優先序

**設計推論：**以一個 Workplace 輸出「本案觀察→映射依據→適用技術→候選偵測／緩解→資料缺口→下一步／負責人」；報告包含來源、版本、未知項與審核狀態。保留現有 Navigator／CSV 功能，新增真正可讀的分析報告而非只有 ID 清單。

優先順序可用相關威脅、資產重要性、適用平台、可用資料與驗證缺口來說明，初期避免自動合成看似客觀的單一分數。這是對官方「依組織情境決定優先範圍」的產品推論，不是既有通用風險公式。

**待驗證：**交付對象是 SOC 同事、客戶或主管；每份報告目前花多久；最常重複貼入哪些欄位；是否需工單／Git 提交而非額外報告格式。

### 5. 測試結果能回到原分析與待改善事項

**官方證據：**CISA 的防禦驗證建議包含選技術、對齊技術與控制、測試、分析偵測／預防表現，再依結果調整人員、流程及技術。[CISA AA24-016A，Validate Security Controls](https://www.cisa.gov/news-events/cybersecurity-advisories/aa24-016a)

**設計推論：**先支援手動匯入測試結果及證據連結，保存 run ID、時間、環境、procedure 版本、預期／實際遙測、是否產生 alert、延遲與失敗原因。後續才接外部執行平台。結果要綁定被測的規則版本與情境，查詢／來源變動時提示重新檢視，而非永遠保留綠色。

**待驗證：**團隊是否已有測試平台、是否能取得其結果、誰願意處理失敗分類、最小可用證據是檔案／URL 還是 API。

## CLI 與現成工具的重疊及互補

| 工具 | 官方已提供 | Fusion 應做的互補工作 |
| --- | --- | --- |
| `mitreattack-python` | Python ATT&CK 資料存取；官方範例用本地 STIX bundle 與 `get_object_by_attack_id` 查物件並列印。[官方範例](https://github.com/mitre-attack/mitreattack-python/blob/main/examples/get_object_by_attack_id.py) | 提供免寫 Python 的一致命令、批次與固定輸出契約；共用 Fusion 的 ATT&CK／ATLAS／CAR 快照、關聯與工作區。不要把簡單查 ID 宣稱成官方工具做不到的新能力。 |
| Sigma CLI／pySigma | 已有 Sigma 規則管理、列舉、轉換、backend 與 processing pipeline 插件；轉換依目標及 pipeline 設定。[Sigma CLI README](https://github.com/SigmaHQ/sigma-cli/blob/main/README.md) | 索引原生 rule 與版本、連回 TTP／證據／環境，重用 pySigma 的轉換能力，保存 backend、pipeline、版本及輸出。避免自行維護通用 Sigma→SIEM 翻譯器。轉換成功本身不代表查詢已在環境有效。 |
| CISA Decider | 用 guided questions 協助行為映射，支援篩選及 cart 匯出。[官方 repo](https://github.com/cisagov/Decider) | 把已建立映射帶入本地工作區，保留證據、人工審核與後續偵測計畫。 |
| Attack Flow | 表達行為組合與序列，具有現成 Builder。[官方 overview](https://center-for-threat-informed-defense.github.io/attack-flow/overview/) | 先保存事件／procedure 的時間及證據關係，之後依版本化規格互通；不要因能畫箭頭就宣稱已還原攻擊因果。 |

## 建議優先序與驗證方式

下列是設計判斷，應透過實際試用調整：

1. **P0：真正免 GUI 的 CLI。** 先做 show／search／related／batch、text／JSON／Markdown、stdout／stderr 分離、明確來源版本。以「一份現有 ID 清單能否直接補成可交付結果」驗證價值。
2. **P1：Case Evidence 與分析報告。** 將選取清單提升為有原文、理由、信心、review 與未知項的工作成果。以一份真實去識別報告或事件片段走完流程，確認節省哪些重複作業。
3. **P2：Telemetry Profile 與部署／實測證據。** 先選一個真實 logsource 與少數優先 TTP，實際呈現缺欄位／未知與測試結果，再擴大範圍。
4. **P3：Sigma 原生規則索引與 pySigma 轉換。** 在有目標環境與 pipeline 需求後加入，先支援一個 backend，將轉換與本地測試分開驗證。

跨四階段持續確認五件事：使用者目前怎麼做、最耗時在哪、會把結果交給誰、能用什麼真實樣本驗證、功能是否真的減少切換與重工。這些尚未完成訪談，不應把本文件中的優先序表述成已證實的產業共識。

## 來源核對限制

CISA mapping PDF 的搜尋索引可讀到脈絡、實作細節與情報缺口段落，但本次直接下載遭 403；MITRE roadmap 的搜尋索引可讀到其重述的 mapping 步驟，直接展開因 PDF 體積限制未成功。因此本文件未將無法核對的逐字引文、信心數值或強制欄位歸給該指引。NIST 正式版、MITRE Get Started、mitreattack-python 範例、Sigma 文件、Decider 及 Attack Flow 官方頁面均已直接查閱。來源採查閱日狀態；未宣稱已在實際 SOC／SIEM 環境測試上述提案。
