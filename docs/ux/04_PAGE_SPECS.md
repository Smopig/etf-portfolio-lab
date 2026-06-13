# 04. Page Specs — 逐頁規格

每頁皆遵循 00 §2「先摘要、再展開」骨架。所有資料欄位均對應 Phase 9 API 真實回應；無對應 API 之需求列於各頁「Backend gaps」。

---

## 1. Dashboard (`/`)

### 主任務
讓使用者知道目前資料狀態，以及可以從哪裡開始研究。

### Wireframe
```text
┌─────────────────────────────────────────────────────────┐
│ PageHeader：「研究入口」                                    │
├─────────────────────────────────────────────────────────┤
│ [上方] MetricCard x4（橫列）                                │
│  ETF總數 | 已匯入成分股數 | 已有價格資料數 | 最後更新時間        │
├─────────────────────────────────────────────────────────┤
│ [中間] 4 張排行卡（2x2 grid）                                │
│  半導體曝險最高ETF | 金融曝險最高ETF                         │
│  成分股最集中ETF   | 產業最分散ETF                          │
├─────────────────────────────────────────────────────────┤
│ [下方] 資料品質警告表（DataTable）                           │
├─────────────────────────────────────────────────────────┤
│ 快速入口（按鈕群）：比較／組合／回測／推算／資料來源           │
├─────────────────────────────────────────────────────────┤
│ SourceFooter                                              │
└─────────────────────────────────────────────────────────┘
```

### API 對應
| 區塊 | 端點 | 欄位 |
|---|---|---|
| ETF 總數 / 啟用數 | `GET /api/etfs` | `data.length`；`is_active` 過濾 |
| 已有成分股/價格資料 ETF 數 | `GET /api/etfs` + 逐檔 `holdings`／無直接旗標 | **見 Backend gaps** |
| 最後更新時間 | `GET /api/imports/status` | `recent_quality_checks[0].checked_at` |
| 資料品質警告 | `GET /api/data-quality?status=FAIL` 或 `WARN` | `dataset_type`, `dataset_key`, `check_name`, `severity`, `message`, `checked_at` |
| 排行卡（4 種） | — | **見 Backend gaps**（需聚合端點） |

### 關鍵指標（含解釋＋等級）
- 「資料品質警告」MetricCard：數量 + Badge（依 `severity` 著色：ERROR=error, WARN=warning），說明「目前有 N 筆資料品質檢查未通過，建議前往資料來源頁查看」。

### 互動
- 排行卡點擊 → `/etf/[symbol]`
- 資料品質列點擊 → 若可定位 ETF，連到 `/etf/[symbol]`；否則連到 `/data-sources`
- 快速入口按鈕 → 對應路由

### Backend gaps for Phase 11
1. **「已匯入成分股 ETF 數量」「已有價格資料 ETF 數量」**：目前 `GET /api/etfs` 不含此旗標，需新增聚合欄位或新端點（如 `GET /api/etfs?has_holdings=true` 或在 list 回應加入 `has_holdings`/`has_price_data` boolean）。
2. **「半導體曝險最高 ETF」「金融曝險最高 ETF」**：需要跨 ETF 的產業曝險排行端點，例如 `GET /api/industries/{industry}/etf-ranking`（**此端點已存在於 `industries.py`！** → 可直接用 `GET /api/industries/半導體/etf-ranking?level=1` 與 `GET /api/industries/金融/etf-ranking?level=1`，取排行第一筆。需確認後端產業名稱字串是否為「半導體」「金融」並可作 path 參數，含中文 URL encoding）。
3. **「成分股最集中 ETF」「產業最分散 ETF」**：需要跨 ETF 排序端點，目前 `concentration`/`industry-exposure` 僅支援單檔查詢。建議新增 `GET /api/etfs/ranking?metric=hhi&order=desc&limit=1` 類型聚合端點。

> 結論：項目 1、3 為新端點需求；項目 2 可能可重用現有 `industries/{industry}/etf-ranking`，但需 Opus 確認資料庫中產業名稱字串與路由相容性。

---

## 2. ETF Detail (`/etf/[symbol]`)

### 主任務
理解單檔 ETF 的結構。

### Wireframe
```text
┌─────────────────────────────────────────────────────────┐
│ PageHeader：「{symbol} {name}」+ Badge群(主動/被動,資產類別,風格) │
│ actions: 「加入比較」                                       │
├─────────────────────────────────────────────────────────┤
│ [上方] 策略卡 + ConcentrationPanel（MetricCard x6）          │
│  追蹤指數／選股邏輯／加權方式／調整頻率（文字卡）              │
│  HHI／effective_holdings／top1~10 pct（含解釋＋等級）         │
├─────────────────────────────────────────────────────────┤
│ [中間] ChartCard: 前十大成分股權重圖（橫條圖）                 │
│        ChartCard: 產業占比圖（環圈圖，level切換1/2）          │
├─────────────────────────────────────────────────────────┤
│ [下方] 全部成分股表格（DataTable，搜尋/排序/CSV）              │
│        持股變化 Timeline（區塊）                             │
├─────────────────────────────────────────────────────────┤
│ AI 摘要區（即將推出 Badge）                                  │
├─────────────────────────────────────────────────────────┤
│ SourceFooter                                              │
└─────────────────────────────────────────────────────────┘
```

### API 對應
| 區塊 | 端點 | 欄位 |
|---|---|---|
| 策略卡 + Badge群 | `GET /api/etfs/{symbol}` | `name`,`issuer`,`management_type`,`asset_class`,`investment_style`,`strategy_type`,`tracking_index`,`index_provider`,`expense_ratio`,`management_fee`,`custody_fee`,`dividend_frequency` |
| ConcentrationPanel | 同上 `concentration.*`（card 內含） 或 `GET /api/etfs/{symbol}/concentration`（完整版） | `hhi`,`effective_holdings`,`top1_pct..top10_pct`,`holding_date`,`num_holdings` |
| 前十大成分股圖 | `GET /api/etfs/{symbol}/holdings?n=10` | `asset_symbol`,`asset_name`,`weight_pct` |
| 全部成分股表格 | `GET /api/etfs/{symbol}/holdings?n=200` | 同上（n 上限 200） |
| 產業占比圖 | `GET /api/etfs/{symbol}/industry-exposure?level=1|2` | `industries[].{industry,weight_pct}`,`unclassified.weight_pct`,`top3_industries`,`max_industry`,`holding_date` |
| 持股變化 Timeline | — | **Backend gap** |
| AI 摘要 | `POST /api/ai/analyze-etf` | 目前 501，顯示「即將推出」 |
| SourceFooter | `GET /api/etfs/{symbol}` | `data_provenance.{source_name,source_url,data_date,fetched_at,confidence_level}` |

### 關鍵指標說明範例
- HHI（依 00 §3 範例直接套用）
- `effective_holdings`：「有效持股數約 X 檔——數字越接近實際持股數，代表權重分布越平均」
- `top10_pct`：「前十大持股合計占比，數字越高代表組合越集中於少數標的」

### 互動
- 產業占比圖 level 切換（1/2）→ 重打 `industry-exposure?level=`
- 表格列點擊個股 → 目前無反查路由，暫不可點擊（純文字），未來可連 `GET /api/stocks/{symbol}/etfs`
- 「加入比較」→ 導向 `/compare?symbols={symbol}`（若已有其他選取則 append）

### Backend gaps for Phase 11
1. **持股變化 Timeline**：07 §5.2 要求顯示，但目前無對應 API（需 `etf_holding_change_events` 類資料表與 `GET /api/etfs/{symbol}/holding-changes` 端點）。Phase 11 暫以「資料尚未提供，敬請期待」空狀態取代，不可虛構資料。
2. **股票反查連結**（成分股 → 其他持有該股的 ETF）：`GET /api/stocks/{stock_symbol}/etfs` 已存在於 `industries.py`，可在 Phase 11 將表格個股設為可點擊連結（非 gap，僅標記為可選增強）。

---

## 3. ETF Compare (`/compare?symbols=A,B,C`)

### 主任務
比較多檔 ETF 的差異與重疊。

### Wireframe
```text
┌─────────────────────────────────────────────────────────┐
│ PageHeader：「ETF 比較」 + ETF選擇器（最多4-5檔）             │
├─────────────────────────────────────────────────────────┤
│ [上方] 基本資料比較表（橫向，每欄一檔ETF）                     │
│  含 Badge群：主動/被動、資產類別、投資風格                     │
├─────────────────────────────────────────────────────────┤
│ [中間] OverlapHeatmap（重疊度熱力圖，N x N）                  │
│        ChartCard: 產業占比比較（並排環圈圖或堆疊橫條）         │
│        ChartCard: 集中度比較（HHI/top10_pct 並排柱狀）        │
├─────────────────────────────────────────────────────────┤
│ [下方] 前十大持股比較表（DataTable，每ETF一欄）                │
│        （2檔時）成分股重疊明細表 + 產業相似度                 │
├─────────────────────────────────────────────────────────┤
│ AI 比較結論（即將推出 Badge）                                │
├─────────────────────────────────────────────────────────┤
│ SourceFooter（多個資料日期需逐檔列出）                        │
└─────────────────────────────────────────────────────────┘
```

### API 對應
| 區塊 | 端點 | 欄位 |
|---|---|---|
| ETF 選擇器 | `GET /api/etfs` | `symbol`,`name` 供下拉 |
| 基本資料比較表 | 每檔 `GET /api/etfs/{symbol}` | `name`,`issuer`,`management_type`,`asset_class`,`investment_style`,`expense_ratio`,`tracking_index` |
| OverlapHeatmap (N檔) | `GET /api/etfs/compare?symbols=A,B,C` | multi-overlap matrix（`get_multi_overlap` 回傳結構——逐對 `weighted_overlap_pct`/`overlap_rating`） |
| 重疊明細表 (2檔) | `GET /api/etfs/overlap?symbols=A,B` | `overlap.overlap_assets[]`(`asset_symbol`,`asset_name`,`weight_a_pct`,`weight_b_pct`,`min_weight_pct`), `overlap.overlap_count`,`overlap.weighted_overlap_pct`,`overlap.jaccard`,`overlap.overlap_rating`,`overlap.common_top10`,`industry_similarity` |
| 前十大持股比較 | 每檔 `GET /api/etfs/{symbol}/holdings?n=10` | `asset_symbol`,`asset_name`,`weight_pct` |
| 產業占比比較 | 每檔 `GET /api/etfs/{symbol}/industry-exposure?level=1` | `industries[]`,`unclassified` |
| 集中度比較 | 每檔 `GET /api/etfs/{symbol}/concentration` | `hhi`,`top10_pct`,`effective_holdings` |
| AI 比較結論 | `POST /api/ai/analyze-portfolio` | 501，顯示「即將推出」 |

### 關鍵指標說明
- `overlap_rating.label`（極低/低度/中度/高度重疊）：直接顯示後端標籤 + 說明「重疊度越高，代表兩檔 ETF 持股越相似，分散效果越低」。
- `jaccard`：「兩檔 ETF 成分股集合的相似度（不考慮權重），0為完全不同，1為完全相同」。

### 互動
- ETF 選擇器新增/移除 → 更新 `symbols` query，重打所有相關 API
- 2 檔 vs 3+ 檔模式切換：2 檔顯示重疊明細表+產業相似度；3+ 檔僅顯示 Heatmap（`compare` 端點）
- Heatmap cell hover → tooltip 顯示 `weighted_overlap_pct`/`jaccard`/`overlap_rating.label`

### Backend gaps for Phase 11
1. `GET /api/etfs/compare` 的回應結構需確認是否包含逐對 `overlap_rating`／`jaccard`（用於 Heatmap tooltip）；若 `get_multi_overlap` 僅回傳矩陣數值，需補充逐對 metadata。**請 Opus 確認 `overlap_service.get_multi_overlap` 實際回傳結構**（本次未完整讀取該函式定義）。
2. 「產業相似度」(`industry_similarity`) 僅在 2 檔比較時提供（`/etfs/overlap`），3+ 檔比較時無對應端點 — Phase 11 先限制產業相似度顯示僅於 2 檔模式。

---

## 4. Portfolio Builder (`/portfolio`, `/portfolio/[id]`)

### 主任務
建立 ETF 配置，並理解穿透後曝險。

### Wireframe
```text
┌─────────────────────────────────────────────────────────┐
│ PageHeader：「投資組合：{name}」 actions: 儲存/執行回測/推算  │
├─────────────────────────────────────────────────────────┤
│ [上方] WeightAllocator                                     │
│  ETF清單+權重輸入 | 權重總和狀態Badge(PASS/WARN/FAIL)         │
│  套用範本下拉 | PortfolioWarningsList                       │
├─────────────────────────────────────────────────────────┤
│ [中間] ChartCard: 穿透後產業曝險圖                           │
│        ChartCard: Top10 實際股票曝險（橫條圖）                │
│        ConcentrationPanel（組合層級 HHI 等）                  │
├─────────────────────────────────────────────────────────┤
│ [下方] LookThroughExposurePanel 明細表（個股穿透全表）         │
├─────────────────────────────────────────────────────────┤
│ 免責聲明（00 §4 portfolio look-through 文字）                │
├─────────────────────────────────────────────────────────┤
│ SourceFooter                                              │
└─────────────────────────────────────────────────────────┘
```

### API 對應
| 區塊 | 端點 | 欄位 |
|---|---|---|
| 列表/載入 | `GET /api/portfolios`、`GET /api/portfolios/{id}` | `id`,`name`,`description`,`base_currency`,`items[].{etf_symbol,target_weight}` |
| 建立/更新 | `POST /api/portfolios`、`PUT /api/portfolios/{id}` | body=`{name,description,base_currency,items}` |
| 草稿即時分析（未儲存） | `POST /api/portfolios/analyze` | body=`{items}` → `validation`,`stock_exposure`,`industry_exposure`,`concentration`,`warnings` |
| 已存組合分析 | `GET /api/portfolios/{id}/exposure?level=1|2`、`/concentration`、`/overlap-risk`、`/warnings` | 同上對應欄位 |
| 權重檢查 | `validation.{status,weight_sum_pct,message,duplicate_symbols,unknown_symbols}` | Badge(PASS=success/WARN=warning/FAIL=error) + message |
| 穿透產業曝險圖 | `industry_exposure.industries[].{industry,weight_pct}` + `unclassified` | |
| Top10股票曝險 | `stock_exposure`（依權重排序取前10） | |
| 組合集中度 | `concentration.{hhi,top10_pct,effective_holdings,...}` | |
| 分散度提醒 | `warnings[].{code,severity,message}` | `WEIGHT_SUM`/`DUPLICATE_ETF`/`UNKNOWN_ETF` 等 |

### 關鍵指標說明
- 權重總和狀態：`status==PASS` → 「權重總和為 X%，符合 100% 容許範圍」（success）；`WARN`/`FAIL` 對應 message 直接顯示，Badge 對應 tone。
- 組合 HHI／Top10 曝險：套用與 ETF Detail 相同的解釋＋等級規則。

### 互動
- 加入/移除 ETF → 即時呼叫 `POST /portfolios/analyze`（debounce）更新所有圖表/指標（不落地）
- 「套用預設配置模板」→ 前端內建模板（symbol+weight 組合），套用後同樣走 `analyze`
- 儲存 → `POST /portfolios` 或 `PUT /portfolios/{id}`
- 「執行回測」→ `/backtest?portfolio_id={id}`（需先儲存，否則提示先儲存）
- 「推算未來資產」→ `/projection`（可選帶入 portfolio 名稱供記錄）

### Backend gaps for Phase 11
1. **「預設配置模板」**：07 要求但目前無後端範本資料表/端點。Phase 11 先以前端硬編碼 2-3 組範本（如「核心衛星」「全球分散」），列為前端 mock 模板，需在 UI 標示「範本為建議起點，請自行確認成分」。長期建議後端提供 `GET /api/portfolio-templates`。
2. **回測/推算前必須先儲存** 的限制是否合理需 Opus 確認 — `POST /api/backtests` 的 `BacktestRequest` 同時支援 `symbols`+`weights`（不需 portfolio_id），故技術上「未儲存草稿」也可直接回測；Phase 11 UX 可選擇支援「直接用草稿回測」以避免強制儲存。

---

## 5. Backtest (`/backtest?portfolio_id=`)

### 主任務
驗證配置在歷史資料中的表現。

### Wireframe
```text
┌─────────────────────────────────────────────────────────┐
│ PageHeader：「回測」                                        │
├─────────────────────────────────────────────────────────┤
│ [表單] 選擇Portfolio / 起止日期 / 初始投入 / 每月投入 /        │
│        配息再投入 / 再平衡頻率 / 交易成本   [執行回測]         │
├─────────────────────────────────────────────────────────┤
│ 免責聲明：「回測結果不代表未來績效，僅供研究分析。」（常駐）    │
├─────────────────────────────────────────────────────────┤
│ [上方] BacktestSummaryMetrics（MetricCard x8）              │
│  final_value/total_contribution/total_profit/cagr/irr/    │
│  max_drawdown/annualized_volatility/sharpe_ratio          │
├─────────────────────────────────────────────────────────┤
│ [中間] BacktestChart：資產曲線 + 回撤曲線（雙圖同軸）          │
├─────────────────────────────────────────────────────────┤
│ [下方] AnnualReturnsTable（年度報酬）                        │
├─────────────────────────────────────────────────────────┤
│ 風險提醒區塊                                                │
├─────────────────────────────────────────────────────────┤
│ SourceFooter（資料期間=start_date~end_date）                │
└─────────────────────────────────────────────────────────┘
```

### API 對應
| 區塊 | 端點 | 欄位 |
|---|---|---|
| 表單提交 | `POST /api/backtests?persist=false` | body = `BacktestRequest`（`portfolio_id` 或 `symbols`+`weights`，`start_date`,`end_date`,`initial_amount`,`monthly_contribution`,`dividend_reinvest`,`rebalance_frequency`,`transaction_cost_rate`,`risk_free_rate`,`name`） |
| Portfolio 選擇器 | `GET /api/portfolios` | `id`,`name` |
| 摘要指標 | response `data.*` | `final_value`,`total_contribution`,`total_profit`,`cagr`,`irr`,`max_drawdown`,`annualized_volatility`,`sharpe_ratio` |
| 資產曲線 | `data.portfolio_value_series[]` | `{date,value}` |
| 回撤曲線 | `data.drawdown_series[]` | `{date,drawdown}` |
| 年度報酬表 | `data.annual_returns`（dict） | 轉為 `{year, return_pct}[]` |
| 免責聲明 | `data.disclaimer` | 「回測結果不代表未來績效，僅供研究分析。」 |

### 關鍵指標說明（範例）
- `cagr`（年化複合成長率）：「衡量整段期間的年化報酬率，數字越高代表平均成長越快，但不代表未來會持續」
- `max_drawdown`：「歷史最大跌幅，數字越大代表曾經發生過的最大損失幅度越深」+ 風險等級 Badge（**等級門檻為 gap，見 02 §7**）
- `sharpe_ratio`：「每承擔一單位風險所獲得的超額報酬，數字越高代表風險調整後表現越好」
- `irr`：「考慮每月投入時間點的內部報酬率，較能反映定期定額的實際報酬」

### 互動
- 表單變更 → 不自動觸發（避免昂貴計算），點擊「執行回測」才呼叫 API
- `persist=true` 選項：若使用者勾選「儲存此次回測」則帶 `?persist=true`（目前表單不預設顯示，Phase 11 視需求加開關）
- 再平衡頻率下拉：`none`/`monthly`/`quarterly`/`semiannual`/`annual`（對應 `VALID_REBALANCE_FREQUENCIES`）

### Backend gaps for Phase 11
無重大 gap。可選增強：歷史回測紀錄列表（`persist=true` 後資料存於 DB，但目前無 `GET /api/backtests` 列表端點可供「查看過去回測紀錄」——若 Phase 11 要做歷史列表頁，需新增此端點。本頁本身（即時回測）不受影響。

---

## 6. Projection (`/projection`)

### 主任務
估算未來資產成長與目標可行性。

### Wireframe
```text
┌─────────────────────────────────────────────────────────┐
│ PageHeader：「資產推算」                                    │
├─────────────────────────────────────────────────────────┤
│ [表單] 初始投入 / 每月投入 / 投資年限 / 目標金額(可選) [推算]   │
├─────────────────────────────────────────────────────────┤
│ 免責聲明：「未來模擬基於假設報酬率，不代表保證收益，僅供研究分析。」│
├─────────────────────────────────────────────────────────┤
│ [上方] ScenarioToggle（保守4% / 中性6% / 樂觀8%）             │
│        MetricCard：選定情境 final_value/total_profit/達標狀態 │
├─────────────────────────────────────────────────────────┤
│ [中間] ProjectionChart：本金 vs 收益堆疊面積圖（隨情境切換）   │
├─────────────────────────────────────────────────────────┤
│ [下方] 達標分析 + GoalSeekPanel（目標倒推三模式）             │
├─────────────────────────────────────────────────────────┤
│ SourceFooter（標示為模擬資料，無外部資料來源）                │
└─────────────────────────────────────────────────────────┘
```

### API 對應
| 區塊 | 端點 | 欄位 |
|---|---|---|
| 三情境計算 | `POST /api/projections/scenarios` | body=`{initial_amount,monthly_contribution,years,target_amount?}` → `data.scenarios[].{scenario_name,annual_return_rate,final_value,total_contribution,total_profit,target_achieved,yearly_series}`, `data.rates_used`(`{保守:0.04,中性:0.06,樂觀:0.08}`), `data.disclaimer` |
| 單一情境（自訂年化率+可儲存） | `POST /api/projections`（`?persist=`） | body=`ProjectionConfig`(`annual_return_rate` 自訂) |
| 目標倒推 | `POST /api/projections/goal-seek` | body=`{solve_for: 'years'|'monthly_contribution'|'annual_return', ...}` |

### 關鍵指標說明
- `final_value` / `total_profit`：每個情境皆顯示，並附「此為假設報酬率下的模擬結果，非保證」
- `target_achieved`：Badge（達標=success / 未達標=warning）+「在第 N 年資產是否達到目標金額 {target_amount}」
- ScenarioToggle 三個按鈕分別顯示對應 `annual_return_rate`（4%/6%/8%），切換時更新 ProjectionChart 與 MetricCard

### 互動
- 表單提交 → `POST /projections/scenarios`，三情境一次取得，前端切換不需重打 API
- 目標倒推：使用者選擇「倒推年限／每月投入／年化報酬率」之一 → `POST /projections/goal-seek`，結果獨立顯示於 GoalSeekPanel
- 不提供「儲存」按鈕於主流程（`POST /projections` 含 persist 為次要功能，Phase 11 可選擇性加在進階選項）

### Backend gaps for Phase 11
無。三個端點完整覆蓋頁面需求。

---

## 7. Data Sources (`/data-sources`)

### 主任務
管理資料來源、資料品質與更新狀態。

### Wireframe
```text
┌─────────────────────────────────────────────────────────┐
│ PageHeader：「資料來源管理」                                │
├─────────────────────────────────────────────────────────┤
│ [上方] MetricCard：啟用來源數 / 資料品質 FAIL數 / 最近檢查時間 │
├─────────────────────────────────────────────────────────┤
│ [中間] DataSourceTable（資料來源清單）                       │
├─────────────────────────────────────────────────────────┤
│ [下方] DataQualityTable（可篩選 dataset_type/status）        │
│        ImportStatusPanel（手動匯入入口 + CLI 說明 + 歷史）    │
├─────────────────────────────────────────────────────────┤
│ SourceFooter                                              │
└─────────────────────────────────────────────────────────┘
```

### API 對應
| 區塊 | 端點 | 欄位 |
|---|---|---|
| 資料來源清單 | `GET /api/data-sources` | `source_name`,`source_type`,`base_url`,`description`,`update_frequency`,`reliability_level`,`license_note`,`enabled` |
| 資料品質檢查 | `GET /api/data-quality?dataset_type=&status=&limit=` | `dataset_type`,`dataset_key`,`check_name`,`status`,`severity`,`message`,`checked_at` |
| 匯入狀態/歷史 | `GET /api/imports/status` | `recent_quality_checks[]`,`note`（CLI 匯入提示文字） |

### 關鍵指標說明
- `reliability_level` → Badge（資料可信度 高/中/低，依 02 §1.4 對應色）
- `status`（PASS/WARN/FAIL）→ Badge，`severity` 作為次要標示
- `enabled`（boolean）→ 「啟用中」/「已停用」Badge

### 互動
- DataQualityTable 篩選器：`dataset_type`、`status` 下拉（對應 query params）
- 「手動匯入入口」：因 `data_import.py` 為唯讀 placeholder（無 POST 上傳），顯示 `note` 文字：「File-upload based data import is not implemented...data is currently loaded via CLI importers」→ 中文化為「目前資料透過 CLI 匯入工具更新，尚未提供網頁上傳功能」，並提供「查看 CLI 匯入文件」連結（如有）

### Backend gaps for Phase 11
1. **手動匯入（檔案上傳）**：07 §5.7 要求「手動匯入入口」，但 `data_import.py` 明確標註為 placeholder，僅回傳 `note`。Phase 11 應將此區塊設計為「即將推出」+ CLI 操作說明，不可做出實際上傳 UI 直到後端 `POST /api/imports` 完成。
2. **匯入歷史紀錄**：目前僅有最近 10 筆 `data_quality_checks`，並非真正的「匯入批次歷史」（無 import job/run 記錄表）。Phase 11 標示此區塊為「資料品質檢查歷程」而非「匯入歷史」，避免誤導；若需真正匯入歷史，需新增 import run 資料表與端點。

---

## 8. AI Assistant (`/ai`)

### 主任務
基於系統資料解釋分析結果。

### Wireframe
```text
┌─────────────────────────────────────────────────────────┐
│ PageHeader：「AI 助手」+ Badge「即將推出」                   │
├─────────────────────────────────────────────────────────┤
│ 說明區：本功能將基於系統資料回答問題，附資料來源與日期，        │
│         不提供買賣建議（連結 CLAUDE.md §7 概念，以白話呈現）   │
├─────────────────────────────────────────────────────────┤
│ AIChatPanel（disabled狀態）                                 │
│  - 上下文選擇（ETF / Portfolio）— 可操作，預存供未來使用       │
│  - 輸入框 — disabled，placeholder：「AI 分析功能即將推出」     │
│  - 對話區 — 顯示「此功能尚未開放，目前呼叫會回傳 501」          │
├─────────────────────────────────────────────────────────┤
│ SourceFooter                                              │
└─────────────────────────────────────────────────────────┘
```

### API 對應
| 區塊 | 端點 | 狀態 |
|---|---|---|
| 提問（ETF） | `POST /api/ai/analyze-etf` | 501 `NOT_IMPLEMENTED`：「AI ETF analysis is not implemented yet (Phase 13).」 |
| 提問（Portfolio） | `POST /api/ai/analyze-portfolio` | 501 `NOT_IMPLEMENTED`：「AI portfolio analysis is not implemented yet (Phase 13).」 |

### AI 限制（一旦 Phase 13 開放後必須遵守，先寫入規格供日後驗收）
- 每則回覆必須附「資料來源」與「資料日期」
- 不可提供買賣指令／進出場時點建議
- 回測/模擬相關回答必須附帶「不代表未來績效」字樣
- 僅能基於系統資料回答（不得引用外部猜測的成分股/產業資料）

### 互動
- 上下文選擇器（ETF symbol / Portfolio id）可操作，選擇後預存於前端 state，待 API 開放後直接帶入 request body
- 輸入框與送出按鈕 disabled，hover 顯示 tooltip：「AI 分析功能規劃中（Phase 13），目前後端回應 501」
- 若使用者仍嘗試呼叫並收到 501 → 顯示 ErrorPanel，文案「此功能即將推出，敬請期待」（NOT_IMPLEMENTED 映射，見 05 文件）

### Backend gaps for Phase 11
- 無前端可解的 gap（本頁本質即為等待 Phase 13）。Phase 11 僅需把「即將推出」狀態做好，介面骨架（上下文選擇、輸入框、對話區）先行完成，方便 Phase 13 直接接上。
