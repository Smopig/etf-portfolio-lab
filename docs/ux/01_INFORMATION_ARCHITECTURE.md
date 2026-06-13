# 01. Information Architecture

## 1. 站點地圖

```text
/                          Dashboard（研究入口）
/etf/[symbol]              ETF Detail
/compare                   ETF Compare（多檔比較）
/portfolio                 Portfolio Builder（含列表 + 建立/編輯）
/portfolio/[id]            Portfolio 詳情（穿透曝險／集中度／警示）
/backtest                  Backtest
/projection                Projection
/data-sources              Data Sources
/ai                         AI Assistant
```

說明：
- `frontend/app/` 目前僅有根 `page.tsx`，以上路由為 Phase 11 新增的 App Router 結構建議（`app/etf/[symbol]/page.tsx`、`app/compare/page.tsx` 等）。
- `/portfolio/[id]` 是否獨立路由或以 modal/tab 呈現由 Sonnet 在 Phase 11 決定；本規格僅要求「建立」與「分析結果」邏輯分離。

---

## 2. 左側導覽（SideNav）

固定顯示於桌面版左側，順序如下（對應 CLAUDE.md §1 主任務分類）：

| 順序 | 名稱 | 路由 | 圖示用途說明 |
|---|---|---|---|
| 1 | Dashboard | `/` | 系統總覽 / 進入點 |
| 2 | ETF 詳情 | `/etf/[symbol]`（無預設，從搜尋/列表進入） | 單檔研究 |
| 3 | ETF 比較 | `/compare` | 多檔比較 |
| 4 | 投資組合 | `/portfolio` | 配置建立 |
| 5 | 回測 | `/backtest` | 歷史驗證 |
| 6 | 資產推算 | `/projection` | 未來估算 |
| 7 | 資料來源 | `/data-sources` | 資料品質管理 |
| 8 | AI 助手 | `/ai` | 資料說明（即將推出） |

ETF Detail 不放在主導覽固定項目中（無預設 symbol），而是透過：
- TopBar 全域 ETF 搜尋框（輸入代號跳轉 `/etf/[symbol]`）
- Dashboard / Compare / Portfolio 頁面內的 ETF symbol 連結

---

## 3. 頁面 → 主要 API 對照表

| 頁面 | 主要 API | 次要 API |
|---|---|---|
| Dashboard | `GET /api/etfs`（總數、清單） | `GET /api/data-quality`（品質警告）、`GET /api/imports/status`（最後更新） |
| ETF Detail | `GET /api/etfs/{symbol}`（卡片：策略、集中度、top3產業、provenance） | `GET /api/etfs/{symbol}/holdings`、`GET /api/etfs/{symbol}/concentration`、`GET /api/etfs/{symbol}/industry-exposure`、`POST /api/ai/analyze-etf`（501） |
| ETF Compare | `GET /api/etfs/compare?symbols=A,B,C`（multi-overlap matrix） | 每檔 `GET /api/etfs/{symbol}`、`GET /api/etfs/overlap?symbols=A,B`（兩檔時，含 industry_similarity）、`POST /api/ai/analyze-portfolio`（501，比較摘要用） |
| Portfolio Builder | `GET /api/portfolios`、`POST /api/portfolios`、`PUT /api/portfolios/{id}` | `POST /api/portfolios/analyze`（草稿即時分析）、`GET /api/portfolios/{id}/exposure`、`GET /api/portfolios/{id}/concentration`、`GET /api/portfolios/{id}/overlap-risk`、`GET /api/portfolios/{id}/warnings` |
| Backtest | `POST /api/backtests`（含 `?persist=`） | `GET /api/portfolios`（選擇 Portfolio 來源） |
| Projection | `POST /api/projections/scenarios`（情境圖） | `POST /api/projections`（單一情境+persist）、`POST /api/projections/goal-seek`（目標倒推） |
| Data Sources | `GET /api/data-sources`、`GET /api/data-quality` | `GET /api/imports/status`（匯入歷史/CLI 說明） |
| AI Assistant | `POST /api/ai/analyze-etf`、`POST /api/ai/analyze-portfolio`（皆 501） | — |

---

## 4. 跨頁導覽關係

```text
Dashboard
  ├─ 「半導體曝險最高 ETF」「集中度最高 ETF」等卡片 → ETF Detail (/etf/[symbol])
  ├─ 「快速入口」 → ETF Compare / Portfolio Builder / Backtest / Projection
  └─ 「資料品質警告」 → Data Sources

ETF Detail
  ├─ Top holdings 中的個股 → （Phase 11+ 可選）股票反查頁，目前無路由，暫以唯讀文字呈現
  └─ 「加入比較」 → ETF Compare（帶入 symbol）

ETF Compare
  └─ 「建立此組合的 Portfolio」 → Portfolio Builder（帶入 symbols 草稿）

Portfolio Builder
  ├─ 「執行回測」 → Backtest（帶入 portfolio_id）
  └─ 「推算未來資產」 → Projection

Backtest / Projection
  └─ 「返回投資組合」 → Portfolio Builder

Data Sources
  └─ 「查看受影響 ETF」（資料品質訊息含 dataset_key 時）→ ETF Detail
```

---

## 5. URL 參數慣例

| 路由 | Query / Path 參數 | 用途 |
|---|---|---|
| `/etf/[symbol]` | `?level=1|2`（產業層級）、`?date=YYYY-MM-DD`（指定 holding_date） | 對應 API 的 `level` / `date` query |
| `/compare` | `?symbols=A,B,C` | 對應 `symbols` query（逗號分隔） |
| `/portfolio?draft=A:0.5,B:0.5` | 草稿模式：未儲存即可呼叫 `/portfolios/analyze` | 不落地 DB，純前端狀態 |
| `/backtest?portfolio_id=1` | 預選 Portfolio | 對應 `BacktestRequest.portfolio_id` |
| `/projection?years=20` | 預填年限 | 對應 `ProjectionRequest.years` |
