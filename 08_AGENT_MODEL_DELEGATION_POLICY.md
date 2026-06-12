# 08_AGENT_MODEL_DELEGATION_POLICY.md — Agent 與模型分工規範

---

## 1. 核心目標

降低 Opus 4.8 token 消耗，同時提升專案品質。

Opus 4.8 必須當總指揮，不當苦工。

---

## 2. 模型角色

```text
Opus 4.8：Chief Architect / Orchestrator / Reviewer
Sonnet：主要工程師 / UX 設計 / 實作
Haiku：研究助理 / 文件助理 / 測試助理
```

---

## 3. Agent 架構

```text
Chief Architect — Opus 4.8
│
├── Data Engineer — Sonnet
├── Backend Engineer — Sonnet
├── Quant Engineer — Sonnet
├── UX Designer — Sonnet
├── Frontend Engineer — Sonnet
├── Research Assistant — Haiku
├── QA Assistant — Haiku
└── Documentation Assistant — Haiku
```

---

## 4. Chief Architect — Opus

### 負責

- 需求理解
- 任務拆解
- 架構決策
- 技術選型
- 任務分派
- 輸出審查
- 風險判斷
- 最終總結

### 不負責

- 大量 coding
- 大量 CSS
- 大量文件撰寫
- 大量資料研究
- 大量測試草稿
- 重複性格式整理

---

## 5. Data Engineer — Sonnet

負責：

- 資料庫 schema
- 資料匯入器
- Provider abstraction
- 資料清洗
- 資料品質檢查
- 資料來源 metadata
- 快照與變化事件

---

## 6. Backend Engineer — Sonnet

負責：

- FastAPI
- API endpoints
- service layer
- repository layer
- error handling
- API tests
- data validation

---

## 7. Quant Engineer — Sonnet

負責：

- ETF 集中度計算
- 產業曝險
- ETF 重疊度
- Portfolio 穿透分析
- 回測引擎
- CAGR / MDD / volatility / Sharpe
- 配息再投入
- 再平衡邏輯
- 財務模擬

---

## 8. UX Designer — Sonnet

負責：

- UX flow
- Information architecture
- Page task definition
- Component hierarchy
- Design system
- Empty / loading / error states
- UX review

---

## 9. Frontend Engineer — Sonnet

負責：

- Next.js pages
- React components
- Tailwind CSS
- shadcn/ui
- charts
- tables
- forms
- API integration
- frontend tests

---

## 10. Research Assistant — Haiku

負責：

- ETF 資料來源調查
- 投信網站欄位整理
- 官方文件摘要
- 指數公司公告整理
- 第三方資料源比較
- 資料取得難度評估

---

## 11. QA Assistant — Haiku

負責：

- 測試案例草稿
- edge cases
- API 測試清單
- UI 驗收清單
- 資料品質檢查清單

---

## 12. Documentation Assistant — Haiku

負責：

- README 草稿
- 使用說明
- API 文件草稿
- 匯入教學
- 開發紀錄
- changelog

---

## 13. 任務分派規則

| 任務 | 指派模型 |
|---|---|
| 架構決策 | Opus |
| 任務拆解 | Opus |
| 最終審查 | Opus |
| 後端實作 | Sonnet |
| 前端實作 | Sonnet |
| 資料庫設計 | Sonnet |
| 回測引擎 | Sonnet |
| UX 設計 | Sonnet |
| 資料來源調查 | Haiku |
| 文件整理 | Haiku |
| 測試案例草稿 | Haiku |
| CSV 範例資料 | Haiku |
| 錯誤訊息整理 | Haiku |
| 重複性小修 | Haiku |

---

## 14. 每輪回報格式

每輪必須使用：

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

---

## 15. 禁止事項

Opus 禁止：

- 未分派直接做完整大型功能
- 一口氣修改大量檔案且無審查
- 直接做整個前端
- 直接做大量文件
- 直接爬大量資料來源
- 自行跳過 UX 規劃
- 自行跳過資料品質檢查
