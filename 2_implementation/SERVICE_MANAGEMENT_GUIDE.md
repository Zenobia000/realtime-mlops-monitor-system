# 🚀 Model API 監控系統 - 服務管理指南

## 📋 概述

本指南介紹如何使用一鍵啟動腳本 `start_monitoring_services.sh` 管理 Model API 監控系統的所有服務。

## 🎯 腳本功能

### 主要命令
- `start` - 啟動所有監控服務
- `stop` - 停止所有監控服務  
- `restart` - 重啟所有監控服務
- `status` - 檢查服務健康狀態
- `logs` - 顯示服務日誌

## 🔧 使用方法

### 基本命令

```bash
# 啟動所有服務
./start_monitoring_services.sh start

# 檢查服務狀態
./start_monitoring_services.sh status

# 停止所有服務
./start_monitoring_services.sh stop

# 重啟所有服務
./start_monitoring_services.sh restart

# 查看服務日誌
./start_monitoring_services.sh logs
```

### 詳細操作流程

#### 1. 首次啟動
```bash
# 確保Docker服務運行
docker-compose up -d

# 啟動監控服務
./start_monitoring_services.sh start
```

#### 2. 日常監控
```bash
# 檢查服務狀態
./start_monitoring_services.sh status

# 查看實時日誌
./start_monitoring_services.sh logs
```

#### 3. 服務維護
```bash
# 重啟服務
./start_monitoring_services.sh restart

# 停止服務
./start_monitoring_services.sh stop
```

## 🏗️ 服務架構

### Docker 基礎服務
| 服務名稱 | 端口 | 用途 |
|----------|------|------|
| platform-timescaledb | 5433 | 時序數據庫 |
| platform-redis | 6380 | 快取服務 |
| platform-rabbitmq | 5672 | 訊息佇列 |
| platform-grafana | 3002 | 監控儀表板 |

### Python 監控服務
| 服務名稱 | 端口 | PID 文件 | 日誌文件 |
|----------|------|----------|----------|
| 指標處理服務 | - | metrics_processing.pid | metrics_processing.log |
| 監控 API 服務 | 8001 | monitoring_api.pid | monitoring_api.log |
| 測試模型 API | 8002 | test_model_api.pid | test_model_api.log |
| 特徵生成器 | - | feature_generator.pid | feature_generator.log |

## 📊 服務啟動順序

腳本按以下順序啟動服務，確保依賴關係：

```
1. 檢查 Docker 服務狀態
2. 啟動指標處理服務 (消費 RabbitMQ)
3. 啟動監控 API 服務 (端口 8001)
4. 啟動測試模型 API (端口 8002)
5. 啟動特徵生成器 (永續運行)
6. 執行健康檢查
```

## 🔍 健康檢查

### 自動檢查項目
- Docker 容器狀態
- 服務端口響應
- 進程存活狀態
- API 健康端點

### 手動驗證方法
```bash
# 檢查 API 端點
curl http://localhost:8001/health
curl http://localhost:8002/health

# 檢查數據庫連接
curl http://localhost:8001/v1/metrics/summary

# 檢查 Grafana
open http://localhost:3002
```

## 📝 日誌管理

### 日誌位置
所有服務日誌統一存放在 `logs/` 目錄：
- `metrics_processing.log` - 指標處理服務
- `monitoring_api.log` - 監控 API 服務
- `test_model_api.log` - 測試模型 API
- `feature_generator.log` - 特徵生成器

### 日誌輪轉
腳本會自動創建和管理日誌文件，建議定期清理：
```bash
# 清理舊日誌 (保留最近7天)
find logs/ -name "*.log" -mtime +7 -delete
```

## 🚨 故障排除

### 常見問題

#### 1. Docker 服務未啟動
```bash
# 檢查 Docker 狀態
docker ps

# 啟動 Docker 服務
docker-compose up -d

# 檢查服務健康
./start_monitoring_services.sh status
```

#### 2. 端口被佔用
```bash
# 檢查端口使用
lsof -i :8001
lsof -i :8002

# 停止衝突進程
./start_monitoring_services.sh stop
```

#### 3. 服務啟動失敗
```bash
# 查看詳細日誌
./start_monitoring_services.sh logs

# 檢查錯誤訊息
tail -f logs/monitoring_api.log
```

#### 4. 數據庫連接失敗
```bash
# 檢查 TimescaleDB 狀態
docker logs platform-timescaledb

# 重啟數據庫服務
docker-compose restart platform-timescaledb
```

### 服務重置
如果服務狀態異常，可以完全重置：
```bash
# 停止所有服務
./start_monitoring_services.sh stop

# 清理 PID 文件
rm -f *.pid

# 重啟 Docker 服務
docker-compose restart

# 重新啟動監控服務
./start_monitoring_services.sh start
```

## 🔧 配置參數

### 環境變數
腳本使用以下配置，可在腳本頂部修改：
```bash
MONITORING_API_PORT=8001      # 監控 API 端口
TEST_MODEL_API_PORT=8002      # 測試 API 端口
FEATURE_GENERATOR_DURATION="3600"  # 特徵生成器運行時間(秒)
```

### 服務參數
- **指標處理服務**: 自動從 RabbitMQ 消費事件
- **監控 API**: 綁定到所有網路介面 (0.0.0.0)
- **測試模型 API**: 模擬機器學習推理服務
- **特徵生成器**: 永續運行模式，1.5秒間隔請求

## 📈 性能監控

### 關鍵指標
- **QPS**: 每秒請求數 (~0.67)
- **響應時間**: 平均 ~55ms
- **錯誤率**: 目標 <1%
- **服務可用性**: 目標 >99%

### 監控地址
- **Grafana 儀表板**: http://localhost:3002 (admin/admin)
- **監控 API**: http://localhost:8001
- **API 文檔**: http://localhost:8001/docs

## 🛡️ 安全考量

### API 認證
- 所有 API 端點使用 API Key 認證
- 測試環境 API Key: `test-api-key-12345`
- 生產環境請更換強密碼

### 網路安全
- 服務綁定到本地端口
- 生產環境建議使用反向代理
- 配置防火牆規則限制訪問

## 📚 相關文檔

- [系統架構文檔](../1_design/architecture/)
- [API 規格文檔](docs/Model_API_Monitoring_API_Specification.md)
- [部署指南](README.md)
- [故障排除手冊](MONITORING_SETUP.md)

---

**版本**: v1.0  
**最後更新**: 2024-12-19  
**維護者**: VibeCoding Assistant 