# 發行說明（JoinMarket ABCMint Launcher 1.0.0）

## 版本
- 標籤：`v1.0.0`
- 構建日期：2025-12-06

## 下載
- 可執行檔：Release 資產 `JoinMarket-ABCMint-LauncherV1.0.0.exe`
- 校驗檔：Release 資產 `SHA256SUMS.txt`

## 變更
- 新增：提供 Windows 平台的 ABCMint Mix Launcher（基於 PyQt6）與本地混幣服務托管（waitress），面向終端用戶簡化設定與啟動流程
- 新增：圖形介面支持參數填寫、連線測試、日誌輸出、系統托盤常駐與快速開啟 Web UI
- 新增：服務托管使用 `waitress` 啟動後端服務，監聽 `0.0.0.0:5000`
- 新增：設定持久化至 `%LOCALAPPDATA%/JoinMarket-ABCMint/launcher_config.json`
- 新增：打包流程提供 PyInstaller 規範檔與建置產物目錄

## 系統需求
- Windows 10/11（x64）
- 本地 ABCMINT/相容 Bitcoin 節點，啟用 JSON-RPC（`127.0.0.1` 可訪問）

## ABCMINT全节点配置
### Windows 開放 8332 埠分步教程
1. **打開 Windows 防火牆高級設定**
   - 按下 `Win + R` 鍵，輸入 `wf.msc` 並按 Enter
   - 在左側面板點擊「入站規則」

2. **建立新的入站規則**
   - 在右側面板點擊「新增規則」
   - 規則類型選擇「埠」，點擊「下一步」
   - 選擇「TCP」，然後在「特定本機埠」中輸入 `8332`，點擊「下一步」
   - 操作選擇「允許連線」，點擊「下一步」
   - 設定檔保持預設（網域、私人、公用全選），點擊「下一步」
   - 名稱輸入「ABCMINT RPC 8332」，描述可選，點擊「完成」

3. **驗證埠是否開放**
   - 按下 `Win + R` 鍵，輸入 `cmd` 並按 Enter
   - 在命令提示字元中輸入 `netstat -an | findstr :8332`
   - 若看到類似 `TCP    0.0.0.0:8332           0.0.0.0:0              LISTENING` 的輸出，說明埠已成功開放

## 安裝與使用
- 雙擊 `exe` 啟動
- 填寫 RPC 設定（埠預設 `8332`）
- 點擊 `[ INITIALIZE LINK ]`，瀏覽器開啟 `http://localhost:5000`

## 校驗
```powershell
Get-FileHash -Path ".\JoinMarket-ABCMint-LauncherV1.0.0.exe" -Algorithm SHA256
```
SHA256：`8B21AAF4A8437D7D42477DAF08E599313577D8EC44500819E3A31580667DFC3D`

## 授權
- 本版本依 GPLv3 發佈，詳見 `LICENSE`、`NOTICE` 與 `THIRD-PARTY-LICENSES.txt`。
- 保留並致謝上游 JoinMarket 與各開源組件。
