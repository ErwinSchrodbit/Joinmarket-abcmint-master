# ABCMint 混幣服務

基於 JoinMarket_abcmint 的集中式混幣服務，提供 Web 介面與 HTTP API。

## 文件用途
- 本文件面向開發者與運維人員，說明後端服務與 API。
- 終端用戶請參考：`joinmarket_abcmint/docs/啟動器使用指南.md`。

## 功能特性

- **簡單易用**：使用者僅需輸入混幣數量與目標地址
- **自動生成**：每次混幣生成唯一的 SL274 安全等級入金地址
- **自動扣費**：動態費率（依分片與跳數計算）扣除至指定地址
- **兩步混幣**：入金 → 混幣地址 → 目標地址
- **即時追蹤**：每 15 秒輪詢偵測入金與確認狀態
- **QR Code**：自動生成入金地址二維碼

## 環境要求

- Python 3.7+
- ABCMint 節點 JSON‑RPC 存取
- 已設定的 JoinMarket_abcmint

## 快速開始

1. **設定環境變數**：
```powershell
$env:ABCMINT_RPC_HOST="127.0.0.1"
$env:ABCMINT_RPC_PORT="8332"
$env:ABCMINT_RPC_USER="your_rpc_user"
$env:ABCMINT_RPC_PASSWORD="your_rpc_password"
```

2. **安裝相依套件**：
```powershell
cd joinmarket_abcmint
pip install -r service/requirements.txt
```

3. **啟動服務**：
```powershell
python service/start_service.py
```

4. **存取服務**：
於瀏覽器開啟 http://localhost:5000

## API 介面

### 建立混幣請求
```http
POST /api/mix/request
Content-Type: application/json

{
    "amount": 40.0,
    "targetAddress": "<TARGET_ADDRESS>"
}
```

回應：
```json
{
    "jobId": "uuid-string",
    "depositAddress": "<DEPOSIT_ADDRESS>",
    "amount": 40.0
}
```

### 查詢混幣狀態
```http
GET /api/mix/status?jobId=uuid-string
```

回應：
```json
{
    "status": "waiting_deposit",
    "confirmations": 0,
    "txid1": null,
    "txid2": null,
    "error": null
}
```

## 狀態說明

- `pending`：等待處理
- `waiting_deposit`：等待使用者入金
- `deposit_received`：入金已接收
- `mixing_step1`：執行第一步混幣
- `waiting_confirmations`：等待確認
- `mixing_step2`：執行第二步混幣
- `completed`：混幣完成
- `error`：發生錯誤

## 混幣流程

1. 使用者輸入混幣數量與目標地址
2. 系統生成唯一的 SL274 入金地址
3. 使用者向入金地址發送指定數量的 ABCMint
4. 系統每 15 秒偵測入金狀態
5. 收到入金後執行第一步混幣（扣除動態費率的服務費）
6. 等待 6 個確認
7. 執行第二步混幣（發送淨額至目標地址）
8. 混幣完成

## 手續費設定

預設設定位於 `service/mixing_service.py` 與 `service/fee_model.py`：
- 費率模型：基線 + 分片增量 + 跳數增量（含上下限與絕對費下限）
- 手續費地址：由部署者配置（示例：`<FEE_ADDRESS>`）
- 固定礦工費：可配置（示例：`0.01` ABCMint/筆）
- 確認要求：預設 `6` 個區塊，可依鏈上情況調整

可透過環境變數調整：
```powershell
$env:ABCMINT_DEDUCTION_PERCENT   # 由服務層自動計算並注入，無需手動設定
$env:ABCMINT_FEE_ADDRESS="<FEE_ADDRESS>"
$env:FIXED_FEE="<FIXED_FEE>"
$env:REQUIRED_CONF="6"
```
