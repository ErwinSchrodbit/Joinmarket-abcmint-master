# 發行說明模板（JoinMarket ABCMint）

## 版本
- 標籤：`vX.Y.Z`
- 構建日期：YYYY-MM-DD

## 下載
- 可執行檔：`dist/JoinMarket-ABCMint-LauncherX.Y.Z.exe`
- 校驗檔：`dist/SHA256SUMS.txt`

## 變更
- 新增：
- 修正：
- 相容性：

## 系統需求
- Windows 10/11（x64）
- Python 3.12（僅開發者）
- 本地 ABCMint/相容 Bitcoin 節點，啟用 JSON-RPC（`127.0.0.1` 可訪問）

## 安裝與使用
- 雙擊 `exe` 啟動
- 填寫 RPC 設定（埠預設 `8332`）
- 點擊 `[ INITIALIZE LINK ]`，瀏覽器開啟 `http://localhost:5000`

## 校驗
```powershell
Get-FileHash -Path "dist/JoinMarket-ABCMint-LauncherX.Y.Z.exe" -Algorithm SHA256
```
或使用 `dist/SHA256SUMS.txt` 逐行比對。

## 授權
- 本版本依 GPLv3 發佈，詳見 `LICENSE` 與 `NOTICE`。
- 保留並致謝上游 JoinMarket 與各開源組件。
