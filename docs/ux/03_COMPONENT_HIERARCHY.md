# 03. Component Hierarchy — 元件庫與屬性對照

## 1. Layout Shell

### AppShell
- 子元件：`SideNav` + `TopBar` + `<main>` page content
- Props：`children`

### SideNav
- 對應 01 §2 八個導覽項目（Dashboard / ETF Detail(不固定) / ETF 比較 / 投資組合 / 回測 / 資產推算 / 資料來源 / AI 助手）
- Props：`activeRoute: string`
- 桌面：固定展開（icon+文字）；平板以下收合為 icon-only（見 05 文件）

### TopBar
- 內容：全站搜尋框（ETF symbol → `/etf/[symbol]`）、目前資料快照時間（取自 `imports/status` 最新 `checked_at`）、深色主題標識
- Props：`onSearch(symbol: string)`, `lastUpdated?: string`

### PageHeader
- Props：`title: string`, `subtitle: string`（主任務一句話）, `actions?: ReactNode`（如「加入比較」「執行回測」按鈕）

---

## 2. 通用資料元件

### DataTable
通用表格，承載 07 §6.1 規則。

| Prop | 類型 | 說明 |
|---|---|---|
| `columns` | `Column[]`（`key`, `label`, `align`, `format: 'text'\|'number'\|'percent'\|'currency'\|'date'`, `sortable`, `sticky?`） | 欄位定義 |
| `rows` | `Record<string, unknown>[]` | 資料（直接對應 API 回應陣列） |
| `searchable` | `boolean` | 是否顯示搜尋框 |
| `filters` | `{key, label, options}[]` | 下拉篩選 |
| `exportCsv` | `boolean` | 是否顯示 CSV 匯出按鈕 |
| `emptyState` | `{title, description, action?}` | 空資料時顯示 |
| `loading` | `boolean` | 顯示 skeleton rows |
| `dataDate` | `string \| null` | 顯示於表格標題旁（如「資料日期：2026-05-30」） |

### MetricCard
單一指標卡，落實 00 §3「解釋＋等級」規則。

| Prop | 類型 | 範例值來源 |
|---|---|---|
| `label` | `string` | 「集中度（HHI）」 |
| `value` | `string \| number \| null` | `concentration.hhi` |
| `unit` | `string?` | "" / "%" |
| `grade` | `{label: string, tone: 'success'\|'warning'\|'error'\|'info'\|'neutral'}` | 由 `hhi`/`overlap_rating`/`confidence_level` 等映射 |
| `explanation` | `string` | 「前幾大持股對 ETF 影響較明顯，需注意單一股票或單一產業曝險。」 |
| `loading` | `boolean` | |

### ChartCard
圖表容器，強制落實 07 §6.2。

| Prop | 類型 | 說明 |
|---|---|---|
| `title` | `string` | 必填 |
| `unit` | `string` | 顯示於副標或軸標籤 |
| `dataDate` | `string \| {start:string,end:string} \| null` | 顯示於右上角 |
| `explanation` | `string` | 圖表下方解讀文字，必填 |
| `chart` | `ReactNode`（ECharts instance） | |
| `loading` / `empty` / `error` | `boolean` / `boolean` / `{code,message}` | |

### Badge
| Prop | 類型 | 說明 |
|---|---|---|
| `label` | `string` | 顯示文字（如「被動型」「資料可信度：高」） |
| `tone` | `'success'\|'warning'\|'error'\|'info'\|'neutral'` | 對應 02 §1.4 |
| `tooltip?` | `string` | 滑入顯示說明 |

### SourceFooter
| Prop | 類型 | 說明 |
|---|---|---|
| `sourceName` | `string \| null` | `data_provenance.source_name` |
| `sourceUrl` | `string \| null` | `data_provenance.source_url` |
| `dataDate` | `string \| null` | `data_provenance.data_date` |
| `confidenceLevel` | `'高'\|'中'\|'低' \| null` | `data_provenance.confidence_level` → Badge |
| `disclaimer?` | `string` | 視頁面套用 00 §4 對應免責聲明 |

### EmptyState / LoadingSkeleton / ErrorPanel
- `EmptyState`: `{icon, title, description, actionLabel?, actionHref?}`
- `LoadingSkeleton`: `{variant: 'table'|'chart'|'card'|'text', rows?: number}`
- `ErrorPanel`: `{code: string, message: string, retry?: () => void}`（code→友善文案映射見 05 文件）

---

## 3. 領域元件（per-domain）

### HoldingsTable
- 基於 `DataTable`
- 資料來源：`GET /etfs/{symbol}/holdings`
- 欄位：`asset_symbol`（sticky）、`asset_name`、`weight_pct`（number, %）
- Props 額外：`topN?: number`（前十大時傳 10，全部表格不傳）

### IndustryExposureChart
- ECharts 環圈圖/橫條圖
- 資料來源：`GET /etfs/{symbol}/industry-exposure`（或 portfolio look-through `industry_exposure`）
- Props：`industries: {industry, weight_pct}[]`, `unclassified: {weight_pct}`, `level: 1|2`, `holdingDate`
- 顏色：依 02 §1.5 產業色票一致性規則

### ConcentrationPanel
- 組合多個 `MetricCard`：`top1_pct`/`top3_pct`/`top5_pct`/`top10_pct`/`hhi`/`effective_holdings`
- 資料來源：`GET /etfs/{symbol}/concentration` 或 `GET /portfolios/{id}/concentration`
- 每張卡含 grade + explanation（00 §3）

### OverlapHeatmap
- ECharts heatmap
- 資料來源：`GET /etfs/compare?symbols=...`（multi-overlap matrix）
- Props：`symbols: string[]`, `matrix: number[][]`（weighted_overlap_pct）, `ratings: string[][]`
- Cell tooltip 顯示 `weighted_overlap_pct` + `jaccard` + `overlap_rating.label`

### EtfTypeBadgeGroup
- 組合 Badge：`management_type`、`asset_class`、`investment_style`
- 資料來源：`GET /etfs/{symbol}`（card 主資料）

### WeightAllocator
- Portfolio Builder 用：ETF 清單 + 權重輸入 + 加總顯示
- Props：`items: {etf_symbol, target_weight}[]`, `weightSumPct: number`, `validationStatus: 'PASS'|'WARN'|'FAIL'`, `validationMessage: string`, `duplicateSymbols: string[]`, `unknownSymbols: string[]`（對應 `validate_weights` 回傳）
- 內含「加入 ETF」搜尋（`GET /etfs`）、「移除」、「套用範本」

### LookThroughExposurePanel
- 整合 `IndustryExposureChart` + `HoldingsTable`（個股穿透）
- 資料來源：`GET /portfolios/{id}/exposure`（`stock_exposure` + `industry_exposure`）

### PortfolioWarningsList
- 列表呈現 `GET /portfolios/{id}/warnings`，每項 `{code, severity, message}` → Badge(severity) + message
- `WEIGHT_SUM` / `DUPLICATE_ETF` / `UNKNOWN_ETF` 等 code 對應圖示

### BacktestForm
- 欄位：Portfolio 選擇器（`GET /portfolios`）或手動 symbols/weights、`start_date`/`end_date`、`initial_amount`、`monthly_contribution`、`dividend_reinvest`、`rebalance_frequency`、`transaction_cost_rate`
- 提交 → `POST /backtests`

### BacktestChart
- ECharts 雙圖：資產曲線（`portfolio_value_series`）+ 回撤曲線（`drawdown_series`），共用時間軸
- Props：`series: {date, value}[]`, `drawdown: {date, drawdown}[]`, `disclaimer: string`

### BacktestSummaryMetrics
- `MetricCard` 群組：`final_value`、`total_contribution`、`total_profit`、`cagr`、`irr`、`max_drawdown`、`annualized_volatility`、`sharpe_ratio`
- 每卡含 grade + explanation（風險指標需風險等級，見 02 §7「風險等級」gap）

### AnnualReturnsTable
- 基於 `DataTable`，資料來源：`annual_returns: dict[str, float]` → 轉陣列 `{year, return_pct}`

### ProjectionForm
- 欄位：`initial_amount`、`monthly_contribution`、`years`、目標金額（可選）
- 提交 → `POST /projections/scenarios`（主要）與 `POST /projections/goal-seek`

### ScenarioToggle
- 三態切換：保守 / 中性 / 樂觀（對應 `scenarios.*.annual_return_rate`，預設 4%/6%/8%）
- Props：`scenarios: {scenario_name, annual_return_rate, final_value, ...}[]`, `selected: string`

### ProjectionChart
- ECharts 堆疊面積圖：本金 vs 收益（`yearly_series[].contributed` / `.profit`）
- Props：`yearlySeries: {year, value, contributed, profit}[]`, `targetAmount?: number`, `targetAchieved?: boolean`, `disclaimer: string`

### GoalSeekPanel
- 三種倒推模式（`solve_for`: years / monthly_contribution / annual_return）對應 `POST /projections/goal-seek`

### DataSourceTable / DataQualityTable
- 基於 `DataTable`
- 資料來源：`GET /data-sources`（含 `enabled`、`reliability_level`）、`GET /data-quality`（含 `status`、`severity`）

### ImportStatusPanel
- 資料來源：`GET /imports/status`
- 顯示 `recent_quality_checks` 列表 + 固定說明文字（CLI 匯入提示 `note`）

### AIChatPanel
- 輸入框 + 上下文選擇（ETF symbol / Portfolio id）+ 對話紀錄
- 因 `POST /ai/analyze-etf`、`/ai/analyze-portfolio` 目前回 501（`NOT_IMPLEMENTED`），元件需支援「即將推出」鎖定狀態（見 04、05 文件）
- Props：`context: {type: 'etf'|'portfolio', id: string}`, `disabled: boolean`, `disabledReason: string`

---

## 4. 元件層級圖（摘要）

```text
AppShell
├─ TopBar
├─ SideNav
└─ <page>
   ├─ PageHeader
   ├─ [摘要區] MetricCard[] / Badge[]
   ├─ [圖表區] ChartCard
   │   └─ IndustryExposureChart | OverlapHeatmap | BacktestChart | ProjectionChart | ...
   ├─ [明細區] DataTable
   │   └─ HoldingsTable | AnnualReturnsTable | DataSourceTable | ...
   └─ SourceFooter
```
