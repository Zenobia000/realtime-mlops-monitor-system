# Model API 監控系統 - API 合約文檔

## 📋 概覽

本目錄包含 Model API 監控系統的完整 API 合約文檔，遵循 RESTful API 設計原則和行業最佳實踐。

## 📚 文檔結構

### 🔧 規格文檔
- [`openapi.yaml`](./openapi.yaml) - OpenAPI 3.0 規格定義
- [`api-reference.md`](./api-reference.md) - 完整 API 參考文檔
- [`authentication.md`](./authentication.md) - 認證機制說明

### 📊 功能分類
- [`metrics-api.md`](./metrics-api.md) - 指標查詢 API
- [`alerts-api.md`](./alerts-api.md) - 告警管理 API  
- [`services-api.md`](./services-api.md) - 服務監控 API
- [`dashboards-api.md`](./dashboards-api.md) - 儀表板數據 API
- [`websocket-api.md`](./websocket-api.md) - WebSocket 實時 API

### 🔐 認證與安全
- [`authentication.md`](./authentication.md) - 認證機制說明
- [`rate-limiting.md`](./rate-limiting.md) - 限流規則
- [`error-codes.md`](./error-codes.md) - 錯誤代碼參考

### 📖 開發指南
- [`getting-started.md`](./getting-started.md) - 快速開始指南
- [`sdk-examples.md`](./sdk-examples.md) - SDK 使用範例
- [`webhooks.md`](./webhooks.md) - Webhook 整合
- [`changelog.md`](./changelog.md) - API 變更日誌

## 🚀 快速導航

### 核心 API 端點

| 分類 | 描述 | 端點數量 | 文檔 |
|------|------|----------|------|
| 🏥 **系統健康** | 服務狀態檢查 | 3 | [系統 API](#system-apis) |
| 📊 **指標查詢** | 監控數據查詢 | 5 | [指標 API](./api-reference.md#指標查詢-api) |
| 🚨 **告警管理** | 告警查詢與管理 | 6 | [告警 API](./api-reference.md#告警管理-api) |
| 🔍 **服務監控** | 服務狀態監控 | 4 | [服務 API](./api-reference.md#服務監控-api) |
| 📈 **儀表板** | 儀表板數據 | 3 | [儀表板 API](./api-reference.md#儀表板-api) |
| ⚡ **實時數據** | WebSocket 推送 | 2 | [WebSocket API](./api-reference.md#websocket-api) |

### 系統 APIs

```http
GET  /                    # 服務基本信息
GET  /health             # 健康檢查
GET  /v1                 # API 版本信息
```

### 認證方式

```bash
# API Key (Header) - 推薦
curl -H "X-API-Key: your-api-key" https://api.monitor.example.com/v1/metrics/summary

# Bearer Token
curl -H "Authorization: Bearer your-api-key" https://api.monitor.example.com/v1/metrics/summary
```

## 🌟 特色功能

### 🔄 實時數據流
- **WebSocket 連接**: 支持實時指標和告警推送
- **自動重連**: 客戶端連接斷開自動重連
- **訊息壓縮**: 優化傳輸效率
- **非侵入式監控**: 額外延遲 < 20ms

### 📊 豐富的查詢選項
- **時間範圍查詢**: 支持靈活的時間窗口
- **多維度過濾**: 服務、端點、指標類型過濾
- **聚合統計**: 滑動視窗算法聚合（60秒視窗，12個5秒子視窗）
- **分頁支持**: 處理大數據集

### 🛡️ 企業級安全
- **API Key 認證**: 支持 Header 和 Bearer Token 兩種方式
- **速率限制**: 防止 API 濫用（300次/分鐘）
- **CORS 支持**: 跨域請求安全
- **輸入驗證**: 嚴格的參數驗證

### 🏗️ 技術架構
- **數據存儲**: PostgreSQL + TimescaleDB
- **快取層**: Redis 即時數據
- **消息系統**: RabbitMQ 事件驅動
- **API 框架**: FastAPI + Pydantic

## 📊 API 使用統計

```
總端點數量: 21
RESTful API: 19
WebSocket API: 2
認證端點: 19 (保護)
公開端點: 2

平均響應時間: < 100ms
API 可用性: 99.9%
支持的請求格式: JSON
支持的回應格式: JSON, WebSocket
```

## 🔧 開發環境

### Base URLs

```
開發環境: http://localhost:8001
測試環境: https://test-api.monitor.example.com
生產環境: https://api.monitor.example.com
```

### 版本控制

- **當前版本**: v1.0.0
- **API 版本**: v1
- **向後兼容**: 支持
- **版本策略**: 語意化版本控制

## 🎯 快速開始

1. **獲取 API Key**
   ```bash
   # 開發環境預設 API Key
   export API_KEY="monitor_api_key_dev_2025"
   ```

2. **測試連接**
   ```bash
   curl -H "X-API-Key: $API_KEY" http://localhost:8001/health
   ```

3. **查詢實時指標**
   ```bash
   curl -H "X-API-Key: $API_KEY" http://localhost:8001/v1/metrics/real-time
   ```

4. **建立 WebSocket 連接**
   ```javascript
   const ws = new WebSocket('ws://localhost:8001/v1/ws/metrics?api_key=your-key');
   ```

## 📞 技術支援

- **API 文檔**: `/docs` (Swagger UI)
- **API 狀態**: [status.monitor.example.com](http://localhost:8001/health)
- **技術支援**: support@monitor.example.com
- **版本更新**: [變更日誌](./changelog.md)

---

**最後更新**: 2025-07-01  
**文檔版本**: v1.0.0  
**API 版本**: v1 