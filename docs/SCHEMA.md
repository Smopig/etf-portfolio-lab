# 資料表架構說明 (SCHEMA.md)

本文件記錄 ETF Portfolio Lab 在 PostgreSQL 中由 Alembic 遷移 0001_initial_schema 建立的 15 個資料表結構。

---

## 資料來源與品質追蹤

所有主要資料表都包含來源追蹤欄位，以滿足 CLAUDE.md §7 資料來源與日期要求：
- `source_name` — 資料來源名稱
- `source_url` — 資料來源網址
- `data_date` 或 `fetched_at` — 資料抓取日期
- `confidence_level` — 資料可信度等級

這些欄位用於記錄每筆資料的出處、抓取時間與可信度，確保使用者了解資料背景與適用限制。

---

## 1. etf_master — ETF 主檔

目的：儲存 ETF 基本資訊、管理特徵、費用結構、追蹤指數資料。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| symbol | VARCHAR(20) | UNIQUE；ETF 代碼 |
| name | TEXT | ETF 名稱 |
| issuer | TEXT | 發行商 |
| listing_date | DATE | 上市日期 |
| management_type | TEXT | 管理型態（主動/被動） |
| asset_class | TEXT | 資產類別 |
| investment_style | TEXT | 投資風格 |
| strategy_type | TEXT | 策略類型 |
| tracking_index | TEXT | 追蹤指數名稱 |
| index_provider | TEXT | 指數提供商 |
| selection_method | TEXT | 成分股選取方法 |
| weighting_method | TEXT | 加權方式 |
| rebalance_frequency | TEXT | 再平衡頻率 |
| replication_method | TEXT | 複製方式 |
| expense_ratio | NUMERIC | 費用率 |
| management_fee | NUMERIC | 管理費 |
| custody_fee | NUMERIC | 保管費 |
| dividend_frequency | TEXT | 配息頻率 |
| source_name | TEXT | 資料來源名稱 |
| source_url | TEXT | 資料來源網址 |
| data_date | DATE | 資料日期 |
| fetched_at | TIMESTAMP | 抓取時間 |
| confidence_level | TEXT | 可信度等級 |
| is_active | BOOLEAN | 是否有效 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 最後更新時間 |

**UNIQUE 約束**：`(symbol)`

---

## 2. etf_holdings — ETF 成分股明細表

目的：記錄特定日期 ETF 的持股組成，包含標的代碼、權重、數量、價值。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| etf_symbol | VARCHAR(20) | 外鍵參考 etf_master.symbol |
| holding_date | DATE | 持股日期 |
| asset_symbol | VARCHAR(20) | 標的代碼（股票/基金） |
| asset_name | TEXT | 標的名稱 |
| asset_type | TEXT | 標的類型（股票/債券等） |
| weight | NUMERIC | 權重（百分比） |
| shares | NUMERIC | 持股數量 |
| market_value | NUMERIC | 市值 |
| source_name | TEXT | 資料來源名稱 |
| source_url | TEXT | 資料來源網址 |
| fetched_at | TIMESTAMP | 抓取時間 |
| confidence_level | TEXT | 可信度等級 |
| created_at | TIMESTAMP | 建立時間 |

**UNIQUE 約束**：`(etf_symbol, holding_date, asset_symbol)`

---

## 3. stock_industry — 股票產業分類表

目的：儲存股票的產業分類（GICS 三級）、市場、自訂分類。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| stock_symbol | VARCHAR(20) | UNIQUE；股票代碼 |
| stock_name | TEXT | 股票名稱 |
| market | TEXT | 交易市場 |
| industry_level_1 | TEXT | 一級產業 |
| industry_level_2 | TEXT | 二級產業 |
| industry_level_3 | TEXT | 三級產業 |
| custom_sector | TEXT | 自訂業別 |
| custom_theme | TEXT | 自訂主題 |
| source_name | TEXT | 資料來源名稱 |
| source_url | TEXT | 資料來源網址 |
| updated_at | TIMESTAMP | 最後更新時間 |

**UNIQUE 約束**：`(stock_symbol)`

---

## 4. etf_industry_exposure — ETF 產業曝險快取表

目的：快取 ETF 對各產業的曝險比例，加快產業分析查詢。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| etf_symbol | VARCHAR(20) | 外鍵參考 etf_master.symbol |
| exposure_date | DATE | 曝險日期 |
| industry_level_1 | TEXT | 一級產業 |
| industry_level_2 | TEXT | 二級產業 |
| weight | NUMERIC | 曝險權重 |
| source_holding_date | DATE | 來源持股日期（參考用） |
| created_at | TIMESTAMP | 建立時間 |

**UNIQUE 約束**：`(etf_symbol, exposure_date, industry_level_1, industry_level_2)`

---

## 5. etf_holding_snapshots — ETF 持股快照表

目的：記錄每次抓取 ETF 持股的快照元資料（來源、抓取時間、檔案路徑）。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| etf_symbol | VARCHAR(20) | 外鍵參考 etf_master.symbol |
| snapshot_date | DATE | 快照日期 |
| source_name | TEXT | 資料來源名稱 |
| source_url | TEXT | 資料來源網址 |
| raw_file_path | TEXT | 原始檔案路徑 |
| parser_version | TEXT | 解析器版本 |
| fetched_at | TIMESTAMP | 抓取時間 |
| created_at | TIMESTAMP | 建立時間 |

**UNIQUE 約束**：`(etf_symbol, snapshot_date, source_name)`

---

## 6. etf_holding_snapshot_items — 快照成分股明細表

目的：儲存單次快照內的成分股明細，每筆記錄對應一個快照中的一隻標的。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| snapshot_id | INTEGER | 外鍵參考 etf_holding_snapshots.id |
| asset_symbol | VARCHAR(20) | 標的代碼 |
| asset_name | TEXT | 標的名稱 |
| asset_type | TEXT | 標的類型 |
| weight | NUMERIC | 權重 |
| shares | NUMERIC | 持股數量 |
| market_value | NUMERIC | 市值 |
| created_at | TIMESTAMP | 建立時間 |

**關係**：`snapshot_id` → `etf_holding_snapshots.id`

---

## 7. etf_holding_change_events — 持股變化事件表

目的：記錄 ETF 持股的增減與權重變化事件。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| etf_symbol | VARCHAR(20) | 外鍵參考 etf_master.symbol |
| from_date | DATE | 變化起始日期 |
| to_date | DATE | 變化截止日期 |
| change_type | TEXT | 變化類型：ADDED / REMOVED / WEIGHT_INCREASE / WEIGHT_DECREASE / UNCHANGED |
| asset_symbol | VARCHAR(20) | 標的代碼 |
| asset_name | TEXT | 標的名稱 |
| old_weight | NUMERIC | 舊權重 |
| new_weight | NUMERIC | 新權重 |
| weight_delta | NUMERIC | 權重變化量 |
| change_reason | TEXT | 變化原因 |
| confidence_level | TEXT | 可信度等級 |
| source_type | TEXT | 來源類型：OFFICIAL_ANNOUNCEMENT / SNAPSHOT_DIFF / MANUAL_INPUT |
| source_url | TEXT | 來源網址 |
| created_at | TIMESTAMP | 建立時間 |

---

## 8. etf_prices — ETF 歷史價格表

目的：儲存 ETF 的每日交易價格（開高低收、成交量、成交金額）。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| etf_symbol | VARCHAR(20) | 外鍵參考 etf_master.symbol |
| trade_date | DATE | 交易日期 |
| open | NUMERIC | 開盤價 |
| high | NUMERIC | 最高價 |
| low | NUMERIC | 最低價 |
| close | NUMERIC | 收盤價 |
| adjusted_close | NUMERIC | 調整收盤價 |
| volume | NUMERIC | 成交量 |
| turnover | NUMERIC | 成交金額 |
| source_name | TEXT | 資料來源名稱 |
| source_url | TEXT | 資料來源網址 |
| fetched_at | TIMESTAMP | 抓取時間 |
| created_at | TIMESTAMP | 建立時間 |

**UNIQUE 約束**：`(etf_symbol, trade_date, source_name)`

---

## 9. etf_dividends — ETF 配息記錄表

目的：記錄 ETF 的配息明細（除息日、配息日、配息金額、配息殖利率）。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| etf_symbol | VARCHAR(20) | 外鍵參考 etf_master.symbol |
| ex_dividend_date | DATE | 除息日 |
| payment_date | DATE | 配息日 |
| dividend_amount | NUMERIC | 配息金額 |
| dividend_yield | NUMERIC | 配息殖利率 |
| source_name | TEXT | 資料來源名稱 |
| source_url | TEXT | 資料來源網址 |
| fetched_at | TIMESTAMP | 抓取時間 |
| created_at | TIMESTAMP | 建立時間 |

**UNIQUE 約束**：`(etf_symbol, ex_dividend_date, source_name)`

---

## 10. portfolio — 使用者配置方案表

目的：儲存使用者建立的投資組合方案（名稱、說明、基礎幣別）。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| name | TEXT | 配置方案名稱 |
| description | TEXT | 配置方案說明 |
| base_currency | TEXT | 基礎幣別（預設 TWD） |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 最後更新時間 |

---

## 11. portfolio_items — 配置方案明細表

目的：儲存單一配置方案內的 ETF 配置比例。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| portfolio_id | INTEGER | 外鍵參考 portfolio.id |
| etf_symbol | VARCHAR(20) | 外鍵參考 etf_master.symbol |
| target_weight | NUMERIC | 目標權重 |
| created_at | TIMESTAMP | 建立時間 |

**關係**：`portfolio_id` → `portfolio.id`；`etf_symbol` → `etf_master.symbol`

---

## 12. backtest_runs — 回測紀錄表

目的：儲存投資組合的歷史回測結果與績效指標。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| portfolio_id | INTEGER | 外鍵參考 portfolio.id |
| name | TEXT | 回測名稱 |
| start_date | DATE | 回測起始日 |
| end_date | DATE | 回測截止日 |
| initial_amount | NUMERIC | 初始金額 |
| monthly_contribution | NUMERIC | 月定投金額（預設 0） |
| rebalance_frequency | TEXT | 再平衡頻率 |
| dividend_reinvest | BOOLEAN | 是否再投資配息（預設 true） |
| transaction_cost_rate | NUMERIC | 交易成本率（預設 0） |
| final_value | NUMERIC | 最終資產值 |
| total_contribution | NUMERIC | 總投入 |
| total_profit | NUMERIC | 總利潤 |
| cagr | NUMERIC | 年複合成長率 |
| max_drawdown | NUMERIC | 最大回撤 |
| annualized_volatility | NUMERIC | 年化波動率 |
| sharpe_ratio | NUMERIC | 夏普比率 |
| result_json | JSONB | 回測結果詳細 JSON |
| created_at | TIMESTAMP | 建立時間 |

**關係**：`portfolio_id` → `portfolio.id`

---

## 13. projection_runs — 財務模擬紀錄表

目的：儲存未來財務模擬結果（基於固定報酬率假設）。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| name | TEXT | 模擬名稱 |
| initial_amount | NUMERIC | 初始金額 |
| monthly_contribution | NUMERIC | 月定投金額（預設 0） |
| annual_return_rate | NUMERIC | 假設年報酬率 |
| years | INTEGER | 模擬年數 |
| target_amount | NUMERIC | 目標金額 |
| final_value | NUMERIC | 模擬最終值 |
| total_contribution | NUMERIC | 總投入 |
| total_profit | NUMERIC | 總利潤 |
| target_achieved | BOOLEAN | 是否達成目標 |
| result_json | JSONB | 模擬結果詳細 JSON |
| created_at | TIMESTAMP | 建立時間 |

---

## 14. data_source_registry — 資料來源登錄表

目的：登錄與追蹤系統使用的所有資料來源（爬蟲、API、檔案），包含頻率、可靠性、授權等資訊。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| source_name | TEXT | 資料來源名稱 |
| source_type | TEXT | 來源類型（API / Web Scraping / File Upload 等） |
| base_url | TEXT | 基礎網址 |
| description | TEXT | 來源說明 |
| update_frequency | TEXT | 更新頻率 |
| reliability_level | TEXT | 可靠度等級 |
| license_note | TEXT | 授權說明 |
| enabled | BOOLEAN | 是否啟用（預設 true） |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 最後更新時間 |

---

## 15. data_quality_checks — 資料品質檢查結果表

目的：記錄資料品質檢查結果（缺失值、異常值、邏輯矛盾等）。

| 欄位 | 類型 | 備註 |
|------|------|------|
| id | SERIAL | 主鍵 |
| dataset_type | TEXT | 資料集類型（etf_master / etf_prices 等） |
| dataset_key | TEXT | 資料集識別鍵（如 symbol） |
| check_name | TEXT | 檢查項目名稱 |
| status | TEXT | 檢查狀態（PASS / FAIL / WARNING） |
| severity | TEXT | 嚴重程度（INFO / WARNING / ERROR） |
| message | TEXT | 檢查訊息 |
| checked_at | TIMESTAMP | 檢查時間 |

---

## 資料關係圖

```
etf_master
  ├─ symbol → etf_holdings.etf_symbol
  ├─ symbol → etf_prices.etf_symbol
  ├─ symbol → etf_dividends.etf_symbol
  ├─ symbol → etf_holding_snapshots.etf_symbol
  ├─ symbol → etf_industry_exposure.etf_symbol
  └─ symbol → etf_holding_change_events.etf_symbol

stock_industry
  └─ stock_symbol → etf_holdings.asset_symbol（間接參考）

etf_holding_snapshots
  └─ id → etf_holding_snapshot_items.snapshot_id

portfolio
  ├─ id → portfolio_items.portfolio_id
  └─ id → backtest_runs.portfolio_id

portfolio_items
  ├─ portfolio_id → portfolio.id
  └─ etf_symbol → etf_master.symbol
```

---

## 備註

- 所有時間戳記預設使用 PostgreSQL `NOW()` 函數。
- 所有 `NUMERIC` 欄位用於財務計算，以避免浮點數精度問題。
- JSONB 欄位（`result_json`）用於儲存複雜的結構化結果，支援完整的 SQL 查詢與索引。
- 資料來源追蹤欄位（`source_name`, `source_url`, `fetched_at`, `confidence_level` 等）用於資料完全性與可信度追蹤，符合 CLAUDE.md §7 要求。
- 快照機制（`etf_holding_snapshots` + `etf_holding_snapshot_items`）允許重新解析歷史持股，而不會遺失原始資料。
