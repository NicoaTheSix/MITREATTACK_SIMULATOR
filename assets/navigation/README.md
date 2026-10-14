# ATT&CK Navigation Icons

此套圖示以現有 TTP 點陣 Icon 為風格參考，使用內建 image_gen 工具逐一生成六個新圖示；TTP 沿用現有圖像。藍色、深灰與白色點綴延續專案的視覺風格，所有 PNG 外部背景透明。各造型為本專案依 ATT&CK 分類含義設計的視覺比喻，非 MITRE 官方圖示。

## 圖示與定義

Groups 與 Campaigns 已依要求移除盾牌外框及深灰底板，分別只保留三個人物、旗幟與三個時間節點。仍使用藍色點陣風格，符號之間的空隙與外部背景均透明。更新透過內建 image_gen 編輯原圖，再替換同名 PNG；完整編輯提示詞與原版生成紀錄保存在 `generation-prompts.json` 的各分類項目及 `previous_versions`。程式沿用原有載入路徑，重新啟動即可套用。

| 分類 | 預覽 | 造型 | 對應含義與官方來源 |
| --- | --- | --- | --- |
| TTP | <img src="../ttp-selection-studio-icon-pixel.png" width="64" alt="TTP icon"> | 盾牌＋階層節點＋勾選 | 瀏覽與挑選戰術、技術與程序，對應本專案的文件選取流程；[ATT&CK](https://attack.mitre.org/) |
| Mitigations | <img src="mitigations.png" width="64" alt="Mitigations icon"> | 盾牌＋屏障 | [阻止技術成功執行的安全概念與防護技術](https://attack.mitre.org/mitigations/) |
| Assets | <img src="assets.png" width="64" alt="Assets icon"> | 工控設備 | [可能被技術鎖定的 ICS 裝置、設備能力與功能](https://attack.mitre.org/assets/) |
| Detections | <img src="detections.png" width="64" alt="Detections icon"> | 放大鏡＋訊號 | [偵測對手技術的策略、分析與資料元件](https://attack.mitre.org/detectionstrategies/) |
| Groups | <img src="groups.png" width="64" alt="Groups icon"> | 三個人物 | [以共同名稱追蹤的關聯入侵活動群組](https://attack.mitre.org/groups/) |
| Software | <img src="software.png" width="64" alt="Software icon"> | 程式視窗＋提示符 | [對手使用的惡意程式與工具](https://attack.mitre.org/software/) |
| Campaigns | <img src="campaigns.png" width="64" alt="Campaigns icon"> | 旗幟＋時間節點 | [特定時間內具有共同目標的入侵活動](https://attack.mitre.org/campaigns/) |

## 輸入、輸出與流程

- 風格參考輸入：`D:\MITREATTACK_SIMULATOR\assets\ttp-selection-studio-icon-pixel.png`
- 專案分類定義輸入：`D:\MITREATTACK_SIMULATOR\attack_catalog.py`、`D:\MITREATTACK_SIMULATOR\README.md`，以及上表官方網頁。
- 輸出目錄：`D:\MITREATTACK_SIMULATOR\assets\navigation`
- 六個輸出 PNG：`mitigations.png`、`assets.png`、`detections.png`、`groups.png`、`software.png`、`campaigns.png`。
- 完整生成提示詞與原始來源路徑：`D:\MITREATTACK_SIMULATOR\assets\navigation\generation-prompts.json`。

製作進度：1/4 查閱定義並制定造型；2/4 使用內建 image_gen 分別生成每個圖示；3/4 複製資產、整合七個導覽按鈕；4/4 檢查 PNG 透明背景、按鈕與介面預覽。原始生成圖保留，沒有覆寫現有的應用程式圖示。

## 程式載入

`main.py` 的 `load_navigation_icons()` 使用 `NAVIGATION_ICON_FILES` 對應七個分類，從程式位置解析絕對輸入路徑。啟動時先列出全部輸入路徑及 `Output files: None`，再逐一顯示載入（2/3，1/7 至 7/7）進度，最後顯示完成數（3/3）。PNG 讀取失敗時顯示路徑與訊息，該分類保留文字按鈕。

按鈕以 32 × 32 的圖示搭配下方置中的分類文字，預先準備 32、64、96 像素影像供不同顯示縮放使用，採用 Qt `FastTransformation` 保留像素邊緣。上方選單 **Settings → Show navigation labels** 可關閉文字，切換為精簡圖示導覽列；滑鼠停留時仍以提示文字顯示分類名稱。分類名稱、無障礙名稱、互斥選取與點擊切換功能保留。設定存入 `D:\MITREATTACK_SIMULATOR\data\ui-settings.ini`，啟動讀取及切換儲存均先顯示絕對路徑並回報各階段進度；完整讀寫流程見專案根目錄 README。重新啟動程式會沿用文字顯示設定。

## 驗證結果

導覽文字設定已另外驗證：預設文字位於 Icon 下方，選單操作能切換精簡版面，七個按鈕的真實 Qt ToolTip 事件均能顯示分類名稱；隱藏設定在獨立的新程式行程中正確還原。切換前後保留目前分類、文件 ID 與已選 TTP，並通過原有介面 smoke check。測試使用隔離的設定檔，沒有修改使用者的設定。

兩種新版介面預覽：`D:\MITREATTACK_SIMULATOR\artifacts\navigation-labels-below-preview.png`、`D:\MITREATTACK_SIMULATOR\artifacts\navigation-icons-only-preview.png`，皆已檢視。

已使用專案的 Python／PySide6 環境，從 `D:\MITREATTACK_SIMULATOR\assets` 工作目錄驗證全部七個 PNG 能載入且保留透明背景，尺寸皆為 1254 × 1254。七個按鈕皆具圖示、原分類文字與無障礙名稱。載入資料後逐一點擊七個分類，確認切換成功且保持互斥選取，並通過原有介面 smoke check。文字版面目前為 Icon 下方顯示，或依設定僅顯示 Icon。

最新介面預覽輸出：`D:\MITREATTACK_SIMULATOR\artifacts\navigation-icons-no-shields-preview.png`，已檢視移除盾牌後的 Groups、Campaigns，以及整組圖示的對比與文字版面。替換圖像後的介面 smoke check 通過。

可重新執行既有介面驗證與預覽：

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& 'C:\Users\nick5\MITREATTACK_SIMULATOR\Scripts\python.exe' -B 'D:\MITREATTACK_SIMULATOR\main.py' --smoke-test --screenshot 'D:\MITREATTACK_SIMULATOR\artifacts\navigation-icons-no-shields-preview.png'
```

