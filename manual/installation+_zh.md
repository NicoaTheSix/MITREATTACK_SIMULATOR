# 安裝與啟動

## 系統需求

使用 Windows 或具圖形介面的 Linux、專案原始碼與宣告的相依套件。本工具是 Python／PySide6 桌面程式。Linux 實測環境為 Kali 2026.2、WSL2／WSLg、Python 3.14.7 與 PySide6 6.12.0。WSLg 可在 Windows 顯示 Linux 視窗；僅有終端機的 Linux 伺服器仍需要圖形工作階段才能互動操作。

## 建立專案環境

在專案資料夾開啟 PowerShell，建立專案專用的虛擬環境：

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
```

`requirements-lock.txt` 是 Windows 環境的套件快照。Linux 請在自己的 Linux 虛擬環境中使用 `requirements.txt` 安裝；完整安裝參考資料保存在專案根目錄 README。

## 啟動介面

```powershell
& '.\.venv\Scripts\python.exe' -B '.\main.py'
```

程式會先顯示輸入檔案的絕對路徑，再載入指定的本機資料。請等待各階段完成。若有先前的復原檢查點，會自動還原，並在操作紀錄／狀態區提醒。

## Windows 快速啟動指令（PowerShell 與 cmd）

完成安裝後，雙擊專案資料夾內的 `setup-fusionstudio.cmd`，或在 PowerShell 執行 `.\setup-fusionstudio.cmd`（cmd 則執行 `setup-fusionstudio.cmd`）。重新開啟終端機後，即可從任何目錄輸入 `fusionstudio`，不必手動啟用虛擬環境。`fusionstudio -Check` 只檢查路徑與依賴，不開啟視窗或寫入應用程式檔案。

自動化註冊可執行 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Install-FusionStudioCommand.ps1`，不會停下等待按鍵。安裝器先顯示絕對輸入路徑及使用者 PATH 登錄輸出，再依序驗證專案、檢查依賴、註冊一次專案目錄及驗證結果。啟動器先顯示程式、環境、資料、設定、工作階段及日誌的絕對路徑，再顯示驗證、啟動與完成進度。日誌位於 `<project-root>\artifacts\launch`。

原本的 `ttpselecter`／`ttpselector` Windows 啟動器與舊安裝入口已移除。如果專案目錄原本已加入 PATH，可直接使用 `fusionstudio`，無須重新安裝。請保留專案資料夾；搬移後，先移除舊 PATH 項目，再於新位置註冊。此 Windows 設定與下方 Linux 設定分開。

## Linux／WSL2 安裝與啟動

在 Kali Linux 內安裝 Python 虛擬環境支援、Qt 執行函式庫與繁體中文字型：

```bash
printf 'Input package sources: /etc/apt/sources.list and /etc/apt/sources.list.d\nOutput package directories: /usr, /var/lib/apt/lists, /var/cache/apt\n'
sudo apt-get update
sudo apt-get install -y --no-install-recommends python3 python3-venv \
  libegl1 libopengl0 libglib2.0-0t64 libxkbcommon-x11-0 \
  libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 libxcb-render-util0 fonts-noto-cjk
```

建議在 Linux 家目錄準備獨立的專案副本，並在該專案目錄執行：

```bash
printf 'Input requirements: %s/requirements.txt\nOutput environment: %s/.venv\n' "$PWD" "$PWD"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
# 沒有有效的 ATT&CK 快照時才需要下載：
.venv/bin/python -B scripts/download_attack_data.py
bash start-fusionstudio.sh
```

Linux 不可沿用 Windows `.venv` 或 `.cmd` 啟動腳本。若共用 Windows 原始碼目錄，請改建 `.venv-linux`；Bash 啟動器在找不到 Linux `.venv/bin/python` 時會使用它的 `bin/python`。`bash start-fusionstudio.sh --check` 檢查依賴，`--no-session` 可供隔離工作區停用復原。啟動器會顯示絕對輸入路徑與三階段進度，程式接著回報資料、設定、工作階段路徑與載入進度；操作期間請保持終端機開啟。可用 `QT_QPA_PLATFORM=xcb bash start-fusionstudio.sh` 明確指定 WSLg／X11。若先前設定了 `QT_QPA_PLATFORM=offscreen`，請先取消設定才能看到視窗。其他發行版的系統套件名稱可能不同。

## Linux 一次性指令設定

完成 Linux 安裝後，在專案目錄執行 `bash setup-fusionstudio.sh`。重新開啟 Bash 或 Zsh，即可從任何目錄輸入 `fusionstudio`。目前的終端機若不想重開，可先執行一次 `export PATH="$HOME/.local/bin:$PATH"`。`fusionstudio --check` 可在不開啟視窗的情況下檢查依賴。

設定會將啟動指令放入目前使用者的 `~/.local/bin`，並在 Bash／Zsh 啟動設定檔加入有標記的 PATH 區塊；程式本體仍使用原專案位置。修改既有設定檔前會先備份，重複執行不會新增重複區塊或備份，不需要 `sudo`。移動專案後請在新位置重跑設定；其他 shell 需自行設定 PATH。腳本會顯示絕對輸入、指令／設定檔／備份輸出位置與四階段進度；若遇到不屬於本工具的同名指令或被修改的管理區塊，會在寫入前停止。

已有 Linux 快速啟動設定時，重跑新版安裝器即可遷移。新 `fusionstudio --check` 成功後，才會移除本專案產生且未被修改的舊 `~/.local/bin/ttpselecter` 啟動器，沿用既有 PATH 區塊並保留歷史備份。其他同名指令或符號連結會保留；被修改過的舊管理啟動器會讓預檢停止，不進行變更。原本的 `setup-ttpselecter.sh` 與 `start-ttpselecter.sh` 入口已移除。遷移後請重開終端機，或在 Bash 執行 `hash -r`、Zsh 執行 `rehash`。

需要指定其他原生 Linux Python 環境時，可在執行安裝器或啟動器時設定 `FUSIONSTUDIO_PYTHON=/absolute/path/to/venv/bin/python`；舊的 `TTPSELECTER_PYTHON` 變數不再使用。安裝器不會停下等待輸入，可用於自動化流程，但不會安裝依賴套件。

## 資料與語言

目前預設資料為 ATT&CK v20.0。已下載的快照可離線使用，下載其他版本則需要連線至 MITRE 官方 GitHub 來源。

介面與手冊預設為英文。使用 **Settings → Language → 繁體中文（臺灣）** 切換為臺灣繁體中文。偏好會存於本機設定檔，不會寫入 Studio 文件。

[回操作手冊](in_app_manual+_zh.md)
