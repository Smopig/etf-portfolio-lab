# 02_SYSTEM_ARCHITECTURE.md — ETF Portfolio Lab 系統架構

---

## 1. 架構總覽

```text
ETF Portfolio Lab
│
├── Frontend：Next.js + React + TypeScript
│   ├── Dashboard
│   ├── ETF Detail
│   ├── ETF Compare
│   ├── Portfolio Builder
│   ├── Backtest
│   ├── Projection
│   ├── Data Sources
│   └── AI Assistant
│
├── Backend：Python FastAPI
│   ├── ETF API
│   ├── Holding API
│   ├── Industry API
│   ├── Portfolio API
│   ├── Backtest API
│   ├── Projection API
│   ├── Data Import API
│   └── AI Analysis API
│
├── Database：PostgreSQL
│   ├── ETF 主檔
│   ├── 成分股
│   ├── 持股快照
│   ├── 股票產業分類
│   ├── 歷史價格
│   ├── 配息資料
│   ├── Portfolio
│   ├── Backtest runs
│   └── Data source registry
│
├── Data Processing：pandas / numpy
│   ├── 匯入清洗
│   ├── 曝險計算
│   ├── 重疊度計算
│   ├── 回測
│   └── 財務模擬
│
├── Provider Layer
│   ├── CSV / Excel Provider
│   ├── TWSE Provider
│   ├── Yahoo Finance Provider
│   ├── Fund Company Provider
│   └── Manual Upload Provider
│
└── AI Layer
    ├── Claude Provider
    ├── MiniMax Provider
    ├── OpenAI Provider
    ├── Gemini Provider
    └── Mock Provider
```

---

## 2. 技術選型

### 2.1 Frontend

建議：

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- ECharts 或 Recharts
- TanStack Table

原因：

- 適合資料密集型 Web App
- 適合建立互動式金融研究工具
- TypeScript 可降低資料欄位錯誤
- Tailwind + shadcn 可建立一致 UI
- ECharts 適合複雜圖表與金融分析圖

---

### 2.2 Backend

建議：

- Python FastAPI
- Pydantic
- pandas
- numpy
- SQLAlchemy / SQLModel
- Alembic
- APScheduler

原因：

- Python 適合金融資料處理
- pandas 適合 ETF 成分股、價格、配息與回測計算
- FastAPI 適合資料 API
- Pydantic 可確保資料格式一致
- APScheduler 可支援每日 / 每週資料更新

---

### 2.3 Database

建議：

- PostgreSQL

原因：

- 適合長期保存 ETF 歷史資料
- 關聯查詢能力強
- 可支援 JSONB 儲存 metadata
- 未來可升級 TimescaleDB
- 適合 Docker Compose 開發環境

---

### 2.4 Data Provider Abstraction

外部資料來源不可直接寫進 service。

必須設計：

```text
BaseDataProvider
│
├── CsvProvider
├── ExcelProvider
├── TwseProvider
├── YahooFinanceProvider
├── YuantaProvider
├── CathayProvider
├── FubonProvider
└── ManualUploadProvider
```

---

## 3. 專案目錄建議

```text
etf-portfolio-lab/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   │
│   │   ├── models/
│   │   │   ├── etf.py
│   │   │   ├── holding.py
│   │   │   ├── industry.py
│   │   │   ├── price.py
│   │   │   ├── dividend.py
│   │   │   ├── portfolio.py
│   │   │   └── data_source.py
│   │   │
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── import_service.py
│   │   │   ├── exposure_service.py
│   │   │   ├── overlap_service.py
│   │   │   ├── portfolio_service.py
│   │   │   ├── backtest_service.py
│   │   │   ├── projection_service.py
│   │   │   └── ai_analysis_service.py
│   │   │
│   │   ├── providers/
│   │   │   ├── base_provider.py
│   │   │   ├── csv_provider.py
│   │   │   ├── excel_provider.py
│   │   │   ├── twse_provider.py
│   │   │   ├── yahoo_provider.py
│   │   │   └── fund_company_provider.py
│   │   │
│   │   ├── api/
│   │   │   ├── etfs.py
│   │   │   ├── holdings.py
│   │   │   ├── industries.py
│   │   │   ├── portfolios.py
│   │   │   ├── backtests.py
│   │   │   ├── projections.py
│   │   │   ├── data_import.py
│   │   │   └── ai.py
│   │   │
│   │   └── utils/
│   │       ├── finance_math.py
│   │       ├── data_quality.py
│   │       └── date_utils.py
│   │
│   ├── scripts/
│   ├── tests/
│   ├── pyproject.toml
│   └── .env.example
│
├── frontend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── etf/[symbol]/
│   │   ├── compare/
│   │   ├── portfolio/
│   │   ├── backtest/
│   │   ├── projection/
│   │   ├── data-sources/
│   │   └── ai/
│   │
│   ├── components/
│   │   ├── charts/
│   │   ├── tables/
│   │   ├── etf/
│   │   ├── portfolio/
│   │   └── layout/
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   └── format.ts
│   │
│   └── package.json
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── samples/
│
├── docs/
│
├── docker-compose.yml
├── README.md
└── .env.example
```

---

## 4. 資料流

```text
外部資料 / CSV / Excel
↓
Provider Layer
↓
Import Service
↓
Data Quality Check
↓
PostgreSQL
↓
Analysis Services
↓
FastAPI Endpoints
↓
Next.js Frontend
↓
AI Analysis Layer
```

---

## 5. API 分層

### ETF 基本資料

- `GET /api/etfs`
- `GET /api/etfs/{symbol}`

### ETF 成分股

- `GET /api/etfs/{symbol}/holdings`
- `GET /api/etfs/{symbol}/top-holdings`
- `GET /api/etfs/{symbol}/concentration`

### 產業曝險

- `GET /api/etfs/{symbol}/industry-exposure`
- `GET /api/industries/{industry}/etf-ranking`

### ETF 比較

- `GET /api/etfs/compare?symbols=0050,006208,00878`
- `GET /api/etfs/overlap?symbols=0050,006208`

### Portfolio

- `POST /api/portfolios`
- `GET /api/portfolios`
- `GET /api/portfolios/{id}`
- `GET /api/portfolios/{id}/exposure`

### Backtest

- `POST /api/backtests`
- `GET /api/backtests/{id}`

### Projection

- `POST /api/projections`
- `GET /api/projections/{id}`

### AI

- `POST /api/ai/analyze-etf`
- `POST /api/ai/compare-etfs`
- `POST /api/ai/analyze-portfolio`
- `POST /api/ai/explain-backtest`

---

## 6. 設計原則

- API 回傳格式一致。
- 所有資料必須有資料日期。
- 所有關鍵資料必須有來源。
- 分析結果必須可追溯。
- 資料匯入與分析邏輯分離。
- Provider 與 Service 分離。
- Service 與 API router 分離。
- UI 不直接處理複雜金融計算。
