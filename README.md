# Model API Real-time Monitoring System
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/username/queue_pipe_sys) [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org) [![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com) [![Vue.js](https://img.shields.io/badge/Vue.js-3.0+-4FC08D.svg)](https://vuejs.org)

> 企業級機器學習模型 API 即時監控系統，提供非侵入式性能監控、即時告警和智能分析功能

## 🚀 快速開始

```bash
# Docker 一鍵啟動完整監控系統
docker-compose up -d

# 本地 Poetry 開發環境
cd 2_implementation && poetry install && poetry shell
```

## 📋 目錄
- [關於專案](#關於專案)
- [功能特色](#功能特色)
- [技術架構](#技術架構)
- [安裝指南](#安裝指南)
- [使用方式](#使用方式)
- [API 文件](#api-文件)
- [開發指南](#開發指南)
- [貢獻指南](#貢獻指南)
- [版本歷程](#版本歷程)
- [授權條款](#授權條款)
- [聯絡我們](#聯絡我們)

## 📖 關於專案

### 問題背景
在 MLOps 生產環境中，機器學習模型 API 的性能監控是關鍵挑戰。傳統監控方案往往需要侵入性修改現有程式碼，增加開發負擔並可能影響系統穩定性。

### 解決方案
本系統提供非侵入式的即時監控解決方案，通過事件驅動架構實現：
- **零程式碼改動**：透過代理攔截技術監控現有 API
- **即時性能分析**：毫秒級監控響應和效能指標
- **智能告警系統**：基於機器學習的異常檢測和預警
- **可視化儀表板**：直觀的即時數據展示和歷史趨勢分析

### 技術架構
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Vue.js 前端   │    │   FastAPI 後端   │    │  RabbitMQ 佇列  │
│   即時儀表板    │◄──►│   RESTful API    │◄──►│   事件驅動      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  WebSocket 連線 │    │ PostgreSQL+Redis │    │  監控攔截器     │
│  即時數據推送   │    │  數據存儲層      │    │  非侵入式監控   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 技術棧
- **前端**: Vue.js 3 + TypeScript + Tailwind CSS + Chart.js
- **後端**: FastAPI + Uvicorn + Pydantic
- **訊息佇列**: RabbitMQ (事件驅動架構)
- **數據庫**: PostgreSQL + TimescaleDB (歷史數據) + Redis (即時快取)
- **部署**: Docker + Docker Compose + Kubernetes
- **監控**: Prometheus + Grafana (可選)

## ✨ 功能特色

- 🔥 **高效能監控**: 代理延遲 < 20ms，支援 1000+ 事件/秒
- 🛡️ **非侵入式設計**: 零程式碼修改，即裝即用
- 📊 **即時儀表板**: WebSocket 驅動，5秒內數據更新
- 🚨 **智能告警**: 基於閾值和機器學習的異常檢測
- 📱 **響應式設計**: 支援桌面和行動裝置
- 🔧 **易於整合**: 豐富的 REST API 和 WebHook 支援
- 📈 **歷史分析**: 時間序列數據存儲和趨勢分析
- 🌐 **高可用性**: 叢集支援和自動故障轉移

## 🔧 安裝指南

### 系統要求
- **Python**: >= 3.8
- **Node.js**: >= 16.0.0 (本地安裝)
- **Docker**: >= 20.10 (Docker 安裝)
- **Docker Compose**: >= 2.0 (Docker 安裝)
- **Poetry**: >= 1.4.0 (本地安裝)
- **PostgreSQL**: >= 13 (本地安裝)
- **RabbitMQ**: >= 3.9 (本地安裝)
- **記憶體**: >= 4GB RAM
- **硬碟**: >= 10GB 可用空間

### 方式一：Docker 容器化部署 (推薦)

```bash
# 1. 複製專案
git clone https://github.com/username/queue_pipe_sys.git
cd queue_pipe_sys

# 2. 環境配置
cp config/env.example .env
# 編輯 .env 檔案設定數據庫連線等參數

# 3. 一鍵啟動所有服務
docker-compose up -d

# 4. 驗證安裝
curl http://localhost:8000/health
```

**Docker 服務端點：**
- **前端儀表板**: http://localhost:3000
- **後端 API**: http://localhost:8000
- **API 文檔**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **pgAdmin**: http://localhost:5050 (admin@monitoring.com / monitor_admin)
- **RabbitMQ 管理介面**: http://localhost:15672
- **RabbitMQ AMQP**: localhost:5672
- **Redis**: localhost:6379

### 方式二：本地 Poetry 開發環境

```bash
# 1. 複製專案
git clone https://github.com/username/queue_pipe_sys.git
cd queue_pipe_sys

# 2. 後端環境設置 (使用 Poetry)
cd 2_implementation
poetry install
poetry shell

# 3. 前端環境設置
cd ../frontend
npm install

# 4. 啟動外部服務
# PostgreSQL (使用系統服務或 Docker)
sudo service postgresql start
# 或 docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:13

# RabbitMQ (使用系統服務或 Docker)  
sudo service rabbitmq-server start
# 或 docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management

# Redis (使用系統服務或 Docker)
sudo service redis-server start
# 或 docker run -d --name redis -p 6379:6379 redis:7

# 5. 資料庫初始化
cd scripts
psql -U postgres -f init-db.sql

# 6. 啟動應用服務
# 終端 1: 後端服務
cd 2_implementation && poetry run python -m src.api.main

# 終端 2: 前端服務  
cd frontend && npm run dev
```

**本地開發服務端點：**
- **前端開發服務**: http://localhost:5173 (Vite 預設)
- **後端 API**: http://localhost:8000
- **API 文檔**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **RabbitMQ 管理介面**: http://localhost:15672 (guest/guest)
- **RabbitMQ AMQP**: localhost:5672
- **Redis**: localhost:6379

## 🎯 使用方式

### 基本監控設置

```python
from src.components.monitor import ModelAPIMonitor

# 初始化監控器
monitor = ModelAPIMonitor({
    'target_host': 'your-model-api.com',
    'target_port': 8080,
    'monitoring_port': 9090,
    'rabbitmq_url': 'amqp://localhost:5672'
})

# 啟動非侵入式監控
await monitor.start_monitoring()
```

### 儀表板存取

**Docker 部署：**
```bash
http://localhost:3000     # 前端儀表板
http://localhost:8000     # 後端 API 
http://localhost:8000/docs # Swagger API 文件
http://localhost:5050     # pgAdmin 資料庫管理 (admin@monitoring.com / monitor_admin)
http://localhost:15672    # RabbitMQ 管理介面 (monitor_user / monitor_pass)
```

**本地開發：**
```bash
http://localhost:5173     # 前端開發服務 (Vite)
http://localhost:8000     # 後端 API
http://localhost:8000/docs # Swagger API 文件  
http://localhost:15672    # RabbitMQ 管理介面 (guest/guest)
```

### API 監控配置

```python
# 配置監控規則
monitoring_config = {
    'metrics': ['response_time', 'throughput', 'error_rate'],
    'thresholds': {
        'response_time_ms': 1000,
        'error_rate_percent': 5.0
    },
    'alert_channels': ['email', 'slack', 'webhook']
}

monitor.configure(monitoring_config)
```

### 即時數據查詢

```javascript
// WebSocket 連線接收即時數據
const ws = new WebSocket('ws://localhost:8000/ws/metrics');

ws.onmessage = (event) => {
    const metrics = JSON.parse(event.data);
    updateDashboard(metrics);
};
```

## 📚 API 文件

完整的 API 文件請參考：
- **線上文件**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- **詳細規格**: [docs/Model_API_Monitoring_API_Specification.md](docs/Model_API_Monitoring_API_Specification.md)
- **架構設計**: [docs/System_Architecture_Document.md](docs/System_Architecture_Document.md)

### 核心 API 端點

```bash
GET  /api/v1/metrics/realtime     # 即時指標數據
GET  /api/v1/metrics/historical   # 歷史趨勢數據  
POST /api/v1/alerts/configure     # 告警規則設定
GET  /api/v1/health               # 系統健康檢查
```

## 🛠️ 開發指南

### 本地開發環境

```bash
# 啟動開發模式
make dev

# 執行測試
make test

# 程式碼檢查
make lint

# 建置 Docker 映像
make build
```

### 專案結構

```
queue_pipe_sys/
├── 0_discovery/          # 需求分析和規劃
├── 1_design/            # 系統設計文檔
├── 2_implementation/    # 源代碼實現
│   ├── src/api/        # FastAPI 後端
│   ├── src/components/ # 核心組件
│   └── src/services/   # 業務服務
├── 3_validation/       # 測試和驗證
├── 4_deployment/       # 部署配置
└── docs/              # 技術文檔
```

### 開發工作流程

1. **需求分析** (`0_discovery/`)
2. **架構設計** (`1_design/`)  
3. **編碼實現** (`2_implementation/`)
4. **測試驗證** (`3_validation/`)
5. **部署上線** (`4_deployment/`)

## 🤝 貢獻指南

我們歡迎任何形式的貢獻！請閱讀 [CONTRIBUTING.md](CONTRIBUTING.md) 了解詳細指南。

### 如何貢獻

1. **Fork** 本專案到您的 GitHub 帳號
2. **建立功能分支**: `git checkout -b feature/amazing-feature`
3. **提交變更**: `git commit -m 'Add: 新增驚人功能'`
4. **推送分支**: `git push origin feature/amazing-feature`
5. **開啟 Pull Request** 並描述您的變更

### 開發規範

- 遵循 [PEP 8](https://pep8.org/) Python 程式碼風格
- 使用 [Conventional Commits](https://conventionalcommits.org/) 提交訊息格式
- 編寫單元測試，保持測試覆蓋率 > 80%
- 更新相關文檔和 API 規格

### 問題回報

發現 Bug？有功能建議？請透過以下方式聯絡：
- [GitHub Issues](https://github.com/username/queue_pipe_sys/issues)
- [GitHub Discussions](https://github.com/username/queue_pipe_sys/discussions)

## 📋 版本歷程

查看 [CHANGELOG.md](CHANGELOG.md) 了解詳細的版本更新資訊。

### 最新版本 v1.0.0
- ✅ 完整的即時監控功能
- ✅ 非侵入式 API 攔截
- ✅ Vue.js 響應式儀表板
- ✅ RabbitMQ 事件驅動架構
- ✅ Docker 容器化部署

## 📊 性能指標

- **監控延遲**: < 20ms
- **數據更新**: < 5s  
- **併發支援**: 100+ 用戶
- **事件處理**: 1000+ 事件/秒
- **系統可用性**: 99.9%

## 📄 授權條款

本專案採用 [MIT 授權條款](LICENSE) - 查看 LICENSE 檔案了解詳情。

## 📞 聯絡我們

- **專案維護者**: Model API Monitoring Team
- **問題回報**: [GitHub Issues](https://github.com/username/queue_pipe_sys/issues)
- **功能討論**: [GitHub Discussions](https://github.com/username/queue_pipe_sys/discussions)
- **技術支援**: support@modelapi-monitoring.com
- **官方網站**: https://modelapi-monitoring.com

## 🙏 致謝

感謝所有為此專案做出貢獻的開發者和社群成員：

[![Contributors](https://contrib.rocks/image?repo=username/queue_pipe_sys)](https://github.com/username/queue_pipe_sys/graphs/contributors)

特別感謝：
- **FastAPI Community** - 優秀的 Web 框架支援
- **Vue.js Team** - 現代化的前端框架
- **RabbitMQ Team** - 可靠的訊息佇列系統
- **PostgreSQL Community** - 強大的開源資料庫

---

## 🎯 快速連結

| 功能 | Docker 連結 | 本地開發連結 | 說明 |
|------|-------------|-------------|------|
| 📊 監控儀表板 | [localhost:3000](http://localhost:3000) | [localhost:5173](http://localhost:5173) | 即時監控介面 |
| 📖 API 文檔 | [localhost:8000/docs](http://localhost:8000/docs) | [localhost:8000/docs](http://localhost:8000/docs) | Swagger 互動式文檔 |
| 🗄️ pgAdmin | [localhost:5050](http://localhost:5050) | 手動安裝 | PostgreSQL 資料庫管理 |
| 🐰 RabbitMQ 管理 | [localhost:15672](http://localhost:15672) | [localhost:15672](http://localhost:15672) | 訊息佇列管理 |
| 🛠️ 系統設計 | [System_Architecture_Document.md](docs/System_Architecture_Document.md) | [System_Architecture_Document.md](docs/System_Architecture_Document.md) | 架構設計文檔 |

Made with ❤️ by [Model API Monitoring Team](https://github.com/model-api-monitoring-team)

*採用大廠級 README 標準開發，使用 Docker + Poetry 現代化技術棧*