# 系統詳細設計文檔 (System Design Document) - 指標處理服務

---

**文件版本 (Document Version):** `v0.1`

**最後更新 (Last Updated):** `2025-07-01`

**主要作者/設計師 (Lead Author/Designer):** `Vibe Coder`

**審核者 (Reviewers):** `MLOps Team, Backend Team`

**狀態 (Status):** `草稿 (Draft)`

**相關系統架構文檔 (SA Document):** `[docs/System_Architecture_Document.md](./System_Architecture_Document.md)`

**相關 User Stories/Features:** `US-002: 收集 API 性能指標, US-003: 監控容器資源使用, US-004: 設定基本告警`

**相關 ADRs (若適用):** `[待定]`

---

## 目錄 (Table of Contents)

1.  [引言 (Introduction)](#1-引言-introduction)
2.  [模組概述 (Module Overview)](#2-模組概述-module-overview)
3.  [詳細設計 (Detailed Design)](#3-詳細設計-detailed-design)
4.  [設計考量 (Design Considerations)](#4-設計考量-design-considerations)
5.  [未來展望 (Future Considerations)](#5-未來展望-future-considerations)

---

## 1. 引言 (Introduction)

### 1.1 目的 (Purpose)
*   為「指標處理服務 (Metrics Processing Service)」提供具體的實現細節和規格，指導開發和測試工作。該服務是 Model API 監控系統的核心數據處理組件。

### 1.2 範圍 (Scope)
*   本文檔涵蓋指標處理服務的內部結構、數據模型、核心算法、API 設計和錯誤處理機制。範圍包括從 RabbitMQ 消費事件、數據聚合計算、寫入 PostgreSQL 和 Redis 的完整流程。

### 1.3 術語表 (Glossary)

| 術語/縮寫 | 完整名稱/解釋 |
| :------- | :----------- |
| MPS      | Metrics Processing Service，指標處理服務。 |
| Consumer | 訊息佇列的消費者，負責從 RabbitMQ 讀取事件。 |
| Aggregator | 聚合器，負責將原始指標數據聚合成統計指標。 |
| Sliding Window | 滑動視窗，用於計算時間窗口內的統計指標。 |

### 1.4 參考文件 (References)
*   [系統架構文檔: docs/System_Architecture_Document.md]
*   [專案簡報: docs/Model_API_Monitoring_Brief.md]
*   [RabbitMQ Python Client (Pika) 文檔]
*   [PostgreSQL TimescaleDB 文檔]

---

## 2. 模組概述 (Module Overview)

### 2.1 功能描述 (Functional Description)
*   **核心職責:** 指標處理服務是監控系統的數據處理中心，負責：
    *   從 RabbitMQ 消費 Model API 的性能指標事件 (延遲、狀態碼、時間戳)
    *   執行即時數據聚合計算 (QPS、平均延遲、錯誤率、P95 延遲等)
    *   將聚合後的指標數據持久化到 PostgreSQL (歷史數據) 和 Redis (即時數據)
    *   檢測異常指標並觸發告警

### 2.2 與系統其他部分的關係 (Relationship to Other System Parts)
*   **輸入 (Inputs):** 
    *   從 RabbitMQ `metrics.api_requests` 佇列接收 JSON 格式的指標事件
    *   事件格式: `{timestamp, api_endpoint, response_time_ms, status_code, service_name}`
*   **輸出 (Outputs):** 
    *   向 PostgreSQL `metrics_aggregated` 表寫入聚合後的歷史數據
    *   向 Redis 寫入即時指標數據 (Key-Value 格式)
    *   向 RabbitMQ `alerts.notifications` 佇列發送告警事件
*   **依賴 (Dependencies):** 
    *   RabbitMQ (訊息佇列)
    *   PostgreSQL with TimescaleDB (時間序列數據庫)
    *   Redis (快取數據庫)

---

## 3. 詳細設計 (Detailed Design)

### 3.1 模組結構與組件設計 (Module Structure and Component Design)

#### 3.1.1 類別圖/組件圖 (Class/Component Diagrams)
```mermaid
classDiagram
    class MetricsProcessor {
        -consumer: EventConsumer
        -aggregator: MetricsAggregator
        -storage: StorageManager
        -alert_manager: AlertManager
        +start()
        +stop()
        +process_event(event: MetricEvent)
    }
    
    class EventConsumer {
        -connection: RabbitMQConnection
        -queue_name: str
        +connect()
        +consume_events(callback: function)
        +ack_message(delivery_tag)
    }
    
    class MetricsAggregator {
        -sliding_windows: Dict[str, SlidingWindow]
        +aggregate_qps(events: List[MetricEvent]): float
        +aggregate_latency(events: List[MetricEvent]): LatencyStats
        +aggregate_error_rate(events: List[MetricEvent]): float
        +get_real_time_metrics(): Dict
    }
    
    class StorageManager {
        -postgres_client: PostgreSQLClient
        -redis_client: RedisClient
        +save_historical_metrics(metrics: AggregatedMetrics)
        +update_real_time_cache(metrics: Dict)
        +get_latest_metrics(): Dict
    }
    
    class AlertManager {
        -thresholds: AlertThresholds
        -publisher: RabbitMQPublisher
        +check_thresholds(metrics: AggregatedMetrics): List[Alert]
        +send_alert(alert: Alert)
    }
    
    class MetricEvent {
        +timestamp: datetime
        +api_endpoint: str
        +response_time_ms: int
        +status_code: int
        +service_name: str
    }
    
    class AggregatedMetrics {
        +timestamp: datetime
        +service_name: str
        +qps: float
        +avg_latency_ms: float
        +p95_latency_ms: float
        +error_rate: float
    }
    
    MetricsProcessor --> EventConsumer
    MetricsProcessor --> MetricsAggregator
    MetricsProcessor --> StorageManager
    MetricsProcessor --> AlertManager
    MetricsAggregator --> MetricEvent
    StorageManager --> AggregatedMetrics
    AlertManager --> AggregatedMetrics
```

#### 3.1.2 主要類別/介面詳述 (Key Classes Details)

*   **`MetricsProcessor`** (主控制器)
    *   **職責:** 協調整個指標處理流程，管理組件生命週期
    *   **主要方法:**
        *   `start() -> None`: 啟動消費者並開始處理事件
        *   `stop() -> None`: 優雅停止服務
        *   `process_event(event: MetricEvent) -> None`: 處理單個指標事件的核心方法

*   **`EventConsumer`** (事件消費者)
    *   **職責:** 負責從 RabbitMQ 佇列消費指標事件
    *   **主要方法:**
        *   `connect() -> None`: 建立與 RabbitMQ 的連接
        *   `consume_events(callback: function) -> None`: 開始消費事件並調用回調函數
        *   `ack_message(delivery_tag) -> None`: 確認訊息處理完成

*   **`MetricsAggregator`** (指標聚合器)
    *   **職責:** 執行指標的實時聚合計算
    *   **主要屬性:** `sliding_windows: Dict[str, SlidingWindow]` - 為不同服務維護滑動視窗
    *   **主要方法:**
        *   `aggregate_qps(events: List[MetricEvent]) -> float`: 計算每秒查詢數
        *   `aggregate_latency(events: List[MetricEvent]) -> LatencyStats`: 計算延遲統計 (平均值、P95、P99)
        *   `aggregate_error_rate(events: List[MetricEvent]) -> float`: 計算錯誤率

*   **`StorageManager`** (存儲管理器)
    *   **職責:** 管理數據的持久化和快取
    *   **主要方法:**
        *   `save_historical_metrics(metrics: AggregatedMetrics) -> None`: 保存聚合指標到 PostgreSQL
        *   `update_real_time_cache(metrics: Dict) -> None`: 更新 Redis 中的實時數據

### 3.2 資料庫設計 (Data Model / Database Design)

#### 3.2.1 資料庫表結構/Schema

**表名: `metrics_aggregated`** (PostgreSQL + TimescaleDB)

| 欄位名稱 | 資料型別 | 約束 | 描述 |
| :------- | :------- | :--- | :--- |
| `id` | `SERIAL` | `PRIMARY KEY` | 主鍵 |
| `timestamp` | `TIMESTAMPTZ` | `NOT NULL` | 聚合時間戳 (時間序列主鍵) |
| `service_name` | `VARCHAR(100)` | `NOT NULL` | 服務名稱 |
| `api_endpoint` | `VARCHAR(200)` | `NOT NULL` | API 端點 |
| `qps` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0` | 每秒查詢數 |
| `avg_latency_ms` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0` | 平均延遲 (毫秒) |
| `p95_latency_ms` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0` | P95 延遲 (毫秒) |
| `p99_latency_ms` | `DECIMAL(10,2)` | `NOT NULL DEFAULT 0` | P99 延遲 (毫秒) |
| `error_rate` | `DECIMAL(5,4)` | `NOT NULL DEFAULT 0` | 錯誤率 (0-1) |
| `total_requests` | `INTEGER` | `NOT NULL DEFAULT 0` | 總請求數 |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT NOW()` | 記錄創建時間 |

*   **索引:** 
    *   Primary Index: `(timestamp, service_name)` (TimescaleDB 時間分區)
    *   Secondary Index: `(service_name, api_endpoint, timestamp)`

**Redis 快取結構:**
```
Key: "real_time_metrics:{service_name}"
Value: JSON {
  "qps": 45.2,
  "avg_latency_ms": 120.5,
  "p95_latency_ms": 250.0,
  "error_rate": 0.02,
  "last_updated": "2025-07-01T10:30:00Z"
}
TTL: 300 seconds (5 minutes)
```

### 3.3 核心演算法/邏輯流程 (Core Algorithms / Logic Flow)

#### 3.3.1 主要業務流程圖 (Key Business Process Flows)
```mermaid
graph TD
    Start([開始處理事件]) --> ReceiveEvent[從 RabbitMQ 接收事件]
    ReceiveEvent --> ValidateEvent{驗證事件格式}
    ValidateEvent -- 有效 --> AddToWindow[加入滑動視窗]
    ValidateEvent -- 無效 --> LogError[記錄錯誤] --> AckMessage[確認訊息]
    
    AddToWindow --> CheckWindowReady{視窗是否就緒?}
    CheckWindowReady -- 是 --> AggregateMet[聚合指標計算]
    CheckWindowReady -- 否 --> AckMessage
    
    AggregateMet --> SavePostgres[保存至 PostgreSQL]
    SavePostgres --> UpdateRedis[更新 Redis 快取]
    UpdateRedis --> CheckAlerts{檢查告警閾值}
    
    CheckAlerts -- 超過閾值 --> SendAlert[發送告警]
    CheckAlerts -- 正常 --> AckMessage
    SendAlert --> AckMessage
    
    AckMessage --> End([處理完成])
    LogError --> End
```

#### 3.3.2 滑動視窗算法 (Sliding Window Algorithm)
*   **設計目標:** 計算過去 1 分鐘內的即時指標
*   **視窗大小:** 60 秒，分割為 12 個 5 秒的子視窗
*   **更新策略:** 每 5 秒觸發一次聚合計算

```python
# 偽代碼示例
class SlidingWindow:
    def __init__(self, window_size_seconds=60, bucket_size_seconds=5):
        self.buckets = deque(maxlen=window_size_seconds // bucket_size_seconds)
        self.current_bucket = MetricsBucket()
        
    def add_event(self, event: MetricEvent):
        # 檢查是否需要輪轉 bucket
        if self.should_rotate_bucket(event.timestamp):
            self.buckets.append(self.current_bucket)
            self.current_bucket = MetricsBucket()
        
        self.current_bucket.add_event(event)
    
    def calculate_qps(self) -> float:
        total_requests = sum(bucket.request_count for bucket in self.buckets)
        return total_requests / 60.0  # 每秒查詢數
```

### 3.4 錯誤處理與例外機制 (Error Handling and Exception Strategy)

*   **主要例外類型:**
    *   `InvalidMetricEventError`: 事件格式不正確
    *   `DatabaseConnectionError`: 資料庫連接失敗
    *   `RabbitMQConnectionError`: 訊息佇列連接失敗
    *   `AggregationError`: 指標聚合計算失敗

*   **錯誤處理策略:**
    *   **重試機制:** 對於暫時性錯誤 (網路、資料庫連接)，實施指數退避重試，最多重試 3 次
    *   **死信佇列:** 無法處理的事件轉送至 `metrics.dlq` 死信佇列
    *   **降級處理:** PostgreSQL 寫入失敗時，仍然更新 Redis 快取，確保即時監控不中斷

*   **錯誤日誌記錄:**
```json
{
  "timestamp": "2025-07-01T10:30:00Z",
  "level": "ERROR",
  "service": "metrics-processor",
  "error_type": "DatabaseConnectionError",
  "message": "Failed to connect to PostgreSQL",
  "event_id": "evt_12345",
  "retry_count": 2
}
```

### 3.5 配置管理 (Configuration)

| 配置項 | 描述 | 型別 | 預設值 | 環境變數名 |
| :--- | :--- | :--- | :--- | :--- |
| `RABBITMQ_URL` | RabbitMQ 連接字串 | `String` | `amqp://guest:guest@localhost:5672/` | `MPS_RABBITMQ_URL` |
| `POSTGRES_URL` | PostgreSQL 連接字串 | `String` | `postgresql://user:pass@localhost:5432/db` | `MPS_POSTGRES_URL` |
| `REDIS_URL` | Redis 連接字串 | `String` | `redis://localhost:6379` | `MPS_REDIS_URL` |
| `WINDOW_SIZE_SECONDS` | 滑動視窗大小 | `Integer` | `60` | `MPS_WINDOW_SIZE` |
| `AGGREGATION_INTERVAL` | 聚合間隔 (秒) | `Integer` | `5` | `MPS_AGG_INTERVAL` |
| `P95_LATENCY_THRESHOLD` | P95延遲告警閾值 (ms) | `Integer` | `500` | `MPS_P95_THRESHOLD` |
| `ERROR_RATE_THRESHOLD` | 錯誤率告警閾值 | `Float` | `0.05` | `MPS_ERROR_THRESHOLD` |

---

## 4. 設計考量 (Design Considerations)

### 4.1 安全性 (Security)
*   **輸入驗證:** 對所有接收的事件進行嚴格的 JSON Schema 驗證
*   **資料庫安全:** 使用參數化查詢防止 SQL 注入，敏感配置通過環境變數注入
*   **網路安全:** 所有數據庫連接使用 TLS 加密

### 4.2 性能 (Performance)
*   **目標指標:** 每秒處理 1000+ 事件，單事件處理延遲 < 10ms
*   **優化策略:**
    *   批量寫入 PostgreSQL (每 5 秒或累積 100 條記錄)
    *   Redis Pipeline 操作減少網路往返
    *   異步 I/O 處理數據庫操作
    *   內存中維護滑動視窗，減少計算開銷

### 4.3 可擴展性 (Scalability)
*   **水平擴展:** 設計為無狀態服務，可以部署多個實例並行消費同一佇列
*   **分區策略:** 可按 `service_name` 進行佇列分區，不同服務的指標由不同實例處理

### 4.4 可靠性與容錯 (Reliability & Fault Tolerance)
*   **訊息可靠性:** 使用 RabbitMQ 的 message acknowledgment 確保事件不丟失
*   **資料一致性:** PostgreSQL 寫入失敗時，記錄到本地日誌以便後續重放
*   **故障隔離:** Redis 故障不影響歷史數據寫入，PostgreSQL 故障不影響即時監控

### 4.5 可測試性 (Testability)
*   **依賴注入:** 所有外部依賴 (資料庫、訊息佇列) 通過介面注入，方便 Mock
*   **單元測試:** 每個聚合算法都有獨立的單元測試
*   **整合測試:** 使用 TestContainers 進行完整的端到端測試

### 4.6 可維護性 (Maintainability)
*   **結構化日誌:** 使用 JSON 格式的結構化日誌，包含 trace_id 便於問題追蹤
*   **健康檢查:** 提供 `/health` 端點檢查各依賴服務狀態
*   **指標監控:** 為服務本身暴露 Prometheus 指標 (處理速度、錯誤率等)

### 4.7 部署考量 (Deployment)
*   **容器化:** 服務打包為 Docker 鏡像，支援 12-factor app 原則
*   **資源需求:** CPU: 0.5 核心，記憶體: 512MB，適合在 Kubernetes 中部署
*   **優雅停機:** 接收 SIGTERM 信號時，完成正在處理的事件後再停止

---

## 5. 未來展望 (Future Considerations)

*   **自適應視窗:** 根據流量動態調整滑動視窗大小和聚合間隔
*   **異常檢測:** 引入機器學習算法進行異常檢測，不僅僅依賴固定閾值
*   **多級聚合:** 支援多個時間粒度的聚合 (1分鐘、5分鐘、1小時)
*   **流處理引擎:** 考慮使用 Apache Kafka + Kafka Streams 替代 RabbitMQ 以獲得更好的流處理能力

---
**文件審核記錄 (Review History):**

| 日期       | 審核人     | 版本 | 變更摘要/主要反饋 |
| :--------- | :--------- | :--- | :---------------- |
| 2025-07-01 | Vibe Coder | v0.1 | 初稿建立           | 