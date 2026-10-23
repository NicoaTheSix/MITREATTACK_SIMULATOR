# Linux／WSL2 實測報告

實測日期：2026-10-20。結果：**在本次 Kali WSL2 環境中，31 個功能檢查程式以最新重測結果計均通過**。真實 WSLg 視窗另通過 30 個英／臺灣繁體中文 Manual 功能連結案例與自訂來源匯入流程。

這份結論針對下列環境與案例，不代表所有 Linux 發行版、桌面環境或全部可能操作都已驗證。

2026-10-22 補充：Linux 啟動與安裝入口已統一為 `fusionstudio`、`start-fusionstudio.sh` 與 `setup-fusionstudio.sh`；環境變數改為 `FUSIONSTUDIO_PYTHON`。下方 2026-10-20 的舊指令、舊副本與圖形測試紀錄保留為歷史證據；目前安裝方式請依 [README](README.md#linux--wsl2-installation)。新版安裝／遷移另於 Kali WSL2 的隔離 HOME 通過 [69 項檢查](artifacts/linux-command-setup/6cb2fcfdaf3840468989a72115dfe814/audit.json)，涵蓋 Bash／Zsh、新舊入口遷移及驗證失敗時保留舊入口；本次未開啟 GUI，也未修改個人 shell 設定檔。

## 環境與資料隔離

| 項目 | 實測內容 |
| --- | --- |
| 發行版 | Kali GNU/Linux 2026.2，x86_64，WSL2 |
| 核心 | `6.18.54.1-microsoft-standard-WSL2` |
| Python | 原生 Linux Python 3.14.7，獨立 `.venv` |
| 主要套件 | PySide6 6.12.0、mitreattack-python 6.2.1、openpyxl 3.1.5 |
| GUI | WSLg：X11／xcb、原生 Wayland、自動選擇 Qt 後端 |
| 預設資料 | ATT&CK v20.0；歷史案例使用已快取的 v19.2、v11.3、v11.2、v1.0 |
| Windows 原始專案 | `D:\MITREATTACK_SIMULATOR` |
| Linux 隔離副本 | `/home/kali/.local/share/ttp-selection-studio-wsl-test/project` |

測試副本放在 Linux 原生檔案系統，排除 Windows `.venv`、個人設定與復原工作階段，避免測試寫入原有工作區。測試中的 `active.json`／`latest.json` 雜湊檢查均維持不變。各套件完整版本存於 [Linux 套件清單](artifacts/linux-wsl/pip-freeze-linux.txt)。

## 結果與證據

- [彙整驗證資料](artifacts/linux-wsl/verification.json)：31 個程式的最終結果、採用的重測紀錄、初次結果及限制。
- [Manual 逐項結果](artifacts/linux-wsl/manual-link-results.json)：15 個功能連結 × 2 種語言，共 30 案例。
- [真實 xcb 視窗檢查](artifacts/linux-wsl/xcb/audit.json)：Manual 與自訂來源兩組 GUI 流程。
- [Windows 來源回歸紀錄](artifacts/linux-wsl/windows-custom-data-regression.log)：同一項路徑修正通過 70 項檢查。
- 畫面：[Linux 啟動](artifacts/linux-wsl/startup-xcb.png)、[英文 Manual](artifacts/linux-wsl/manual-en.png)、[繁體中文 Manual](artifacts/linux-wsl/manual-zh-TW.png)。

初次完整掃描為 **21/31 通過**。修正實際問題與舊測試假設後，對失敗項目進行針對性重測，最終各項均通過；這不是宣稱「單次完整執行 31/31」。初次失敗的日誌仍保留在 `artifacts/linux-wsl/offscreen`，重測則位於 `rechecks`、`color-rechecks`、`version-recheck`、`source-path-final`。彙整檔的 `attempt_history` 保留採用過程。

### 已通過的功能

| 功能範圍 | 本次驗證內容 | 檢查程式 |
| --- | --- | --- |
| 啟動與資料瀏覽 | 三種 GUI 啟動路徑、官方資料結構與雜湊、搜尋、詳細資料、選取同步 | `main.py --smoke-test`、`audit_catalog.py` |
| 文件與復原 | 多文件、Unicode 名稱、JSON／CSV、Studio 存取、取消、失敗保護、髒狀態與工作階段復原 | `audit_documents.py`、`audit_comments.py`、`audit_workspace.py`、`audit_studio_lifecycle.py` |
| ATT&CK 領域 | Enterprise、Mobile、ICS 文件隔離、原生匯入與版本比較、自訂領域 | `audit_domains.py`、`audit_custom_domains.py` |
| 矩陣與圖層 | Flat／Side／Mini、顏色與清除顏色、多圖層疊圖、顯示設定、儲存的展開偏好 | `audit_matrix.py`、`audit_matrix_actions.py`、`audit_layers.py`、`audit_clear_colors.py`、`audit_overlay.py`、`audit_matrix_display.py`、`audit_visibility_presets.py` |
| 搜尋與來源 | 來源關聯、來源批次選取、懸停預覽、偵測策略搜尋、選取與搜尋偏好 | `audit_related_ttps.py`、`audit_selection_search.py`、`audit_source_selection.py`、`audit_source_preview.py`、`audit_detection_interaction.py` |
| Navigator 與自訂資料 | 圖層交換、多圖層批次匯入、相容設定、自訂來源審查、快取與內容變更確認 | `audit_navigator.py`、`audit_navigator_bundle.py`、`audit_navigator_parity.py`、`audit_custom_data_url.py`、`audit_advanced_navigator.py` |
| 批次編輯與匯出 | 註記批次編輯、分數公式、彙總、SVG／Excel、JSON 註記與可見範圍匯出 | `audit_batch_operations.py`、`audit_layer_analysis.py`、`audit_formula_features.py`、`audit_export_options.py`、`audit_json_annotation_export.py` |
| Manual 與語言 | 30 個功能／語言案例、真實 Qt 檔案選擇器、分頁開關、文件內容與語言偏好保護 | `audit_manual_language.py` |
| 版本選單 | 已快取版本呈現、搜尋、離線刷新失敗時保留清單及進度恢復 | `audit_versions.py --picker-only` |

完整功能掃描主要使用 **Linux 原生 Python 與 Qt offscreen 後端**；測試仍執行實際的資料處理、Qt 控制項與輸出檔案驗證。額外的真實 xcb／WSLg 視窗覆蓋啟動、Manual 的連結／對話框／檔案選擇器，以及自訂來源流程。Wayland 與自動後端目前僅執行主程式的啟動煙霧測試。

## 修正內容

### 1. Linux Qt 系統依賴

最初的圖形啟動會因 xcb 外掛無法載入而中止。`ldd` 確認缺少 `libxcb-icccm.so.4` 與 `libxcb-keysyms.so.1`，補上 `libxcb-icccm4`、`libxcb-keysyms1` 後成功啟動。README 的 Linux 安裝步驟已列入完整測試用依賴及中文字型。這是 Linux 環境準備問題，並未以略過 GUI 測試作為解法。

### 2. POSIX 本機 Bundle 路徑被當成遠端網址

遠端圖層帶有 HTTP origin 時，原流程會將 `/home/.../custom/<hash>.json` 接到遠端網址，造成讀取本機快取時發出錯誤的 HTTP 請求。

`custom_data_dialog.py` 現在將瀏覽、快取選擇與使用者輸入的原生絕對路徑明確標示為本機 `Path`；`custom_data_import.resolve_location()` 依此保留本機檔案語意。遠端圖層宣告的字串參照仍保留相對／根相對 URL 語意。修改來源欄位會取消先前的驗證結果；不完整的家目錄輸入也不會造成 UI 例外。

回歸檢查包含快取、手動輸入、無效輸入、失敗後重試、遠端相對網址與內容雜湊確認；在 Linux offscreen、真實 WSLg xcb，以及 Windows 均通過。

### 3. Linux 啟動與測試工具

- 新增 `start-ttpselecter.sh`，從自己的位置解析專案路徑，檢查 Linux Python／依賴，並轉交參數至 `main.py`。
- 支援 `.venv/bin/python`、共用原始碼時的 `.venv-linux/bin/python`，以及 `TTPSELECTER_PYTHON` 指定的環境。
- `--check` 僅檢查依賴；`--no-session` 可供隔離測試停用自動復原。
- `.gitattributes` 指定 `.sh` 使用 LF，避免 Windows 簽出後的換行相容性問題。
- 新增 `scripts/audit_linux.py`，逐項顯示進度、保留日誌、檢查退出碼／逾時／traceback 與資料指標雜湊，並支援 `--output-dir` 分開存放重測結果。

程式流程、絕對輸入／輸出、階段進度與失敗處理已記錄於同目錄的 README；安裝指南亦同步至英文與臺灣繁體中文 Manual。

### 4. 舊測試維護

本次也修正了 v19.2 固定版本／版本數量假設、非同步匯入尚未完成就斷言、選單固定索引失效，以及最終清理停在未儲存提示的問題。顏色／疊圖測試則更新為目前的選取標記與儲存展開偏好語意。

這些改動屬於測試同步、資料假設與清理維護；沒有取消產品的 Save／Discard／Cancel 保護。專門的文件與復原測試仍檢查儲存、失敗與取消行為。

### 5. Linux 一次性指令設定

後續新增 `setup-ttpselecter.sh` 與 `scripts/install_linux_command.py`，完成安裝後可執行一次，將使用者專用的 `ttpselecter` 指令註冊至 `~/.local/bin`，並保留、備份及補齊 Bash／Zsh 的 PATH 設定。移動專案後重新執行即可更新指令指向；其他人的同名指令與被修改的管理區塊會在寫入前拒絕取代。

`scripts/audit_linux_command.py --gui-smoke` 在隔離 HOME 中通過 **43 項檢查**，涵蓋 Bash／Zsh 的登入及非登入互動終端、既有設定內容與備份、重複設定、同名指令衝突、管理區塊修改、缺少環境、含空白／Unicode／單引號的路徑，以及從 `/tmp` 透過 `ttpselecter` 啟動真實 WSLg 視窗。並另外在目前 Kali 帳號完成設定、驗證新開 Bash／Zsh 的指令辨識。這些是新增的指令設定檢查，沒有取代原本 31 個應用程式功能測試。

證據：[43 項檢查](artifacts/linux-command-setup/audit.json)、[圖形視窗](artifacts/linux-command-setup/gui-smoke.png)、[目前帳號設定紀錄](artifacts/linux-command-setup/current-user-install.log)。

## 尚未驗證的部分

- **其他 Linux 環境**：Ubuntu／Debian、其他發行版、ARM64、實體機與完整 GNOME／KDE 等桌面尚未實測。
- **完整 Wayland 操作**：目前只確認啟動與主程式煙霧檢查，尚未在 Wayland 重跑全部功能。
- **外部網站開啟**：此最小 WSL 環境沒有設定預設瀏覽器，因此尚未驗證 MITRE／GitHub 等外部網址能否透過系統瀏覽器開啟。內部 Manual 功能連結已驗證；兩者不能混為一談。使用者需先配置可用的預設瀏覽器與桌面 URL 開啟工具。
- **完整網路下載與歷史版本**：驗證了快取版本及離線失敗回復，尚未完整執行所有版本下載與所有歷史快照的操作。
- **長時間與桌面整合**：大型使用者資料、長時間穩定性、效能、多螢幕／HiDPI，以及 `.desktop`／AppImage／deb 等發佈方式尚未驗證。
- **其他 shell 的指令設定**：Bash／Zsh 的 `ttpselecter` 設定已驗證；Fish 等其他 shell 的 PATH 啟動格式尚未配置或驗證。Windows 安裝器不負責 Linux shell；目前 Windows 入口已改名為 `setup-fusionstudio.cmd`，啟動指令為 `fusionstudio`，不影響本報告的 Linux 測試紀錄。

## 重現與啟動方式

通用安裝請依 [README 的 Linux／WSL2 Installation](README.md#linux--wsl2-installation)。此電腦已有的隔離副本可從 PowerShell 先進入正確的發行版：

```powershell
wsl -d kali-linux
```

接著在 Linux 中啟動測試副本：

```bash
cd /home/kali/.local/share/ttp-selection-studio-wsl-test/project
bash start-ttpselecter.sh --no-session
```

重跑檢查時，請使用可寫入的隔離副本；輸出會留在該副本的 `artifacts`：

```bash
.venv/bin/python -B scripts/audit_linux.py
.venv/bin/python -B scripts/audit_linux.py --platform xcb \
  --only audit_manual_language.py audit_custom_data_url.py
```

更完整的測試工具流程、歷史快取需求與逾時處理，見 [scripts/README.md](scripts/README.md#linux--wsl2-feature-audits)。
