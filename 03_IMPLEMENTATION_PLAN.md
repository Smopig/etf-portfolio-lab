# 03_IMPLEMENTATION_PLAN.md — ETF Portfolio Lab 工程實作計畫

---

## 1. 實作總原則

本專案必須依照：

```text
資料優先
分析其次
API 第三
前端第四
AI 最後
```

不可一開始就製作大量 UI mockup。

---

## 2. Phase 0：建立專案骨架

### 目標

建立可啟動的 monorepo 專案。

### 任務

- 建立 `backend/`
- 建立 `frontend/`
- 建立 `data/`
- 建立 `docs/`
- 建立 `docker-compose.yml`
- 建立 `.env.example`
- 建立 README
- 建立 FastAPI hello world
- 建立 Next.js hello world
- 建立 PostgreSQL container

### 驗收標準

可以執行：

```bash
docker compose up
```

並開啟：

```text
Frontend: http://localhost:3000
Backend Swagger: http://localhost:8000/docs
```

---

## 3. Phase 1：資料庫 Schema

### 目標

建立所有核心資料表。

### 必做資料表

- `etf_master`
- `etf_holdings`
- `etf_holding_snapshots`
- `etf_holding_snapshot_items`
- `etf_holding_change_events`
- `stock_industry`
- `etf_prices`
- `etf_dividends`
- `portfolio`
- `portfolio_items`
- `backtest_runs`
- `projection_runs`
- `data_source_registry`
- `data_quality_checks`

### 驗收標準

- migration 可執行
- 資料表可建立
- 有基本 seed data
- 有 schema 文件

---

## 4. Phase 2：CSV / Excel 匯入

### 目標

先不自動爬蟲，先支援手動匯入。

### 任務

建立 scripts：

- `import_etf_master.py`
- `import_holdings.py`
- `import_industry.py`
- `import_prices.py`
- `import_dividends.py`

### 支援格式

- CSV
- Excel
- UTF-8
- Big5 / CP950 需能處理或明確報錯

### 驗收標準

能匯入 sample data：

```bash
python scripts/import_etf_master.py data/samples/etf_master.csv
python scripts/import_holdings.py data/samples/0050_holdings.csv
python scripts/import_industry.py data/samples/stock_industry.csv
python scripts/import_prices.py data/samples/0050_prices.csv
python scripts/import_dividends.py data/samples/0050_dividends.csv
```

---

## 5. Phase 3：資料品質檢查

### 目標

避免爛資料進入分析。

### 檢查項目

- ETF 持股權重是否接近 100%
- 成分股代號是否缺失
- 股票產業分類是否缺失
- 價格資料日期是否缺漏
- 配息資料是否重複
- 資料日期是否過舊
- ETF 主檔是否缺少重要欄位
- 資料來源是否記錄完整

### 驗收標準

每次匯入後產生 `data_quality_checks` 紀錄。

---

## 6. Phase 4：ETF 分析服務

### 目標

建立單檔 ETF 分析能力。

### 功能

- 前十大成分股
- Top 1 / Top 3 / Top 5 / Top 10 權重
- HHI
- 有效持股數
- 產業占比
- 最大產業占比
- 前三大產業占比
- 股票反查 ETF
- 產業反查 ETF

### 驗收標準

有 service tests：

- `test_exposure_service.py`
- `test_concentration_service.py`
- `test_reverse_lookup_service.py`

---

## 7. Phase 5：ETF 重疊度分析

### 目標

比較不同 ETF 是否高度重疊。

### 功能

- 兩檔 ETF 重疊成分股
- 多檔 ETF 重疊分析
- 加權重疊分數
- 共同前十大持股
- 產業曝險相似度

### 驗收標準

輸入：

```text
0050, 006208
```

能輸出：

- 重疊股票清單
- 重疊權重
- 重疊程度評級

---

## 8. Phase 6：Portfolio Builder

### 目標

建立 ETF 組合並穿透分析。

### 功能

- 建立配置方案
- ETF 權重加總檢查
- 穿透後股票曝險
- 穿透後產業曝險
- 組合集中度
- 組合重疊風險
- 配置方案比較

### 驗收標準

輸入：

```text
0050 40%
00878 30%
00679B 30%
```

能輸出：

- ETF 配置
- 股票曝險
- 產業曝險
- 集中度
- 風險提醒

---

## 9. Phase 7：回測引擎

### 目標

建立歷史回測功能。

### 支援

- 單筆投入
- 定期定額
- 配息再投入
- 不再平衡
- 每季再平衡
- 每半年再平衡
- 每年再平衡
- 交易成本

### 輸出

- 最終資產
- 總投入本金
- 投資收益
- CAGR
- 最大回撤
- 年化波動
- Sharpe Ratio
- 年度報酬
- 資產曲線
- 回撤曲線

### 驗收標準

必須有單元測試驗證：

- 報酬率計算
- CAGR
- MDD
- 定期定額現金流
- 再平衡邏輯
- 配息再投入邏輯

---

## 10. Phase 8：財務模擬

### 目標

建立未來複利估算與目標倒推。

### 功能

- 固定年化報酬率模擬
- 多情境模擬
- 目標金額倒推
- 每月投入倒推
- 所需報酬率倒推
- 達標年數估算

### 驗收標準

輸入：

```text
初始投入 1,000,000
每月投入 20,000
年化報酬 6%
期間 20 年
```

能輸出：

- 未來資產
- 本金
- 投資收益
- 年度曲線

---

## 11. Phase 9：API endpoints

### 目標

將分析服務暴露給前端。

### 必做 API

- ETF API
- Holding API
- Industry API
- Compare API
- Portfolio API
- Backtest API
- Projection API
- Data Import API
- AI API

### 驗收標準

- `/docs` 可測
- 回傳格式一致
- 錯誤格式一致
- 有 API tests

---

## 12. Phase 10：前端 UX / UI

### 目標

建立可用且好用的前端。

### 順序

1. UX specification
2. Design system
3. Component hierarchy
4. Dashboard
5. ETF Detail
6. ETF Compare
7. Portfolio Builder
8. Backtest
9. Projection
10. Data Sources
11. AI Assistant

### 驗收標準

- 不可只有 mock data
- 每頁都能接 API
- 有 loading / empty / error state
- 所有文字使用繁體中文
- 表格可排序 / 搜尋 / 篩選
- 圖表有明確解釋

---

## 13. Phase 11：Data Provider 自動化

### 目標

逐步從手動匯入升級為半自動 / 自動資料更新。

### 順序

1. CSV Provider
2. Excel Provider
3. Yahoo Finance Provider
4. TWSE Provider
5. Fund Company Provider
6. Scheduler

### 驗收標準

- Provider 介面一致
- 每次抓取有 source log
- 失敗時有錯誤紀錄
- 不影響既有手動匯入

---

## 14. Phase 12：AI 分析助手

### 目標

讓 AI 基於系統資料做說明。

### 功能

- 單檔 ETF 分析摘要
- 多檔 ETF 比較摘要
- Portfolio 曝險摘要
- 回測結果摘要
- 財務模擬摘要
- 風險提醒

### 驗收標準

- AI 回答需引用系統資料
- 不可憑空推論
- 不可直接給買賣指令
- 必須顯示資料日期與來源
