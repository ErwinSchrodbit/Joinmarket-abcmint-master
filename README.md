# JoinMarket ABCMint 適配與啟動器

本倉庫提供 JoinMarket 在 ABCMint 區塊鏈上的適配層與一個 Windows 啟動器（ABCMint Mix Launcher），用於快速拉起本地混幣服務與 Web 介面。

## 快速開始（終端用戶）
- 可執行檔：Release 資產 `JoinMarket-ABCMint-LauncherV1.0.0.exe`
- 執行步驟：
  1. 本機需已執行啟用 JSON‑RPC 的 ABCMint/相容 Bitcoin 節點（`127.0.0.1` 可存取）。
  2. 滑鼠雙擊啟動器 EXE，填寫 `RPC Port/User/Password`（埠預設 `8332`）。
  3. 點擊 `[ INITIALIZE LINK ]` 進行連線測試，成功後自動開啟 `http://localhost:5000`。
- 詳細指南：見 [啟動器使用指南](docs/啟動器使用指南.md)

## 校驗
- PowerShell 校驗：
  ```powershell
  Get-FileHash -Path ".\JoinMarket-ABCMint-LauncherV1.0.0.exe" -Algorithm SHA256 | Select-Object -ExpandProperty Hash
  ```
- SHA256 校驗值：`8B21AAF4A8437D7D42477DAF08E599313577D8EC44500819E3A31580667DFC3D`

## 專案結構
- `service/`：後端混幣服務（Flask/Waitress），入口 `app.py`，說明見 [`service/README.md`](service/README.md)。
- `src/`：適配層原始碼，如 `jmclient/abcmint_interface.py`。
- `joinmarket-clientserver-master/`：上游 JoinMarket 原始碼與文件。
- `launcher.py`：Windows 啟動器原始碼；打包規範 `JoinMarket-ABCMint-LauncherV1.0.0.spec`。
- `dist/`、`build/`：打包產物目錄。
- `docs/`：專案文件集合（見下文索引）。

## 文件入口
- 使用指南：[啟動器使用指南.md](docs/啟動器使用指南.md)
- 安裝部署：[安裝部署指南.md](docs/安裝部署指南.md)
- 相容性說明：[相容性說明.md](docs/相容性說明.md)
- 遷移說明：[遷移說明.md](docs/遷移說明.md)
- 持續整合：[持續整合指南.md](docs/持續整合指南.md)
- 服務說明：[service/README.md](service/README.md)
- 上游指南：[README.md](joinmarket-clientserver-master/README.md)、[USAGE.md](joinmarket-clientserver-master/docs/USAGE.md)

## 開發與建置
- 語言與環境：Python 3.12，Windows 建議使用 PowerShell。
- 相依參考：`requirements_launcher.txt`（啟動器）與服務端 `service/requirements.txt`。
- 路徑準備：確保 `joinmarket-clientserver-master/src`、`service` 於執行路徑可匯入。
- 打包：使用 PyInstaller，規範檔 `JoinMarket-ABCMint-LauncherV1.0.0.spec`。

## 版本與發佈
- 啟動器版本以可執行檔與 GUI 標題展示（`V1.0.0`/`V.1.0`）。
 - 變更日誌：見 [`CHANGELOG.md`](CHANGELOG.md)
- 發行說明：見 [`docs/release-notes/發行說明-JoinMarket-ABCMint-Launcher-1.0.0.md`](docs/release-notes/發行說明-JoinMarket-ABCMint-Launcher-1.0.0.md)
- 正式發佈前建議固定相依版本與建置環境，並於後續版本持續更新以上文件。

## 授權與致謝
- 本倉庫依賴並致謝上游 JoinMarket 專案及相關開源組件。
- 專案採用 GPLv3 授權；詳見 `LICENSE`、`NOTICE` 與 `THIRD-PARTY-LICENSES.txt`。
- 上游 JoinMarket 授權與文本：`joinmarket-clientserver-master/LICENSE`。

## 合規發佈
- 使用 GitHub Releases 上傳可執行檔與校驗檔，不將二進制直接提交到代碼區。
- 於 Release Notes 附上系統需求、使用說明、已知問題與變更列表（模板見 `docs/release-notes/RELEASE_TEMPLATE.md`）。
- 提供對應版本源碼與構建規範（包含本倉庫全部內容與 `*.spec`）。
- 生成校驗檔：
  ```powershell
  pwsh joinmarket_abcmint/scripts/generate_checksums.ps1 -DistPath "joinmarket_abcmint/dist" -Pattern "*.exe"
  ```
