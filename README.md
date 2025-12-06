# JoinMarket‑ABCMint Launcher 1.0.0 發行說明

## 概述
本版本提供 Windows 平台的 ABCMint Mix Launcher（基於 PyQt6）與本地混幣服務托管（waitress），面向終端用戶簡化設定與啟動流程。

## 下載與校驗
- 可執行檔：`joinmarket_abcmint/dist/JoinMarket-ABCMint-LauncherV1.0.0.exe`
- SHA256：`8B21AAF4A8437D7D42477DAF08E599313577D8EC44500819E3A31580667DFC3D`
- PowerShell 校驗：
  ```powershell
  Get-FileHash -Path "joinmarket_abcmint/dist/JoinMarket-ABCMint-LauncherV1.0.0.exe" -Algorithm SHA256 | Select-Object -ExpandProperty Hash
  ```

## 新特性
- 圖形介面：參數填寫（RPC 埠/使用者名稱/密碼）、連線測試、日誌輸出、系統托盤常駐與快速開啟 Web UI。
- 服務托管：使用 `waitress` 啟動後端服務，監聽 `0.0.0.0:5000`，存取 `http://localhost:5000`。
- 設定持久化：`%LOCALAPPDATA%/JoinMarket-ABCMint/launcher_config.json` 自動載入/儲存。
- 打包流程：提供 PyInstaller 規範檔與建置產物目錄。

## 升級與注意事項
- 節點要求：需本機執行啟用 JSON‑RPC 的 ABCMint/相容 Bitcoin 節點，預設 `127.0.0.1` 與埠 `8332`。
- 相容性：缺少 `estimatesmartfee/getmempoolinfo/testmempoolaccept/gettxoutproof/verifytxoutproof`，費用策略採 `paytxfee` 基線與回退；RBF 固定為 `False`；錢包視圖透過地址過濾與 UTXO 查詢實作。
- 埠占用：後端固定 `5000`，若占用需釋放後重試。
- 單一實例：再次啟動將提示已在執行，請於系統托盤管理。

## 已知問題
- 在極端網路或節點負載情況下，連線測試可能逾時，請檢查 RPC 鑑權與網路連線。
- 不支援證明相關介面的功能將降級或停用。

## 回滾
- 若需回退，保留上一版本可執行檔與設定檔；或自原始碼執行 `joinmarket_abcmint/service/start_service.py` 以繼續使用後端服務。

## 文件與參考
- 啟動器使用指南：`joinmarket_abcmint/docs/啟動器使用指南.md`
- 安裝與部署：`joinmarket_abcmint/docs/安裝部署指南.md`
- 相容性說明：`joinmarket_abcmint/docs/相容性說明.md`
- 遷移說明：`joinmarket_abcmint/docs/遷移說明.md`
- 服務說明：`joinmarket_abcmint/service/README.md`

## 致謝與授權
- 致謝 JoinMarket 上游專案與相關開源相依。
- 授權以各自倉庫為準。
