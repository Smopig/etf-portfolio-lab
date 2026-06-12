# REST API 參考 (API.md)

本文件記錄 ETF Portfolio Lab 的所有 REST API 端點、請求參數、回應格式。

**基址**：`http://localhost:8000/api`

**文件**：訪問 `http://localhost:8000/docs` 查看互動式 Swagger UI

---

## 回應格式

所有成功回應遵循標準信封格式：

```json
{
  "data": {...},
  "meta": {}
}
```

所有錯誤回應：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

**常見錯誤碼**：
- `NOT_FOUND`：資源不存在（HTTP 404）
- `VALIDATION_ERROR`：輸入參數無效（HTTP 400）
- `NOT_IMPLEMENTED`：功能尚未實作（HTTP 501）
- `INTERNAL_ERROR`：伺服器內部錯誤（HTTP 500）

---

## ETF 端點 (`/etfs`)

### 列出 ETF

**端點**：`GET /api/etfs`

**查詢參數**：
| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `active` | bool | null | 篩選是否有效（null = 不篩選） |

**回應範例**：
```json
{
  "data": [
    {
      "symbol": "0050",
      "name": "元大台灣50",
      "issuer": "元大投信",
      "asset_class": "股票",
      "management_type": "被動",
      "is_active": true,
      "has_holdings": true,
      "has_price_data": true
    }
  ],
  "meta": {}
}
```

---

### 取得 ETF 詳情

**端點**：`GET /api/etfs/{symbol}`

**路徑參數**：
- `symbol` (string)：ETF 代碼，例如 `0050`

**回應範例**：
```json
{
  "data": {
    "symbol": "0050",
    "name": "元大台灣50",
    "issuer": "元大投信",
    "listing_date": "2003-06-30",
    "management_type": "被動",
    "asset_class": "股票",
    "tracking_index": "台灣50指數",
    "expense_ratio": 0.32,
    "dividend_frequency": "季配",
    "source_name": "公開資訊觀測站",
    "data_date": "2026-06-01",
    "confidence_level": "高"
  },
  "meta": {}
}
```

---

### 取得 ETF 成分股（持股）

**端點**：`GET /api/etfs/{symbol}/holdings`

**路徑參數**：
- `symbol` (string)：ETF 代碼

**查詢參數**：
| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `date` | date (YYYY-MM-DD) | null | 持股日期；若 null，使用最新 |
| `n` | int | 10 | 回傳的前 N 個持股（1-200） |

**回應範例**：
```json
{
  "data": {
    "etf_symbol": "0050",
    "holding_date": "2026-06-01",
    "holdings": [
      {
        "asset_symbol": "2330",
        "asset_name": "台積電",
        "weight": 19.50,
        "rank": 1
      },
      {
        "asset_symbol": "2317",
        "asset_name": "鴻海",
        "weight": 9.80,
        "rank": 2
      }
    ]
  },
  "meta": {}
}
```

---

### 取得 ETF 集中度指標

**端點**：`GET /api/etfs/{symbol}/concentration`

**路徑參數**：
- `symbol` (string)：ETF 代碼

**查詢參數**：
| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `date` | date (YYYY-MM-DD) | null | 持股日期；若 null，使用最新 |

**回應範例**：
```json
{
  "data": {
    "etf_symbol": "0050",
    "holding_date": "2026-06-01",
    "total_holdings": 50,
    "herfindahl_index": 0.0850,
    "top_10_weight": 65.5,
    "top_20_weight": 85.3,
    "concentration_score": "中等偏高"
  },
  "meta": {}
}
```

---

### 取得 ETF 產業曝露

**端點**：`GET /api/etfs/{symbol}/industry-exposure`

**路徑參數**：
- `symbol` (string)：ETF 代碼

**查詢參數**：
| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `level` | int | 1 | 產業分類層級（1 = 一級，2 = 二級） |
| `date` | date (YYYY-MM-DD) | null | 持股日期；若 null，使用最新 |

**回應範例**（level=1）：
```json
{
  "data": {
    "etf_symbol": "0050",
    "level": 1,
    "holding_date": "2026-06-01",
    "industries": [
      {
        "name": "資訊科技",
        "weight": 35.5,
        "holding_count": 12
      },
      {
        "name": "金融",
        "weight": 18.2,
        "holding_count": 5
      }
    ]
  },
  "meta": {}
}
```

---

### 比較多個 ETF

**端點**：`GET /api/etfs/compare`

**查詢參數**：
| 參數 | 類型 | 說明 |
|------|------|------|
| `symbols` | string | 逗號分隔的 ETF 代碼，例如 `0050,006208,00878` |

**回應範例**：
```json
{
  "data": {
    "comparison": {
      "etf_count": 3,
      "pairwise_overlaps": [
        {
          "etf_a": "0050",
          "etf_b": "006208",
          "overlap_rate": 0.92,
          "common_holdings": 45
        }
      ],
      "multi_overlap": {
        "all_three": ["2330", "2317", "2454"],
        "all_three_count": 3
      }
    }
  },
  "meta": {}
}
```

---

### ETF 排名

**端點**：`GET /api/etfs/ranking`

**查詢參數**：
| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `metric` | string | - | 排名指標（必填）：`expense_ratio`、`herfindahl_index`、`top_10_weight`、`holding_count`、`industry_exposure` |
| `order` | string | desc | 排序方向（`asc` 或 `desc`） |
| `limit` | int | 10 | 回傳結果數量（1-100） |
| `industry` | string | null | 產業名稱（metric=industry_exposure 時必填） |
| `level` | int | 1 | 產業層級（1 或 2） |

**回應範例**（metric=expense_ratio，order=asc）：
```json
{
  "data": [
    {
      "symbol": "006208",
      "name": "富邦台50",
      "value": 0.20
    },
    {
      "symbol": "0050",
      "name": "元大台灣50",
      "value": 0.32
    }
  ],
  "meta": {
    "metric": "expense_ratio",
    "order": "asc",
    "limit": 10
  }
}
```

---

### ETF 間重疊分析

**端點**：`GET /api/etfs/overlap`

**查詢參數**：
| 參數 | 類型 | 說明 |
|------|------|------|
| `symbols` | string | 逗號分隔的 2 個 ETF 代碼，例如 `0050,006208` |

**回應範例**：
```json
{
  "data": {
    "overlap": {
      "etf_a": "0050",
      "etf_b": "006208",
      "overlap_rate": 0.92,
      "common_holdings": 45,
      "total_holdings_a": 50,
      "total_holdings_b": 50
    },
    "industry_similarity": {
      "euclidean_distance": 0.15,
      "cosine_similarity": 0.98
    }
  },
  "meta": {}
}
```

---

## 產業端點 (`/industries`, `/stocks`)

### 按產業查找 ETF

**端點**：`GET /api/industries/{industry}/etf-ranking`

**路徑參數**：
- `industry` (string)：產業名稱，例如 `資訊科技`

**查詢參數**：
| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `level` | int | 1 | 產業層級（1 或 2） |

**回應範例**：
```json
{
  "data": [
    {
      "symbol": "0050",
      "name": "元大台灣50",
      "industry_weight": 35.5
    }
  ],
  "meta": {}
}
```

---

### 按股票查找 ETF

**端點**：`GET /api/stocks/{stock_symbol}/etfs`

**路徑參數**：
- `stock_symbol` (string)：股票代碼，例如 `2330`

**回應範例**：
```json
{
  "data": {
    "stock_symbol": "2330",
    "stock_name": "台積電",
    "etfs": [
      {
        "etf_symbol": "0050",
        "etf_name": "元大台灣50",
        "weight_in_etf": 19.50
      }
    ]
  },
  "meta": {}
}
```

---

## 投資組合端點 (`/portfolios`)

### 建立投資組合

**端點**：`POST /api/portfolios`

**請求體**：
```json
{
  "name": "我的組合",
  "description": "均衡股債配置",
  "base_currency": "TWD",
  "items": [
    {
      "etf_symbol": "0050",
      "target_weight": 0.60
    },
    {
      "etf_symbol": "006208",
      "target_weight": 0.40
    }
  ]
}
```

**回應範例**：
```json
{
  "data": {
    "id": 1,
    "name": "我的組合",
    "description": "均衡股債配置",
    "base_currency": "TWD",
    "items": [
      {
        "etf_symbol": "0050",
        "target_weight": 0.60
      },
      {
        "etf_symbol": "006208",
        "target_weight": 0.40
      }
    ],
    "total_weight": 1.0,
    "created_at": "2026-06-12T10:30:00",
    "updated_at": "2026-06-12T10:30:00"
  },
  "meta": {}
}
```

---

### 列出投資組合

**端點**：`GET /api/portfolios`

**回應範例**：
```json
{
  "data": [
    {
      "id": 1,
      "name": "我的組合",
      "base_currency": "TWD",
      "item_count": 2,
      "total_weight": 1.0,
      "created_at": "2026-06-12T10:30:00"
    }
  ],
  "meta": {}
}
```

---

### 取得投資組合詳情

**端點**：`GET /api/portfolios/{portfolio_id}`

**路徑參數**：
- `portfolio_id` (int)：投資組合 ID

**回應範例**：
```json
{
  "data": {
    "id": 1,
    "name": "我的組合",
    "description": "均衡股債配置",
    "base_currency": "TWD",
    "items": [
      {
        "etf_symbol": "0050",
        "target_weight": 0.60
      },
      {
        "etf_symbol": "006208",
        "target_weight": 0.40
      }
    ]
  },
  "meta": {}
}
```

---

### 更新投資組合

**端點**：`PUT /api/portfolios/{portfolio_id}`

**路徑參數**：
- `portfolio_id` (int)：投資組合 ID

**請求體**（可選欄位）：
```json
{
  "name": "新名稱",
  "description": "新描述",
  "base_currency": "USD",
  "items": [
    {
      "etf_symbol": "0050",
      "target_weight": 0.50
    },
    {
      "etf_symbol": "006208",
      "target_weight": 0.50
    }
  ]
}
```

**回應範例**：
```json
{
  "data": {
    "id": 1,
    "name": "新名稱",
    "updated_at": "2026-06-12T11:00:00"
  },
  "meta": {}
}
```

---

### 刪除投資組合

**端點**：`DELETE /api/portfolios/{portfolio_id}`

**路徑參數**：
- `portfolio_id` (int)：投資組合 ID

**回應範例**：
```json
{
  "data": {
    "deleted": true,
    "id": 1
  },
  "meta": {}
}
```

---

### 分析投資組合（ad-hoc）

**端點**：`POST /api/portfolios/analyze`

**請求體**（不保存，只分析）：
```json
{
  "items": [
    {
      "etf_symbol": "0050",
      "target_weight": 0.60
    },
    {
      "etf_symbol": "006208",
      "target_weight": 0.40
    }
  ]
}
```

**回應範例**：
```json
{
  "data": {
    "validation": {
      "total_weight": 1.0,
      "is_valid": true,
      "warnings": []
    },
    "stock_exposure": {
      "total_stocks": 95,
      "top_stocks": [
        {
          "symbol": "2330",
          "name": "台積電",
          "weight": 11.5
        }
      ]
    },
    "industry_exposure": {
      "level": 1,
      "industries": [
        {
          "name": "資訊科技",
          "weight": 32.1
        }
      ]
    },
    "concentration": {
      "herfindahl_index": 0.065,
      "top_10_weight": 58.3
    },
    "warnings": []
  },
  "meta": {}
}
```

---

### 投資組合穿透分析

**端點**：`GET /api/portfolios/{portfolio_id}/exposure`

**路徑參數**：
- `portfolio_id` (int)：投資組合 ID

**查詢參數**：
| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `level` | int | 1 | 產業層級（1 或 2） |

**回應範例**：
```json
{
  "data": {
    "portfolio_id": 1,
    "stock_exposure": {
      "total_stocks": 95,
      "top_10_weight": 58.3
    },
    "industry_exposure": {
      "level": 1,
      "industries": [
        {
          "name": "資訊科技",
          "weight": 32.1
        }
      ]
    }
  },
  "meta": {}
}
```

---

### 投資組合集中度分析

**端點**：`GET /api/portfolios/{portfolio_id}/concentration`

**路徑參數**：
- `portfolio_id` (int)：投資組合 ID

**回應範例**：
```json
{
  "data": {
    "portfolio_id": 1,
    "herfindahl_index": 0.065,
    "top_10_weight": 58.3,
    "concentration_score": "適中"
  },
  "meta": {}
}
```

---

### 投資組合重疊風險

**端點**：`GET /api/portfolios/{portfolio_id}/overlap-risk`

**路徑參數**：
- `portfolio_id` (int)：投資組合 ID

**回應範例**：
```json
{
  "data": {
    "portfolio_id": 1,
    "pairwise_overlaps": [
      {
        "etf_a": "0050",
        "etf_b": "006208",
        "overlap_rate": 0.92,
        "risk_level": "高"
      }
    ]
  },
  "meta": {}
}
```

---

### 投資組合警告

**端點**：`GET /api/portfolios/{portfolio_id}/warnings`

**路徑參數**：
- `portfolio_id` (int)：投資組合 ID

**回應範例**：
```json
{
  "data": {
    "portfolio_id": 1,
    "warnings": [
      {
        "type": "overlap",
        "severity": "warning",
        "message": "ETF 0050 與 006208 重疊率高達 92%"
      }
    ]
  },
  "meta": {}
}
```

---

## 回測端點 (`/backtests`)

### 執行回測

**端點**：`POST /api/backtests`

**查詢參數**：
| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `persist` | bool | false | 是否將結果保存至資料庫 |

**請求體**（兩種方式）：

**方式 1：指定投資組合 ID**
```json
{
  "portfolio_id": 1,
  "start_date": "2020-01-01",
  "end_date": "2026-06-12",
  "initial_amount": 100000,
  "monthly_contribution": 5000,
  "dividend_reinvest": true,
  "rebalance_frequency": "quarterly",
  "transaction_cost_rate": 0.001,
  "risk_free_rate": 0.02
}
```

**方式 2：直接指定 ETF 與權重**
```json
{
  "symbols": ["0050", "006208"],
  "weights": [0.60, 0.40],
  "start_date": "2020-01-01",
  "end_date": "2026-06-12",
  "initial_amount": 100000,
  "monthly_contribution": 5000,
  "dividend_reinvest": true,
  "rebalance_frequency": "quarterly",
  "transaction_cost_rate": 0.001,
  "risk_free_rate": 0.02
}
```

**回應範例**：
```json
{
  "data": {
    "start_date": "2020-01-01",
    "end_date": "2026-06-12",
    "initial_amount": 100000,
    "final_amount": 125340.50,
    "total_return": 0.2534,
    "annualized_return": 0.0412,
    "volatility": 0.1250,
    "max_drawdown": -0.1850,
    "sharpe_ratio": 0.3280,
    "period_in_years": 6.47,
    "total_contributions": 360000,
    "total_dividends_received": 12500,
    "total_rebalancing_costs": 450
  },
  "meta": {}
}
```

---

## 財務模擬端點 (`/projections`)

### 簡單投影

**端點**：`POST /api/projections`

**請求體**：
```json
{
  "initial_amount": 100000,
  "monthly_contribution": 5000,
  "annual_return_rate": 0.08,
  "years": 10,
  "target_amount": 1000000,
  "persist": false,
  "name": "我的投影"
}
```

**回應範例**：
```json
{
  "data": {
    "initial_amount": 100000,
    "monthly_contribution": 5000,
    "annual_return_rate": 0.08,
    "years": 10,
    "target_amount": 1000000,
    "final_amount": 742500,
    "total_contributions": 600000,
    "total_return": 42500
  },
  "meta": {}
}
```

---

### 多情景投影

**端點**：`POST /api/projections/scenarios`

**請求體**：
```json
{
  "initial_amount": 100000,
  "monthly_contribution": 5000,
  "years": 10,
  "target_amount": 1000000,
  "scenarios": [
    {
      "name": "樂觀",
      "annual_return_rate": 0.10
    },
    {
      "name": "中性",
      "annual_return_rate": 0.08
    },
    {
      "name": "悲觀",
      "annual_return_rate": 0.05
    }
  ]
}
```

**回應範例**：
```json
{
  "data": {
    "scenarios": [
      {
        "name": "樂觀",
        "final_amount": 890000,
        "total_return": 190000
      },
      {
        "name": "中性",
        "final_amount": 742500,
        "total_return": 42500
      },
      {
        "name": "悲觀",
        "final_amount": 618000,
        "total_return": -82000
      }
    ]
  },
  "meta": {}
}
```

---

### 目標反演計算

**端點**：`POST /api/projections/goal-seek`

**請求體**（根據 `solve_for` 欄位）：

**求解年數**：
```json
{
  "initial_amount": 100000,
  "monthly_contribution": 5000,
  "annual_return_rate": 0.08,
  "target_amount": 1000000,
  "solve_for": "years"
}
```

**求解月投資額**：
```json
{
  "initial_amount": 100000,
  "annual_return_rate": 0.08,
  "years": 10,
  "target_amount": 1000000,
  "solve_for": "monthly_contribution"
}
```

**求解年報酬率**：
```json
{
  "initial_amount": 100000,
  "monthly_contribution": 5000,
  "years": 10,
  "target_amount": 1000000,
  "solve_for": "annual_return"
}
```

**回應範例**（solve_for=years）：
```json
{
  "data": {
    "required_years": 12.45,
    "message": "需時 12.45 年達到 1000000 目標"
  },
  "meta": {}
}
```

---

## AI 分析端點 (`/ai`)

### 分析 ETF

**端點**：`POST /api/ai/analyze-etf`

**請求體**：
```json
{
  "symbol": "0050",
  "question": "這檔 ETF 的風險特性如何？"
}
```

**回應範例**：
```json
{
  "data": {
    "symbol": "0050",
    "analysis": "元大台灣50 是一檔被動管理的台灣大型股 ETF，費用率 0.32% 相對低廉。成分股集中於台積電（19.5%）等科技大廠，產業風險偏高...",
    "provider": "mock",
    "data_sources": [
      {
        "type": "etf_master",
        "date": "2026-06-01"
      },
      {
        "type": "etf_holdings",
        "date": "2026-06-01"
      }
    ]
  },
  "meta": {}
}
```

---

### 分析投資組合

**端點**：`POST /api/ai/analyze-portfolio`

**請求體**（方式 1：按 ID）：
```json
{
  "portfolio_id": 1,
  "question": "這個組合有什麼風險？"
}
```

**請求體**（方式 2：ad-hoc items）：
```json
{
  "items": [
    {
      "etf_symbol": "0050",
      "target_weight": 0.60
    },
    {
      "etf_symbol": "006208",
      "target_weight": 0.40
    }
  ],
  "question": "這個組合有什麼風險？"
}
```

**回應範例**：
```json
{
  "data": {
    "portfolio_id": 1,
    "analysis": "該投資組合的 0050 和 006208 重疊率高達 92%，兩者都追蹤台灣 50 指數，構成重複持股風險...",
    "provider": "mock",
    "data_sources": []
  },
  "meta": {}
}
```

---

### 解讀回測結果

**端點**：`POST /api/ai/explain-backtest`

**請求體**：
```json
{
  "result": {
    "start_date": "2020-01-01",
    "end_date": "2026-06-12",
    "annualized_return": 0.0412,
    "volatility": 0.1250,
    "max_drawdown": -0.1850,
    "sharpe_ratio": 0.3280
  },
  "question": "這個回測結果說明了什麼？"
}
```

**回應範例**：
```json
{
  "data": {
    "explanation": "該投資組合在過去 6 年的年化報酬率為 4.12%，波動率為 12.5%，最大回撤達 18.5%。這表示該組合的風險調整後報酬（夏普比 0.33）相對不高...",
    "disclaimer": "本分析為研究用途，回測結果不代表未來績效。",
    "provider": "mock"
  },
  "meta": {}
}
```

---

### 解讀財務模擬結果

**端點**：`POST /api/ai/explain-projection`

**請求體**：
```json
{
  "result": {
    "initial_amount": 100000,
    "monthly_contribution": 5000,
    "annual_return_rate": 0.08,
    "years": 10,
    "final_amount": 742500
  },
  "question": "這個投影說明了什麼？"
}
```

**回應範例**：
```json
{
  "data": {
    "explanation": "假設初始投資 10 萬元，每月定額投資 5,000 元，年報酬率 8%，10 年後將累積約 74.25 萬元，總報酬 16.25 萬元...",
    "disclaimer": "本投影為參考，實際結果取決於市場表現與投資決策。",
    "provider": "mock"
  },
  "meta": {}
}
```

---

## 資料來源端點 (`/data-sources`)

### 列出資料來源

**端點**：`GET /api/data-sources`

**回應範例**：
```json
{
  "data": [
    {
      "id": 1,
      "source_name": "公開資訊觀測站",
      "source_type": "台灣證券交易所",
      "base_url": "https://mops.twse.gov.tw",
      "description": "台灣上市公司基本資訊與公告",
      "update_frequency": "日更新",
      "reliability_level": "高",
      "license_note": "公開資訊，政府數據",
      "enabled": true
    }
  ],
  "meta": {}
}
```

---

### 列出資料品質檢查結果

**端點**：`GET /api/data-quality`

**查詢參數**：
| 參數 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `dataset_type` | string | null | 篩選資料集類型（例如 `etf_master`, `etf_holdings`） |
| `status` | string | null | 篩選狀態（`pass`, `warning`, `fail`） |
| `limit` | int | 50 | 回傳筆數（1-500） |

**回應範例**：
```json
{
  "data": [
    {
      "id": 1,
      "dataset_type": "etf_master",
      "dataset_key": "0050",
      "check_name": "unique_symbol",
      "status": "pass",
      "severity": "info",
      "message": "Symbol 0050 is unique",
      "checked_at": "2026-06-12T09:00:00"
    }
  ],
  "meta": {}
}
```

---

## 資料匯入端點 (`/data-import`)

### 匯入狀態

**端點**：`GET /api/imports/status`

**回應範例**：
```json
{
  "data": {
    "recent_quality_checks": [
      {
        "dataset_type": "etf_master",
        "dataset_key": "0050",
        "check_name": "uniqueness",
        "status": "pass",
        "checked_at": "2026-06-12T09:00:00"
      }
    ],
    "note": "File-upload based data import is not implemented in this phase; data is currently loaded via CLI importers (Phase 2)."
  },
  "meta": {}
}
```

---

## 儀表板端點 (`/dashboard`)

### 儀表板摘要

**端點**：`GET /api/dashboard/summary`

**回應範例**：
```json
{
  "data": {
    "etf_count": 3,
    "etf_with_holdings": 1,
    "etf_with_prices": 1,
    "total_stocks": 95,
    "earliest_price_date": "2020-01-01",
    "latest_price_date": "2026-06-12",
    "price_data_completeness": 0.95
  },
  "meta": {}
}
```

---

## 健康檢查

### 服務健康狀態

**端點**：`GET /health`

**回應範例**：
```json
{
  "status": "ok"
}
```

---

## 根端點

### 歡迎訊息

**端點**：`GET /`

**回應範例**：
```json
{
  "message": "Welcome to the ETF Portfolio Lab API"
}
```
