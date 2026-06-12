# 06_ANALYTICS_BACKTEST_PROJECTION_SPEC.md — 分析、回測與財務模擬規格

---

## 1. ETF 集中度分析

### Top N 權重

計算：

```text
Top 1 權重
Top 3 權重
Top 5 權重
Top 10 權重
```

### HHI

```text
HHI = sum(weight_i ^ 2)
```

權重需使用小數，例如 20% = 0.2。

### 有效持股數

```text
Effective Number of Holdings = 1 / HHI
```

---

## 2. 產業曝險分析

將 ETF 成分股權重與股票產業分類合併。

### 輸出

- industry_level_1 exposure
- industry_level_2 exposure
- 半導體占比
- 金融占比
- 電子占比
- 傳產占比
- 最大產業占比
- 前三大產業占比

---

## 3. ETF 重疊度

### 成分股重疊

兩檔 ETF：

```text
overlap_assets = assets_A ∩ assets_B
```

### 加權重疊分數

```text
weighted_overlap = sum(min(weight_A_i, weight_B_i))
```

### 輸出

- 重疊股票數量
- 重疊股票清單
- 重疊權重
- 共同前十大股票
- 產業曝險相似度

---

## 4. Portfolio 穿透分析

使用者配置：

```text
ETF_A 40%
ETF_B 30%
ETF_C 30%
```

穿透後單一股票權重：

```text
portfolio_stock_weight_i =
sum(etf_weight_j * stock_weight_i_in_etf_j)
```

穿透後產業權重：

```text
portfolio_industry_weight_k =
sum(portfolio_stock_weight_i where stock_i belongs to industry_k)
```

---

## 5. 回測輸入

回測需支援：

- start_date
- end_date
- initial_amount
- monthly_contribution
- portfolio weights
- dividend_reinvest
- rebalance_frequency
- transaction_cost_rate
- benchmark optional

---

## 6. 回測輸出

必須輸出：

- final_value
- total_contribution
- total_profit
- CAGR
- max_drawdown
- annualized_volatility
- sharpe_ratio
- annual_returns
- portfolio_value_series
- drawdown_series

---

## 7. CAGR

```text
CAGR = (final_value / initial_total_basis) ^ (1 / years) - 1
```

若包含定期定額，CAGR 需小心解釋；也可額外計算 money-weighted return / IRR。

---

## 8. 最大回撤

```text
running_max = cumulative_max(portfolio_value)
drawdown = portfolio_value / running_max - 1
max_drawdown = min(drawdown)
```

---

## 9. 年化波動

```text
daily_returns = pct_change(portfolio_value)
annualized_volatility = std(daily_returns) * sqrt(252)
```

---

## 10. Sharpe Ratio

```text
Sharpe = (annualized_return - risk_free_rate) / annualized_volatility
```

MVP 可先假設 risk_free_rate = 0，正式版需可設定。

---

## 11. 配息再投入

配息資料需包含：

- ex_dividend_date
- payment_date
- dividend_amount

再投入邏輯：

```text
若 dividend_reinvest = true：
在 payment_date 將現金配息按配置買回 ETF
```

MVP 可簡化為除息日或發放日再投入，但需明確標示。

---

## 12. 再平衡

支援：

- 不再平衡
- 每月
- 每季
- 每半年
- 每年
- 偏離目標超過門檻才再平衡

再平衡需考慮：

- 交易成本
- 權重目標
- 可用現金
- 小數股 / 整股假設

---

## 13. 財務模擬

### 未來值公式

每年化報酬率轉月報酬率：

```text
monthly_rate = (1 + annual_rate) ^ (1 / 12) - 1
```

每月滾動：

```text
value = value * (1 + monthly_rate) + monthly_contribution
```

---

## 14. 情境模擬

需支援：

- 保守情境
- 中性情境
- 樂觀情境

例如：

```text
保守：4%
中性：6%
樂觀：8%
```

---

## 15. 目標倒推

需支援：

- 目標金額倒推所需年數
- 目標金額倒推每月投入
- 目標金額倒推年化報酬率

---

## 16. 重要聲明

所有回測與財務模擬結果必須顯示：

```text
回測結果不代表未來績效。
未來模擬基於假設報酬率，不代表保證收益。
本系統只提供研究分析與風險理解，不提供直接買賣建議。
```
