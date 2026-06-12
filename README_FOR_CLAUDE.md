# ETF Portfolio Lab — Claude 專案入口說明

> 本文件是 Claude / Claude Code 進入本專案後必讀的總入口。  
> 請先閱讀本文件，再依序閱讀其他規格文件。

---

## 1. 專案定位

本專案名稱：

**ETF Portfolio Lab — ETF 配置研究、回測與財務模擬系統**

這不是即時看盤系統，也不是自動交易系統。  
本系統暫時不需要即時報價、WebSocket 或券商下單功能。

本系統的核心目標是協助使用者理解：

1. 每檔 ETF 是什麼類型？
2. ETF 是主動型、被動型、Smart Beta、債券型、主題型，還是其他型態？
3. ETF 實際持有哪些成分股？
4. 每檔成分股權重是多少？
5. ETF 的產業曝險是多少？
6. 不同 ETF 之間是否高度重疊？
7. 使用者建立多檔 ETF 配置後，穿透後實際股票與產業曝險如何？
8. 某個 ETF 組合過去回測表現如何？
9. 若假設年化報酬率、投入本金、每月投入金額，未來可能累積多少資產？
10. 若有財務目標，應該如何倒推每月投入、投資年限或所需年化報酬率？

---

## 2. 專案核心原則

本專案必須遵守：

- 資料優先，不可先做空洞 UI。
- 分析邏輯必須可測試。
- 資料來源必須可追溯。
- 外部資料來源不可寫死在業務邏輯裡。
- AI 分析只能基於系統資料，不可憑空推測。
- 不提供直接買進 / 賣出指令。
- 前端必須先有 UX / UI 規格，再開始施工。
- Opus 4.8 只做總指揮、架構、分派、審查與總結，不做大量實作。

---

## 3. 建議閱讀順序

Claude 進入專案後，請依序閱讀：

1. `README_FOR_CLAUDE.md`
2. `CLAUDE.md`
3. `01_PRODUCT_REQUIREMENTS.md`
4. `02_SYSTEM_ARCHITECTURE.md`
5. `03_IMPLEMENTATION_PLAN.md`
6. `04_DATA_MODEL_AND_SCHEMA.md`
7. `05_DATA_SOURCES_AND_PROVIDER_STRATEGY.md`
8. `06_ANALYTICS_BACKTEST_PROJECTION_SPEC.md`
9. `07_UX_UI_DESIGN_SPEC.md`
10. `08_AGENT_MODEL_DELEGATION_POLICY.md`
11. `09_DEVELOPMENT_TASK_BREAKDOWN.md`
12. `10_ACCEPTANCE_CRITERIA_AND_QA.md`

---

## 4. 第一版 MVP 範圍

第一版 MVP 必須完成：

- ETF 主檔資料結構
- ETF 類型分類
- ETF 成分股匯入
- 股票產業分類匯入
- ETF 歷史價格匯入
- ETF 配息資料匯入
- 單檔 ETF 成分股分析
- 單檔 ETF 產業曝險分析
- ETF 重疊度分析
- Portfolio Builder
- 穿透式股票曝險
- 穿透式產業曝險
- 簡易歷史回測
- 複利財務模擬
- 資料品質檢查
- 基本前端頁面
- README 與啟動方式

第一版暫時不要做：

- 即時報價
- WebSocket
- 自動交易
- 完整券商串接
- 全部投信網站自動爬蟲
- 複雜多 Agent 自動化框架
- 預測式買賣建議

---

## 5. 技術棧建議

建議技術棧：

- Frontend：Next.js + React + TypeScript
- UI：Tailwind CSS + shadcn/ui
- Chart：ECharts，MVP 可先用 Recharts
- Backend：Python FastAPI
- Database：PostgreSQL
- ORM：SQLAlchemy + Alembic，MVP 可評估 SQLModel
- Data Processing：pandas / numpy
- Scheduler：APScheduler
- AI Layer：Claude / OpenAI / MiniMax Provider abstraction
- Dev：Docker Compose

---

## 6. 開發總順序

正確順序：

```text
資料結構
→ 資料匯入
→ 資料清洗
→ 分析計算
→ API
→ 前端
→ AI
→ 自動更新
```

錯誤順序：

```text
先做漂亮 UI
→ 再補資料
→ 再補分析
```

這會導致系統看起來有功能，但分析結果不可靠。

---

## 7. 每輪工作回報格式

每一輪 Claude / Agent 工作完成後，必須回報：

```markdown
## 本輪任務

## 分派內容

## 使用模型 / Agent

## 完成內容

## 新增 / 修改檔案

## 如何測試

## Opus 審查結果

## 發現問題

## 下一步建議
```
