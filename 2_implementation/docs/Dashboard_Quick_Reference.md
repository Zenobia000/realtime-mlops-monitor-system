# 📊 Model API 監控儀表板 - 快速參考表

## 🎯 Wireframe 組件對應表

| Wireframe 組件 | Grafana 類型 | 查詢語法重點 | 單位 | 閾值/配置 |
|---------------|-------------|-------------|-----|----------|
| **📈 總 QPS** | `stat` | `AVG(qps)` from `overall` | `reqps` | 綠<80, 黃80-100, 紅>100 |
| **⏱️ 平均延遲** | `stat` | `AVG(avg_response_time)` | `ms` | 綠<50, 黃50-100, 紅>100 |
| **🚨 錯誤率** | `stat` | `AVG(error_rate)` | `percent` | 綠<1, 黃1-5, 紅>5 |
| **📊 總請求量** | `stat` | `SUM(total_requests)` | `short` | 無閾值 |
| **📈 QPS & 請求量趨勢** | `timeseries` | 雙軸: QPS + requests | `reqps` + `short` | 左軸QPS, 右軸請求量 |
| **⏱️ 響應時間分位數** | `timeseries` | avg + p95 + p99 | `ms` | 多線圖 |
| **🚨 錯誤率監控** | `timeseries` | 按服務分組 | `percent` | 閾值線 1%, 5% |
| **🔥 服務性能熱圖** | `heatmap` | 5分鐘桶 + 服務 | `ms` | Oranges 色彩 |
| **📋 Top 異常端點** | `table` | 按錯誤率排序 | `percent`, `ms` | 背景色彩 |
| **📊 服務對比矩陣** | `barchart` | 分組條形圖 | `reqps`, `ms`, `percent` | 分組顯示 |
| **📈 端點性能排行** | `table` | 按QPS排序 | `reqps`, `ms` | 漸變條形 |

---

## 🕒 時間篩選器標準配置

```json
{
  "time": {"from": "now-1h", "to": "now"},
  "refresh": "30s",
  "timepicker": {
    "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"],
    "time_options": ["5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"]
  }
}
```

---

## 📏 標準查詢模板

### 1. 統計面板查詢
```sql
-- 模板
SELECT time_bucket_gapfill('1m', timestamp) as time, 
       {聚合函數}({指標欄位}) as value 
FROM metrics_aggregated 
WHERE metric_type = '{類型}' 
  AND timestamp >= $__timeFrom() 
  AND timestamp <= $__timeTo() 
GROUP BY time ORDER BY time

-- 實例
SELECT time_bucket_gapfill('1m', timestamp) as time, 
       AVG(qps) as value 
FROM metrics_aggregated 
WHERE metric_type = 'overall' 
  AND timestamp >= $__timeFrom() 
  AND timestamp <= $__timeTo() 
GROUP BY time ORDER BY time
```

### 2. 時間序列查詢
```sql
-- 單一指標
SELECT time_bucket_gapfill('30s', timestamp) as time, 
       AVG({指標欄位}) as {別名}
FROM metrics_aggregated 
WHERE metric_type = '{類型}' 
  AND timestamp >= $__timeFrom() 
  AND timestamp <= $__timeTo() 
GROUP BY time ORDER BY time

-- 分組指標
SELECT time_bucket_gapfill('30s', timestamp) as time, 
       service_name, 
       AVG({指標欄位}) as {別名}
FROM metrics_aggregated 
WHERE metric_type = 'service' 
  AND service_name IS NOT NULL 
  AND timestamp >= $__timeFrom() 
  AND timestamp <= $__timeTo() 
GROUP BY time, service_name ORDER BY time
```

### 3. 表格查詢
```sql
-- 聚合表格
SELECT service_name as "服務名稱",
       endpoint as "端點",
       AVG({指標1}) as "{顯示名稱1}",
       AVG({指標2}) as "{顯示名稱2}",
       SUM({指標3}) as "{顯示名稱3}"
FROM metrics_aggregated 
WHERE metric_type = 'endpoint' 
  AND timestamp >= $__timeFrom() 
  AND timestamp <= $__timeTo() 
GROUP BY service_name, endpoint 
ORDER BY AVG({排序欄位}) DESC 
LIMIT {限制數量}
```

---

## 🎨 單位與格式配置

### Grafana 標準單位

| 指標類型 | 單位代碼 | 顯示格式 | 範例 |
|----------|----------|----------|------|
| **QPS/頻率** | `reqps` | requests/sec | 125.5 req/s |
| **時間** | `ms` | milliseconds | 45.2 ms |
| **百分比** | `percent` | % | 2.5% |
| **數量** | `short` | 自動縮放 | 1.2K, 3.4M |
| **位元組** | `bytes` | 自動縮放 | 1.5 KB, 2.3 MB |
| **無單位** | `none` | 純數字 | 1234 |

### 顏色閾值配置

```json
{
  "thresholds": {
    "mode": "absolute",
    "steps": [
      {"color": "green", "value": null},    // 預設綠色
      {"color": "yellow", "value": 80},     // 警告黃色
      {"color": "red", "value": 100}        // 危險紅色
    ]
  }
}
```

---

## 🔧 常用配置片段

### 變數定義
```json
{
  "name": "service",
  "label": "服務",
  "query": "SELECT DISTINCT service_name FROM metrics_aggregated WHERE service_name IS NOT NULL",
  "multi": true,
  "includeAll": true,
  "refresh": 1
}
```

### 圖例格式
```json
{
  "legendFormat": "{{service_name}}",     // 服務名稱
  "legendFormat": "{{service_name}}:{{endpoint}}", // 服務:端點
  "legendFormat": "平均響應時間"            // 固定名稱
}
```

### 軸配置
```json
{
  "custom": {
    "axisPlacement": "left",     // 左軸
    "axisPlacement": "right",    // 右軸
    "axisPlacement": "auto"      // 自動
  }
}
```

---

## 📋 資料庫表結構快查

### metrics_aggregated 主要欄位

| 欄位名 | 類型 | 說明 | 使用場景 |
|--------|------|------|----------|
| `timestamp` | timestamp | 記錄時間 | 時間篩選 |
| `metric_type` | varchar | 指標類型 | overall/service/endpoint |
| `service_name` | varchar | 服務名稱 | test-model-api-v1.0 |
| `endpoint` | varchar | API端點 | /predict |
| `qps` | numeric | 每秒請求數 | QPS統計 |
| `avg_response_time` | numeric | 平均響應時間 | 延遲分析 |
| `p95_response_time` | numeric | P95響應時間 | 性能分析 |
| `p99_response_time` | numeric | P99響應時間 | 性能分析 |
| `error_rate` | numeric | 錯誤率(%) | 錯誤監控 |
| `total_requests` | integer | 總請求數 | 流量統計 |
| `total_errors` | integer | 總錯誤數 | 錯誤統計 |

### 常用過濾條件

```sql
-- 按指標類型過濾
WHERE metric_type = 'overall'     -- 總體指標
WHERE metric_type = 'service'     -- 服務級指標
WHERE metric_type = 'endpoint'    -- 端點級指標

-- 按時間過濾
WHERE timestamp >= $__timeFrom() AND timestamp <= $__timeTo()

-- 按服務過濾
WHERE service_name IS NOT NULL
WHERE service_name LIKE 'test-model-api%'
WHERE service_name = 'test-model-api-v1.0'

-- 按端點過濾
WHERE endpoint IS NOT NULL
WHERE endpoint = '/predict'
```

---

## 🚀 快速部署指令

### 1. 驗證資料庫連接
```bash
docker exec platform-timescaledb psql -U admin -d platform_db -c "SELECT COUNT(*) FROM metrics_aggregated;"
```

### 2. 測試查詢語法
```bash
docker exec platform-timescaledb psql -U admin -d platform_db -c "
SELECT time_bucket_gapfill('1m', timestamp) as time, 
       AVG(qps) as qps 
FROM metrics_aggregated 
WHERE metric_type = 'overall' 
  AND timestamp >= NOW() - INTERVAL '1 hour' 
GROUP BY time 
ORDER BY time LIMIT 5;"
```

### 3. 檢查服務狀態
```bash
curl -s http://localhost:8002/health | jq '.'
```

---

## 📞 常見問題排查

### Q: 圖表顯示空白
**A:** 檢查時間範圍和資料可用性
```sql
SELECT MIN(timestamp), MAX(timestamp), COUNT(*) 
FROM metrics_aggregated;
```

### Q: 單位顯示錯誤
**A:** 確認欄位配置單位設定
```json
{"unit": "ms", "decimals": 1}
```

### Q: 閾值不觸發
**A:** 檢查閾值數值和資料範圍
```sql
SELECT AVG(qps), MIN(qps), MAX(qps) 
FROM metrics_aggregated 
WHERE metric_type = 'overall';
```

---

**📄 完整文檔**: [Grafana_Dashboard_Configuration.md](./Grafana_Dashboard_Configuration.md) 