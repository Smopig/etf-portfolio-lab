# 09_DEVELOPMENT_TASK_BREAKDOWN.md — 開發任務拆解

---

## Epic 0：專案初始化

### Tasks

- 建立 monorepo
- 建立 backend
- 建立 frontend
- 建立 docker-compose
- 建立 PostgreSQL
- 建立 README
- 建立 .env.example

### Agent

- Backend Engineer：Sonnet
- Frontend Engineer：Sonnet
- Documentation Assistant：Haiku
- Opus：審查

---

## Epic 1：資料庫與資料模型

### Tasks

- 建立 ETF master model
- 建立 holdings model
- 建立 holding snapshot model
- 建立 stock industry model
- 建立 price model
- 建立 dividend model
- 建立 portfolio model
- 建立 backtest model
- 建立 projection model
- 建立 data source registry
- 建立 data quality checks

### Agent

- Data Engineer：Sonnet
- Opus：審查資料模型一致性

---

## Epic 2：資料匯入

### Tasks

- CSV 匯入 ETF master
- CSV 匯入 holdings
- CSV 匯入 stock industry
- CSV 匯入 prices
- CSV 匯入 dividends
- Excel 匯入
- 匯入錯誤處理
- 匯入紀錄
- raw file 保存

### Agent

- Data Engineer：Sonnet
- QA Assistant：Haiku
- Opus：審查資料流

---

## Epic 3：資料品質檢查

### Tasks

- 權重加總檢查
- 缺少股票代號檢查
- 缺少產業分類檢查
- 價格缺漏檢查
- 配息重複檢查
- 資料過舊檢查
- 來源缺失檢查
- data quality API

### Agent

- Data Engineer：Sonnet
- QA Assistant：Haiku
- Opus：審查檢查規則

---

## Epic 4：ETF 分析服務

### Tasks

- Top holdings
- Concentration metrics
- HHI
- Effective number of holdings
- Industry exposure
- Stock reverse lookup
- Industry reverse lookup
- ETF strategy card data

### Agent

- Quant Engineer：Sonnet
- Backend Engineer：Sonnet
- Opus：審查計算邏輯

---

## Epic 5：ETF 重疊度分析

### Tasks

- Pairwise overlap
- Weighted overlap
- Common holdings
- Industry similarity
- Overlap heatmap data
- Compare API

### Agent

- Quant Engineer：Sonnet
- Backend Engineer：Sonnet
- Opus：審查重疊公式

---

## Epic 6：Portfolio Builder

### Tasks

- Portfolio CRUD
- Portfolio item CRUD
- Weight sum validation
- Look-through stock exposure
- Look-through industry exposure
- Portfolio concentration
- Portfolio warnings
- Portfolio compare

### Agent

- Quant Engineer：Sonnet
- Backend Engineer：Sonnet
- Opus：審查曝險計算

---

## Epic 7：Backtesting Engine

### Tasks

- Price series alignment
- Portfolio daily value
- Initial investment
- Monthly contribution
- Dividend reinvestment
- Rebalancing
- Transaction cost
- CAGR
- MDD
- Volatility
- Sharpe
- Annual return
- Backtest result storage

### Agent

- Quant Engineer：Sonnet
- QA Assistant：Haiku
- Opus：審查金融邏輯

---

## Epic 8：Projection Engine

### Tasks

- Future value simulation
- Multi-scenario simulation
- Target amount analysis
- Required monthly contribution
- Required annual return
- Required years
- Projection result storage

### Agent

- Quant Engineer：Sonnet
- QA Assistant：Haiku
- Opus：審查公式

---

## Epic 9：API Layer

### Tasks

- ETF API
- Holding API
- Industry API
- Compare API
- Portfolio API
- Backtest API
- Projection API
- Data Import API
- Data Source API
- AI API placeholder

### Agent

- Backend Engineer：Sonnet
- QA Assistant：Haiku
- Opus：審查 API contract

---

## Epic 10：UX / UI 規劃

### Tasks

- UX flow
- Information architecture
- Design system
- Page specs
- Component hierarchy
- Empty / loading / error states
- Responsive rules

### Agent

- UX Designer：Sonnet
- Opus：審查 UX 是否符合金融研究流程

---

## Epic 11：Frontend Implementation

### Tasks

- Dashboard
- ETF Detail
- ETF Compare
- Portfolio Builder
- Backtest
- Projection
- Data Sources
- AI Assistant
- Layout
- Navigation
- Theme
- Chart components
- Table components

### Agent

- Frontend Engineer：Sonnet
- UX Designer：Sonnet
- Opus：審查 UI / UX

---

## Epic 12：Provider Automation

### Tasks

- BaseDataProvider
- CsvProvider
- ExcelProvider
- YahooProvider
- TwseProvider
- FundCompanyProvider placeholder
- Scheduler
- Fetch logs

### Agent

- Data Engineer：Sonnet
- Research Assistant：Haiku
- Opus：審查資料來源策略

---

## Epic 13：AI Analysis

### Tasks

- AI Provider interface
- Claude provider
- MiniMax provider
- Mock provider
- ETF analysis prompt
- Portfolio analysis prompt
- Backtest explanation prompt
- Projection explanation prompt
- Citation / data source injection
- Safety rules

### Agent

- Backend Engineer：Sonnet
- Documentation Assistant：Haiku
- Opus：審查 AI 行為限制

---

## Epic 14：Documentation

### Tasks

- README
- Setup guide
- Data import guide
- API docs
- User guide
- Developer guide
- Troubleshooting

### Agent

- Documentation Assistant：Haiku
- Opus：審查完整性

---

## Epic 15：QA / Final Review

### Tasks

- Unit tests
- API tests
- UI checklist
- Data quality tests
- Backtest correctness tests
- End-to-end smoke test
- Final bug list
- Release notes

### Agent

- QA Assistant：Haiku
- Sonnet engineers 修正
- Opus 最終審查
