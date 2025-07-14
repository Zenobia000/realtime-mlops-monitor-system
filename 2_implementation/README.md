# 💻 Implementation Phase - 實作階段

## 🚀 快速啟動

### 📋 前置要求

1. **Python 3.10+** 已安裝
2. **Poetry** 套件管理器已安裝
3. **Docker** 服務運行中 (platform-* 服務)

### 💻 安裝 Poetry (如果尚未安裝)

```bash
# 安裝 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 或使用 pip
pip install poetry
```

### ⚡ 一鍵設置

```bash
# 1. 進入實作目錄
cd 2_implementation

# 2. 完整項目設置 (環境 + 依賴 + .env)
make setup

# 3. 啟動開發服務器
make dev
```

### 📝 詳細步驟

#### 1. 環境設置

```bash
# 安裝 Poetry 環境和依賴
make install

# 或手動設置
poetry env use python3.10
poetry install
```

#### 2. 環境配置

```bash
# 生成 .env 文件 (基於 Docker 服務配置)
make env

# 或手動執行
poetry run python setup_env.py
```

#### 3. 啟動服務

```bash
# 開發模式 (熱重載)
make dev

# 生產模式
make run

# 手動啟動
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## 🔗 服務端點

| 服務 | 地址 | 說明 |
|------|------|------|
| **API 服務** | http://localhost:8000 | FastAPI 主服務 |
| **API 文檔** | http://localhost:8000/docs | Swagger UI |
| **健康檢查** | http://localhost:8000/health | 系統狀態 |
| **測試 Model API** | http://localhost:8002 | 測試用 ML API 服務 |
| **測試 API 文檔** | http://localhost:8002/docs | 測試 API Swagger UI |
| **指標處理服務** | 後台服務 | ✅ 60秒滑動視窗指標聚合 |
| **PostgreSQL** | localhost:5433 | TimescaleDB 資料庫 (外部端口) |
| **Redis** | localhost:6380 | 快取服務 (外部端口) |
| **RabbitMQ** | localhost:5672 | 訊息佇列 |
| **RabbitMQ 管理** | http://localhost:15672 | RabbitMQ 管理界面 |
| **Grafana** | http://localhost:3002 | 數據視覺化 |
| **pgAdmin** | http://localhost:5050 | 資料庫管理 |

## 🔐 認證資訊

| 服務 | 用戶名 | 密碼 | 說明 |
|------|--------|------|------|
| **PostgreSQL** | admin | admin123 | 資料庫: platform_db |
| **Redis** | - | admin123 | 需要密碼認證 |
| **RabbitMQ** | admin | admin123 | 訊息佇列服務 |
| **Grafana** | admin | admin123 | 數據視覺化 |
| **pgAdmin** | admin@monitoring.com | monitor_admin | 資料庫管理界面 |
| **API Key** | - | monitor_api_key_dev_2025 | API 認證金鑰 |

## 🛠️ 開發工具

### 常用指令

```bash
# 檢查所有可用指令
make help

# 檢查服務狀態
make status

# 快速 API 測試 (Phase 2.1 端點)
make test-api

# API 端點測試腳本
python test_api_endpoints.py

# 程式碼格式化
make format

# 程式碼檢查
make lint

# 運行測試
make test

# 完整品質檢查
make check
```

### API 測試範例

```bash
# 主 API 健康檢查
curl http://localhost:8000/health

# API 資訊
curl http://localhost:8000/v1

# 受保護端點 (需要 API Key)
curl -H "X-API-Key: monitor_api_key_dev_2025" \
     http://localhost:8000/v1/protected

# 測試 Model API 健康檢查
curl http://localhost:8002/health

# 模型預測請求
curl -X POST -H "Content-Type: application/json" \
     -d '{"features": [1.0, 2.0, 3.0], "model_version": "v1.0"}' \
     http://localhost:8002/predict

# 監控統計查詢
curl http://localhost:8002/monitoring/stats

# Phase 2.1 API 端點測試
curl -H "X-API-Key: monitor_api_key_dev_2025" \
     http://localhost:8000/v1/metrics/summary

# 歷史指標查詢
curl -H "X-API-Key: monitor_api_key_dev_2025" \
     "http://localhost:8000/v1/metrics/historical?hours=24&limit=100"

# 實時指標數據
curl -H "X-API-Key: monitor_api_key_dev_2025" \
     http://localhost:8000/v1/metrics/realtime

# 告警查詢
curl -H "X-API-Key: monitor_api_key_dev_2025" \
     http://localhost:8000/v1/alerts

# 儀表板概覽
curl -H "X-API-Key: monitor_api_key_dev_2025" \
     http://localhost:8000/v1/dashboards/overview

# WebSocket 實時數據 (需要 WebSocket 客戶端)
# wscat -c "ws://localhost:8000/v1/ws/metrics?api_key=monitor_api_key_dev_2025"

# 指標處理服務測試 (使用正確的認證)
export DATABASE_URL="postgresql://admin:admin123@localhost:5433/platform_db"
export REDIS_URL="redis://:admin123@localhost:6380/0"
export RABBITMQ_URL="amqp://admin:admin123@localhost:5672/"
poetry run python test_metrics_processing.py test-basic
```

## 📁 專案結構

```
2_implementation/
├── src/                    # 源代碼
│   ├── api/               # FastAPI 應用
│   │   ├── main.py        # 主程式
│   │   ├── config.py      # 配置管理
│   │   ├── database.py    # 資料庫連接
│   │   ├── cache.py       # Redis 快取
│   │   └── dependencies.py # 依賴注入
│   ├── components/        # ✅ 監控組件 (WBS 1.3)
│   │   ├── __init__.py    # 組件匯出
│   │   ├── metrics_event.py # 監控事件數據結構
│   │   ├── event_publisher.py # RabbitMQ 事件發送器
│   │   └── monitor.py     # 監控攔截器核心
│   ├── services/          # ✅ 指標處理服務 (WBS 1.4)
│   │   ├── __init__.py         # 服務模組匯出
│   │   ├── event_consumer.py   # RabbitMQ 事件消費者
│   │   ├── metrics_aggregator.py # 60秒滑動視窗聚合器
│   │   ├── storage_manager.py  # PostgreSQL + Redis 存儲
│   │   ├── alert_manager.py    # 告警管理器
│   │   └── metrics_processor.py # 主處理器協調器
│   └── utils/             # 共用工具
├── tests/                 # 測試文件
├── test_model_api.py      # ✅ 測試用 ML API 服務
├── test_monitoring_performance.py # ✅ 性能測試腳本
├── run_monitoring_demo.py # ✅ CLI 演示工具
├── MONITORING_SETUP.md    # ✅ 監控設置指南
├── pyproject.toml        # Poetry 配置
├── Makefile              # 開發指令
├── setup_env.py          # 環境設置腳本
└── README.md             # 說明文檔
```

## 🔧 環境變數

主要配置在 `.env` 文件中：

```bash
# 資料庫 (使用實際外部端口)
DATABASE_URL=postgresql://admin:admin123@localhost:5433/platform_db

# Redis (使用實際外部端口)
REDIS_URL=redis://:admin123@localhost:6380/0

# RabbitMQ  
RABBITMQ_URL=amqp://admin:admin123@localhost:5672/

# API
API_KEY=monitor_api_key_dev_2025
API_PORT=8000
TEST_API_PORT=8002
```

## 🐛 疑難排解

### 常見問題

**1. Poetry 找不到 Python 3.10**
```bash
# 確認 Python 3.10 已安裝
python3.10 --version

# 指定 Python 版本
poetry env use python3.10
```

**2. 服務連接失敗**
```bash
# 檢查 Docker 服務狀態
make status

# 確認服務運行
docker ps --filter "name=platform-"
```

**3. 端口衝突**
```bash
# 檢查主要端口使用
netstat -tlnp | grep -E ":(8000|8002|5433|6380|5672|15672|5050)"

# 修改 .env 中的端口配置
# API_PORT=8000          # 主 API 服務
# TEST_API_PORT=8002     # 測試 Model API 服務
```

## 🔍 監控系統快速啟動

### 啟動測試 Model API 服務

```bash
# 啟動測試 API 服務 (端口 8002)
python test_model_api.py

# 或使用演示工具
python run_monitoring_demo.py start-api
```

### 監控系統演示

```bash
# 檢查系統狀態
python run_monitoring_demo.py status

# 運行基本功能測試
python run_monitoring_demo.py test

# 運行性能測試
python run_monitoring_demo.py performance

# 運行完整演示
python run_monitoring_demo.py demo
```

### 指標處理服務管理

```bash
# 指標處理服務管理工具
python run_metrics_processing_service.py start    # 啟動服務
python run_metrics_processing_service.py status   # 檢查狀態
python run_metrics_processing_service.py config   # 查看配置
python run_metrics_processing_service.py test     # 運行測試

# 指標處理測試工具
python test_metrics_processing.py test-basic      # 基礎功能測試
python test_metrics_processing.py test-performance # 性能測試
python test_metrics_processing.py monitor         # 實時監控模式
```

### 查看監控數據

```bash
# 檢查 RabbitMQ 管理界面
http://localhost:15672

# 查看監控統計
curl http://localhost:8002/monitoring/stats

# 查看 API 文檔
http://localhost:8002/docs
```

## 📚 下一步

1. ✅ **環境設置完成**
2. ✅ **開發監控攔截器** (Phase 1.3) - **已完成**
3. ✅ **指標處理服務** (Phase 1.4) - **已完成**
4. ✅ **後端 API 端點** (Phase 2.1) - **已完成**
5. 🔮 **前端儀表板開發** (Phase 2.2-2.3)
6. 🎯 **告警和歷史功能** (Phase 3.1-3.3)
7. 🚀 **系統整合測試** (Phase 3.4)

---

## 💡 開發提示

- 使用 `make dev` 啟動開發服務器，支援熱重載
- 使用 `make check` 進行完整程式碼品質檢查
- API 文檔自動生成於 `/docs` 端點
- 所有環境配置都在 `.env` 文件中管理

##  階段目標
- 🛠️ 撰寫核心程式碼
- 📡 實作 API 和服務
- 🔗 整合第三方服務
- 🧪 開發單元測試

## 🛠️ VibeCoding 工具使用
```bash
@vibe code "核心功能"           # 生成核心代碼
@vibe comp "React 組件"         # 生成組件
@vibe api "API 接口"            # 生成 API
@vibe review "[代碼]"           # 代碼審查
@vibe refactor "優化代碼"       # 重構代碼
```

## 📁 資料夾結構說明
- **src/**: 源代碼檔案
- **tests/**: 測試代碼和測試策略
- **scripts/**: 建構和部署腳本

## ✅ 完成檢查清單

### Phase 1.3 - 監控攔截器開發 (已完成)
- [x] ✅ 開發 Python Middleware 攔截器
- [x] ✅ 實現請求/響應攔截邏輯  
- [x] ✅ 確保非侵入式設計 (< 20ms 額外延遲)
- [x] ✅ 指標事件格式設計
- [x] ✅ RabbitMQ 事件發送 (異步發送、重試機制、佇列配置)
- [x] ✅ 建立測試用 Model API
- [x] ✅ 攔截器效能驗證 (壓力測試、延遲測試、成功率驗證)

### ✅ Phase 1.4 - 指標處理服務 (已完成) 🎉
- [x] MetricsProcessor 主類別
- [x] EventConsumer RabbitMQ 消費者
- [x] MetricsAggregator 滑動視窗算法
- [x] StorageManager PostgreSQL + Redis
- [x] AlertManager 告警管理
- [x] 60 秒視窗，12 個 5 秒子視窗
- [x] QPS、延遲、錯誤率計算
- [x] 批量寫入優化
- [x] Redis 快取 TTL 管理
- [x] 處理延遲 < 1 秒驗證

### ✅ Phase 2.1 - 後端 API 端點開發 (已完成) 🎉
- [x] RESTful API 端點設計與實現 (14個端點)
- [x] WebSocket 實時數據推送 (2個端點)
- [x] API Key 認證機制
- [x] 統一錯誤處理和響應格式
- [x] 模組化路由設計 (`src/api/routers/`)
- [x] 依賴注入系統 (`dependencies.py`)
- [x] 異步數據庫集成 (AsyncPG)
- [x] Redis 快取集成
- [x] 連接池管理和優化
- [x] API 端點測試腳本 (`test_api_endpoints.py`)
- [x] 時區問題修復
- [x] Redis 連接錯誤修復
- [x] 重試邏輯和錯誤處理

**測試結果**:
- ✅ **總測試數**: 14 個端點
- ✅ **成功率**: 92.86% → 100% (修復後)
- ✅ **平均響應時間**: ~3ms
- ✅ **認證測試**: 通過
- ✅ **錯誤處理**: 統一格式驗證通過

### 待開發項目
- [ ] 前端儀表板開發 (Phase 2.2-2.3)
- [ ] 告警系統開發 (Phase 3.1-3.3)