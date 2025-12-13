# 發行說明模板（JoinMarket ABCMint）

## 版本
- 標籤：`vX.Y.Z`
- 構建日期：YYYY-MM-DD

## 下載
- 可執行檔：Release 資產 `JoinMarket-ABCMint-LauncherX.Y.Z.exe`
- 校驗檔：Release 資產 `SHA256SUMS.txt`

## 變更
- 新增：
- 修正：
- 相容性：

## 系統需求
- Windows 10/11（x64）
- Python 3.12（僅開發者）
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
Get-FileHash -Path ".\JoinMarket-ABCMint-LauncherX.Y.Z.exe" -Algorithm SHA256
```
或使用 Release 資產 `SHA256SUMS.txt` 逐行比對。

## 授權
- 本版本依 GPLv3 發佈，詳見 `LICENSE` 與 `NOTICE`。
- 保留並致謝上游 JoinMarket 與各開源組件。
