# 類別組件關係文檔 (Class Relationships Document) - [專案名稱]

---

**文件版本 (Document Version):** `v1.0`

**最後更新 (Last Updated):** `YYYY-MM-DD`

**主要作者 (Lead Author):** `[請填寫]`

**審核者 (Reviewers):** `[列出主要審核人員/團隊]`

**狀態 (Status):** `[例如：草稿 (Draft), 審核中 (In Review), 已批准 (Approved)]`

**相關設計文檔 (Related Design Documents):**
*   專案檔案結構文檔: `[連結到 07_project_structure_document.md]`
*   檔案相依關係文檔: `[連結到 08_file_dependencies_document.md]`
*   系統架構文檔: `[連結到 02_system_architecture_document.md]`

---

## 目錄 (Table of Contents)

1.  [概述 (Overview)](#1-概述-overview)
2.  [核心類別架構 (Core Class Architecture)](#2-核心類別架構-core-class-architecture)
3.  [類別分層結構 (Class Layer Structure)](#3-類別分層結構-class-layer-structure)
4.  [關係類型詳解 (Relationship Types Details)](#4-關係類型詳解-relationship-types-details)
5.  [設計模式應用 (Design Pattern Applications)](#5-設計模式應用-design-pattern-applications)
6.  [接口契約 (Interface Contracts)](#6-接口契約-interface-contracts)
7.  [擴展性考量 (Extensibility Considerations)](#7-擴展性考量-extensibility-considerations)
8.  [類別職責分離 (Class Responsibility Separation)](#8-類別職責分離-class-responsibility-separation)

---

## 1. 概述 (Overview)

### 1.1 文檔目的 (Document Purpose)
*   `[描述本文檔的主要目的，例如：使用 Mermaid 類別圖描述 [專案名稱] 中主要類別之間的關係，包括繼承、組合、依賴和接口定義。]`

### 1.2 類別建模範圍 (Class Modeling Scope)
*   **包含範圍**: `[例如：核心業務類別、資料模型、服務類別、控制器類別]`
*   **排除範圍**: `[例如：工具類別、測試類別、第三方框架類別]`
*   **抽象層級**: `[例如：主要類別和接口，不包括私有方法細節]`

### 1.3 UML 符號說明 (UML Notation Conventions)
*   **繼承關係**: `[例如：--|> 表示繼承 (is-a 關係)]`
*   **組合關係**: `[例如：*-- 表示組合 (has-a 關係，強擁有)]`
*   **聚合關係**: `[例如：o-- 表示聚合 (has-a 關係，弱擁有)]`
*   **依賴關係**: `[例如：..> 表示依賴 (uses 關係)]`
*   **實現關係**: `[例如：..|> 表示實現接口]`

---

## 📝 使用指南 (Usage Guide)

### 如何使用此模板 (How to Use This Template)
1. **複製模板**: 將此檔案複製並重新命名為 `03_class_relationships.md`
2. **填寫基本資訊**: 更新文檔頭部的版本、日期、作者等資訊
3. **替換佔位符**: 將所有 `[...]` 佔位符替換為專案實際內容
4. **繪製類別圖**: 使用 Mermaid 繪製實際的類別關係圖
5. **定義契約**: 完成接口契約和方法規範定義
6. **驗證設計**: 檢查 SOLID 原則和設計品質 