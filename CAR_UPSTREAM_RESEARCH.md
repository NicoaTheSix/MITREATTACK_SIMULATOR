# CAR 上游資料研究

調查日期：2026-10-21。範圍：MITRE 官方 CAR repository、官方網站，以及固定提交中的 schema、資料樣本與生成流程。本文件僅記錄研究與整合建議，未變更應用程式。

## 結論

CAR 適合作為本專案的「偵測分析知識庫」：把使用者選取的 ATT&CK 技術連到分析思路、工具查詢、必要資料欄位、候選感測器與測試說明。CAR 官方明確區分 ATT&CK 的威脅描述與 CAR 的可能偵測方法，並指出實際適用性由組織環境決定。因此，產品應提供候選分析及證據管理，不能只因存在對應 CAR 條目就宣告環境已偵測或完整覆蓋。[官方定位](https://car.mitre.org/)

## 快照與可重現性

本次透過 GitHub API 讀取 `branches/master`，確認提交為 `1b922fe1527d956e222a99473472e594f10f610b`，提交時間 `2025-05-16T14:27:55Z`。遞迴 Git tree 回傳 `truncated=false`，其中 `analytics/*.yaml` 有 102 份、`data_model/*.yaml` 有 13 份、`sensors/*.yaml` 有 7 份；這是檔案數，不代表獨立技術數或可直接執行規則數。`releases` API 本次回傳空陣列，整合時宜採 commit SHA 與內容雜湊作版本識別，避免自行命名不存在的 CAR release。[分支 API](https://api.github.com/repos/mitre-attack/car/branches/master)、[固定提交](https://github.com/mitre-attack/car/commit/1b922fe1527d956e222a99473472e594f10f610b)、[完整 Git tree](https://api.github.com/repos/mitre-attack/car/git/trees/1b922fe1527d956e222a99473472e594f10f610b?recursive=1)、[Releases API](https://api.github.com/repos/mitre-attack/car/releases)

建議原始 YAML、schema、生成程式及必要授權檔一起固定版本。官方網站適合閱讀與導航，正式匯入應以快照中的原始資料為準；不要把不同時間取得的網站頁面、YAML、感測器結果混成同一份資料集。

## Analytics 資料形狀

以下以該固定提交的 Yamale schema 為準；「可選」指 schema 的 `required=False`，不表示欄位實際存在時可以忽略。[analytic schema](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/scripts/analytic_schema.yaml)

| 類別 | 欄位 | 匯入注意事項 |
| --- | --- | --- |
| schema 必填 | `title`, `submission_date`, `information_domain`, `subtypes`, `analytic_types`, `id`, `description` | 日期格式是 `YYYY/MM/DD`；`information_domain` 是字串，不宜硬假設永遠只有單一分類。 |
| schema 可選 | `update_date`, `platforms`, `contributors`, `coverage`, `implementations`, `unit_tests`, `true_positives`, `data_model_references`, `references`, `d3fend_mappings` | UI 必須能呈現缺漏資料，不要填成「無需資料」或「已驗證」。 |
| `coverage[]` | 必填 `technique`, `tactics`, `coverage`；可選 `subtechniques` | 保留父、子技術與 tactic 原始結構。`coverage` 在 schema 是一般字串，不能硬轉為百分比。 |
| `implementations[]` | 必填 `type`；可選 `name`, `description`, `code`, `data_model` | 有實作項目仍可能沒有查詢碼，甚至僅包含外部參考連結。 |
| `unit_tests[]` | `description`；另有可選 `configurations`, `commands` | 這是測試說明／命令資料，不能視為本專案已執行成功。 |
| `true_positives[]` | 必填 `source`；可選 `description`, `event_snippet`, `full_event` | 上游提供的範例證據與本地環境驗證證據分開儲存。 |

`CONTRIBUTING.md` 的最低投稿清單與 schema 不完全一致：投稿指引把 `platforms`, `contributors`, `coverage` 列為最低欄位，而 schema 將它們標為可選；schema 另要求 `analytic_types`。匯入器應記錄實際資料與警告，避免只靠投稿文字推定每份歷史檔案一致。[投稿規範](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/CONTRIBUTING.md)

### 經核對的樣本

- `CAR-2013-05-009` 對應 `T1036`、`T1036.003`、`TA0005`，標示 `Moderate`；提供 Splunk、DNIF、LogPoint 查詢及僅連結的 Sigma 項目，資料需求包括 `process/create/exe` 與 `process/create/md5_hash`，另有 D3FEND 參考。其標題／描述討論同 hash 不同名稱，但 Basic Query 實際按 `Image` 統計不同 `Hashes`，方向存在可疑差異。整合時保留原文並允許「待審查」狀態；本次未在環境執行查詢，也不宣稱已證實有效。[完整 YAML](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/analytics/CAR-2013-05-009.yaml)
- `CAR-2013-07-001` 同時提供多個工具版本、資料欄位需求及 Windows 7 測試設定，說明測試前提可以相當舊，且部分查詢原文已提醒誤報問題；不宜只顯示查詢碼而隱藏限制與前提。[完整 YAML](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/analytics/CAR-2013-07-001.yaml)
- `CAR-2013-01-002` 有多個 ATT&CK 映射與 D3FEND 資料，但沒有 `implementations`, `unit_tests`, `data_model_references`；其描述也說明需要分析人員檢視輸出，不能把所有 analytic 一概當成自動告警規則。[完整 YAML](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/analytics/CAR-2013-01-002.yaml)

## Data Model 與 Sensors

CAR Data Model 以物件、動作、欄位描述遙測，analytic 使用例如 `process/create/command_line` 的三段參考。`process.yaml` 的 `actions` 與 `fields` 分別帶名稱及說明，欄位可附範例。這些參考是 CAR 的邏輯資料名稱，不等同目前 ATT&CK STIX Detection Strategy、Analytic、Data Component 的物件 ID。[process data model](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/data_model/process.yaml)、[data model schema](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/scripts/datamodel_schema.yaml)

Sensor 資料保留工具與版本，透過 `mappings[].object`, `action`, `fields`, `notes` 描述可取得內容。例如 `sysmon_13.yaml` 對 `process/create` 附 Event 1 說明及欄位；對網路 flow 的對應還明確附有語義可能不完全相同的註解。匯入時應保存版本及 notes，不能把「有 Sysmon」簡化成全部資料已具備。[Sysmon 13 原始資料](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/sensors/sysmon_13.yaml)、[sensor schema](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/scripts/sensor_schema.yaml)

特別注意：官方 `generate_sensors.py` 在建立 sensor→analytic 候選關聯時，僅檢查 sensor 欄位集合與 analytic 的 `data_model_references` 是否有**任一交集**，不是要求全部參考皆滿足。因此，網站的 Applicable Sensors 與 sensor 的 analytic coverage，不能直接當成資料需求完整滿足的證據。產品應自行呈現「已知需要／可提供／缺少／尚待確認」欄位，以及本地實際收集設定；即使所有列出的欄位都有，也仍需查詢相容性及偵測測試。[官方生成邏輯](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/scripts/generate_sensors.py)

## ATT&CK 映射與 Navigator 的版本限制

固定快照的 `generate_attack_nav_layer.py` 將 layer version 設為 `4.5`、ATT&CK 設為 `14`、Navigator 設為 `4.9.4`，domain 為 `mitre-enterprise`。目前專案使用 ATT&CK v20，應重新對目前載入的 domain／version 解析每個 ID，對無法解析、已撤回、已廢棄或 tactic 不符的映射保留原文並標示待處理。[官方 layer generator](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/scripts/generate_attack_nav_layer.py)

該 generator 對每個 `coverage` 先加入父層 `technique`，再加入明列的 `subtechniques`；父層 entry 會設定 `showSubtechniques=True`。這代表官方 layer 同時列出父層與指定子技術，**並不代表父層所有子技術都有相同分析支援**。整合後若提供「加入全部對應 TTP」，需要讓範圍清楚可見；可列父層彙總與精確子技術，但不得展開未明列的兄弟／子技術。同樣地，移除應只影響明確映射的選取，保留其他技術與註記。[同一生成流程](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/scripts/generate_attack_nav_layer.py)

本次查閱的 CAR schema 與上述樣本以 ATT&CK 技術 ID 映射，沒有據此建立 ATLAS `AML.Txxxx` 的直接官方對應。未來若由 ATLAS→ATT&CK 參考再連到 CAR，必須顯示為間接候選，不能因此宣告某 AI 行為已有偵測能力。

## 官方驗證流程代表什麼

`lint-yaml.yml` 在 push 至 master 時執行 YAML lint、三種 Yamale schema 驗證（使用 `--no-strict`，容許額外欄位）、檔案類型檢查及 ID／檔名一致性檢查。這些檢查可以作為本專案匯入驗證的參考，但不等同在各 SIEM 平台執行每一份分析並驗證告警品質。[官方驗證 workflow](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/.github/workflows/lint-yaml.yml)

`regenerate-docs.yml` 依序生成 data models、analytics、sensors、Navigator layer，再提交靜態網站輸出。故正式匯入可直接讀原始 YAML，不必執行這些會重建 docs 的上游腳本。匯入器另外應保留未知欄位，以免未來上游擴充造成資料遺失。[官方文件生成 workflow](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/.github/workflows/regenerate-docs.yml)

## 與本專案銜接的建議

以下是根據上游資料提出的產品設計建議，並非 CAR 官方已提供的本地功能：

1. **CAR 瀏覽器與雙向技術連結**：按平台、工具、analytic type、ATT&CK 技術與已選技術篩選。每個條目同時顯示原文、查詢／外部連結、資料需求、來源提交與映射狀態。
2. **獨立 catalog adapter**：CAR ID 保持獨立命名空間，不和 ATT&CK 的 `x-mitre-analytic` 合併。解析 YAML、來源資訊與版本差異由 adapter 負責，UI 只讀取正規化記錄。
3. **工作區偵測計畫**：讓使用者針對已選 ATT&CK TTP 指派 CAR 候選、工具版本與環境，記錄尚未評估、資料準備、已部署、已測試及相關證據。不要覆寫原有技術分數、註記與選取狀態。
4. **資料缺口與可重現匯出**：輸出 analytic ID、ATT&CK ID、實作類型、資料欄位、缺口、版本及證據。來源更新時可比對查詢或映射改變，要求重新評估舊驗證結果。
5. **測試與執行作後續模組**：先呈現測試說明與環境前提；若未來接 CALDERA／其他驗證環境，測試運行與結果採獨立執行紀錄。匯入知識庫本身不執行測試命令。

初期優先做 catalog、映射、查詢閱讀與選取連動；接著才增加環境遙測與證據追蹤。BZAR 與 OSSEM-CDM 在 repository 中是子模組，若後續擴大整合應分別追蹤來源提交及授權，不應假設只下載 CAR YAML 就已包含整套 Zeek 邏輯或通用事件正規化能力。[repository tree](https://github.com/mitre-attack/car/tree/1b922fe1527d956e222a99473472e594f10f610b)、[官方 BZAR 定位](https://car.mitre.org/)

## 授權與來源保存

CAR repository 採 Apache-2.0 並附 `NOTICE.txt`。發佈內附資料時，應隨附授權與適用的來源／歸屬聲明；修改檔案應保留變更說明。Sigma 等僅以連結引用的第三方內容，若未來改為直接下載及再散布，需另外追蹤其內容與授權，不能推定 CAR 的授權涵蓋所有外部連結。[LICENSE.txt](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/LICENSE.txt)、[NOTICE.txt](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/NOTICE.txt)
