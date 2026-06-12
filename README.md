# ETF 投資組合研究實驗室 (ETF Portfolio Lab)

## 專案說明

ETF 投資組合研究實驗室是一套用於分析交易所交易基金 (ETF) 的研究工具，專注於：

- **ETF 分類與追蹤**：瞭解 ETF 的分類、成分股構成與費用結構
- **成分股分析**：深入分析 ETF 內含的持股及其權重分佈
- **重疊分析**：檢視多個 ETF 之間的持股重疊情況
- **歷史回測**：基於歷史資料進行投資組合績效回測
- **財務模擬**：模擬未來投資情景下的預期表現

**重要提醒**：本工具為研究分析用途，回測結果 **不代表未來績效**。任何投資決策應結合專業金融顧問建議。

## 技術堆疊

- **後端**：Python FastAPI + SQLAlchemy + PostgreSQL
- **前端**：Next.js + TypeScript + React
- **資料庫**：PostgreSQL 16
- **容器化**：Docker & Docker Compose

## 環境需求

- Docker & Docker Compose
- Git

## 快速開始

### 1. 複製環境變數設定

```bash
cp .env.example .env
```

### 2. 啟動容器

```bash
docker compose up
```

### 3. 訪問應用

- **前端**：http://localhost:3000
- **後端 API 文件**：http://localhost:8000/docs

## 專案結構

```
etf-portfolio-lab/
├── backend/          # FastAPI 後端應用
│   ├── app/
│   ├── tests/
│   └── pyproject.toml
├── frontend/         # Next.js 前端應用
│   ├── app/
│   ├── components/
│   └── package.json
├── data/             # 資料目錄
│   ├── raw/          # 原始資料
│   ├── processed/    # 處理後資料
│   └── samples/      # 樣本資料
├── docs/             # 文件
├── docker-compose.yml
├── .env.example
└── README.md
```

## 詳細規格文件

本專案基於以下設計文件開發：

- [01_PRODUCT_REQUIREMENTS.md](01_PRODUCT_REQUIREMENTS.md) - 產品需求
- [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md) - 系統架構
- [03_IMPLEMENTATION_PLAN.md](03_IMPLEMENTATION_PLAN.md) - 實作計劃
- [04_DATA_MODEL_AND_SCHEMA.md](04_DATA_MODEL_AND_SCHEMA.md) - 資料模型
- [05_DATA_SOURCES_AND_PROVIDER_STRATEGY.md](05_DATA_SOURCES_AND_PROVIDER_STRATEGY.md) - 資料來源策略
- [06_ANALYTICS_BACKTEST_PROJECTION_SPEC.md](06_ANALYTICS_BACKTEST_PROJECTION_SPEC.md) - 回測與投影規格
- [07_UX_UI_DESIGN_SPEC.md](07_UX_UI_DESIGN_SPEC.md) - UI/UX 設計規格
- [08_AGENT_MODEL_DELEGATION_POLICY.md](08_AGENT_MODEL_DELEGATION_POLICY.md) - 模型分工政策
- [09_DEVELOPMENT_TASK_BREAKDOWN.md](09_DEVELOPMENT_TASK_BREAKDOWN.md) - 開發任務拆解
- [10_ACCEPTANCE_CRITERIA_AND_QA.md](10_ACCEPTANCE_CRITERIA_AND_QA.md) - 驗收標準與 QA
- [11_SAMPLE_CLAUDE_START_PROMPT.md](11_SAMPLE_CLAUDE_START_PROMPT.md) - Claude 初始提示

## 開發與貢獻

本專案遵守 [CLAUDE.md](CLAUDE.md) 中定義的開發流程與模型分工政策。

## 免責聲明

本工具提供的回測結果與分析建議僅供研究參考，**不構成投資建議**。過去表現不保證未來績效。使用者應根據自身風險承受能力與投資目標，結合專業金融顧問的意見做出投資決策。
