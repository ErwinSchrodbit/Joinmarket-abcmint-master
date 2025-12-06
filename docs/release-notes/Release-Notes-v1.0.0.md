# 發行說明（JoinMarket ABCMint Launcher 1.0.0）

## 版本
- 標籤：`v1.0.0`
- 構建日期：2025-12-06

## 下載
- 可執行檔：`dist/JoinMarket-ABCMint-LauncherV1.0.0.exe`
- 校驗檔：`dist/SHA256SUMS.txt`

## 校驗
- SHA256：`8B21AAF4A8437D7D42477DAF08E599313577D8EC44500819E3A31580667DFC3D`
- PowerShell：
  ```powershell
  Get-FileHash -Path "dist/JoinMarket-ABCMint-LauncherV1.0.0.exe" -Algorithm SHA256 | Select-Object -ExpandProperty Hash
  ```

## 變更
- 初版發佈：提供 Windows 啟動器與 Web 介面，支持本地 ABCMint 節點混幣流程。
- 引入費率模型與分片/跳躍路徑，支持故障恢復。

## 系統需求
- Windows 10/11（x64）
- 本地 ABCMint/相容 Bitcoin 節點，啟用 JSON-RPC（`127.0.0.1` 可訪問）

## 安裝與使用
- 雙擊 `exe` 啟動
- 填寫 RPC 設定（埠預設 `8332`）
- 點擊 `[ INITIALIZE LINK ]`，瀏覽器開啟 `http://localhost:5000`
- 詳細指南見 `docs/啟動器使用指南.md`

## 已知問題
- 無法連線節點時需檢查 RPC 使用者與密碼。
- Windows SmartScreen 可能攔截未簽名二進制，可選擇自簽或商用憑證簽名。

## 授權
- 本版本依 GPLv3 發佈，詳見 `LICENSE`、`NOTICE` 與 `THIRD-PARTY-LICENSES.txt`。
- 保留並致謝上游 JoinMarket 與各開源組件。
