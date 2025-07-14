# 系統架構設計文檔 (System Architecture Document) - Model API 即時監控系統

---

**文件版本 (Document Version):** `v0.1`

**最後更新 (Last Updated):** `2025-07-01`

**主要作者/架構師 (Lead Author/Architect):** `Vibe Coder`

**審核者 (Reviewers):** `MLOps Team, Tech Lead`

**狀態 (Status):** `草稿 (Draft)`

**相關 PRD/專案簡報:** `[docs/Model_API_Monitoring_Brief.md](./Model_API_Monitoring_Brief.md)`

**相關 ADRs:** `[待定]`

---

## 目錄 (Table of Contents)
<!-- omit in toc -->
1.  [引言 (Introduction)](#1-引言-introduction)
    1.1. [目的與範圍 (Purpose and Scope)](#11-目的與範圍-purpose-and-scope)
    1.2. [目標讀者 (Target Audience)](#12-目標讀者-target-audience)
    1.3. [術語表 (Glossary)](#13-術語表-glossary)
2.  [架構概述與目標 (Architecture Overview and Goals)](#2-架構概述與目標-architecture-overview-and-goals)
    2.1. [架構目標與原則 (Architectural Goals and Principles)](#21-架構目標與原則-architectural-goals-and-principles)
    2.2. [主要制約因素與假設 (Key Constraints and Assumptions)](#22-主要制約因素與假設-key-constraints-and-assumptions)
3.  [需求回顧 (Requirements Revisited)](#3-需求回顧-requirements-revisited)
    3.1. [功能性需求摘要 (Functional Requirements Summary)](#31-功能性需求摘要-functional-requirements-summary)
    3.2. [非功能性需求 (Non-Functional Requirements - NFRs)](#32-非功能性需求-non-functional-requirements---nfrs)
4.  [高層次架構設計 (High-Level Architectural Design)](#4-高層次架構設計-high-level-architectural-design)
    4.1. [選定的架構模式 (Chosen Architectural Pattern)](#41-選定的架構模式-chosen-architectural-pattern)
    4.2. [系統組件圖 (System Component Diagram)](#42-系統組件圖-system-component-diagram)
    4.3. [主要組件/服務及其職責 (Key Components/Services and Responsibilities)](#43-主要組件服務及其職責-key-componentsservices-and-responsibilities)
    4.4. [資料流圖 (Data Flow Diagrams - DFDs)](#44-資料流圖-data-flow-diagrams---dfds)
    4.5. [請求流時序圖 (Request Flow Sequence Diagram)](#45-請求流時序圖-request-flow-sequence-diagram)
5.  [技術選型詳述 (Technology Stack Details)](#5-技術選型詳述-technology-stack-details)
6.  [可行性分析概要 (Feasibility Analysis Summary)](#6-可行性分析概要-feasibility-analysis-summary)
7.  [Production Readiness Checklist (PRC) - 初步考量](#7-production-readiness-checklist-prc---初步考量)
8.  [未來展望與演進方向 (Future Considerations and Evolution)](#8-未來展望與演進方向-future-considerations-and-evolution)

---

## 1. 引言 (Introduction)

### 1.1 目的與範圍 (Purpose and Scope)
*   **目的 (Purpose):** 為「Model API 即時監控系統」提供一個清晰、一致的高層次架構藍圖，用以指導後續的詳細設計、開發實施和團隊溝通。
*   **範圍 (Scope):** 本文檔涵蓋了系統的整體架構、核心組件設計、數據流、技術選型以及關鍵的非功能性需求考量。範圍限定在 MVP 版本，核心是實現對現有基於 Docker 的 Model API 進行即時性能監控。

### 1.2 目標讀者 (Target Audience)
*   開發團隊、架構師、MLOps 工程師、產品經理、維運團隊及技術主管。

### 1.3 術語表 (Glossary)

| 術語/縮寫 | 完整名稱/解釋 |
| :------- | :----------- |
| MLOps    | Machine Learning Operations，機器學習維運。 |
| QPS      | Queries Per Second，每秒查詢數。 |
| P95 延遲 | 95th Percentile Latency，第95百分位的延遲時間，代表95%的請求延遲都低於此值。 |
| Interceptor | 攔截器，以非侵入式方式（如 Middleware）攔截 API 請求以收集數據的組件。 |
| EDA      | Event-Driven Architecture，事件驅動架構。 |

---

## 2. 架構概述與目標 (Architecture Overview and Goals)

### 2.1 架構目標與原則 (Architectural Goals and Principles)
*   **架構目標 (Goals):**
    *   **高可觀測性 (High Observability):** 系統的核心目標，必須提供即時、準確、易於理解的監控數據。
    *   **低侵入性/低開銷 (Low Intrusion/Overhead):** 對被監控的 Model API 性能影響必須降至最低（< 5% 的額外延遲）。
    *   **可擴展性 (Scalability):** 系統應能平滑擴展，以支持未來監控數十個甚至上百個 Model API 實例。
    *   **可維護性 (Maintainability):** 模組化的設計，使得新增監控指標或支持新型模型變得容易。
*   **設計原則 (Principles):**
    *   **事件驅動 (Event-Driven):** 指標的收集、傳輸和處理採用異步事件驅動模式，實現組件解耦和系統彈性。
    *   **關注點分離 (Separation of Concerns):** 明確劃分指標收集、數據處理、數據存儲和數據展示的職責。
    *   **非侵入式監控 (Non-invasive Monitoring):** 盡可能不修改現有 Model API 的業務代碼。
    *   **API 優先 (API-First):** 後端服務需提供清晰的 API 供前端或其他服務消費。

### 2.2 主要制約因素與假設 (Key Constraints and Assumptions)
*   **制約因素 (Constraints):**
    *   **技術棧:** 必須與現有 MLOps 環境兼容，優先使用 Python 生態系。
    *   **時間線:** MVP 版本需在 3 週內完成開發。
    *   **基礎設施:** 監控目標 (Model API) 已在 Docker 環境中運行。
*   **假設 (Assumptions):**
    *   被監控的 Model API 服務是可信的內部服務，具有網路可達性。
    *   可以透過 Docker API 或其他方式獲取容器的資源使用數據。
    *   可以為 Model API 添加監控攔截器 (Middleware)。

---

## 3. 需求回顧 (Requirements Revisited)

### 3.1 功能性需求摘要 (Functional Requirements Summary)
*   **即時儀表板:** 視覺化展示 QPS、延遲、錯誤率等核心指標。(對應 US-001)
*   **性能指標收集:** 攔截 API 請求，收集並發送性能數據。(對應 US-002)
*   **資源監控:** 監控 Docker 容器的 CPU 和記憶體使用情況。(對應 US-003)
*   **基本告警:** 當關鍵指標超過預設閾值時，在儀表板上顯示告警。(對應 US-004)
*   **歷史數據查詢:** 能夠查詢並展示過去24小時的性能趨勢。(對應 US-005)

### 3.2 非功能性需求 (Non-Functional Requirements - NFRs)

| NFR 分類         | 具體需求描述                               | 目標值 (MVP)                            |
| :--------------- | :----------------------------------------- | :---------------------------------------- |
| **性能 (Performance)** | 監控代理造成的額外 API 延遲                | `< 20ms`                                  |
|                  | 儀表板數據更新延遲                         | `< 5s`                                    |
| **可擴展性 (Scalability)** | MVP 版本支援的 Model API 實例數量        | `5+`                                      |
|                  | 架構設計應能支持的實例數量                 | `50+`                                     |
| **可用性 (Availability)** | 監控系統核心服務的年可用性               | `99.5%`                                   |
| **安全性 (Security)**   | 服務間通信                               | 內部網路，但密碼等敏感配置需透過環境變數管理 |
| **可維護性 (Maintainability)** | 新增一個同類型的 Model API 監控所需時間 | `< 1 小時` (配置)                          |

---

## 4. 高層次架構設計 (High-Level Architectural Design)

### 4.1 選定的架構模式 (Chosen Architectural Pattern)
*   本系統採用 **事件驅動架構 (Event-Driven Architecture, EDA)** 作為核心，並結合 **分層架構 (Layered Architecture)**。
*   **選擇理由:**
    *   **解耦與彈性:** EDA 使得指標收集器（生產者）與後端處理服務（消費者）完全解耦。即使後端服務短暫不可用，指標數據也能暫存在 RabbitMQ 中，提高了系統的可靠性和彈性。
    *   **擴展性:** 當監控流量增加時，可以獨立地擴展後端處理服務（增加消費者數量），而無需改動指標收集器。
    *   **分層清晰:** 在前端、後端服務內部，採用經典的分層架構（表現層、業務邏輯層、數據訪問層），使得各層職責清晰，易於開發和維護。

### 4.2 系統組件圖 (System Component Diagram)
```mermaid
graph TD
    subgraph "使用者瀏覽器"
        Dashboard[Vue.js 監控儀表板]
    end

    subgraph "監控系統後端 (Docker)"
        Backend[FastAPI 後端服務<br/>- REST API<br/>- WebSocket]
        Processor[指標處理服務<br/>(Consumer)]
        RabbitMQ[RabbitMQ<br/>事件佇列]
        PostgreSQL[PostgreSQL<br/>歷史指標數據]
        Redis[Redis<br/>即時數據快取]
    end

    subgraph "現有 Model API 環境 (Docker)"
        ModelAPI["現有 Model API<br/>(e.g., FastAPI, Flask)"]
        Interceptor["監控攔截器<br/>(Middleware)"]
    end
    
    Dashboard -- "HTTP/WebSocket" --> Backend
    Backend -- "讀寫" --> Redis
    Backend -- "讀取" --> PostgreSQL
    
    ModelAPI -- "攔截請求/響應" --> Interceptor
    Interceptor -- "異步發送指標事件" --> RabbitMQ
    
    Processor -- "消費指標事件" --> RabbitMQ
    Processor -- "寫入" --> PostgreSQL
    Processor -- "寫入" -- > Redis

```
*   **圖示說明:**
    *   使用者透過 **Vue.js 儀表板** 訪問系統。
    *   **監控攔截器** 作為 Middleware 嵌入到現有的 **Model API** 中，它捕獲請求和響應信息，生成指標事件並異步發送到 **RabbitMQ**。
    *   **指標處理服務** 作為消費者，從 RabbitMQ 獲取事件，處理後將數據寫入 **PostgreSQL** (用於歷史分析) 和 **Redis** (用於即時儀表板)。
    *   **FastAPI 後端服務** 提供 REST API 和 WebSocket，前端儀表板透過它們從 Redis 和 PostgreSQL 獲取數據並即時展示。

### 4.3 主要組件/服務及其職責 (Key Components/Services and Responsibilities)

| 組件/服務名稱 | 核心職責 | 主要技術 |
| :-------------- | :----------------------------------------------------------- | :------------- |
| **監控攔截器** | 非侵入式地攔截 API 請求，收集延遲、狀態碼等原始數據，並將其作為事件發送到 RabbitMQ。 | Python Middleware |
| **RabbitMQ** | 作為異步事件佇列，緩衝並傳遞來自攔截器的指標事件，實現生產者和消費者的解耦。 | RabbitMQ |
| **指標處理服務** | 從 RabbitMQ 消費指標事件，進行聚合計算，並將結果持久化到 PostgreSQL 和 Redis。 | Python, Pika |
| **PostgreSQL** | 長期存儲聚合後的歷史指標數據，用於趨勢分析和報告。建議使用 TimescaleDB 擴展。 | PostgreSQL |
| **Redis** | 存儲最新的、用於即時儀表板展示的指標數據和狀態，提供快速讀取。 | Redis |
| **FastAPI 後端服務** | 提供數據查詢的 REST API 和用於即時推送的 WebSocket 端點。 | FastAPI |
| **Vue.js 儀表板** | 負責數據的視覺化展示，透過 WebSocket 實現圖表和指標的即時更新。 | Vue.js, Chart.js |

### 4.4 資料流圖 (Data Flow Diagrams - DFDs)
*   **DFD 0: 指標收集與處理流程**
    ```mermaid
    graph TD
        A(Model API Interceptor) -- "指標事件 (JSON)" --> B{RabbitMQ Event Queue}
        B -- "讀取事件" --> C(指標處理服務)
        C -- "寫入歷史數據" --> D[PostgreSQL]
        C -- "更新即時數據" --> E[Redis Cache]
        F(儀表板後端) -- "查詢" --> D
        F -- "查詢" --> E
        G(前端儀表板) -- "請求/訂閱" --> F
    ```

### 4.5 請求流時序圖 (Request Flow Sequence Diagram)
*   **場景: 一個被監控的 API 請求處理流程**
    ```mermaid
    sequenceDiagram
        participant C as Client
        participant M as Model API
        participant I as Interceptor
        participant R as RabbitMQ
        
        C->>+M: /predict request
        M->>I: before_request (start_time)
        Note right of I: 核心業務邏輯執行
        M-->>I: after_request (status_code)
        I->>I: duration = now() - start_time
        I-->>-M: response
        M-->>-C: final response
        
        par 非同步
            I->>R: publish({duration, status_code, ...})
        end
    ```

---

## 5. 技術選型詳述 (Technology Stack Details)
*   **前端:** Vue 3 + TypeScript + Tailwind CSS + Chart.js
    *   **理由:** 現代、高效的開發體驗，TypeScript 保證類型安全，Tailwind CSS 快速構建界面，Chart.js 滿足圖表需求。
*   **後端:** FastAPI + Uvicorn
    *   **理由:** 基於 Python 類型提示，性能高，開發速度快，自動生成 API 文檔，非常適合構建 API 服務。
*   **資料庫與儲存:**
    *   **PostgreSQL (+ TimescaleDB extension):** 成熟可靠的開源關聯式資料庫。TimescaleDB 擴展專為時間序列數據優化，非常適合存儲監控指標。
    *   **Redis:** 高性能的內存數據庫，用作即時數據快取，性能優異。
*   **訊息佇列:** RabbitMQ
    *   **理由:** 成熟、穩定，支持多種消息模式，社區活躍，與 Python 集成良好，完全滿足本專案的異步解耦需求。
*   **基礎設施與部署:** Docker + Docker Compose
    *   **理由:** 實現開發、測試和生產環境的一致性，簡化部署流程。

---

## 6. 可行性分析概要 (Feasibility Analysis Summary)

*   **技術可行性:** 非常高。所選技術均為主流開源技術，有成熟的解決方案和活躍的社區支持。核心挑戰在於設計一個通用且低開銷的監控攔截器。
*   **經濟可行性:** 非常高。所有核心組件均為開源軟體，無授權費用。主要成本為開發人力和雲端伺服器資源。
*   **時程可行性:** 實際。PRD 中定義的 MVP 範疇清晰，3 週的開發週期在專注投入的情況下是可行的。
*   **關鍵風險:** 主要風險與 PRD 中識別的一致，即監控代理的性能影響和與現有 API 的整合複雜度。緩解措施為前期充分測試和提供清晰的整合文檔。

---

## 7. Production Readiness Checklist (PRC) - 初步考量

*   **可觀測性:** 如何監控本監控系統？需為 FastAPI 後端、指標處理服務等核心組件添加 Health Check 端點。監控 RabbitMQ 的佇列深度。
*   **可擴展性:** 性能瓶頸最可能出現在指標處理服務。該服務應設計為無狀態，以便可以簡單地水平擴展（啟動多個實例消費同一個佇列）。
*   **安全性與機密管理:** 所有服務的密碼（如資料庫、RabbitMQ）必須通過環境變數或 Secrets Management 工具注入，不能硬編碼。
*   **可靠性與容錯:** 指標處理服務需要實現冪等性，防止因消息重傳導致數據重複計算。攔截器發送消息到 RabbitMQ 應有重試機制。
*   **部署與回滾:** 使用 Docker Compose 管理部署，更新時可採用滾動更新策略。所有變更需有版本控制，確保可回滾。

---

## 8. 未來展望與演進方向

*   **告警增強:** 集成 Email、Slack 或 PagerDuty，實現更主動的告警通知。
*   **標準化:** 採用 OpenTelemetry 標準來收集和傳輸指標，以獲得更好的通用性和擴展性。
*   **分析能力:** 引入更複雜的異常檢測算法，自動發現性能問題。
*   **追蹤集成:** 增加分散式追蹤功能，以可視化單個請求在整個系統中的完整生命週期。

---
**文件審核記錄 (Review History):**

| 日期       | 審核人     | 版本 | 變更摘要/主要反饋 |
| :--------- | :--------- | :--- | :---------------- |
| 2025-07-01 | Vibe Coder | v0.1 | 初稿建立           | 