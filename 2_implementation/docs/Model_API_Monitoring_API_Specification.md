# API 設計規範 (API Design Specification) - Model API 即時監控系統

---

**文件版本 (Document Version):** `v1.0.0`

**最後更新 (Last Updated):** `2025-07-01`

**主要作者/設計師 (Lead Author/Designer):** `Vibe Coder`

**審核者 (Reviewers):** `MLOps Team, Frontend Team, Backend Team`

**狀態 (Status):** `草稿 (Draft)`

**相關 SD 文檔:** `[docs/System_Architecture_Document.md](./System_Architecture_Document.md), [docs/Metrics_Processing_Service_Design.md](./Metrics_Processing_Service_Design.md)`

**OpenAPI/Swagger 定義文件:** `[待生成 - 將由 FastAPI 自動生成]`

---

## 目錄 (Table of Contents)

1.  [引言 (Introduction)](#1-引言-introduction)
2.  [通用設計約定 (General Design Conventions)](#2-通用設計約定-general-design-conventions)
3.  [認證與授權 (Authentication and Authorization)](#3-認證與授權-authentication-and-authorization)
4.  [錯誤處理 (Error Handling)](#4-錯誤處理-error-handling)
5.  [速率限制與配額 (Rate Limiting and Quotas)](#5-速率限制與配額-rate-limiting-and-quotas)
6.  [API 端點詳述 (API Endpoint Definitions)](#6-api-端點詳述-api-endpoint-definitions)
7.  [資料模型/Schema 定義 (Data Models / Schema Definitions)](#7-資料模型schema-定義-data-models--schema-definitions)
8.  [安全性考量 (Security Considerations)](#8-安全性考量-security-considerations)
9.  [向後兼容性與棄用策略 (Backward Compatibility and Deprecation Policy)](#9-向後兼容性與棄用策略-backward-compatibility-and-deprecation-policy)
10. [附錄 (Appendices)](#10-附錄-appendices)

---

## 1. 引言 (Introduction)

### 1.1 目的 (Purpose)
*   為 Model API 即時監控系統的前端儀表板、內部服務及第三方集成提供統一、明確的 API 接口規範，確保系統組件間的協調一致並支持高效的監控數據存取。

### 1.2 目標讀者 (Target Audience)
*   前端開發者、後端 API 實現者、MLOps 工程師、測試工程師、第三方集成開發者及技術文件撰寫者。

### 1.3 API 風格與原則 (API Style and Principles)
*   **RESTful 設計:** 遵循 REST 成熟度模型 Level 2，使用標準 HTTP 方法和狀態碼，資源導向的 URI 設計。
*   **核心原則:**
    *   **即時性優先:** API 設計優先考慮即時監控數據的快速獲取和推送。
    *   **資源導向:** URI 設計以監控資源（服務、指標、告警）為中心。
    *   **無狀態:** 所有 API 端點設計為無狀態，支持水平擴展。
    *   **一致性:** 統一的請求/回應格式、錯誤處理和命名約定。
    *   **向後兼容:** API 變更遵循語義版本控制，確保向後兼容性。

---

## 2. 通用設計約定 (General Design Conventions)

### 2.1 基本 URL (Base URL)
*   **生產環境 (Production):** `https://api-monitor.company.com/v1`
*   **預備環境 (Staging):** `https://staging-api-monitor.company.com/v1`
*   **開發環境 (Development):** `http://localhost:8000/v1`

### 2.2 版本控制 (Versioning)
*   **策略:** URL 路徑版本控制 (例如 `/v1/`, `/v2/`)，便於客戶端明確指定版本。
*   **當前版本:** `v1`

### 2.3 請求格式 (Request Formats)
*   **主要格式:** `application/json` (UTF-8 編碼)
*   **WebSocket 協議:** 用於即時數據推送
*   **Content-Type Header:** 所有包含請求體的 API 呼叫必須設置 `Content-Type: application/json`

### 2.4 回應格式 (Response Formats)
*   **主要格式:** `application/json` (UTF-8 編碼)
*   **統一回應結構:**
    ```json
    // 成功回應
    {
      "success": true,
      "data": { /* 實際數據對象或列表 */ },
      "meta": { /* 元數據，如分頁、時間戳等 */ },
      "timestamp": "2025-07-01T10:30:00Z"
    }
    
    // 錯誤回應
    {
      "success": false,
      "error": { /* 錯誤詳情，見錯誤處理章節 */ },
      "timestamp": "2025-07-01T10:30:00Z"
    }
    ```

### 2.5 日期與時間格式 (Date and Time Formats)
*   **標準格式:** ISO 8601 格式 `YYYY-MM-DDTHH:mm:ss.sssZ` (UTC 時間)
*   **時區處理:** 所有 API 交換的時間數據均為 UTC 時間，前端負責本地時區轉換

### 2.6 命名約定 (Naming Conventions)
*   **資源路徑:** 小寫，多個單詞用連字符連接，名詞複數形式 (例如 `/metrics`, `/services`, `/alerts`)
*   **查詢參數:** snake_case (例如 `start_time`, `service_name`)
*   **JSON 欄位:** snake_case (與查詢參數保持一致)
*   **HTTP Headers (自定義):** `X-Monitor-` 前綴 (例如 `X-Monitor-Client-Version`)

### 2.7 分頁 (Pagination)
*   **策略:** 基於偏移量/限制 (Offset/Limit) 的分頁，適合歷史數據查詢
*   **查詢參數:**
    *   `offset`: 偏移量，預設值為 0
    *   `limit`: 每頁數量，預設值為 50，最大值為 1000
*   **回應中的分頁信息:**
    ```json
    "meta": {
      "pagination": {
        "total_items": 1250,
        "total_pages": 25,
        "current_page": 1,
        "per_page": 50,
        "has_next": true,
        "has_prev": false
      }
    }
    ```

### 2.8 排序 (Sorting)
*   **查詢參數:** `sort_by`
*   **格式:** `sort_by=field_name` (升序) 或 `sort_by=-field_name` (降序)
*   **可排序欄位:** `timestamp`, `service_name`, `qps`, `avg_latency_ms`, `error_rate`

### 2.9 過濾 (Filtering)
*   **時間範圍過濾:**
    *   `start_time`: 開始時間 (ISO 8601 格式)
    *   `end_time`: 結束時間 (ISO 8601 格式)
*   **服務過濾:**
    *   `service_name`: 精確匹配服務名稱
    *   `api_endpoint`: 精確匹配 API 端點
*   **指標過濾:**
    *   `min_qps`, `max_qps`: QPS 範圍過濾
    *   `min_latency`, `max_latency`: 延遲範圍過濾

---

## 3. 認證與授權 (Authentication and Authorization)

### 3.1 認證機制 (Authentication Mechanism)
*   **API Key 認證:** 適用於內部服務和儀表板
    *   Header: `X-API-Key: <api_key>`
    *   API Key 通過環境變數配置，支持多個 Key 以實現輪轉
*   **WebSocket 認證:** 連接時通過查詢參數傳遞 API Key
    *   格式: `ws://localhost:8000/v1/ws/real-time?api_key=<api_key>`

### 3.2 授權模型/範圍 (Authorization Model/Scopes)
*   **讀取權限 (read):** 可讀取所有監控數據和歷史記錄
*   **配置權限 (config):** 可修改告警閾值和系統配置
*   **管理員權限 (admin):** 可管理 API Key 和系統管理功能
*   **當前 MVP 版本:** 簡化為單一權限級別，所有有效 API Key 具有讀取權限

---

## 4. 錯誤處理 (Error Handling)

### 4.1 標準錯誤回應格式 (Standard Error Response Format)
```json
{
  "success": false,
  "error": {
    "code": "INVALID_TIME_RANGE",
    "message": "指定的時間範圍無效",
    "developer_message": "start_time must be earlier than end_time",
    "target": "start_time",
    "details": [
      {
        "code": "VALIDATION_ERROR",
        "target": "start_time",
        "message": "時間格式必須符合 ISO 8601 標準"
      }
    ]
  },
  "timestamp": "2025-07-01T10:30:00Z"
}
```

### 4.2 通用 HTTP 狀態碼使用 (Common HTTP Status Codes)
*   **2xx - 成功:**
    *   `200 OK`: 成功獲取數據
    *   `201 Created`: 成功創建告警規則
    *   `204 No Content`: 成功刪除或更新，無回應內容
*   **4xx - 客戶端錯誤:**
    *   `400 Bad Request`: 請求參數格式錯誤
    *   `401 Unauthorized`: API Key 無效或缺失
    *   `403 Forbidden`: 權限不足
    *   `404 Not Found`: 指定的服務或資源不存在
    *   `422 Unprocessable Entity`: 請求格式正確但業務邏輯驗證失敗
    *   `429 Too Many Requests`: 超過速率限制
*   **5xx - 伺服器錯誤:**
    *   `500 Internal Server Error`: 內部處理錯誤
    *   `503 Service Unavailable`: 依賴服務不可用 (Redis, PostgreSQL)

---

## 5. 速率限制與配額 (Rate Limiting and Quotas)

*   **策略:** 基於 API Key 的速率限制
*   **限制閾值:**
    *   **一般查詢端點:** 每分鐘 300 次請求
    *   **即時數據端點:** 每分鐘 60 次請求 (每秒 1 次)
    *   **WebSocket 連接:** 每個 API Key 最多 5 個並發連接
*   **超出限制時的回應:** HTTP 429 Too Many Requests
*   **相關 Headers:**
    *   `X-RateLimit-Limit`: 當前時間窗口內的總請求數限制
    *   `X-RateLimit-Remaining`: 當前時間窗口內剩餘的請求數
    *   `X-RateLimit-Reset`: 當前時間窗口重置的 Unix 時間戳
    *   `Retry-After`: 建議客戶端重試的秒數

---

## 6. API 端點詳述 (API Endpoint Definitions)

### 6.1 資源：系統健康與狀態

#### 6.1.1 `GET /health`
*   **描述:** 獲取監控系統的健康狀態
*   **認證/授權:** 無需認證 (公開端點)
*   **查詢參數:** 無
*   **成功回應 (200 OK):**
    ```json
    {
      "success": true,
      "data": {
        "status": "healthy",
        "version": "1.0.0",
        "uptime_seconds": 3600,
        "dependencies": {
          "rabbitmq": "healthy",
          "postgresql": "healthy", 
          "redis": "healthy"
        }
      },
      "timestamp": "2025-07-01T10:30:00Z"
    }
    ```
*   **錯誤回應:** 503 Service Unavailable (依賴服務不健康)

### 6.2 資源：即時監控數據

#### 6.2.1 `GET /metrics/real-time`
*   **描述:** 獲取所有受監控服務的即時指標數據
*   **認證/授權:** 需要 API Key (read 權限)
*   **查詢參數:**
    *   `service_name` (可選): 篩選特定服務
    *   `include_details` (可選): 是否包含詳細指標，預設 false
*   **成功回應 (200 OK):**
    ```json
    {
      "success": true,
      "data": [
        {
          "service_name": "model-prediction-api",
          "api_endpoint": "/predict",
          "qps": 45.2,
          "avg_latency_ms": 120.5,
          "p95_latency_ms": 250.0,
          "p99_latency_ms": 380.0,
          "error_rate": 0.02,
          "total_requests": 2710,
          "status": "healthy",
          "last_updated": "2025-07-01T10:30:00Z"
        }
      ],
      "meta": {
        "total_services": 1,
        "healthy_services": 1,
        "data_freshness_seconds": 3
      },
      "timestamp": "2025-07-01T10:30:00Z"
    }
    ```

#### 6.2.2 `GET /metrics/real-time/{service_name}`
*   **描述:** 獲取指定服務的詳細即時指標
*   **認證/授權:** 需要 API Key (read 權限)
*   **路徑參數:**
    *   `service_name`: 服務名稱 (string)
*   **查詢參數:**
    *   `api_endpoint` (可選): 篩選特定 API 端點
*   **成功回應 (200 OK):** 同上，但只包含指定服務的數據
*   **錯誤回應:** 404 Not Found (服務不存在)

### 6.3 資源：歷史監控數據

#### 6.3.1 `GET /metrics/historical`
*   **描述:** 獲取歷史聚合監控數據，支持時間範圍查詢
*   **認證/授權:** 需要 API Key (read 權限)
*   **查詢參數:**
    *   `start_time` (必需): 查詢開始時間 (ISO 8601)
    *   `end_time` (必需): 查詢結束時間 (ISO 8601)
    *   `service_name` (可選): 篩選特定服務
    *   `api_endpoint` (可選): 篩選特定 API 端點
    *   `aggregation_interval` (可選): 聚合間隔，可選值 `5m`, `1h`, `1d`，預設 `5m`
    *   分頁參數: `offset`, `limit`
    *   排序參數: `sort_by`
*   **成功回應 (200 OK):**
    ```json
    {
      "success": true,
      "data": [
        {
          "timestamp": "2025-07-01T10:25:00Z",
          "service_name": "model-prediction-api",
          "api_endpoint": "/predict",
          "qps": 42.8,
          "avg_latency_ms": 115.2,
          "p95_latency_ms": 245.0,
          "p99_latency_ms": 375.0,
          "error_rate": 0.015,
          "total_requests": 1284
        }
      ],
      "meta": {
        "pagination": {
          "total_items": 288,
          "total_pages": 6,
          "current_page": 1,
          "per_page": 50,
          "has_next": true,
          "has_prev": false
        },
        "time_range": {
          "start_time": "2025-07-01T09:00:00Z",
          "end_time": "2025-07-01T10:30:00Z",
          "aggregation_interval": "5m"
        }
      },
      "timestamp": "2025-07-01T10:30:00Z"
    }
    ```

### 6.4 資源：告警管理

#### 6.4.1 `GET /alerts/rules`
*   **描述:** 獲取所有告警規則配置
*   **認證/授權:** 需要 API Key (read 權限)
*   **成功回應 (200 OK):**
    ```json
    {
      "success": true,
      "data": [
        {
          "id": "rule_001",
          "name": "High P95 Latency Alert",
          "service_name": "model-prediction-api",
          "metric": "p95_latency_ms",
          "threshold": 500,
          "operator": "greater_than",
          "enabled": true,
          "created_at": "2025-07-01T08:00:00Z"
        }
      ],
      "timestamp": "2025-07-01T10:30:00Z"
    }
    ```

#### 6.4.2 `POST /alerts/rules`
*   **描述:** 創建新的告警規則
*   **認證/授權:** 需要 API Key (config 權限)
*   **請求體:**
    ```json
    {
      "name": "High Error Rate Alert",
      "service_name": "model-prediction-api",
      "metric": "error_rate",
      "threshold": 0.05,
      "operator": "greater_than",
      "enabled": true
    }
    ```
*   **成功回應 (201 Created):** 返回創建的告警規則，包含 `id`

#### 6.4.3 `GET /alerts/active`
*   **描述:** 獲取當前激活的告警
*   **認證/授權:** 需要 API Key (read 權限)
*   **成功回應 (200 OK):**
    ```json
    {
      "success": true,
      "data": [
        {
          "id": "alert_12345",
          "rule_id": "rule_001",
          "service_name": "model-prediction-api",
          "metric": "p95_latency_ms",
          "current_value": 650.5,
          "threshold": 500,
          "severity": "warning",
          "started_at": "2025-07-01T10:25:00Z",
          "message": "P95 延遲超過 500ms 閾值"
        }
      ],
      "timestamp": "2025-07-01T10:30:00Z"
    }
    ```

### 6.5 資源：服務管理

#### 6.5.1 `GET /services`
*   **描述:** 獲取所有受監控的服務列表
*   **認證/授權:** 需要 API Key (read 權限)
*   **成功回應 (200 OK):**
    ```json
    {
      "success": true,
      "data": [
        {
          "service_name": "model-prediction-api",
          "display_name": "模型預測 API",
          "endpoints": ["/predict", "/health"],
          "status": "active",
          "last_seen": "2025-07-01T10:30:00Z",
          "monitoring_enabled": true
        }
      ],
      "timestamp": "2025-07-01T10:30:00Z"
    }
    ```

### 6.6 WebSocket 端點

#### 6.6.1 `WS /ws/real-time`
*   **描述:** WebSocket 連接，用於即時推送監控數據更新
*   **認證:** 透過查詢參數 `api_key` 認證
*   **連接 URL:** `ws://localhost:8000/v1/ws/real-time?api_key=<api_key>&service_name=<optional>`
*   **訊息格式:**
    ```json
    // 伺服器推送的即時數據
    {
      "type": "metrics_update",
      "data": {
        "service_name": "model-prediction-api",
        "qps": 47.1,
        "avg_latency_ms": 125.3,
        "p95_latency_ms": 260.0,
        "error_rate": 0.018
      },
      "timestamp": "2025-07-01T10:30:05Z"
    }
    
    // 告警通知
    {
      "type": "alert_triggered",
      "data": {
        "alert_id": "alert_12346",
        "service_name": "model-prediction-api",
        "metric": "error_rate",
        "current_value": 0.08,
        "threshold": 0.05,
        "severity": "critical"
      },
      "timestamp": "2025-07-01T10:30:05Z"
    }
    ```

---

## 7. 資料模型/Schema 定義 (Data Models / Schema Definitions)

### 7.1 `RealTimeMetrics` Schema
```json
{
  "service_name": "string (required, max_length: 100)",
  "api_endpoint": "string (required, max_length: 200)",
  "qps": "number (float, >= 0)",
  "avg_latency_ms": "number (float, >= 0)",
  "p95_latency_ms": "number (float, >= 0)",
  "p99_latency_ms": "number (float, >= 0)",
  "error_rate": "number (float, 0 <= value <= 1)",
  "total_requests": "integer (>= 0)",
  "status": "string (enum: ['healthy', 'warning', 'critical'])",
  "last_updated": "string (date-time, ISO 8601)"
}
```

### 7.2 `HistoricalMetrics` Schema
```json
{
  "timestamp": "string (date-time, ISO 8601, required)",
  "service_name": "string (required, max_length: 100)",
  "api_endpoint": "string (required, max_length: 200)",
  "qps": "number (float, >= 0)",
  "avg_latency_ms": "number (float, >= 0)",
  "p95_latency_ms": "number (float, >= 0)",
  "p99_latency_ms": "number (float, >= 0)",
  "error_rate": "number (float, 0 <= value <= 1)",
  "total_requests": "integer (>= 0)"
}
```

### 7.3 `AlertRule` Schema
```json
{
  "id": "string (optional for create, UUID format)",
  "name": "string (required, max_length: 200)",
  "service_name": "string (required, max_length: 100)",
  "metric": "string (required, enum: ['qps', 'avg_latency_ms', 'p95_latency_ms', 'p99_latency_ms', 'error_rate'])",
  "threshold": "number (required)",
  "operator": "string (required, enum: ['greater_than', 'less_than', 'equal_to'])",
  "enabled": "boolean (default: true)",
  "created_at": "string (date-time, ISO 8601, read-only)",
  "updated_at": "string (date-time, ISO 8601, read-only)"
}
```

### 7.4 `ActiveAlert` Schema  
```json
{
  "id": "string (UUID format)",
  "rule_id": "string (UUID format)",
  "service_name": "string (max_length: 100)",
  "metric": "string",
  "current_value": "number",
  "threshold": "number",
  "severity": "string (enum: ['info', 'warning', 'critical'])",
  "started_at": "string (date-time, ISO 8601)",
  "resolved_at": "string (date-time, ISO 8601, optional)",
  "message": "string (max_length: 500)"
}
```

### 7.5 `ServiceInfo` Schema
```json
{
  "service_name": "string (required, max_length: 100)",
  "display_name": "string (max_length: 200)",
  "endpoints": "array of strings",
  "status": "string (enum: ['active', 'inactive', 'unknown'])",
  "last_seen": "string (date-time, ISO 8601)",
  "monitoring_enabled": "boolean (default: true)"
}
```

---

## 8. 安全性考量 (Security Considerations)

*   **輸入驗證:** 所有 API 端點使用 Pydantic 模型進行嚴格的輸入驗證，防止 XSS 和注入攻擊
*   **API Key 管理:** 
    *   API Key 長度至少 32 字符，使用加密安全的隨機生成器
    *   支持 API Key 輪轉，舊 Key 有 7 天過渡期
    *   API Key 儲存使用 bcrypt 哈希
*   **敏感數據處理:** 
    *   錯誤回應不暴露內部系統詳情
    *   日誌記錄中遮罩 API Key 和敏感配置
*   **速率限制:** 防止 DoS 攻擊和資源濫用
*   **HTTPS 強制:** 生產環境強制使用 HTTPS，包括 WebSocket (WSS)
*   **CORS 配置:** 前端應用的域名白名單配置

---

## 9. 向後兼容性與棄用策略 (Backward Compatibility and Deprecation Policy)

*   **向後兼容性承諾:** API v1 版本承諾 1 年內保持向後兼容，允許增加新的可選欄位，但不會刪除或修改現有欄位型別
*   **API 版本棄用策略:**
    *   提前 6 個月通知棄用計劃
    *   通過 API 回應 Header `X-API-Deprecation-Warning` 和文檔通知
    *   提供遷移指南和工具
    *   棄用後的 API 返回 410 Gone 狀態碼
*   **重大變更處理:** 發布新的主版本 (v2)，並提供並行支持期

---

## 10. 附錄 (Appendices)

### 10.1 請求/回應範例 (Request/Response Examples)

#### 範例 1: 獲取即時指標
**請求:**
```bash
curl -H "X-API-Key: your-api-key-here" \
     "http://localhost:8000/v1/metrics/real-time?service_name=model-prediction-api"
```

**成功回應 (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "service_name": "model-prediction-api",
      "api_endpoint": "/predict",
      "qps": 45.2,
      "avg_latency_ms": 120.5,
      "p95_latency_ms": 250.0,
      "p99_latency_ms": 380.0,
      "error_rate": 0.02,
      "total_requests": 2710,
      "status": "healthy",
      "last_updated": "2025-07-01T10:30:00Z"
    }
  ],
  "meta": {
    "total_services": 1,
    "healthy_services": 1,
    "data_freshness_seconds": 3
  },
  "timestamp": "2025-07-01T10:30:00Z"
}
```

#### 範例 2: 查詢歷史數據
**請求:**
```bash
curl -H "X-API-Key: your-api-key-here" \
     "http://localhost:8000/v1/metrics/historical?start_time=2025-07-01T09:00:00Z&end_time=2025-07-01T10:00:00Z&service_name=model-prediction-api&limit=10"
```

#### 範例 3: WebSocket 連接
**JavaScript 客戶端:**
```javascript
const ws = new WebSocket('ws://localhost:8000/v1/ws/real-time?api_key=your-api-key-here');

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    if (message.type === 'metrics_update') {
        updateDashboard(message.data);
    } else if (message.type === 'alert_triggered') {
        showAlert(message.data);
    }
};
```

#### 範例 4: 創建告警規則
**請求:**
```bash
curl -X POST \
     -H "X-API-Key: your-api-key-here" \
     -H "Content-Type: application/json" \
     -d '{"name":"High Latency Alert","service_name":"model-prediction-api","metric":"p95_latency_ms","threshold":500,"operator":"greater_than","enabled":true}' \
     "http://localhost:8000/v1/alerts/rules"
```

**成功回應 (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "rule_abc123",
    "name": "High Latency Alert",
    "service_name": "model-prediction-api",
    "metric": "p95_latency_ms",
    "threshold": 500,
    "operator": "greater_than",
    "enabled": true,
    "created_at": "2025-07-01T10:30:00Z",
    "updated_at": "2025-07-01T10:30:00Z"
  },
  "timestamp": "2025-07-01T10:30:00Z"
}
```

---

**文件審核記錄 (Review History):**

| 日期       | 審核人     | 版本 | 變更摘要/主要反饋 |
| :--------- | :--------- | :--- | :---------------- |
| 2025-07-01 | Vibe Coder | v1.0 | 初稿建立，涵蓋完整 API 規範 | 