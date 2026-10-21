# MITRE ATT&CK 官方 GitHub 倉庫盤點與整合對映

查核日期：2026-10-16（Asia/Taipei）。本文件是架構規劃的上游證據附錄；功能與整合方式欄位包含架構建議，不代表已實作、已通過相容測試或承諾完整重現上游全部功能。

本次輸入為 GitHub 官方公開組織、repository metadata、README、license 與必要套件原始文件；本地輸出為 `D:\MITREATTACK_SIMULATOR\MITRE_REPOSITORY_INVENTORY.md`。本次未安裝或執行上游程式，未修改本案程式。

## 1. 範圍及完整性證據

- 範圍只計 `mitre-attack` 組織當前公開 repositories，含 fork 及 archived。其他 MITRE／CTID／Apache repo 另列補充。
- GitHub 連線工具實際執行 repository search：`org:mitre-attack is:public fork:true`，`per_page=100`，第1頁21筆，第2頁0筆；沒有套用 archive filter。可人工復核的[官方搜尋](https://github.com/search?q=org%3Amitre-attack+is%3Apublic+fork%3Atrue&type=repositories)與[組織 all 清單](https://github.com/orgs/mitre-attack/repositories?type=all)均對應21個名稱。
- 完整性是「查核當次可見公開清單」；不包含private、被刪除、已移轉出組織或未公開項目。GitHub search有索引延遲，未來應以org REST分頁重跑並與本清單diff。
- 原先嘗試org REST URL遭工具支援限制，shell網路DNS失敗；改用官方GitHub connector分頁搜尋，加上組織網頁全清單及21個逐一repository metadata交叉核對。沒有把失敗的API請求寫成成功證據。
- 21個均讀取README與repository metadata；21個均取default branch commit SHA。8個archived、13個未封存，其中caret為fork。未封存只是GitHub狀態，不等於持續維護或可相容本案。
- 下表日期是 default branch HEAD committer date（UTC），不是 release 日期，也不是 repo任何分支的last pushed時間。SHA是研究快照，不是建議永久固定的產品版本。

## 2. 全部21個repo狀態快照

| Repository | 類型 | 狀態 | Fork | 預設分支 | HEAD日期 UTC | HEAD commit |
|---|---|---|---|---|---|---|
| [attack-stix-data](https://github.com/mitre-attack/attack-stix-data) | 資料／Collection Index | 未封存 | 否 | master | 2026-10-13 | [c2494b29dd26](https://github.com/mitre-attack/attack-stix-data/commit/c2494b29dd268c46a5d0ea0990553e4327cd2253) |
| [mitreattack-python](https://github.com/mitre-attack/mitreattack-python) | Python SDK／分析／格式工具 | 未封存 | 否 | main | 2026-10-13 | [2548d0ae1644](https://github.com/mitre-attack/mitreattack-python/commit/2548d0ae164461b5fb00f21f7ac0f3fe1b09d683) |
| [attack-data-model](https://github.com/mitre-attack/attack-data-model) | TypeScript SDK／schema | 未封存 | 否 | main | 2026-06-25 | [2b50c256e04d](https://github.com/mitre-attack/attack-data-model/commit/2b50c256e04d3633a96f3c49b31c921c8843e9e4) |
| [attack-navigator](https://github.com/mitre-attack/attack-navigator) | Angular UI／layer 規格 | 未封存 | 否 | master | 2026-09-10 | [734a1caba29f](https://github.com/mitre-attack/attack-navigator/commit/734a1caba29fcd51f20b9ca239ce652b3354a47e) |
| [attack-workbench-frontend](https://github.com/mitre-attack/attack-workbench-frontend) | Angular UI／知識庫編輯協作 | 未封存 | 否 | main | 2026-07-24 | [5d1f16a98bef](https://github.com/mitre-attack/attack-workbench-frontend/commit/5d1f16a98bef20852cb7a04ea129d84d6934868a) |
| [attack-workbench-rest-api](https://github.com/mitre-attack/attack-workbench-rest-api) | Node.js 後端／持久化 | 未封存 | 否 | main | 2026-07-06 | [6e6bf5116fcc](https://github.com/mitre-attack/attack-workbench-rest-api/commit/6e6bf5116fcc21eab4962ec1ffa4f9f130744d58) |
| [attack-workbench-taxii-server](https://github.com/mitre-attack/attack-workbench-taxii-server) | Node.js／TAXII 2.1 服務 | 未封存 | 否 | main | 2026-06-17 | [5ebe3f8bbaf5](https://github.com/mitre-attack/attack-workbench-taxii-server/commit/5ebe3f8bbaf56a8cf0dd96e8643dd5d6a383f3ba) |
| [attack-workbench-deployment](https://github.com/mitre-attack/attack-workbench-deployment) | 部署／Docker／Kubernetes | 未封存 | 否 | main | 2026-10-04 | [91ac9b4060fb](https://github.com/mitre-attack/attack-workbench-deployment/commit/91ac9b4060fbc77949e240ec35b663843bbde97b) |
| [attack-website](https://github.com/mitre-attack/attack-website) | 網站建置／官方內容呈現 | 未封存 | 否 | master | 2026-10-14 | [cafe596a6e10](https://github.com/mitre-attack/attack-website/commit/cafe596a6e101ba7ff2d8c1b3e3f976f97782dbe) |
| [car](https://github.com/mitre-attack/car) | 偵測分析知識庫／YAML | 未封存 | 否 | master | 2025-05-16 | [1b922fe1527d](https://github.com/mitre-attack/car/commit/1b922fe1527d956e222a99473472e594f10f610b) |
| [bzar](https://github.com/mitre-attack/bzar) | Zeek 偵測腳本／CAR 元件 | 未封存 | 否 | master | 2024-06-26 | [59bae4a0e784](https://github.com/mitre-attack/bzar/commit/59bae4a0e7849a75fa5ea86a206f10f3ce8dbe22) |
| [caret](https://github.com/mitre-attack/caret) | 舊 UI／關聯視覺化／fork | 未封存 | 是 | master | 2020-01-17 | [a9db8c8636d8](https://github.com/mitre-attack/caret/commit/a9db8c8636d8e71cc30780669866524d6b30d0f0) |
| [attack-arsenal](https://github.com/mitre-attack/attack-arsenal) | 紅隊／對手模擬資源 | 未封存 | 否 | master | 2021-04-20 | [201db70f4036](https://github.com/mitre-attack/attack-arsenal/commit/201db70f403676cc8ec090035f17d98cf9995244) |
| [attack-scripts](https://github.com/mitre-attack/attack-scripts) | 歷史 Python scripts／已替代 | Archived | 否 | master | 2023-12-11 | [445f5614e7a3](https://github.com/mitre-attack/attack-scripts/commit/445f5614e7a389d92b4e1984f203fc59604cc518) |
| [attack-datasources](https://github.com/mitre-attack/attack-datasources) | 歷史研究／YAML／notebook | Archived | 否 | main | 2023-09-13 | [5d50f731de44](https://github.com/mitre-attack/attack-datasources/commit/5d50f731de441eb09078623a2c29cc3420a01949) |
| [attack-datasources-stix-beta](https://github.com/mitre-attack/attack-datasources-stix-beta) | 歷史 schema 示範／mock data | Archived | 否 | main | 2023-09-13 | [c6c37a2fddd6](https://github.com/mitre-attack/attack-datasources-stix-beta/commit/c6c37a2fddd6f51bf74862f1cee98d240c6810ea) |
| [tram](https://github.com/mitre-attack/tram) | 舊報告映射／已移轉 | Archived | 否 | master | 2021-10-06 | [252603f09898](https://github.com/mitre-attack/tram/commit/252603f09898d69fc753c5c7eccab244d6d084ba) |
| [joystick](https://github.com/mitre-attack/joystick) | 歷史 Evaluations 分析工具 | Archived | 否 | master | 2023-09-13 | [1829d7b7284c](https://github.com/mitre-attack/joystick/commit/1829d7b7284caefda0516c6d57271fa64798e284) |
| [attack-evals](https://github.com/mitre-attack/attack-evals) | 歷史 Evaluations 網站／已移轉 | Archived | 否 | master | 2021-04-30 | [d4879476337a](https://github.com/mitre-attack/attack-evals/commit/d4879476337a46a71bd37d073cc31379defb57d3) |
| [evals_caldera](https://github.com/mitre-attack/evals_caldera) | 歷史 CALDERA plugin／已替代 | Archived | 否 | master | 2023-09-14 | [8721102af46a](https://github.com/mitre-attack/evals_caldera/commit/8721102af46ad394d0bc7f2596d122c59eb065b6) |
| [attack-archives](https://github.com/mitre-attack/attack-archives) | 歷史網站快照／已替代 | Archived | 否 | master | 2020-07-21 | [f60e76afba4a](https://github.com/mitre-attack/attack-archives/commit/f60e76afba4ad6f6e7fe2d26b156c9b898bc7db9) |

每個repo metadata可由 `https://api.github.com/repos/mitre-attack/<repo>` 復核；commit證據由表中的不可變連結復核。

## 3. 逐項能力與建議整合方式

### 1. attack-stix-data

- 類別：資料／Collection Index；未封存。
- 官方可見能力：Enterprise、Mobile、ICS 的 STIX 2.1 collections、各版本 bundles、機器可讀 index。
- 建議整合：資料匯入；作官方知識庫主要來源；Provider 下載後建立 immutable snapshot，索引與 UI 只讀投影。
- 授權證據：MITRE 自訂 ATT&CK 資料授權，非 Apache-2.0；須保留授權及版權聲明。 [授權檔](https://github.com/mitre-attack/attack-stix-data/blob/c2494b29dd268c46a5d0ea0990553e4327cd2253/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/attack-stix-data)。
- 限制／待驗證：最新未標版本 JSON 會變；須鎖 release、commit、hash，不能只存 latest URL。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-stix-data/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-stix-data/commit/c2494b29dd268c46a5d0ea0990553e4327cd2253)；README blob SHA：`568614d8d1e2462b34ab19f92766e04a2e2d8478`。

### 2. mitreattack-python

- 類別：Python SDK／分析／格式工具；未封存。
- 官方可見能力：MitreAttackData 關聯查詢；navlayers、attackToExcel、collections、diffStix；下載與 changelog CLI。
- 建議整合：直接 Python 套件經 adapter 包裝；依需求逐個替換重複演算法。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/mitreattack-python/blob/2548d0ae164461b5fb00f21f7ac0f3fe1b09d683/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/mitreattack-python)。
- 限制／待驗證：pyproject.toml 當前 version=6.3.1、Python >=3.11；核心 MitreAttackData 明列 STIX 2.0，與本案 STIX 2.1 不能假設直接互換；先驗證欄位與往返損失。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/mitreattack-python/blob/main/README.md)；[研究HEAD](https://github.com/mitre-attack/mitreattack-python/commit/2548d0ae164461b5fb00f21f7ac0f3fe1b09d683)；README blob SHA：`a5bc365ea8fcc17936a22778da7cff3517c98c57`。

### 3. attack-data-model

- 類別：TypeScript SDK／schema；未封存。
- 官方可見能力：STIX 2.1 Zod schemas、型別、ES6 classes、解析、驗證、序列化、關聯導覽。
- 建議整合：schema 作規格依據；需要官方執行驗證時由可選 Node.js 程序提供 JSON 契約，勿將 TypeScript 當 Python 套件。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/attack-data-model/blob/2b50c256e04d3633a96f3c49b31c921c8843e9e4/LICENSE)；[metadata](https://api.github.com/repos/mitre-attack/attack-data-model)。
- 限制／待驗證：README 相容表仍寫 v18 upcoming，taxii 列 coming soon；實際能力須以套件版本與測試證明。ADM版本、ATT&CK release、ATT&CK spec version 是三個維度；ATTACK_SPEC_VERSION=3.3.0 不是 dataset release。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-data-model/blob/main/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-data-model/commit/2b50c256e04d3633a96f3c49b31c921c8843e9e4)；README blob SHA：`65cec657fcbda9e014683d1431d2b786ef85685b`。

### 4. attack-navigator

- 類別：Angular UI／layer 規格；未封存。
- 官方可見能力：矩陣瀏覽、layers、顏色／註解／分數、平台篩選、自訂 context menu、匯出、版本資料與離線設定；layer 格式規範與範例。
- 建議整合：Navigator layer 格式互通優先；保留本案原生矩陣；可選外部／本地 Navigator 開啟。完整嵌入待獨立決策。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/attack-navigator/blob/734a1caba29fcd51f20b9ca239ce652b3354a47e/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/attack-navigator)。
- 限制／待驗證：Node/Angular 與 Qt 執行環境不同；匯出與公式語義須逐欄對照；readme舊 TAXII 2.0 描述不能當仍受支援承諾。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-navigator/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-navigator/commit/734a1caba29fcd51f20b9ca239ce652b3354a47e)；README blob SHA：`27ab2a93bc36f661729d51af0d78049007ce539c`。

### 5. attack-workbench-frontend

- 類別：Angular UI／知識庫編輯協作；未封存。
- 官方可見能力：探索、建立、註解與分享自訂 ATT&CK 物件與關聯；collections / indexes；整合與操作文件。
- 建議整合：參考操作能力；以 Workbench REST connector 與 collection 互通整合，保留獨立服務 UI，必要時深連結。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/attack-workbench-frontend/blob/5d1f16a98bef20852cb7a04ea129d84d6934868a/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/attack-workbench-frontend)。
- 限制／待驗證：完整服務需要 REST API 與 MongoDB；不能只複製前端就取得完整 Workbench。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-workbench-frontend/blob/main/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-workbench-frontend/commit/5d1f16a98bef20852cb7a04ea129d84d6934868a)；README blob SHA：`bbe196cccadb0649f4533f3d6b92de010e6f830f`。

### 6. attack-workbench-rest-api

- 類別：Node.js 後端／持久化；未封存。
- 官方可見能力：ATT&CK STIX 2.1 物件 CRUD、collection/version管理、認證授權、程式存取；MongoDB 保存。
- 建議整合：遠端 connector 為主；可選使用者管理之本機獨立服務。同步採讀取→預覽→衝突處理→明確發布。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/attack-workbench-rest-api/blob/6e6bf5116fcc21eab4962ec1ffa4f9f130744d58/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/attack-workbench-rest-api)。
- 限制／待驗證：本案本機保存與 Workbench 遠端版本要分離；端點、認證、修改語義、刪除／撤銷不可從 README 推定，須鎖服務版本與 OpenAPI。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-workbench-rest-api/blob/main/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-workbench-rest-api/commit/6e6bf5116fcc21eab4962ec1ffa4f9f130744d58)；README blob SHA：`62afa2882ced5915d37efeaa1ad84346c6b5cb8b`。

### 7. attack-workbench-taxii-server

- 類別：Node.js／TAXII 2.1 服務；未封存。
- 官方可見能力：將 Workbench collections 與版本用 TAXII 2.1 discovery、API roots、collection endpoints 分享；穩定 latest alias。
- 建議整合：TAXII 2.1 ingestion connector；若分享本案資料，優先輸出到 Workbench 再由其服務分享。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/attack-workbench-taxii-server/blob/5ebe3f8bbaf56a8cf0dd96e8643dd5d6a383f3ba/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/attack-workbench-taxii-server)。
- 限制／待驗證：Workbench依賴不可省略；collection alias可能指向不同版本，下載須記錄實際collection/version。先不自製完整TAXII server。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-workbench-taxii-server/blob/main/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-workbench-taxii-server/commit/5ebe3f8bbaf56a8cf0dd96e8643dd5d6a383f3ba)；README blob SHA：`39a58396e1021bd16387922d7ce2b9408d893d1a`。

### 8. attack-workbench-deployment

- 類別：部署／Docker／Kubernetes；未封存。
- 官方可見能力：Docker Compose 互動部署、frontend/API/database；可選 TAXII sidecar；Kubernetes/Kustomize manifests。
- 建議整合：部署模板與運維文件整合；可選獨立部署配置，不將容器引擎作桌面基本依賴。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/attack-workbench-deployment/blob/91ac9b4060fbc77949e240ec35b663843bbde97b/LICENSE)；[metadata](https://api.github.com/repos/mitre-attack/attack-workbench-deployment)。
- 限制／待驗證：需容器、ports、volumes、backup、credentials與服務健康檢查；frontend README 說 Compose 為唯一官方支援，deployment README又提供 k8s，應逐方案確認支援狀態。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-workbench-deployment/blob/main/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-workbench-deployment/commit/91ac9b4060fbc77949e240ec35b663843bbde97b)；README blob SHA：`719579df58d9643ba4c9fb946573feac7a714b85`。

### 9. attack-website

- 類別：網站建置／官方內容呈現；未封存。
- 官方可見能力：產生 ATT&CK 官方網站，可帶入自訂內容；開發、客製、發佈與歷史網站流程。
- 建議整合：官方內容連結／引用及頁面語義參考；可選產生靜態研究入口。結構化資料仍由 STIX 來源供應。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/attack-website/blob/cafe596a6e101ba7ff2d8c1b3e3f976f97782dbe/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/attack-website)。
- 限制／待驗證：網站建置目前要求 Just/uv/Node；不應以 scraping HTML 取代 STIX API。網站資產及 branding與程式授權須分開。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-website/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-website/commit/cafe596a6e101ba7ff2d8c1b3e3f976f97782dbe)；README blob SHA：`5d0da86f0557b03fa34e2fa2691ed1ee30248eff`。

### 10. car

- 類別：偵測分析知識庫／YAML；未封存。
- 官方可見能力：analytic hypothesis、domain、TTP mappings、偽碼、工具實作（如 Splunk/EQL）、觸發測試、資料模型與sensor資訊；analytics YAML。
- 建議整合：資料匯入至 Detection Catalog，保留 CAR ID、版本、原始 query、平台與工具條件；建立 TTP 關聯。
- 授權證據：Apache-2.0（GitHub repository metadata）。 [授權檔](https://github.com/mitre-attack/car/blob/1b922fe1527d956e222a99473472e594f10f610b/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/car)。
- 限制／待驗證：CAR 與 ATT&CK 是不同知識庫；存在規則／TTP mapping 不等於本環境已驗證偵測。測試描述與可執行命令不得在匯入時自動執行。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/car/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/car/commit/1b922fe1527d956e222a99473472e594f10f610b)；README blob SHA：`7af01f21f310c05daf0e13742428d0edb8d82b26`。

### 11. bzar

- 類別：Zeek 偵測腳本／CAR 元件；未封存。
- 官方可見能力：以 SMB、DCE-RPC、File Extraction、SumStats 偵測行為，輸出 Zeek notice log；可用白名單與開關調校。
- 建議整合：先匯入規則 metadata／技術對應與 Zeek notice結果；需執行時使用外部 Zeek，而非 Python內嵌。
- 授權證據：BSD-3-Clause（GitHub metadata；README 指 LICENSE.txt）。 [授權檔](https://github.com/mitre-attack/bzar/blob/59bae4a0e7849a75fa5ea86a206f10f3ce8dbe22/LICENSE)；[metadata](https://api.github.com/repos/mitre-attack/bzar)。
- 限制／待驗證：不是通用 SIEM 引擎；依 Zeek及協定解析版本、環境流量而異；README 自稱資訊截至2020，雖未封存仍須先做兼容驗證。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/bzar/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/bzar/commit/59bae4a0e7849a75fa5ea86a206f10f3ce8dbe22)；README blob SHA：`df502c348fa5526df1a1b774eff0c03df408c536`。

### 12. caret

- 類別：舊 UI／關聯視覺化／fork；未封存，fork自 mitre/caret。
- 官方可見能力：proof-of-concept GUI，連結 ATT&CK groups/techniques 至 CAR analytics、data model、sensors。
- 建議整合：參考功能模型／關聯圖需求；重用資料契約，避免引入舊 gulp/bower 前端。
- 授權證據：LICENSE.md 為 MIT 型許可條款並附政府合約 NOTICE；API分類 NOASSERTION，不應直接說無授權或標成純 MIT。 [授權檔](https://github.com/mitre-attack/caret/blob/a9db8c8636d8e71cc30780669866524d6b30d0f0/LICENSE.md)；[metadata](https://api.github.com/repos/mitre-attack/caret)。
- 限制／待驗證：唯一 fork；未封存但長期未更新；README All Rights Reserved 與 license全文須一併保留／審查。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/caret/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/caret/commit/a9db8c8636d8e71cc30780669866524d6b30d0f0)；README blob SHA：`4374f862eabd5b6fcbf6585bff9d8f4793e795ff`。

### 13. attack-arsenal

- 類別：紅隊／對手模擬資源；未封存。
- 官方可見能力：MITRE發布的 red team／adversary emulation resources，內容可對應 ATT&CK、Evaluations 等研究。
- 建議整合：資源／計畫 metadata 匯入、TTP 關聯與外部連結優先；預留獨立演練 connector。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/attack-arsenal/blob/201db70f403676cc8ec090035f17d98cf9995244/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/attack-arsenal)。
- 限制／待驗證：未封存不表示仍積極維護；README 要求事前明確授權。不能把下載資料等同於允許執行 payload；本次只規劃。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-arsenal/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-arsenal/commit/201db70f403676cc8ec090035f17d98cf9995244)；README blob SHA：`f1548b5603152926d8e6dfb7d7284b87732d24ec`。

### 14. attack-scripts

- 類別：歷史 Python scripts／已替代；已封存。
- 官方可見能力：一次性資料處理與視覺化、Navigator layer 範例；README 指向 mitreattack-python。
- 建議整合：封存參考，按缺口逐項移植到本案能力；優先使用 mitreattack-python。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/attack-scripts/blob/445f5614e7a389d92b4e1984f203fc59604cc518/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/attack-scripts)。
- 限制／待驗證：已明示停止維護；不得作新功能主依賴或將舊 TAXII 相容資訊當現況。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-scripts/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-scripts/commit/445f5614e7a389d92b4e1984f203fc59604cc518)；README blob SHA：`0a798e570621ea90c514e7d2d813f581bd548de6`。

### 15. attack-datasources

- 類別：歷史研究／YAML／notebook；已封存。
- 官方可見能力：Data Source / Data Component 方法論、YAML貢獻、Jupyter notebook。
- 建議整合：參考方法論與歷史格式移轉；正式資料改取相應 ATT&CK snapshot。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/attack-datasources/blob/5d50f731de441eb09078623a2c29cc3420a01949/LICENSE)；[metadata](https://api.github.com/repos/mitre-attack/attack-datasources)。
- 限制／待驗證：README明示已不再需要，Python工具改看mitreattack-python；不得與正式最新版混為一庫。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-datasources/blob/main/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-datasources/commit/5d50f731de441eb09078623a2c29cc3420a01949)；README blob SHA：`eac7ca9f3fbbec817268c84e21d2502039a218ca`。

### 16. attack-datasources-stix-beta

- 類別：歷史 schema 示範／mock data；已封存。
- 官方可見能力：ATT&CK v10前資料源／元件STIX 2.0/2.1表示法示範，含任意隨機生成mock relationships。
- 建議整合：封存規格參考；若授權允許作測試fixture要明標mock並隔離。
- 授權證據：MITRE 自訂 ATT&CK 資料授權。 [授權檔](https://github.com/mitre-attack/attack-datasources-stix-beta/blob/c6c37a2fddd6f51bf74862f1cee98d240c6810ea/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/attack-datasources-stix-beta)。
- 限制／待驗證：不能匯入正式Knowledge Catalog；README明說內容不代表正式 data sources或technique relations。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-datasources-stix-beta/blob/main/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-datasources-stix-beta/commit/c6c37a2fddd6f51bf74862f1cee98d240c6810ea)；README blob SHA：`fe1d6392e8b8e3bf583641859a419beb9eb077d3`。

### 17. tram

- 類別：舊報告映射／已移轉；已封存。
- 官方可見能力：舊 TRAM v0.5，本地單人輸入報告URL，輔助報告→ATT&CK mapping。
- 建議整合：舊repo僅遷移證據；實際評估後繼 CTID TRAM，採可選ML獨立服務／結果匯入。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/tram/blob/252603f09898d69fc753c5c7eccab244d6d084ba/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/tram)。
- 限制／待驗證：已封存且README移至CTID；不得宣稱此repo提供最新ML能力，也不能假定涵蓋全技術或中文。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/tram/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/tram/commit/252603f09898d69fc753c5c7eccab244d6d084ba)；README blob SHA：`bbcfae470c8d43bbfdb5ce674ba43f3cd0c7d351`。

### 18. joystick

- 類別：歷史 Evaluations 分析工具；已封存。
- 官方可見能力：將 ATT&CK Evaluations結果呈現成便於理解的視圖；Python啟動本機單人web app。
- 建議整合：參考查詢／比較視圖；以獨立 Evaluation Catalog 匯入歷史結果、保留輪次與方法論。
- 授權證據：Apache-2.0（GitHub metadata；README僅部分notice）。 [授權檔](https://github.com/mitre-attack/joystick/blob/1829d7b7284caefda0516c6d57271fa64798e284/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/joystick)。
- 限制／待驗證：已停止維護；不同輪次不能直接做總分排名，需要明確比較限制與映射版本。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/joystick/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/joystick/commit/1829d7b7284caefda0516c6d57271fa64798e284)；README blob SHA：`fb12f5de295442aa77b94e230846d94774a389b0`。

### 19. attack-evals

- 類別：歷史 Evaluations 網站／已移轉；已封存。
- 官方可見能力：舊 ATT&CK Evaluations 網站與歷史內容；README指向 attackevals/website。
- 建議整合：封存入口與來源鏈；新資料來源、再散布及API契約待後繼官方渠道查核。
- 授權證據：根目錄未見 LICENSE，GitHub license=null；terms-of-use.html 只轉址。待確認內容與程式可再利用範圍。 [舊terms頁](https://github.com/mitre-attack/attack-evals/blob/d4879476337a46a71bd37d073cc31379defb57d3/terms-of-use.html)；[metadata](https://api.github.com/repos/mitre-attack/attack-evals)。
- 限制／待驗證：不可因public就假設可大量打包；後繼repo本次 README 404，不據此推定消失或停止服務。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-evals/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-evals/commit/d4879476337a46a71bd37d073cc31379defb57d3)；README blob SHA：`69c309e9a37efb31f95c81ca4bf52a7366d8907c`。

### 20. evals_caldera

- 類別：歷史 CALDERA plugin／已替代；已封存。
- 官方可見能力：ATT&CK Evaluations Round 1 APT3 TTPs的CALDERA plugin；README導向Emu。
- 建議整合：封存參考；計畫metadata可建模；執行整合評估後繼Emu/Caldera外部服務。
- 授權證據：Apache-2.0（GitHub metadata）。 [授權檔](https://github.com/mitre-attack/evals_caldera/blob/8721102af46ad394d0bc7f2596d122c59eb065b6/LICENSE)；[metadata](https://api.github.com/repos/mitre-attack/evals_caldera)。
- 限制／待驗證：依賴CALDERA、domain lab/facts；不是獨立模擬引擎，不能直接承諾新版Caldera相容。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/evals_caldera/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/evals_caldera/commit/8721102af46ad394d0bc7f2596d122c59eb065b6)；README blob SHA：`95aac291fe208025bfd01d7a1b14fe399f95e657`。

### 21. attack-archives

- 類別：歷史網站快照／已替代；已封存。
- 官方可見能力：舊ATT&CK網站歷史版本、archives.json、archive_cli.py。
- 建議整合：封存參考；舊頁引用補充；版本資料以attack-stix-data及attack-website現行流程為準。
- 授權證據：Apache-2.0。 [授權檔](https://github.com/mitre-attack/attack-archives/blob/f60e76afba4ad6f6e7fe2d26b156c9b898bc7db9/LICENSE.txt)；[metadata](https://api.github.com/repos/mitre-attack/attack-archives)。
- 限制／待驗證：README明示被website新版versioning取代；不要新增日常同步依賴。
- 功能來源：[README（研究時預設分支）](https://github.com/mitre-attack/attack-archives/blob/master/README.md)；[研究HEAD](https://github.com/mitre-attack/attack-archives/commit/f60e76afba4ad6f6e7fe2d26b156c9b898bc7db9)；README blob SHA：`43afcfdd4c06023e73cff04a6fd029fd6ee6d1b1`。

## 4. 跨repo能力歸併及依賴界線

| 本案能力群 | 上游對映 | 整合邊界 | 建議先後 |
|---|---|---|---|
| 版本化知識庫／來源追溯 | attack-stix-data；archives/website作歷史參考 | Provider→原始快照→解析驗證→查詢投影 | 第一優先 |
| 文件／矩陣／格式交換 | Navigator、mitreattack-python navlayers/Excel | 本案文件是唯一可編輯狀態；codec保留未知欄位與loss report | 第二優先 |
| 關聯查詢／版本差異 | Python SDK、ADM schemas | 內部Query/Diff contract；版本化adapter比較輸出 | 第二優先 |
| 自訂知識與協作／分享 | Workbench frontend/API/TAXII/deployment | 遠端版本與本地快照分離；可選獨立服務 | 基礎穩定後 |
| 偵測內容／資料源／圖譜 | CAR、BZAR、CARET、正式STIX偵測物件 | 不同catalog命名空間；證據與驗證狀態獨立 | 基礎穩定後 |
| 報告文字→候選TTP | 舊TRAM導向CTID TRAM | ML獨立工作；結果是待人工接受候選，含模型版本與原文段落 | 獨立試點 |
| 評估資料比較 | Joystick、attack-evals及後繼 | Evaluation catalog；保留輪次、子步驟、方法論與供應商上下文 | 資料授權確認後 |
| 演練計畫／外部執行 | Arsenal、evals_caldera及後繼Emu/Caldera | Plan/Run/Artifact模型分離；外部runner、明確目標與授權 | 單獨規劃與驗收 |
| 封存及歷史兼容 | scripts、datasources、beta、archives等 | registry標記reference/superseded/mock，避免正式資料自動混入 | 先盤點，不做基礎依賴 |

以上是能力級整合；repo並不一一等於一個本案模組。Workbench四個repo共同構成服務產品，CAR/BZAR有隸屬關係，封存repo已有替代路徑。整合涵蓋率應以功能清單及驗收狀態計算，不能以clone數量計算。

## 5. 必須明確管理的兼容與授權問題

1. **資料／套件／規格分開版本化。** ATT&CK release、STIX spec、ATT&CK spec、Navigator layer schema、ADM版本、Python SDK版本以及遠端服務API版本不可共用單一version欄位。
2. **Python SDK不是STIX 2.1通用替代品。** [MitreAttackData原始碼](https://github.com/mitre-attack/mitreattack-python/blob/main/mitreattack/stix20/MitreAttackData.py)仍明列STIX 2.0；[pyproject](https://github.com/mitre-attack/mitreattack-python/blob/main/pyproject.toml)顯示6.3.1及Python>=3.11、CLI清單；[docs目錄](https://github.com/mitre-attack/mitreattack-python/blob/main/docs/index.rst)列模組。各模組須獨立驗證，不把整個包的相容性一次通過。
3. **ADM為TypeScript。** [README](https://github.com/mitre-attack/attack-data-model/blob/main/README.md)及[package.json](https://github.com/mitre-attack/attack-data-model/blob/main/package.json)證明語言與套件。README開頭泛稱多來源，但具體清單把TAXII標為coming soon；相容表有upcoming資訊，`COMPATIBILITY.md`本次404。須用固定release、公開schema與真實bundle試驗，不能照表承諾支援最新版本。
4. **保留資料來源與命名空間。** ATT&CK technique、CAR analytic、Zeek notice、演練ability、evaluation step、TRAM候選映射不是同一物件；引用關聯要保留source dataset/object/modified/version與證據。mock beta不得進正式庫。
5. **官方工具的環境依賴互不相同。** Qt桌面、Angular/Node、MongoDB、Zeek、ML模型與Caldera應有不同adapter及運行環境。桌面核心不能因可選整合不可用而啟動失敗。
6. **離線應是能力分級。** 本機knowledge/document/query/report可離線；下載、遠端Workbench、TAXII與模型／runner可能需額外環境。缺少功能顯示unavailable與原因，不靜默回退或把遠端結果冒充本機結果。
7. **授權不能按組織統一推定。** 大多程式Apache-2.0，BZAR為BSD-3-Clause，ATT&CK資料為自訂許可，CARET有MIT型條款與額外NOTICE，歷史evals授權待查。license manifest需對應到具體artifact及其第三方依賴；公開repo不代表可省略notice。這是整合工程的資料要求，本文件不代替法律審查。
8. **收集／下載與外部修改或執行分離。** 本次完全沒有執行上游內容；未來Workbench發布、TAXII分享、演練runner應有獨立操作狀態、權限／目標範圍與audit，不能由匯入解析順帶觸發。

## 6. 組織外相關上游（補充，不算入21個）

| Repository / 官方渠道 | 來源關係與可見能力 | 建議 | 本次證據／未確定事項 |
|---|---|---|---|
| [mitre/cti](https://github.com/mitre/cti) | 官方STIX 2.0 ATT&CK與CAPEC；與STIX2.1庫並行 | 作明確STIX2.0 provider及Python SDK兼容選項；CAPEC屬另外資料範圍 | [README](https://github.com/mitre/cti/blob/master/README.md)已讀；不要算成mitre-attack repo |
| [CTID TRAM](https://github.com/center-for-threat-informed-defense/tram) | 舊TRAM README指定後繼；SciBERT候選映射／註記／重訓，README稱開箱支援up to 50常見技術 | 遠端／本機可選ML服務，先驗證涵蓋率、語言、模型與ATT&CK版本 | [README](https://github.com/center-for-threat-informed-defense/tram/blob/main/README.md)已讀，標示ATT&CK v13；不能宣稱全部技術／中文已支援 |
| [mitre/emu](https://github.com/mitre/emu) | evals_caldera README導向；使用CTID emulation library的Caldera plugin | 只先建立Plan匯入與版本追溯；runner另案 | [README](https://github.com/mitre/emu/blob/master/README.md)已讀；payload／facts／插件依賴須後續確認 |
| [CTID adversary_emulation_library](https://github.com/center-for-threat-informed-defense/adversary_emulation_library) | Emu README指定對手模擬計畫來源 | 補充資料provider候選 | 本次僅從Emu建立官方來源鏈，未逐計畫審查或宣稱完整支援 |
| [apache/caldera](https://github.com/apache/caldera)（舊mitre/caldera轉址） | 對手模擬平台、REST API、C2及plugins | 可選外部runner；不可列為當前mitre-attack組織repo | [舊官方URL](https://github.com/mitre/caldera)本次實際轉址apache/caldera；Windows桌面不能假設直接滿足其Linux/macOS伺服器環境 |
| [attackevals/website](https://github.com/attackevals/website)及[官方評估站](https://attackevals.mitre-engenuity.org/) | attack-evals README指定後繼 | 先作來源入口，待查可公開取得的現行資料及使用條款 | 本次connector的README請求404；不推定現行repo狀態、不虛構API能力 |

本補充表不是MITRE／CTID所有專案的完整盤點；本次完整清單的承諾僅限第2節的mitre-attack公開組織範圍。使用者尚未提出的個人構想不在本盤點中推定。

## 7. 後續逐能力驗證記錄建議

每個integration應記錄：upstream repo與owner、用途、adapter ID、可用模式（native/package/data/remote/process/reference）、狀態（discovered/spec-reviewed/prototype/verified/deprecated/blocked）、固定ref與artifact hash、license/notice、dataset/spec/API相容矩陣、輸入／輸出契約、資訊損失、測試fixture、最後驗證時間與替代路徑。狀態未達verified前，介面顯示experimental或unavailable。

下次更新先以官方org清單diff新增／移轉／封存項目，再逐個檢查default branch／release／license變更，最後跑對應契約測試。此次研究僅完成「discovered及spec-reviewed」層級，未執行兼容或功能測試。

