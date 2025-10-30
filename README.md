# 釘釘-Notion 雙向同步系統

一個自動化的雙向同步服務,用於在釘釘待辦事項和 Notion 資料庫之間同步任務。

## 功能特點

- **雙向同步**: 釘釘和 Notion 之間的任務自動雙向同步
- **智能分類**: 自動區分「指派給我的」和「我指派給他人的」任務
- **即時更新**: 釘釘變更通過 Webhook 即時同步,Notion 變更通過定時輪詢同步
- **衝突處理**: 基於時間戳的衝突解決機制,避免數據覆蓋
- **預留接口**: 已預留 LINE 通知接口,方便未來擴展

## 系統架構

```
釘釘 API <--Webhook--> 同步服務 <--Polling--> Notion API
```

## 目錄結構

```
dingtalk-notion-sync/
├── config/
│   └── config.yaml.example    # 配置文件模板
├── src/
│   ├── main.py               # 主程式入口
│   ├── config_loader.py      # 配置載入模組
│   ├── logger.py             # 日誌設置模組
│   ├── dingtalk_client.py    # 釘釘 API 客戶端
│   ├── notion_client.py      # Notion API 客戶端
│   ├── sync_service.py       # 同步服務核心邏輯
│   └── webhook_server.py     # Webhook 服務器
├── logs/                     # 日誌目錄
├── requirements.txt          # Python 依賴
└── README.md                 # 本文件
```

## 快速開始

### 1. 安裝依賴

```bash
cd dingtalk-notion-sync
pip3 install -r requirements.txt
```

### 2. 配置系統

複製配置文件模板並填入您的配置:

```bash
cp config/config.yaml.example config/config.yaml
```

編輯 `config/config.yaml`,填入以下信息:

- 釘釘 AppKey 和 AppSecret
- 釘釘 User UnionId
- Notion Integration Token
- Notion 資料庫 ID (兩個)
- Webhook 配置 (AES Key, Token, Port)

### 3. 設置 Notion 資料庫

請參考「部署說明文檔」中的詳細步驟創建兩個 Notion 資料庫。

### 4. 配置釘釘事件訂閱

在釘釘開發者後台配置事件訂閱,訂閱以下事件:

- 待辦任務新增
- 待辦任務更新
- 待辦任務刪除

### 5. 啟動服務

```bash
python3 src/main.py
```

## 使用說明

### 私人待辦看板 (別人指派給我的)

當有人在釘釘指派待辦給您時,系統會自動在 Notion 的「私人待辦看板」中創建對應的任務。您可以在 Notion 中查看、編輯這些任務,所有變更都會自動同步回釘釘。

### 團隊任務追蹤表 (我指派給別人的)

當您在釘釘指派待辦給團隊成員時,系統會自動在 Notion 的「團隊任務追蹤表」中創建對應的任務記錄。您可以在 Notion 中追蹤任務進度,所有變更都會自動同步回釘釘。

### 注意事項

1. **統一操作源**: 建議在釘釘上進行所有操作,Notion 主要用於查看和管理。這樣可以最大程度避免同步衝突。

2. **同步延遲**: 
   - 釘釘 → Notion: 即時同步 (通過 Webhook)
   - Notion → 釘釘: 根據配置的輪詢間隔 (預設 60 秒)

3. **衝突處理**: 如果同一任務在兩邊同時修改,系統會以最後編輯時間為準。

## 日誌查看

日誌文件位於 `logs/sync_service.log`,您可以查看詳細的同步記錄和錯誤信息:

```bash
tail -f logs/sync_service.log
```

## 故障排除

### 同步不工作

1. 檢查配置文件是否正確填寫
2. 檢查 Notion Integration 是否已分享到兩個資料庫
3. 檢查釘釘 Webhook 是否能訪問您的服務器
4. 查看日誌文件中的錯誤信息

### Webhook 無法接收事件

1. 確保服務器的端口已開放
2. 確保釘釘開發者後台的 Webhook URL 配置正確
3. 檢查 AES Key 和 Token 是否正確

## 未來擴展

### 啟用 LINE 通知

在 `config/config.yaml` 中設置:

```yaml
line:
  enabled: true
  channel_access_token: "your_token"
  user_id: "your_user_id"
```

系統會在以下情況發送 LINE 通知:
- 有人指派待辦給您
- 您指派的任務被完成
- 任務即將逾期

## 技術支持

如有問題,請查看日誌文件或聯繫開發者。

## 授權

本專案僅供個人使用。

