-- Model API 監控系統資料庫初始化腳本
-- 創建時間: 2025-07-01
-- 版本: v1.0

-- 啟用 TimescaleDB 擴展
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 創建聚合指標表 (基於詳細設計文檔)
CREATE TABLE IF NOT EXISTS metrics_aggregated (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    api_endpoint VARCHAR(200) NOT NULL,
    qps DECIMAL(10,2) NOT NULL DEFAULT 0,
    avg_latency_ms DECIMAL(10,2) NOT NULL DEFAULT 0,
    p95_latency_ms DECIMAL(10,2) NOT NULL DEFAULT 0,
    p99_latency_ms DECIMAL(10,2) NOT NULL DEFAULT 0,
    error_rate DECIMAL(5,4) NOT NULL DEFAULT 0,
    total_requests INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 將表轉換為時間序列表 (TimescaleDB)
SELECT create_hypertable('metrics_aggregated', 'timestamp', if_not_exists => TRUE);

-- 創建索引以優化查詢性能
CREATE INDEX IF NOT EXISTS idx_metrics_service_time 
ON metrics_aggregated (service_name, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_endpoint_time 
ON metrics_aggregated (api_endpoint, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_created_at 
ON metrics_aggregated (created_at DESC);

-- 創建告警規則表
CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    metric VARCHAR(50) NOT NULL,
    threshold DECIMAL(10,2) NOT NULL,
    operator VARCHAR(20) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 創建激活告警表
CREATE TABLE IF NOT EXISTS active_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES alert_rules(id),
    service_name VARCHAR(100) NOT NULL,
    metric VARCHAR(50) NOT NULL,
    current_value DECIMAL(10,2) NOT NULL,
    threshold DECIMAL(10,2) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ NULL,
    message TEXT NOT NULL
);

-- 創建服務資訊表
CREATE TABLE IF NOT EXISTS service_info (
    service_name VARCHAR(100) PRIMARY KEY,
    display_name VARCHAR(200),
    endpoints TEXT[], -- PostgreSQL 陣列型別
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    monitoring_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 插入測試數據 (可選，開發環境用)
INSERT INTO service_info (service_name, display_name, endpoints, status) 
VALUES 
    ('model-prediction-api', '模型預測 API', ARRAY['/predict', '/health'], 'active'),
    ('model-training-api', '模型訓練 API', ARRAY['/train', '/status'], 'active')
ON CONFLICT (service_name) DO NOTHING;

-- 插入測試告警規則
INSERT INTO alert_rules (name, service_name, metric, threshold, operator) 
VALUES 
    ('High P95 Latency Alert', 'model-prediction-api', 'p95_latency_ms', 500, 'greater_than'),
    ('High Error Rate Alert', 'model-prediction-api', 'error_rate', 0.05, 'greater_than'),
    ('Low QPS Alert', 'model-prediction-api', 'qps', 1, 'less_than')
ON CONFLICT DO NOTHING;

-- 創建數據保留策略 (保留30天的詳細數據)
SELECT add_retention_policy('metrics_aggregated', INTERVAL '30 days', if_not_exists => TRUE);

-- 創建數據壓縮策略 (7天後壓縮)
ALTER TABLE metrics_aggregated SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'service_name',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('metrics_aggregated', INTERVAL '7 days', if_not_exists => TRUE);

-- 打印初始化完成訊息
DO $$
BEGIN
    RAISE NOTICE '✅ Model API 監控系統資料庫初始化完成';
    RAISE NOTICE '📊 已建立 metrics_aggregated 時間序列表';
    RAISE NOTICE '🚨 已建立告警相關表結構';
    RAISE NOTICE '🔧 已設置索引和 TimescaleDB 優化策略';
END $$; 