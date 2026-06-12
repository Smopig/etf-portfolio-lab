# 04_DATA_MODEL_AND_SCHEMA.md — 資料模型與資料表設計

---

## 1. etf_master

ETF 主檔。

```sql
CREATE TABLE etf_master (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    name TEXT NOT NULL,
    issuer TEXT,
    listing_date DATE,

    management_type TEXT,
    asset_class TEXT,
    investment_style TEXT,
    strategy_type TEXT,

    tracking_index TEXT,
    index_provider TEXT,
    selection_method TEXT,
    weighting_method TEXT,
    rebalance_frequency TEXT,
    replication_method TEXT,

    expense_ratio NUMERIC,
    management_fee NUMERIC,
    custody_fee NUMERIC,
    dividend_frequency TEXT,

    source_name TEXT,
    source_url TEXT,
    data_date DATE,
    fetched_at TIMESTAMP,
    confidence_level TEXT,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 2. etf_holdings

ETF 目前或指定日期成分股。

```sql
CREATE TABLE etf_holdings (
    id SERIAL PRIMARY KEY,
    etf_symbol VARCHAR(20) NOT NULL,
    holding_date DATE NOT NULL,
    asset_symbol VARCHAR(20),
    asset_name TEXT,
    asset_type TEXT,
    weight NUMERIC,
    shares NUMERIC,
    market_value NUMERIC,

    source_name TEXT,
    source_url TEXT,
    fetched_at TIMESTAMP,
    confidence_level TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(etf_symbol, holding_date, asset_symbol)
);
```

---

## 3. stock_industry

股票產業分類。

```sql
CREATE TABLE stock_industry (
    id SERIAL PRIMARY KEY,
    stock_symbol VARCHAR(20) UNIQUE NOT NULL,
    stock_name TEXT,
    market TEXT,

    industry_level_1 TEXT,
    industry_level_2 TEXT,
    industry_level_3 TEXT,

    custom_sector TEXT,
    custom_theme TEXT,

    source_name TEXT,
    source_url TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. etf_industry_exposure

ETF 產業曝險快取表。

```sql
CREATE TABLE etf_industry_exposure (
    id SERIAL PRIMARY KEY,
    etf_symbol VARCHAR(20) NOT NULL,
    exposure_date DATE NOT NULL,
    industry_level_1 TEXT NOT NULL,
    industry_level_2 TEXT,
    weight NUMERIC NOT NULL,
    source_holding_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(etf_symbol, exposure_date, industry_level_1, industry_level_2)
);
```

---

## 5. etf_holding_snapshots

每次抓取 ETF 持股時建立一筆快照。

```sql
CREATE TABLE etf_holding_snapshots (
    id SERIAL PRIMARY KEY,
    etf_symbol VARCHAR(20) NOT NULL,
    snapshot_date DATE NOT NULL,
    source_name TEXT,
    source_url TEXT,
    raw_file_path TEXT,
    parser_version TEXT,
    fetched_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(etf_symbol, snapshot_date, source_name)
);
```

---

## 6. etf_holding_snapshot_items

快照中的成分股明細。

```sql
CREATE TABLE etf_holding_snapshot_items (
    id SERIAL PRIMARY KEY,
    snapshot_id INTEGER NOT NULL,
    asset_symbol VARCHAR(20),
    asset_name TEXT,
    asset_type TEXT,
    weight NUMERIC,
    shares NUMERIC,
    market_value NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 7. etf_holding_change_events

ETF 持股變化事件。

```sql
CREATE TABLE etf_holding_change_events (
    id SERIAL PRIMARY KEY,
    etf_symbol VARCHAR(20) NOT NULL,
    from_date DATE NOT NULL,
    to_date DATE NOT NULL,

    change_type TEXT NOT NULL,
    asset_symbol VARCHAR(20),
    asset_name TEXT,

    old_weight NUMERIC,
    new_weight NUMERIC,
    weight_delta NUMERIC,

    change_reason TEXT,
    confidence_level TEXT,
    source_type TEXT,
    source_url TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);
```

change_type：

- `ADDED`
- `REMOVED`
- `WEIGHT_INCREASE`
- `WEIGHT_DECREASE`
- `UNCHANGED`

source_type：

- `OFFICIAL_ANNOUNCEMENT`
- `SNAPSHOT_DIFF`
- `MANUAL_INPUT`

---

## 8. etf_prices

ETF 歷史價格。

```sql
CREATE TABLE etf_prices (
    id SERIAL PRIMARY KEY,
    etf_symbol VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    adjusted_close NUMERIC,
    volume NUMERIC,
    turnover NUMERIC,

    source_name TEXT,
    source_url TEXT,
    fetched_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(etf_symbol, trade_date, source_name)
);
```

---

## 9. etf_dividends

ETF 配息資料。

```sql
CREATE TABLE etf_dividends (
    id SERIAL PRIMARY KEY,
    etf_symbol VARCHAR(20) NOT NULL,
    ex_dividend_date DATE NOT NULL,
    payment_date DATE,
    dividend_amount NUMERIC,
    dividend_yield NUMERIC,

    source_name TEXT,
    source_url TEXT,
    fetched_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(etf_symbol, ex_dividend_date, source_name)
);
```

---

## 10. portfolio

使用者配置方案。

```sql
CREATE TABLE portfolio (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    base_currency TEXT DEFAULT 'TWD',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 11. portfolio_items

配置方案明細。

```sql
CREATE TABLE portfolio_items (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL,
    etf_symbol VARCHAR(20) NOT NULL,
    target_weight NUMERIC NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 12. backtest_runs

回測紀錄。

```sql
CREATE TABLE backtest_runs (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER,
    name TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

    initial_amount NUMERIC NOT NULL,
    monthly_contribution NUMERIC DEFAULT 0,

    rebalance_frequency TEXT,
    dividend_reinvest BOOLEAN DEFAULT TRUE,
    transaction_cost_rate NUMERIC DEFAULT 0,

    final_value NUMERIC,
    total_contribution NUMERIC,
    total_profit NUMERIC,
    cagr NUMERIC,
    max_drawdown NUMERIC,
    annualized_volatility NUMERIC,
    sharpe_ratio NUMERIC,

    result_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 13. projection_runs

財務模擬紀錄。

```sql
CREATE TABLE projection_runs (
    id SERIAL PRIMARY KEY,
    name TEXT,
    initial_amount NUMERIC NOT NULL,
    monthly_contribution NUMERIC DEFAULT 0,
    annual_return_rate NUMERIC NOT NULL,
    years INTEGER NOT NULL,
    target_amount NUMERIC,

    final_value NUMERIC,
    total_contribution NUMERIC,
    total_profit NUMERIC,
    target_achieved BOOLEAN,
    result_json JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 14. data_source_registry

資料來源登錄表。

```sql
CREATE TABLE data_source_registry (
    id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    base_url TEXT,
    description TEXT,
    update_frequency TEXT,
    reliability_level TEXT,
    license_note TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 15. data_quality_checks

資料品質檢查結果。

```sql
CREATE TABLE data_quality_checks (
    id SERIAL PRIMARY KEY,
    dataset_type TEXT NOT NULL,
    dataset_key TEXT NOT NULL,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT,
    message TEXT,
    checked_at TIMESTAMP DEFAULT NOW()
);
```
