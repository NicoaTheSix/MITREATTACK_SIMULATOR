# Fusion Studio 使用示範影片

- 影片：[fusion-studio-demo-zh-TW.mp4](fusion-studio-demo-zh-TW.mp4)
- 規格：1920 × 1080、24 fps、H.264 MP4、78 秒、無旁白／音樂。
- 內容：實際 Fusion Studio Qt 介面、繁體中文字幕、動畫游標與點擊提示。
- 預覽：[storyboard.png](storyboard.png)
- 字幕：[captions.zh-TW.srt](captions.zh-TW.srt)；中文字幕亦已直接繪入影片畫面。
- 驗證：[report.json](report.json)

## 章節

| 時間 | 操作 |
| --- | --- |
| 00:00–00:05 | Fusion Studio 開場 |
| 00:05–00:13 | 建立獨立文件 |
| 00:13–00:26 | 搜尋並選取 PowerShell、Scheduled Task |
| 00:26–00:35 | 查閱技術詳細資料與案例 |
| 00:35–00:44 | ATT&CK 矩陣與搜尋 |
| 00:44–00:54 | ATLAS 矩陣與 Prompt Injection 選取 |
| 00:54–01:02 | CAR 分析條目與 Workplace 納入 |
| 01:02–01:12 | 保存 Studio JSON、匯出 ATT&CK CSV |
| 01:12–01:18 | 結尾與作者聯絡方式 |

## 操作產出與重建

實際操作產生 [demo-research.json](demo-research.json) 及 [demo-research.csv](demo-research.csv)。JSON 包含 ATT&CK／ATLAS 選取與 CAR 內容；CSV 示範只匯出兩項 ATT&CK 技術。這些是示範研究清單，不會執行任何攻擊或分析程式碼。

來源程式：[scripts/make_demo_video.py](../../scripts/make_demo_video.py)。從專案根目錄執行：

```powershell
& '.\.venv\Scripts\python.exe' -B '.\scripts\make_demo_video.py'
```

需要專案 PySide6 環境與支援 libx264 的 ffmpeg；不在 PATH 時加上 `--ffmpeg '絕對路徑'`。`--preview-only` 只執行流程並產生關鍵畫面與範例，不編碼影片。所有輸入／輸出絕對路徑都會在處理前顯示，並回報準備、逐章擷取、編碼、驗證四階段進度。完整運作流程與失敗處理見 [scripts/README.md](../../scripts/README.md#usage-demonstration-video)。重跑會更新此資料夾內的生成內容。

拍攝使用獨立 `settings.ini` 與示範文件、停用工作區復原；完成時比較正式偏好設定、工作區復原檔與目前資料版本指標，確認沒有變更。啟動可能建立應用程式既有的不可變資料快取。全程使用本機資料，不下載、上傳或發布。

原創程式碼採專案 MIT 授權，作者 Nicoa Wu。MITRE ATT&CK®、ATLAS、CAR、Qt 與其他相依元件保留各自授權；本影片與專案未獲 MITRE 背書。
