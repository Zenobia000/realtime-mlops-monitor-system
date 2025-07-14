# Model API 監控系統 - 專案檔案結構

## 📋 概述

本文檔描述 Model API 監控系統的完整檔案結構，基於 VibeCoding 開發流程和 WBS 階段性組織。

## 🏗️ 專案根目錄結構

```
queue_pipe_sys/
├── 0_discovery/                    # 需求發現階段
│   ├── clarifications/
│   │   └── questions_template.md
│   ├── conversations/
│   ├── requirements/
│   │   └── user_stories_template.md
│   └── README.md
│
├── 1_design/                       # 系統設計階段
│   ├── api-contracts/
│   ├── architecture/               # ★ 架構設計文檔
│   │   ├── 01_project_structure.md    # 本檔案
│   │   ├── 02_file_dependencies.md    # 檔案相依關係
│   │   └── 03_class_relationships.md  # 類別組件關係
│   ├── flow-diagrams/
│   ├── PROJECT_WBS_CHECKLIST.md    # WBS 專案查核清單
│   └── README.md
│
├── 2_implementation/               # ★ 核心實作階段
│   ├── src/                        # 主要源代碼目錄
│   │   ├── api/                    # FastAPI 後端核心
│   │   │   ├── __init__.py
│   │   │   ├── main.py             # FastAPI 應用主程式
│   │   │   ├── config.py           # 配置管理
│   │   │   ├── database.py         # 資料庫連接
│   │   │   ├── cache.py            # Redis 快取
│   │   │   ├── dependencies.py     # 依賴注入
│   │   │   └── routers/            # ★ API 路由模組 (Phase 2.1)
│   │   │       ├── __init__.py     # 路由統一匯出
│   │   │       ├── metrics.py      # 指標查詢 API 
│   │   │       ├── alerts.py       # 告警管理 API 
│   │   │       ├── services.py     # 服務監控 API 
│   │   │       ├── dashboards.py   # 儀表板數據 API 
│   │   │       └── realtime.py     # WebSocket 實時數據 API 
│   │   │
│   │   ├── components/             # ★ 監控攔截器組件
│   │   │   ├── __init__.py         # 組件匯出
│   │   │   ├── metrics_event.py    # 指標事件數據結構
│   │   │   ├── event_publisher.py  # RabbitMQ 事件發送器
│   │   │   └── monitor.py          # 監控攔截器主類別
│   │   │
│   │   ├── services/               # ★ 指標處理服務 (Phase 1.4)
│   │   │   ├── __init__.py         # 服務匯出
│   │   │   ├── event_consumer.py   # RabbitMQ 事件消費者
│   │   │   ├── metrics_aggregator.py # 滑動視窗指標聚合器
│   │   │   ├── storage_manager.py  # PostgreSQL + Redis 存儲管理
│   │   │   ├── alert_manager.py    # 告警規則管理器
│   │   │   └── metrics_processor.py # 指標處理主協調器
│   │   └── utils/                  # 共用工具
│   │
│   ├── tests/                      # 測試套件
│   │   ├── unit/                   # 單元測試
│   │   ├── integration/            # 整合測試
│   │   └── e2e/                    # 端對端測試
│   │
│   ├── scripts/                    # 腳本和工具
│   │   └── init-db.sql             # 資料庫初始化腳本
│   │
│   ├── test_model_api.py           # ★ 測試用 Model API 服務
│   ├── test_monitoring_performance.py # ★ 性能測試腳本
│   ├── test_metrics_processing.py  # ★ 指標處理服務測試
│   ├── test_api_endpoints.py       # ★ API 端點測試腳本 (Phase 2.1)
│   ├── run_monitoring_demo.py      # ★ CLI 演示工具
│   ├── run_metrics_processing_service.py # ★ 指標處理服務管理
│   ├── start_monitoring_services.sh # ★ 一鍵服務管理腳本 (NEW)
│   ├── MONITORING_SETUP.md         # ★ 監控設置指南
│   ├── METRICS_PROCESSING_SERVICE_GUIDE.md # ★ 指標服務使用指南
│   ├── SERVICE_MANAGEMENT_GUIDE.md # ★ 服務管理指南 (NEW)
│   ├── PHASE_2_1_API_DEVELOPMENT_SUMMARY.md # ★ Phase 2.1 開發總結
│   │
│   ├── requirements.txt            # Python 依賴清單
│   ├── pyproject.toml              # Poetry 專案配置
│   ├── poetry.lock                 # Poetry 鎖定檔案
│   ├── Makefile                    # 自動化構建腳本
│   └── README.md                   # 實作階段說明
│
├── 3_validation/                   # 測試驗證階段
│   ├── benchmarks/
│   ├── quality-metrics/
│   ├── test-reports/
│   └── README.md
│
├── 4_deployment/                   # 部署上線階段
│   ├── ci-cd/
│   ├── environments/
│   │   ├── development/
│   │   ├── staging/
│   │   └── production/
│   ├── monitoring/
│   └── README.md
│
├── config/                         # 配置檔案
│   ├── env.example                 # 環境變數範本
│   └── grafana/                    # ★ Grafana 配置 (NEW)
│       ├── corrected_dashboard_sql_fixed.json # ★ 專業優化版儀表板
│       ├── 儀表板優化總結.md        # ★ 儀表板優化文檔
│       └── provisioning/
│           ├── dashboards/
│           ├── datasources/
│           └── notifiers/
│
├── docs/                          # 技術文檔
│   ├── api/
│   ├── technical/
│   ├── user-guide/
│   ├── Model_API_Monitoring_Brief.md           # 專案簡報
│   ├── Model_API_Monitoring_API_Specification.md # API 規格文檔
│   ├── System_Architecture_Document.md         # 系統架構文檔
│   └── Metrics_Processing_Service_Design.md    # 詳細設計文檔
│
├── knowledge-base/                 # 知識庫
│   ├── decisions/
│   ├── patterns/
│   ├── retrospectives/
│   └── solutions/
│
├── design_templates/              # 設計文檔模板
│   ├── 00_project_brief_prd_summary_template.md
│   ├── 01_adr_template.md
│   ├── 02_system_architecture_document_template.md
│   ├── 03_system_design_document_template.md
│   ├── 04_api_design_specification_template.md
│   ├── 05_security_privacy_review_checklist_template.md
│   └── 06_production_readiness_review_template.md
│
├── docker-compose.yml             # Docker 服務編排
├── package.json                   # Node.js 專案配置 (前端準備)
├── README.md                      # 專案主 README
└── VIBECODING_WORKFLOW.md         # VibeCoding 工作流程說明
```

## 🎯 核心實作檔案詳解

### API 路由模組 (`src/api/routers/`) - ★ Phase 2.1 新增

| 檔案 | 用途 | 端點數量 | 主要功能 |
|------|------|----------|----------|
| `__init__.py` | 路由統一匯出 | - | 匯出所有路由模組 |
| `metrics.py` | 指標查詢 API | 4 個 | 指標摘要、歷史查詢、實時數據、服務列表 |
| `alerts.py` | 告警管理 API | 2 個 | 告警列表、活躍告警查詢 |
| `services.py` | 服務監控 API | 1 個 | 服務概覽和健康狀態 |
| `dashboards.py` | 儀表板數據 API | 3 個 | 儀表板概覽、時間序列、實時數據 |
| `realtime.py` | WebSocket 實時 API | 2 個 | 實時指標流、實時告警流 |

### 監控攔截器組件 (`src/components/`)

| 檔案 | 用途 | 主要類別/函數 |
|------|------|---------------|
| `__init__.py` | 組件統一匯出 | 匯出所有公開 API |
| `metrics_event.py` | 事件數據結構 | `MetricsEvent`, `EventType`, `HealthEvent` |
| `event_publisher.py` | RabbitMQ 發送器 | `EventPublisher`, `get_event_publisher()` |
| `monitor.py` | 監控攔截器 | `MonitoringMiddleware`, `ModelAPIMonitor` |

### 指標處理服務 (`src/services/`)

| 檔案 | 用途 | 主要類別/函數 |
|------|------|---------------|
| `__init__.py` | 服務統一匯出 | 匯出所有服務組件 |
| `event_consumer.py` | RabbitMQ 消費者 | `EventConsumer`, 異步事件消費 |
| `metrics_aggregator.py` | 滑動視窗聚合 | `MetricsAggregator`, 60秒視窗算法 |
| `storage_manager.py` | 數據存儲管理 | `StorageManager`, PostgreSQL + Redis |
| `alert_manager.py` | 告警規則管理 | `AlertManager`, 多級告警系統 |
| `metrics_processor.py` | 主協調器 | `MetricsProcessor`, 統一服務管理 |

### 測試和演示檔案

| 檔案 | 用途 | 執行方式 |
|------|------|----------|
| `test_model_api.py` | 測試用 ML API | `python test_model_api.py` |
| `test_monitoring_performance.py` | 監控性能測試 | `python test_monitoring_performance.py` |
| `test_metrics_processing.py` | 指標處理測試 | `python test_metrics_processing.py` |
| `test_api_endpoints.py` | ★ API 端點測試 | `python test_api_endpoints.py` |
| `run_monitoring_demo.py` | CLI 演示工具 | `python run_monitoring_demo.py [command]` |
| `run_metrics_processing_service.py` | 指標服務管理 | `python run_metrics_processing_service.py [command]` |

### 配置和設置檔案

| 檔案 | 用途 | 格式 |
|------|------|------|
| `requirements.txt` | Python 依賴 | pip 格式 |
| `pyproject.toml` | Poetry 配置 | TOML 格式 |
| `docker-compose.yml` | 服務編排 | Docker Compose |
| `config/env.example` | 環境變數範本 | dotenv 格式 |
| `PHASE_2_1_API_DEVELOPMENT_SUMMARY.md` | ★ Phase 2.1 總結 | Markdown |

## 📦 依賴管理

### Python 依賴 (`requirements.txt`)
```text
fastapi==0.104.1          # Web 框架
uvicorn[standard]==0.24.0  # ASGI 服務器
aio_pika==9.3.1           # RabbitMQ 客戶端
asyncpg==0.29.0           # PostgreSQL 異步客戶端
redis==5.0.1              # Redis 客戶端
pydantic==2.5.0           # 數據驗證
aiohttp==3.9.1            # HTTP 客戶端
typer==0.9.0              # CLI 工具
rich==13.7.0              # 終端美化
```

### 開發依賴
```text
pytest==7.4.3            # 測試框架
pytest-asyncio==0.21.1   # 異步測試支援
black==23.11.0            # 程式碼格式化
mypy==1.7.1               # 型別檢查
```

## 🔄 開發階段對應

| WBS 階段 | 目錄 | 狀態 | 主要交付物 |
|----------|------|------|------------|
| Phase 1.1-1.2 | `src/api/` | ✅ 完成 | FastAPI 基礎架構 |
| Phase 1.3 | `src/components/` | ✅ 完成 | 監控攔截器 |
| Phase 1.4 | `src/services/` | ✅ 完成 | 指標處理服務 |
| Phase 2.1 | `src/api/routers/` | ✅ 完成 | API 端點開發 (16個端點) |
| Phase 2.2-2.3 | `frontend/` | ⏳ 待開始 | Vue.js 前端 |
| Phase 3.1-3.3 | `3_validation/` | ⏳ 待開始 | 告警和歷史功能 |

## 📋 檔案統計

```
總檔案數量: 70+ 檔案 (增加 5+ 檔案)
├── Python 源碼: 26 檔案 (~15,000 行)
│   ├── 監控組件: 4 檔案 (~1,500 行)
│   ├── 指標服務: 6 檔案 (~2,300 行)
│   ├── API 核心: 7 檔案 (~8,200 行)
│   └── API 路由: 6 檔案 (~1,525 行)
├── Bash 腳本: 2 檔案 (~600 行) ★ 新增
├── 配置檔案: 10 檔案 (增加 Grafana 配置)
├── 文檔檔案: 19 檔案 (~28,000 行) ★ 增加
├── 測試檔案: 9 檔案 (~4,000 行)
└── 腳本工具: 8 檔案 (~3,100 行) ★ 增加
```

## 🔍 關鍵路徑檔案 (更新)

開發和部署過程中的關鍵檔案：

1. **入口點**: `src/api/main.py` (FastAPI 應用)
2. **核心邏輯**: `src/components/monitor.py` (監控攔截器)
3. **配置中心**: `src/api/config.py` (系統配置)
4. **API 路由**: `src/api/routers/` (16個端點)
5. **服務管理**: `start_monitoring_services.sh` ★ (一鍵啟動)
6. **測試驗證**: `test_api_endpoints.py` (API 端點測試)
7. **監控儀表板**: `config/grafana/corrected_dashboard_sql_fixed.json` ★
8. **部署配置**: `docker-compose.yml` (服務編排)

## 🚀 Phase 2.1 API 端點成果

### RESTful API 端點 (14個)
| 類別 | 端點 | 說明 |
|------|------|------|
| **基礎** | `GET /`, `/health`, `/v1` | 系統基礎服務 |
| **指標** | `GET /v1/metrics/*` | 指標摘要、歷史、實時、服務 (4個) |
| **告警** | `GET /v1/alerts/*` | 告警列表、活躍告警 (2個) |
| **服務** | `GET /v1/services/` | 服務概覽 (1個) |
| **儀表板** | `GET /v1/dashboards/*` | 概覽、時間序列、實時 (3個) |
| **錯誤處理** | `GET /v1/nonexistent` | 404 錯誤測試 (1個) |

### WebSocket 端點 (2個)
- `WS /v1/ws/metrics` - 實時指標流 (5秒間隔)
- `WS /v1/ws/alerts` - 實時告警流 (3秒間隔)

### 技術特性
- ✅ **API Key 認證**: Header 和 Bearer Token 雙支援
- ✅ **統一錯誤處理**: `{success, data/error, timestamp}` 格式
- ✅ **依賴注入**: AsyncPG 連接池 + Redis 客戶端
- ✅ **分頁查詢**: limit/offset 支援
- ✅ **實時推送**: WebSocket 連接管理
- ✅ **優雅降級**: Redis/數據庫連接失敗處理
- ✅ **時區處理**: offset-naive/aware 兼容
- ✅ **重試邏輯**: 測試腳本自動重試機制

### 測試成果
- **總測試數**: 14
- **成功率**: 92.86% → 100% (修復後)
- **平均響應時間**: ~3ms
- **認證測試**: ✅ 通過
- **錯誤處理**: ✅ 通過

---

**文檔版本**: v1.2  
**最後更新**: 2025-07-01  
**對應 WBS**: Phase 2.1 (後端 API 端點開發) - ✅ 已完成 

### 服務管理工具 (NEW)

| 檔案 | 用途 | 執行方式 |
|------|------|----------|
| `start_monitoring_services.sh` | ★ 一鍵服務管理 | `./start_monitoring_services.sh [start\|stop\|restart\|status\|logs]` |
| `SERVICE_MANAGEMENT_GUIDE.md` | ★ 服務管理指南 | 詳細使用說明文檔 |

#### 一鍵啟動腳本功能特性
- ✅ **自動依賴檢查**: 檢查 Docker 服務狀態
- ✅ **按序啟動服務**: 指標處理 → 監控API → 測試API → 特徵生成器
- ✅ **健康檢查**: 端口響應、進程狀態、API健康端點
- ✅ **日誌管理**: 統一日誌收集和查看
- ✅ **PID 管理**: 進程ID文件管理和清理
- ✅ **優雅停止**: 按序停止服務，清理資源
- ✅ **彩色輸出**: 美化的終端輸出和狀態顯示

## 🔧 服務管理新功能 (NEW)

### 一鍵操作
```bash
# 啟動所有服務
./start_monitoring_services.sh start

# 檢查服務狀態  
./start_monitoring_services.sh status

# 停止所有服務
./start_monitoring_services.sh stop

# 重啟服務
./start_monitoring_services.sh restart

# 查看日誌
./start_monitoring_services.sh logs
```

### 服務架構層次
```
Docker 基礎服務層
├── TimescaleDB (5433)
├── Redis (6380)  
├── RabbitMQ (5672)
└── Grafana (3002)

Python 監控服務層
├── 指標處理服務 (後台)
├── 監控 API (8001)
├── 測試模型 API (8002)
└── 特徵生成器 (永續運行)
```

### 配置文件更新
- **PID 管理**: 各服務獨立PID文件
- **日誌管理**: 統一日誌目錄 `logs/`
- **配置參數**: 腳本頂部可配置端口和參數
- **健康檢查**: 自動檢查服務狀態和連通性

---

**文檔版本**: v1.2  
**最後更新**: 2025-07-01  
**對應 WBS**: Phase 2.1 (後端 API 端點開發) - ✅ 已完成 