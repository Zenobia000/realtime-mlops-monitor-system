# 專案檔案結構文檔 (Project Structure Document) - [專案名稱]

---

**文件版本 (Document Version):** `v1.0`

**最後更新 (Last Updated):** `YYYY-MM-DD`

**主要作者 (Lead Author):** `[請填寫]`

**審核者 (Reviewers):** `[列出主要審核人員/團隊]`

**狀態 (Status):** `[例如：草稿 (Draft), 審核中 (In Review), 已批准 (Approved), 活躍 (Active), 已歸檔 (Archived)]`

**相關設計文檔 (Related Design Documents):**
*   系統架構文檔 (SA): `[連結到 02_system_architecture_document.md]`
*   檔案相依關係文檔: `[連結到 08_file_dependencies_document.md]`
*   類別組件關係文檔: `[連結到 09_class_relationships_document.md]`

---

## 目錄 (Table of Contents)

1.  [概述 (Overview)](#1-概述-overview)
2.  [專案根目錄結構 (Project Root Structure)](#2-專案根目錄結構-project-root-structure)
3.  [核心模組詳解 (Core Modules Details)](#3-核心模組詳解-core-modules-details)
4.  [依賴管理 (Dependency Management)](#4-依賴管理-dependency-management)
5.  [開發階段對應 (Development Phase Mapping)](#5-開發階段對應-development-phase-mapping)
6.  [部署文件結構 (Deployment File Structure)](#6-部署文件結構-deployment-file-structure)
7.  [文檔組織 (Documentation Organization)](#7-文檔組織-documentation-organization)
8.  [專案統計資訊 (Project Statistics)](#8-專案統計資訊-project-statistics)

---

## 1. 概述 (Overview)

### 1.1 專案架構類型 (Project Architecture Type)
*   **架構風格**: `[例如：分層架構、微服務架構、插件架構]`
*   **技術棧**: `[例如：Python + FastAPI + PostgreSQL + Docker]`
*   **專案規模**: `[例如：中型專案，預計 100+ 檔案]`

### 1.2 目錄組織原則 (Directory Organization Principles)
*   **[原則1]**: `[例如：按功能模組組織 - 相關功能放在同一目錄]`
*   **[原則2]**: `[例如：按類型分離 - 配置、代碼、文檔分開]`
*   **[原則3]**: `[例如：環境隔離 - 開發、測試、生產環境分離]`

### 1.3 命名約定 (Naming Conventions)
*   **目錄名稱**: `[例如：小寫字母，使用底線分隔]`
*   **檔案名稱**: `[例如：描述性名稱，避免縮寫]`
*   **配置檔案**: `[例如：.env, config.yaml, settings.json]`

---

## 📝 使用指南 (Usage Guide)

### 如何使用此模板 (How to Use This Template)
1. **複製模板**: 將此檔案複製並重新命名為 `01_project_structure.md`
2. **填寫基本資訊**: 更新文檔頭部的版本、日期、作者等資訊
3. **替換佔位符**: 將所有 `[...]` 佔位符替換為專案實際內容
4. **調整目錄結構**: 根據專案實際情況調整目錄樹狀圖
5. **更新統計資訊**: 定期更新檔案統計和複雜度指標
6. **維護里程碑**: 隨專案進展更新開發階段狀態

---

## 2. 專案根目錄結構 (Project Root Structure)

### 2.1 整體目錄樹 (Overall Directory Tree)
*   `[在此提供完整的專案目錄結構。建議使用樹狀格式，並在重要目錄/檔案後加上註解。]`

```
[project_name]/
├── 0_[phase1_name]/                    # [階段1描述，例如：需求發現階段]
│   ├── [subdirectory1]/
│   │   └── [important_files]
│   ├── [subdirectory2]/
│   └── README.md
│
├── 1_[phase2_name]/                    # [階段2描述，例如：系統設計階段]
│   ├── [design_subdirectory]/
│   ├── architecture/                  # ★ [重要模組說明]
│   │   ├── 07_project_structure.md    # 本檔案
│   │   ├── 08_file_dependencies.md    # [檔案相依關係]
│   │   └── 09_class_relationships.md  # [類別組件關係]
│   └── README.md
│
├── 2_[implementation_phase]/           # ★ [核心實作階段]
│   ├── src/                           # [主要源代碼目錄]
│   │   ├── [core_module1]/            # [核心模組1說明]
│   │   │   ├── __init__.py
│   │   │   ├── [main_component].py    # [主要組件說明]
│   │   │   └── [sub_modules]/         # [子模組目錄]
│   │   ├── [core_module2]/            # [核心模組2說明]
│   │   └── [utils]/                   # [共用工具]
│   │
│   ├── tests/                         # [測試套件]
│   │   ├── unit/                      # [單元測試]
│   │   ├── integration/               # [整合測試]
│   │   └── e2e/                       # [端對端測試]
│   │
│   ├── [test_scripts]/                # [測試腳本]
│   ├── [build_scripts]/               # [構建腳本]
│   ├── requirements.txt               # [依賴清單]
│   └── README.md
│
├── 3_[validation_phase]/              # [測試驗證階段]
├── 4_[deployment_phase]/              # [部署上線階段]
├── config/                            # [配置檔案]
├── docs/                              # [技術文檔]
├── design_templates/                  # [設計文檔模板]
├── [container_config].yml             # [容器編排配置]
└── README.md                          # [專案主 README]
```

### 2.2 目錄命名約定 (Directory Naming Conventions)
*   `[說明目錄命名的約定和原則]`
    *   **階段式目錄**: `[例如：使用數字前綴表示開發階段 (0_, 1_, 2_, 3_, 4_)]`
    *   **功能性目錄**: `[例如：src/, tests/, docs/, config/]`
    *   **語言約定**: `[例如：英文小寫，使用下劃線或連字符]`

---

## 3. 核心模組詳解 (Core Modules Details)

### 3.1 [核心模組1名稱] (`src/[module1]/`)

| 檔案 | 用途 | 主要功能/特性 |
|------|------|---------------|
| `__init__.py` | `[模組初始化]` | `[例如：匯出所有公開 API]` |
| `[component1].py` | `[組件1用途]` | `[主要類別/函數列表]` |
| `[component2].py` | `[組件2用途]` | `[主要類別/函數列表]` |
| `[submodule]/` | `[子模組用途]` | `[子模組功能說明]` |

### 3.2 [核心模組2名稱] (`src/[module2]/`)

| 檔案 | 用途 | 主要功能/特性 |
|------|------|---------------|
| `[...]` | `[...]` | `[...]` |

*   `[繼續列出其他重要的核心模組...]`

### 3.3 測試和工具檔案 (Testing and Utility Files)

| 檔案 | 用途 | 執行方式 |
|------|------|----------|
| `[test_script1].py` | `[測試用途1]` | `[執行命令]` |
| `[test_script2].py` | `[測試用途2]` | `[執行命令]` |
| `[build_tool].py` | `[構建工具用途]` | `[執行命令]` |

### 3.4 配置和設置檔案 (Configuration Files)

| 檔案 | 用途 | 格式 |
|------|------|------|
| `requirements.txt` | `[依賴管理]` | `[格式說明]` |
| `[config_file].toml` | `[專案配置]` | `[配置格式]` |
| `[env_file].example` | `[環境變數範本]` | `[環境變數格式]` |

---

## 4. 依賴管理 (Dependency Management)

### 4.1 [主要語言] 依賴 (`[dependency_file]`)
```text
[dependency1]==[version]          # [依賴用途說明]
[dependency2]==[version]          # [依賴用途說明]
[dependency3]==[version]          # [依賴用途說明]
```

### 4.2 開發依賴 (Development Dependencies)
```text
[dev_dependency1]==[version]      # [開發工具用途]
[dev_dependency2]==[version]      # [測試框架用途]
```

### 4.3 依賴管理策略 (Dependency Management Strategy)
*   **鎖定版本**: `[是否使用鎖定檔案，例如：poetry.lock, package-lock.json]`
*   **安全更新**: `[依賴安全掃描和更新策略]`
*   **許可證合規**: `[開源許可證檢查策略]`

---

## 5. 開發階段對應 (Development Phase Mapping)

*   `[將專案目錄結構與開發流程階段進行對應，說明每個階段的主要交付物。]`

| [開發階段] | 目錄 | 狀態 | 主要交付物 |
|------------|------|------|------------|
| [Phase 1.x] | `[directory1]` | `[狀態：✅ 完成 / ⏳ 進行中 / ❌ 待開始]` | `[主要交付物描述]` |
| [Phase 2.x] | `[directory2]` | `[狀態]` | `[主要交付物描述]` |
| [Phase 3.x] | `[directory3]` | `[狀態]` | `[主要交付物描述]` |

---

## 6. 部署文件結構 (Deployment File Structure)

*   `[描述部署文件的結構和用途]`

### 6.1 部署配置檔案 (Deployment Configuration Files)
*   **[配置檔案名稱]**: `[配置檔案路徑]` `([主要用途])`

### 6.2 環境配置檔案 (Environment Configuration Files)
*   **[環境配置名稱]**: `[環境配置路徑]` `([主要用途])`

### 6.3 依賴定義檔案 (Dependency Definition Files)
*   **[依賴定義名稱]**: `[依賴定義路徑]` `([主要用途])`

---

## 7. 文檔組織 (Documentation Organization)

*   `[描述文檔的組織結構和用途]`

### 7.1 技術文檔 (Technical Documentation)
*   **[技術文檔名稱]**: `[技術文檔路徑]` `([主要用途])`

### 7.2 專案文檔 (Project Documentation)
*   **[專案文檔名稱]**: `[專案文檔路徑]` `([主要用途])`

### 7.3 開發文檔 (Development Documentation)
*   **[開發文檔名稱]**: `[開發文檔路徑]` `([主要用途])`

---

## 8. 專案統計資訊 (Project Statistics)

*   `[提供專案檔案的統計資訊，幫助了解專案規模。]`

```
總檔案數量: [X]+ 檔案
├── [語言] 源碼: [X] 檔案 (~[X] 行)
│   ├── [模組1]: [X] 檔案 (~[X] 行)
│   ├── [模組2]: [X] 檔案 (~[X] 行)
│   └── [模組3]: [X] 檔案 (~[X] 行)
├── [腳本類型]: [X] 檔案 (~[X] 行)
├── 配置檔案: [X] 檔案
├── 文檔檔案: [X] 檔案 (~[X] 行)
├── 測試檔案: [X] 檔案 (~[X] 行)
└── 其他工具: [X] 檔案 (~[X] 行)
```

### 8.1 代碼複雜度統計 (Code Complexity Statistics - 選填)
*   **平均檔案大小**: `[X] 行`
*   **最大檔案**: `[檔案名] ([X] 行)`
*   **測試覆蓋率**: `[X]%` (若適用)
*   **技術債務**: `[評估等級]` (若適用)

---

## 📝 使用指南 (Usage Guide)

### 如何使用此模板 (How to Use This Template)
1. **複製模板**: 將此檔案複製並重新命名為 `01_project_structure.md`
2. **填寫基本資訊**: 更新文檔頭部的版本、日期、作者等資訊
3. **替換佔位符**: 將所有 `[...]` 佔位符替換為專案實際內容
4. **調整目錄結構**: 根據專案實際情況調整目錄樹狀圖
5. **更新統計資訊**: 定期更新檔案統計和複雜度指標
6. **維護里程碑**: 隨專案進展更新開發階段狀態

### 最佳實踐建議 (Best Practice Recommendations)
*   **保持同步**: 確保文檔與實際專案結構同步
*   **層級清晰**: 使用一致的目錄層級和命名約定
*   **重點突出**: 使用 ★ 或其他標記突出重要檔案/目錄
*   **統計更新**: 定期更新檔案統計資訊
*   **版本控制**: 重要變更時更新版本號和變更記錄 