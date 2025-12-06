# 變更日誌（JoinMarket ABCMint）

## [1.0.0] - 2025-12-06

### 新增
- Windows 啟動器（`joinmarket_abcmint/launcher.py`），基於 `PyQt6`，支援連線測試、系統托盤管理、自動開啟 Web UI。
- 後端服務托管於 `waitress`，監聽`0.0.0.0:5000`，瀏覽器存取 `http://localhost:5000`。
- 設定持久化至 `%LOCALAPPDATA%/JoinMarket-ABCMint/launcher_config.json`。
- 打包規範檔：`joinmarket_abcmint/JoinMarket-ABCMint-LauncherV1.0.0.spec`，產物位於 `joinmarket_abcmint/dist/`與`joinmarket_abcmint/build/`。
- 文件：`joinmarket_abcmint/docs/啟動器使用指南.md`、安裝部署指南、相容性說明、遷移說明、持續整合指南。

### 變更
- 根 `README.md` 增加文件入口與 EXE 校驗說明，路徑統一為`joinmarket_abcmint/...`。

### 修正
- 在 `--noconsole` 模式下為 `sys.stdout/stderr` 提供最小實作，避免 JoinMarket 預期 `.isatty()` 的錯誤。

### 已棄用
- 無。

### 移除
- 無。

### 安全
- 不在倉庫中存放任何密鑰；RPC 憑據僅保存在本地使用者設定檔中。

### 相容性
- ABCMint RPC 不支援 `estimatesmartfee/getmempoolinfo/testmempoolaccept/gettxoutproof/verifytxoutproof`；採用費用策略回退與功能降級。
- RBF 固定為 `False`；錢包視圖透過地址過濾與 UTXO 查詢實作。

### 參考
- 使用指南：`joinmarket_abcmint/docs/啟動器使用指南.md`
- 服務說明：`joinmarket_abcmint/service/README.md`
- 安裝部署：`joinmarket_abcmint/docs/安裝部署指南.md`
- 相容性說明：`joinmarket_abcmint/docs/相容性說明.md`
- 遷移說明：`joinmarket_abcmint/docs/遷移說明.md`
- 持續整合：`joinmarket_abcmint/docs/持續整合指南.md`
