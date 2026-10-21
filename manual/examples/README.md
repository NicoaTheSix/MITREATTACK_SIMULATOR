# Custom domain example

`custom_domain_bundle.json`, in this directory, is an ATT&CK-compatible catalog example with the `research-lab` domain, two ordered matrices, two tactics, a parent technique and one sub-technique. It describes catalog entries only. Use the application's Browse button to load the JSON; the in-app manual renders Markdown guides.

Choose **File → Load layer URL / custom STIX… → Custom STIX Bundle / Collection**, Browse to this file, use fallback release `1.0`, validate, choose **Research Lab**, then open. Input is the resolved absolute Bundle path. Validated bytes are cached under the project's absolute `data/attack/custom/<sha256>.json` path; source read/parse/validate/cache progress is shown. The input is never edited. Select `LAB-001.child`, add a comment, and Save as Studio JSON or export Navigator/CSV. The two matrices appear as one ordered union: Observe, then Review. No separate matrix-filter state is implied.

中文：選 **File → Load layer URL / custom STIX… → Custom STIX Bundle / Collection**，瀏覽此檔、填備用版本 `1.0`，驗證後選 **Research Lab** 並開啟。輸入檔與快取輸出會顯示絕對路徑及進度。勾選 `LAB-001.child`、新增註解，再儲存 Studio 或匯出 Navigator／CSV。兩份 Matrix 依原始順序合併成 Observe、Review；這是資料目錄範例，不執行技術行為。

[English guide](../custom_domains_en.md) · [中文手冊](../custom_domains+_zh.md) · [All guides](../README.md)
