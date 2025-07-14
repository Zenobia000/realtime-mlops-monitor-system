# API 參考文檔

## 📋 目錄
- [基礎信息](#基礎信息)
- [認證機制](#認證機制)
- [SDK 整合範例](#sdk-整合範例)
- [系統 API](#系統-api)
- [指標查詢 API](#指標查詢-api)
- [告警管理 API](#告警管理-api)
- [服務監控 API](#服務監控-api)
- [儀表板 API](#儀表板-api)
- [WebSocket API](#websocket-api)
- [錯誤處理](#錯誤處理)
- [故障排除](#故障排除)
- [安全最佳實踐](#安全最佳實踐)

## 基礎信息

**Base URL**: `http://localhost:8001`  
**API 版本**: `v1`  
**認證方式**: API Key  
**請求格式**: `application/json`  
**響應格式**: `application/json`

## 認證機制

### 🔐 認證方式

#### 1. Header 認證 (推薦)

通過 `X-API-Key` Header 傳遞 API Key：

```bash
curl -H "X-API-Key: monitor_api_key_dev_2025" \
     https://api.monitor.example.com/v1/metrics/summary
```

#### 2. Bearer Token 認證

通過 `Authorization` Header 使用 Bearer Token：

```bash
curl -H "Authorization: Bearer monitor_api_key_dev_2025" \
     https://api.monitor.example.com/v1/metrics/summary
```

#### 3. WebSocket 認證

WebSocket 連接通過查詢參數傳遞 API Key：

```javascript
const ws = new WebSocket('ws://localhost:8001/v1/ws/metrics?api_key=monitor_api_key_dev_2025');
```

### 🔑 API Key 管理

| 環境 | API Key | 說明 |
|------|---------|------|
| 開發環境 | `monitor_api_key_dev_2025` | 開發測試使用 |
| 測試環境 | `monitor_api_key_test_2025` | 測試環境專用 |
| 生產環境 | 聯繫管理員取得 | 生產環境高安全性 |

### 🛡️ 安全功能

#### 速率限制

| 端點類型 | 限制 | 說明 |
|----------|------|------|
| 一般查詢端點 | 300 requests/minute | 指標查詢、告警查詢等 |
| 實時數據端點 | 60 requests/minute | 實時指標、WebSocket |
| WebSocket 連接 | 5 concurrent connections | 每個 API Key 最多同時連接數 |

#### 速率限制 Headers

```http
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 295
X-RateLimit-Reset: 1625140800
Retry-After: 60
```

#### CORS 支援

系統支援跨域請求，允許以下來源：

```
- http://localhost:3000 (Vue.js 開發服務器)
- http://localhost:8080 (替代前端端口)
- http://127.0.0.1:3000
- http://127.0.0.1:8080
```

## SDK 整合範例

### Python

```python
import requests
import json

class MonitorAPIClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
    
    def get_metrics_summary(self, time_range=3600):
        """獲取指標摘要"""
        url = f"{self.base_url}/v1/metrics/summary"
        params = {'time_range': time_range}
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_real_time_metrics(self, service_name=None):
        """獲取實時指標"""
        url = f"{self.base_url}/v1/metrics/real-time"
        params = {}
        if service_name:
            params['service_name'] = service_name
            
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

# 使用範例
client = MonitorAPIClient(
    base_url="http://localhost:8001",
    api_key="monitor_api_key_dev_2025"
)

# 獲取指標摘要
summary = client.get_metrics_summary()
print(f"總服務數: {summary['data']['summary']['total_services']}")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

class MonitorAPIClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.headers = {
            'X-API-Key': apiKey,
            'Content-Type': 'application/json'
        };
    }
    
    async getMetricsSummary(timeRange = 3600) {
        const response = await axios.get(`${this.baseUrl}/v1/metrics/summary`, {
            headers: this.headers,
            params: { time_range: timeRange }
        });
        return response.data;
    }
    
    // WebSocket 連接
    connectWebSocket(endpoint = 'metrics') {
        const ws = new WebSocket(
            `ws://localhost:8001/v1/ws/${endpoint}?api_key=${this.apiKey}`
        );
        
        ws.onopen = () => console.log('WebSocket 連接已建立');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('收到數據:', data);
        };
        
        return ws;
    }
}

// 使用範例
const client = new MonitorAPIClient(
    'http://localhost:8001',
    'monitor_api_key_dev_2025'
);
```

---

## 系統 API

### 🏠 服務根目錄

```http
GET /
```

**描述**: 獲取服務基本信息

**認證**: 無需認證

**響應範例**:
```json
{
  "message": "Model API 監控系統",
  "version": "1.0.0",
  "docs": "/docs"
}
```

### 🏥 健康檢查

```http
GET /health
```

**描述**: 檢查系統健康狀態

**認證**: 無需認證

**響應範例**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 86400,
    "dependencies": {
      "postgresql": "healthy",
      "redis": "healthy",
      "rabbitmq": "unknown"
    },
    "environment": "development"
  },
  "timestamp": "2025-07-01T10:30:00Z"
}
```

---

## 指標查詢 API

### 📊 指標摘要

```http
GET /v1/metrics/summary
```

**描述**: 獲取系統整體指標摘要

**認證**: 🔒 需要 API Key

**查詢參數**:
| 參數 | 類型 | 必需 | 描述 | 預設值 |
|------|------|------|------|--------|
| `start_time` | string | 否 | 開始時間 (ISO 8601) | 1小時前 |
| `end_time` | string | 否 | 結束時間 (ISO 8601) | 現在 |
| `service_name` | string | 否 | 篩選特定服務 | 全部 |

**響應範例**:
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_services": 5,
      "total_endpoints": 20,
      "total_requests": 15000,
      "average_qps": 4.2,
      "average_error_rate": 0.5,
      "average_response_time": 145.2
    },
    "services": [
      {
        "service_name": "model-api-v1",
        "qps": 2.5,
        "error_rate": 0.2,
        "avg_response_time": 120.5,
        "status": "healthy"
      }
    ]
  },
  "timestamp": "2025-07-01T10:30:00Z"
}
```

### ⚡ 實時指標

```http
GET /v1/metrics/real-time
```

**描述**: 獲取實時指標數據 (Redis 快取)

**認證**: 🔒 需要 API Key

**響應範例**:
```json
{
  "success": true,
  "data": {
    "real_time_metrics": [
      {
        "service_name": "model-api-v1",
        "qps": 2.8,
        "error_rate": 0.1,
        "avg_response_time": 115.2,
        "last_updated": "2025-07-01T10:29:50Z"
      }
    ],
    "total_services": 3,
    "cache_ttl_seconds": 300
  },
  "timestamp": "2025-07-01T10:30:00Z"
}
```

---

## 告警管理 API

### 🚨 告警列表

```http
GET /v1/alerts/
```

**描述**: 獲取告警列表

**認證**: 🔒 需要 API Key

**查詢參數**:
| 參數 | 類型 | 描述 | 可選值 |
|------|------|------|--------|
| `status` | string | 告警狀態 | triggered, resolved, acknowledged |
| `severity` | string | 嚴重程度 | low, medium, high, critical |
| `service_name` | string | 服務名稱 | - |
| `limit` | integer | 返回數量 | 預設 50 |

**響應範例**:
```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "id": "alert_123456",
        "rule_name": "高錯誤率告警",
        "severity": "high",
        "status": "triggered",
        "message": "服務 model-api-v1 錯誤率 = 5.2% > 5%",
        "service_name": "model-api-v1",
        "triggered_at": "2025-07-01T10:25:00Z"
      }
    ]
  },
  "timestamp": "2025-07-01T10:30:00Z"
}
```

---

## WebSocket API

### 📊 實時指標流

```
WS /v1/ws/metrics?api_key={api_key}
```

**描述**: 實時接收指標數據推送

**認證**: 🔒 API Key (查詢參數)

**連接範例**:
```javascript
const ws = new WebSocket('ws://localhost:8001/v1/ws/metrics?api_key=monitor_api_key_dev_2025');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('收到指標數據:', data);
};
```

**推送數據格式**:
```json
{
  "type": "metrics_update",
  "timestamp": "2025-07-01T10:30:00Z",
  "data": {
    "overall": {
      "qps": 4.2,
      "error_rate": 0.5,
      "avg_response_time": 145.2
    },
    "services": {
      "model-api-v1": {
        "qps": 2.5,
        "error_rate": 0.2,
        "avg_response_time": 120.5
      }
    }
  }
}
```

---

## 錯誤處理

### 統一錯誤格式

所有錯誤響應遵循統一格式：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "用戶友好的錯誤信息",
    "developer_message": "詳細的開發者錯誤信息"
  },
  "timestamp": "2025-07-01T10:30:00Z"
}
```

### 常見錯誤碼

| HTTP 狀態碼 | 錯誤碼 | 描述 |
|-------------|--------|------|
| `400` | `INVALID_PARAMETERS` | 請求參數無效 |
| `401` | `MISSING_API_KEY` | 缺少 API Key |
| `401` | `INVALID_API_KEY` | 無效的 API Key |
| `403` | `INSUFFICIENT_PERMISSIONS` | 權限不足 |
| `429` | `RATE_LIMIT_EXCEEDED` | 請求頻率超過限制 |
| `500` | `INTERNAL_SERVER_ERROR` | 內部伺服器錯誤 |

### 認證錯誤範例

```json
{
  "success": false,
  "error": {
    "code": "INVALID_API_KEY",
    "message": "API Key 無效或已過期",
    "developer_message": "請檢查 X-API-Key header 或 Authorization header"
  },
  "timestamp": "2025-07-01T10:30:00Z"
}
```

---

## 故障排除

### 常見問題

1. **API Key 格式錯誤**
   - 確保 API Key 不包含額外的空格或特殊字符
   - 檢查 Header 名稱拼寫是否正確

2. **WebSocket 連接失敗**
   - 確保使用正確的 WebSocket URL 格式
   - 檢查 API Key 是否透過查詢參數正確傳遞

3. **CORS 錯誤**
   - 確保請求來源在允許的 CORS 列表中
   - 檢查是否設置了正確的 Content-Type header

### 測試連接

```bash
# 測試健康檢查 (無需認證)
curl http://localhost:8001/health

# 測試認證端點
curl -H "X-API-Key: monitor_api_key_dev_2025" \
     http://localhost:8001/v1/metrics/summary

# 測試 WebSocket 連接
wscat -c "ws://localhost:8001/v1/ws/metrics?api_key=monitor_api_key_dev_2025"
```

---

## 安全最佳實踐

### 1. API Key 保護
- 不要將 API Key 硬編碼在客戶端代碼中
- 使用環境變數或安全的配置管理
- 定期輪轉 API Key

### 2. 傳輸安全
- 生產環境務必使用 HTTPS
- 避免在 URL 中傳遞敏感信息

### 3. 錯誤處理
- 實現適當的重試機制
- 處理速率限制錯誤
- 記錄認證失敗事件

### 4. 監控
- 監控 API Key 使用情況
- 設置異常存取告警
- 定期審查存取日誌

---

**最後更新**: 2025-07-01  
**文檔版本**: v1.0.0  
**支援聯繫**: support@monitor.example.com 