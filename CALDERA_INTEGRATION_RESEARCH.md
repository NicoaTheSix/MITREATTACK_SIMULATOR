# Caldera 整合可行性研究

查核日期：2026-10-19（Asia/Taipei）。研究對象：目前 canonical `apache/caldera`，以及舊 `mitre/caldera` 來源鏈。

輸入：GitHub 官方 repository metadata、固定 commit 原始碼、README、LICENSE／NOTICE、Fieldmanual 與官方網站；均為唯讀查核。
輸出絕對位址：`D:\MITREATTACK_SIMULATOR\CALDERA_INTEGRATION_RESEARCH.md`。
本次未安裝、啟動或測試 Caldera，未下載或執行 agent／payload，未修改本案程式或 ARCHITECTURE；僅新增本研究文件，並在 README 加入導覽連結。

## 1. 結論與決策範圍

**可以整合；建議由本案作研究、計畫及結果介面，Caldera 保持可選外部服務。**
第一步只接合 abilities／adversaries 目錄及既有 report；第二步建立獨立的演練計畫；第三步才考慮受控 operation 的啟動、追蹤及結果回收。
這是根據既有 REST v2 與物件模型做的架構可行性判斷，尚未通過真實服務的功能驗收。

Caldera 是具實際執行能力的對手模擬框架，不是 ATT&CK 資料瀏覽器或普通 Python 查詢套件。
把 TTP 勾選直接轉成 operation 會省略 ability 選擇、目標平台、executor、facts、權限及執行順序，不能視為可靠整合。
現有架構 R7-R 已預留外部 Runner；本次建議可沿用該邊界，無須先把桌面程式改成服務叢集。

## 2. 上游身分、版本與來源可信度

| 項目 | 查核結果 | 官方證據 |
|---|---|---|
| Canonical repository | `apache/caldera`，public、非 fork、未封存，default branch `master` | [metadata](https://api.github.com/repos/apache/caldera) |
| 舊 repository | 舊 API 回 `Moved Permanently`；舊 GitHub 網址轉至 Apache owner | [舊 API](https://api.github.com/repos/mitre/caldera)、[舊網址](https://github.com/mitre/caldera) |
| 研究 HEAD | `cb8d6a8160e0f4990af323a7c071d5e8482b42c7`；committer date `2026-08-27T00:46:57Z` | [commit](https://github.com/apache/caldera/commit/cb8d6a8160e0f4990af323a7c071d5e8482b42c7) |
| latest 正式 release | `5.3.0`，published `2025-04-24T17:51:59Z`，非 prerelease | [release](https://github.com/apache/caldera/releases/tag/5.3.0)、[latest API](https://api.github.com/repos/apache/caldera/releases/latest) |
| Release 固定 commit | tag `5.3.0` 指向 `b24f6e7a99cab19cbf417009bda9b9c6c81abc31` | [tag object](https://api.github.com/repos/apache/caldera/git/tags/dd22d543a519afe63ca35c454bf1add5d75c45dc) |
| Apache 狀態 | HEAD `DISCLAIMER` 明示 Apache Incubator 孵化階段；不能宣稱已正式畢業 | [DISCLAIMER](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/DISCLAIMER) |
| 文件同步程度 | README 還保留 MITRE research wording；Fieldmanual／ReadTheDocs requirements 比 HEAD README 舊 | [README](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/README.md)、[安裝文件](https://github.com/mitre/fieldmanual/blob/5c222527a6a0375a973fc7500a7c14caa1d39cf6/sphinx-docs/Installing-Caldera.md) |

產品應選一個明確驗證的 release／commit 與插件集合，不以 `master`、`latest` 或 repository `pushed_at` 代替支援版本。
本文件以 HEAD 研究現在架構，但不表示 5.3.0 release 已包含 HEAD 的所有功能；接口驗收必須分開。

## 3. 執行環境與 Windows 專案的相容性

| 面向 | 官方可見事實 | 對本案的影響／建議 |
|---|---|---|
| Server OS | HEAD README 列 Linux 或 macOS；沒有列 Windows 原生 core server | Windows Qt 桌面作 client；Caldera 放 Linux/macOS server 或獨立容器 |
| Python | HEAD README `3.10+`；5.3.0 README `3.9+`；ReadTheDocs latest／Fieldmanual 仍 `3.8+` | 三者不可混用；依固定 ref 的 requirements 與試驗決定 runtime |
| Node | HEAD README 為 v5 Vue UI 推薦 `16+`；HEAD Dockerfile UI builder 使用 `node:23` | 不把舊最低值當完整已驗證矩陣；核心桌面不用依賴 Node |
| Go | HEAD README 推薦 `1.24+`；HEAD Dockerfile 下載 `1.25.0 linux-amd64`；5.3.0 requirements 推薦 `1.17+`，另段落有 `1.19+` | Go 主要關係到 agent 動態編譯；第一期 catalog client 不需 Go |
| Hardware | README 推薦 server 8GB+ RAM、2+ CPU | 不能把桌面本機是否足夠當成已驗證 |
| Docker | 官方提供 Dockerfile、Compose、full/slim 模式 | 可選服務交付方式；不是本案開啟文件的必要依賴 |
| WSL | 本次官方 README／安裝文件未見 WSL 被正式列入支援矩陣 | 可作 Windows 上另行驗證的 Linux runtime 候選；不承諾官方 WSL 支援 |
| CPU architecture | HEAD Dockerfile 的 Go tarball明確寫 `linux-amd64` | 不能宣稱這份 Dockerfile 已保證 ARM64／Apple Silicon 任意組態可用 |

來源：[HEAD README](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/README.md)、[5.3.0 README](https://github.com/apache/caldera/blob/b24f6e7a99cab19cbf417009bda9b9c6c81abc31/README.md)、[HEAD Dockerfile](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/Dockerfile)、[Fieldmanual 安裝文件](https://github.com/mitre/fieldmanual/blob/5c222527a6a0375a973fc7500a7c14caa1d39cf6/sphinx-docs/Installing-Caldera.md)。

Docker 還有必須納入架構的具體限制：

- README 明列 `builder` plugin 不在 Docker 內工作；完整功能不能以「容器可啟動」作結論。
- full 模式為離線情境準備額外內容；slim 省略部分 Emu／Atomic 內容，啟用時可能再下載。
- README 表示 GHCR 預建映像可能落後；產品應鎖 image digest／source ref，而非只寫 image:latest。
- 預設容器資料是短暫的；資料及設定／加密金鑰需要一起持久化，才能復原同一環境。
- README／Dockerfile 的 full/slim 行為、插件依賴、外部資料下載須以指定 ref 再驗證；本次沒有建置映像。

以上限制來源：[HEAD README Docker notes](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/README.md#docker-installation)、[Dockerfile](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/Dockerfile)、[Compose](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/docker-compose.yml)。

## 4. 插件與 submodules：不是一個 repo 就包辦全部能力

HEAD `.gitmodules` 有17個宣告，但固定 HEAD 的 `plugins/` tree 實際可見16個 gitlink；其中 `caltack` 宣告存在而 tree 未列。
README 的 Default 清單還提到 OT；它也不是這個 HEAD plugins tree 的 gitlink。故「README 推薦」「submodule宣告」「實際啟用」是不同狀態。
來源：[.gitmodules](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/.gitmodules)、[固定 plugins tree](https://github.com/apache/caldera/tree/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/plugins)、[README plugins](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/README.md#plugins)。

| 插件群 | 可整合價值 | 邊界 |
|---|---|---|
| Stockpile | abilities、adversaries 與規劃相關內容的主要來源 | 匯入目錄與關聯，先保留原始 UUID／plugin／source ref |
| Emu | CTID 對手模擬計畫接合 | 外部計畫資料還有獨立版本與依賴 |
| Atomic | Atomic Red Team 能力接合 | 額外第三方資料及依賴，不能只繼承 core license |
| Sandcat／Manx | agent 與不同執行／通訊能力 | 不嵌入桌面核心；本次不部署、不產生執行腳本 |
| Magma | Vue UI | 本案 native UI 可保留，必要時開啟外部 Caldera UI |
| Debrief／GameBoard／Compass | operation 摘要、協作視圖、ATT&CK 呈現 | 先用 report artifacts 接合；各插件 API 另驗證 |
| SSL、Builder、Response、Human、Access、Training、Fieldmanual | 通訊、建置、回應、訓練、文件等擴充 | 由服務端啟用清單決定，桌面只暴露已驗證 capability |

能力說明來源：[README](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/README.md)、[術語文件](https://github.com/mitre/fieldmanual/blob/5c222527a6a0375a973fc7500a7c14caa1d39cf6/sphinx-docs/Learning-the-terminology.md)。
一個產品支援 profile 應包含 core commit、每個 submodule SHA、enabled plugin list，以及額外資料／binary artifact hash。
只記 Caldera 版本不足以重現 operation 或 abilities 目錄；也不應在本案每次啟動時自動追 upstream HEAD。

固定 HEAD 的16個插件指標如下（來源為 GitHub contents API 對固定 ref 回傳的 gitlink）：

| Plugin | Pinned SHA |
|---|---|
| [access](https://github.com/mitre/access/tree/8721b9d6a15293cb13a3be2c33df3b6e2eef49b1) | `8721b9d6a15293cb13a3be2c33df3b6e2eef49b1` |
| [atomic](https://github.com/mitre/atomic/tree/5372deeb5c9bf38aeabe58a0dcb69774c6b39332) | `5372deeb5c9bf38aeabe58a0dcb69774c6b39332` |
| [builder](https://github.com/mitre/builder/tree/46559931cd13a853daf30603292c976074390c19) | `46559931cd13a853daf30603292c976074390c19` |
| [compass](https://github.com/mitre/compass/tree/81366bba0bed0d5389ed0b9b7a1f7272f74d75dd) | `81366bba0bed0d5389ed0b9b7a1f7272f74d75dd` |
| [debrief](https://github.com/mitre/debrief/tree/f5d5e89cc98d1190ccea7851ed6c71dd634cf2b1) | `f5d5e89cc98d1190ccea7851ed6c71dd634cf2b1` |
| [emu](https://github.com/mitre/emu/tree/ef3bc4fa8fb605c774446ba7741365ba45d375a8) | `ef3bc4fa8fb605c774446ba7741365ba45d375a8` |
| [fieldmanual](https://github.com/mitre/fieldmanual/tree/5c222527a6a0375a973fc7500a7c14caa1d39cf6) | `5c222527a6a0375a973fc7500a7c14caa1d39cf6` |
| [gameboard](https://github.com/mitre/gameboard/tree/d1ceb580b18a382ba05885664e241b10a2c2b584) | `d1ceb580b18a382ba05885664e241b10a2c2b584` |
| [human](https://github.com/mitre/human/tree/395e93cebe7abcc2c902159ca8afd92d53eb5f1f) | `395e93cebe7abcc2c902159ca8afd92d53eb5f1f` |
| [magma](https://github.com/mitre/magma/tree/317cfdcdfb9e16a32ffbfb7133e9d1ab9caf0596) | `317cfdcdfb9e16a32ffbfb7133e9d1ab9caf0596` |
| [manx](https://github.com/mitre/manx/tree/f688e13e6fa1d822a65f590fe7143e2dd2f705b5) | `f688e13e6fa1d822a65f590fe7143e2dd2f705b5` |
| [response](https://github.com/mitre/response/tree/ad02a9d2eaf358cf3063ae2ff43acf91c54f27ae) | `ad02a9d2eaf358cf3063ae2ff43acf91c54f27ae` |
| [sandcat](https://github.com/mitre/sandcat/tree/ec3e2db425eb6333b9e1fa4fd03e9b94ef05c082) | `ec3e2db425eb6333b9e1fa4fd03e9b94ef05c082` |
| [ssl](https://github.com/mitre/ssl/tree/7b436029143c9e98da86b1ac729e470c8cadc9c3) | `7b436029143c9e98da86b1ac729e470c8cadc9c3` |
| [stockpile](https://github.com/mitre/stockpile/tree/996ec41cd1c5d1c7cc09e620fc55dabe5aefd9cc) | `996ec41cd1c5d1c7cc09e620fc55dabe5aefd9cc` |
| [training](https://github.com/mitre/training/tree/d613da99791af8424763d72c0024a12491441f17) | `d613da99791af8424763d72c0024a12491441f17` |

## 5. 物件與資料的本質

| 上游物件 | 實際含義 | 本案應如何表達 |
|---|---|---|
| Ability | 一個可執行的 TTP implementation；有自己UUID、tactic、technique ID、executors、requirements、privilege、plugin等 | `AbilityReference`／catalog entry；不是官方 technique 本身 |
| Executor | ability 在特定platform／執行器上的實作，還有timeout、parser、cleanup、外部artifact依賴 | Plan step須選明確平台與executor；不可只選T-ID |
| Adversary | abilities集合、atomic_ordering、objective及tags | 外部profile或本案EmulationPlan來源；不是STIX intrusion-set的同義詞 |
| Agent | 回連服務取指令的程式實例；含paw、platform、architecture、executors、privilege、last seen、group | runtime target/capability快照，不是ATT&CK platform filter |
| Fact／Source | operation的已知或學到資訊；trait/value/source/score/provenance及relationships | 來源化runtime輸入；與本案文件註記分開保存 |
| Operation | 綁adversary、agents/group、planner、source及狀態的執行個體 | `RunRecord`；與可編輯計畫分離 |
| Link／Chain | 對agent產生的具體工作及執行狀態；chain是其集合 | StepResult及進度證據；不是純靜態ability清單 |
| Report／Event logs | operation與ability層級的時間、狀態、目標及結果資料；輸出可選包含stdout/stderr | immutable RunArtifact，另做本案摘要投影 |

來源：[Ability](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/c_ability.py)、[Executor](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/secondclass/c_executor.py)、[Adversary](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/c_adversary.py)、[Agent](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/c_agent.py)、[Fact](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/secondclass/c_fact.py)、[Operation](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/c_operation.py)、[Link](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/secondclass/c_link.py)、[術語文件](https://github.com/mitre/fieldmanual/blob/5c222527a6a0375a973fc7500a7c14caa1d39cf6/sphinx-docs/Learning-the-terminology.md)。

相容性判斷至少需要 technique→ability→executor/platform→agent能力→privilege→facts/requirements→artifacts。
同一 technique 可有多個 ability；多個 ability 也可能共享 technique。UUID、technique ID與本案文件ID不能共用。
本案勾選 TTP 是分析範圍；不自帶執行順序，也不能推定具有能在現有 agent 上運行的命令。

現有 `TTPDocument` 可提供選取ID、partial tactic scope、domain與資料版本，適合作Plan的研究來源；仍須新增獨立`AbilityRef`、`PlanStep`、`RunRecord`與`RunArtifact`模型。
AdversaryProfile不能直接當ATT&CK `intrusion-set`；也不能把runtime facts寫回官方STIX物件。來源：[本案文件模型](D:/MITREATTACK_SIMULATOR/ttp_documents.py)、上表Adversary／Operation原始碼。

Agent 原始碼的 `capabilities()` 明確檢查 privilege 與 platform/executor；operation的跳過原因亦處理平台、executor及未完成等情況。
來源：[Agent capability邏輯](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/c_agent.py)、[Operation skipped原因](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/c_operation.py)。

Report 文件與實作亦有差異：Fieldmanual對 command 描述為base64，但HEAD `Operation.report()` 對command呼叫decode；parser須按服務版本處理，保留raw payload。
Report預設可不含agent output；缺輸出不等於失敗。Operation執行成功也不等於藍隊偵測成功，應再與SIEM／規則／觀測證據關聯。
來源：[Operation report實作](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/c_operation.py)、[報告文件](https://github.com/mitre/fieldmanual/blob/5c222527a6a0375a973fc7500a7c14caa1d39cf6/sphinx-docs/Operation-Results.md)。

## 6. REST v2 可行性與副作用邊界

HEAD server註冊 `/api/v2`，Swagger在 `/api/docs`、schema在 `/api/docs/swagger.json`。
來源：[server.py](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/server.py)、[v2 app](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/api/v2/__init__.py)。

| 類別 | 本次核對的接口 | 本案建議 |
|---|---|---|
| 健康／目錄 | GET `/api/v2/health`、`/abilities`、`/adversaries` | 第一期allowlist候選，做catalog同步與診斷 |
| 既有執行資訊 | GET `/agents`、`/operations/{id}`、`/operations/{id}/links/{link_id}/result` | 只讀現有資料；agents/result可能含環境資訊 |
| 既有報告 | POST `/operations/{id}/report`、`/operations/{id}/event-logs` | 雖用POST，語義是產生／取得既有結果；依endpoint明確分類 |
| 物件修改 | ability／adversary CRUD | 第二期以明確同步／發布操作處理，不能由Open/import觸發 |
| 執行建立 | POST `/operations` | 第三期明確Run action；不是plan保存或dry-run |

來源：[health handler](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/api/v2/handlers/health_api.py)、[ability handler](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/api/v2/handlers/ability_api.py)、[adversary handler](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/api/v2/handlers/adversary_api.py)、[agent handler](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/api/v2/handlers/agent_api.py)、[operation handler](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/api/v2/handlers/operation_api.py)。

核心證據：`OperationApiManager.create_object_from_schema()`保存operation後，直接建立 `operation.run(...)` 的async task；Operation預設state為running。
因此不可為了預覽建立operation，再假設它沒有執行。也不可把所有POST一律當成run，因report與event-logs使用POST讀取。
來源：[Operation manager](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/api/v2/managers/operation_api_manager.py)、[Operation model](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/c_operation.py)。

認證使用 `KEY` header、red／blue API keys或session，並非預設Bearer契約；red／blue分類也不等於唯讀／可寫權限。
第一期client應以method+path allowlist限制可呼叫範圍，服務端角色與代理層權限仍須另驗證；密鑰不進文件／snapshot／log。
來源：[auth_svc.py](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/service/auth_svc.py)。

舊 `/api/rest` 文件已明示deprecated，不應以舊版localhost免key敘述設計新connector。
來源：[官方舊REST說明](https://github.com/mitre/fieldmanual/blob/5c222527a6a0375a973fc7500a7c14caa1d39cf6/sphinx-docs/The-REST-API.md)。

## 7. 外部服務整合與Python內嵌比較

| 方案 | 優點 | 成本／限制 | 建議 |
|---|---|---|---|
| 外部HTTP API Adapter | runtime隔離、Linux server可獨立升級、保留官方plugins與UI、本案仍可離線開研究文件 | 要處理認證、版本、逾時、非同步狀態與artifacts | 首選 |
| 本機獨立Caldera程序／容器 | 可作單機lab體驗；仍保留服務邊界 | Windows runtime、ports、volumes、plugin更新與資源需求需管理 | 可選，不是第一期必要 |
| 把core Python objects直接import進Qt | 表面上少一層HTTP | 物件依賴服務registry、event loop、檔案／plugin hooks；失去穩定接口、依賴衝突及啟停耦合 | 不建議 |
| 只匯入YAML／JSON／report | 完全可先離線做研究、規劃與結果分析 | 不提供live能力／狀態；須保留source版本及loss report | 最小可交付 |

比較為本案架構建議；其依據是core server與plugin設計，而不是上游對Qt內嵌作過支援承諾。
來源：[README core/plugins](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/README.md)、[server](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/server.py)、[Operation服務依賴](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/app/objects/c_operation.py)。

## 8. 授權、再散布與商業整合

| 範圍 | 已核對內容 | 整合要求 |
|---|---|---|
| HEAD core | Apache License 2.0；有ASF `NOTICE`及Incubator `DISCLAIMER` | 打包指定HEAD時保留其license/notice與相應聲明 |
| Release 5.3.0 core | 該tag LICENSE亦為Apache-2.0；該tag根目錄沒有目前ASF NOTICE／DISCLAIMER | 用release自己的檔案作清單，不把2026 HEAD聲明偽稱歷史release原檔 |
| HEAD／tag wording | 5.3.0 README有Licensing contact；HEAD該段移除，但LICENSE本身可直接核對 | 不把聯繫商業授權描述誤解成所有API整合必須付費 |
| 插件／第三方資料 | 主要插件多各有LICENSE；本次metadata中Debrief未辨識license；Atomic與Emu會帶外部資料 | 每個實際分發artifact、plugin ref與第三方依賴各自盤點 |

來源：[HEAD LICENSE](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/LICENSE)、[HEAD NOTICE](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/NOTICE)、[HEAD DISCLAIMER](https://github.com/apache/caldera/blob/cb8d6a8160e0f4990af323a7c071d5e8482b42c7/DISCLAIMER)、[5.3.0 LICENSE](https://github.com/apache/caldera/blob/b24f6e7a99cab19cbf417009bda9b9c6c81abc31/LICENSE)、[5.3.0 root](https://github.com/apache/caldera/tree/b24f6e7a99cab19cbf417009bda9b9c6c81abc31)、[5.3.0 README](https://github.com/apache/caldera/blob/b24f6e7a99cab19cbf417009bda9b9c6c81abc31/README.md)。

Apache-2.0明文提供再製、衍生、散布及專利授權，允許另加自有修改條款，但再散布須給LICENSE、保留相關聲明、標示修改、依要求保留NOTICE。
它不授予商標使用權，也不要求把所有獨立介面程式自動改成Apache授權；具體bundle仍需按license全文核對。
以上是授權文本對工程交付的摘要，不代表已完成全部插件、payload或商標的法律審查。來源同上LICENSE第1–4、6、9節。

## 9. 三階段建議及驗收

### C1：唯讀目錄與既有結果

- 新增可選CalderaCatalog Adapter；檔案匯入或API同步abilities/adversaries，保留server identity、ref、plugin、UUID及technique mapping。
- 比對本案文件選取TTP與候選ability；顯示無候選、未知ID、已撤銷／跨版本差異，不自動代選命令。
- 匯入既有report/event logs；artifact原文、hash與取得時間固定保存，再產生矩陣／摘要。
- 驗收：catalog/report失敗不破壞本案文件；所有允許請求都有明確method/path；不呼叫operation建立、agent修改或任意命令端點。

### C2：計畫編輯與相容性預覽

- 獨立`EmulationPlan`保存ordered steps、ability references、executor/platform選擇、facts需求、來源與待解決項。
- Plan與TTPDocument相互引用，避免把研究文件格式塞入runtime資訊；計畫本機保存不建立遠端operation。
- 若提供adversary發布，作明確遠端修改與版本預覽；發布成功也不代表開始operation。
- 驗收：每個步驟可以追到ability及來源版本；不可把TTP ID、adversary profile或UI排序推定為完整可執行契約。

### C3：受控Operation與結果回收

- 在明確選定可用服務、agent／目標範圍、相容能力與操作權限後，才提供獨立Run action。
- `RunRequest`／遠端operation ID／`RunRecord`／`RunArtifact`分離；紀錄請求與結果、時間及版本。
- 狀態更新、重連、重試、停止及cleanup語義均依所選版本驗證；網路失聯不得直接標成已取消。
- Pause／finish只改operation生命週期，不能當成已在agent執行命令的undo；create請求逾時須先確認遠端是否建立成功，不能盲目重試。
- 產生精確進度：已規劃／符合條件／已派發／完成／失敗／跳過／未知分別呈現，不以完成連結數假裝固定百分比。
- 驗收：不重複啟動operation、不由文件匯入自動run、結果可追溯到原計畫與實際平台；偵測成效需獨立證據。

上述為本案建議，沒有包含agent部署、payload下載或實際攻擊步驟；本次只研究接口和責任邊界。

## 10. 仍待實驗或決策的項目

1. 支援release 5.3.0還是較新固定HEAD；兩者API與插件合約須各自做契約測試。
   health version或插件清單只可作能力提示，無法證明server的完整commit或plugin refs相容；需固定來源ref並以契約fixtures核對。
2. Linux／macOS、Windows client＋remote server、WSL2或Docker的實際驗證環境；官方未提供本案完整Windows矩陣。
3. API版本探測、分頁／filter、report encoding、stop／cleanup／timeout與斷線後重連語義。
4. 選定plugins與artifact授權；本次不是全插件／外部payload許可盤點，也未建置full/slim映像。
5. runtime資料（facts、host、輸出）的保存、權限、刪除與敏感欄位；與一般研究文件分開。
6. ATT&CK最新版本與能力庫mapping的落差；不可宣稱整合Caldera就涵蓋全部TTP或保證防禦覆蓋。

研究完成層級：來源與程式結構已審閱；功能可行性有接口依據；安裝、平台兼容、真實operation及商業交付授權清單尚未驗收。

