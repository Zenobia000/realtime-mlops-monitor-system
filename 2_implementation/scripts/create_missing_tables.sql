-- 建立缺失的監控系統表格
-- 適配現有 PostgreSQL 數據庫結構
-- 創建時間: 2025-07-01

-- 建立告警規則表 (alert_rules)
CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    metric VARCHAR(50) NOT NULL,
    threshold DECIMAL(10,2) NOT NULL,
    operator VARCHAR(20) NOT NULL CHECK (operator IN ('>', '<', '>=', '<=', '=')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 建立服務信息表 (service_info)
CREATE TABLE IF NOT EXISTS service_info (
    service_name VARCHAR(100) PRIMARY KEY,
    display_name VARCHAR(200),
    endpoints TEXT[], -- PostgreSQL 陣列型別
    status VARCHAR(20) NOT NULL DEFAULT 'unknown' CHECK (status IN ('active', 'inactive', 'unknown', 'degraded')),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    monitoring_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 創建索引以優化查詢性能
CREATE INDEX IF NOT EXISTS idx_alert_rules_service 
ON alert_rules (service_name, enabled);

CREATE INDEX IF NOT EXISTS idx_alert_rules_metric 
ON alert_rules (metric, enabled);

CREATE INDEX IF NOT EXISTS idx_service_info_status 
ON service_info (status, last_seen DESC);

-- 添加外鍵約束到現有 alerts 表 (如果需要的話)
-- ALTER TABLE alerts ADD COLUMN rule_id UUID REFERENCES alert_rules(id);

-- 插入測試數據
INSERT INTO service_info (service_name, display_name, endpoints, status) 
VALUES 
    ('model-prediction-api', '模型預測 API', ARRAY['/predict', '/health'], 'active'),
    ('model-training-api', '模型訓練 API', ARRAY['/train', '/status'], 'active'),
    ('test-model-api', '測試模型 API', ARRAY['/predict', '/health', '/models'], 'active')
ON CONFLICT (service_name) DO NOTHING;

-- 插入預設告警規則
INSERT INTO alert_rules (name, service_name, metric, threshold, operator, enabled) 
VALUES 
    ('High P95 Latency Alert', 'model-prediction-api', 'p95_response_time', 500.00, '>', TRUE),
    ('High Error Rate Alert', 'model-prediction-api', 'error_rate', 5.00, '>', TRUE),
    ('Low QPS Alert', 'model-prediction-api', 'qps', 1.00, '<', TRUE),
    ('Critical P99 Latency Alert', 'model-prediction-api', 'p99_response_time', 1000.00, '>', TRUE),
    ('Service Offline Alert', 'model-prediction-api', 'qps', 0.10, '<', TRUE)
ON CONFLICT DO NOTHING;

-- 顯示建立結果
DO $$
BEGIN
    RAISE NOTICE '✅ 已建立缺失的監控系統表格';
    RAISE NOTICE '📋 alert_rules: 告警規則配置表';
    RAISE NOTICE '🏢 service_info: 服務信息管理表';
    RAISE NOTICE '🔧 已設置相關索引和約束';
    RAISE NOTICE '📊 已插入測試數據';
END $$;

-- 驗證表格建立
SELECT 'alert_rules' as table_name, count(*) as row_count FROM alert_rules
UNION ALL
SELECT 'service_info' as table_name, count(*) as row_count FROM service_info
UNION ALL  
SELECT 'alerts' as table_name, count(*) as row_count FROM alerts
UNION ALL
SELECT 'metrics_aggregated' as table_name, count(*) as row_count FROM metrics_aggregated; 