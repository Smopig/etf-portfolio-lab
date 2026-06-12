# 00. UX 總覽 — ETF Portfolio Lab

## 1. 設計定位

```text
專業 ETF 研究終端 / 金融分析工作台
深色主題、高資訊密度、清楚層級、可解釋圖表
繁體中文介面
```

不得做成：普通後台管理系統、陽春表格頁、雜亂 dashboard、卡片堆疊 UI。

目標使用者：對 ETF 結構、成分股重疊、產業曝險、回測表現有研究需求的個人投資者。
系統定位：**研究與分析輔助工具**，非交易平台、非投顧服務。

---

## 2. 頁面骨架：「先摘要，再展開」

每一個分析型頁面（ETF Detail / ETF Compare / Portfolio Builder / Backtest / Projection）必須遵循以下垂直結構：

```text
┌─────────────────────────────────────────────┐
│ PageHeader：頁面標題 + 主任務一句話說明        │
├─────────────────────────────────────────────┤
│ 區塊 A：關鍵結論（上方）                       │
│   - MetricCard 群組：最重要的 3-6 個指標       │
│   - 每個指標都有「數值 + 等級 Badge + 一句話說明」│
├─────────────────────────────────────────────┤
│ 區塊 B：圖表與比較（中間）                     │
│   - ChartCard：標題 + 單位 + tooltip + 資料日期│
│   - 圖表下方一律附「這張圖告訴你什麼」說明文字  │
├─────────────────────────────────────────────┤
│ 區塊 C：詳細資料表（下方）                     │
│   - DataTable：可搜尋 / 排序 / 篩選 / 數字格式化│
├─────────────────────────────────────────────┤
│ 區塊 D：資料來源與更新時間（底部，全頁共用）    │
│   - SourceFooter：source_name + data_date     │
│   - 必要時附風險提醒 / 回測免責聲明             │
└─────────────────────────────────────────────┘
```

Dashboard / Data Sources / AI Assistant 為「入口型」與「工具型」頁面，結構略有調整（見 04_PAGE_SPECS.md），但仍須遵守「結論在上、明細在下、來源在底」的精神。

---

## 3. 全域規則：每個金融指標都要解釋

**禁止**：

```text
HHI: 0.184
```

**必須**：

```text
HHI（持股集中度指數）：0.184
集中度等級：中高
說明：前幾大持股對 ETF 影響較明顯，需注意單一股票或單一產業曝險。
資料日期：2026-03-31
```

### 3.1 標準呈現格式（MetricCard 規格）

每個 MetricCard 必須包含以下五要素，缺一不可：

| 要素 | 說明 | 範例 |
|---|---|---|
| 指標名稱（中文） | 避免單純英文縮寫 | 「持股集中度指數 (HHI)」 |
| 數值 | 格式化後數字 | `0.184` |
| 等級 Badge | 依門檻分級，顏色化 | 「中高」（橘色） |
| 一句話說明 | 此數值對使用者的意義 | 「前幾大持股對 ETF 影響較明顯…」 |
| 資料日期（可選，於卡片角標） | 若該指標與卡片整體日期不同才顯示 | `2026-03-31` |

### 3.2 分級門檻參考（後端已定義者直接沿用）

- **重疊度 (weighted_overlap_pct)**：≥70% 高度重疊／≥40% 中度／≥20% 低度／<20% 極低（`overlap_service._overlap_rating`）。
- **HHI**：> 0.15 視為集中度偏高（`portfolio_service.HHI_WARN_THRESHOLD`）；尚需 Opus/Sonnet 補充「低／中／中高／高」四級對照表供前端共用（見 06 backend gap）。
- 其餘指標（單一個股權重 > 30%、未分類曝險 > 30%、ETF 重疊 ≥ 60%）沿用 `portfolio_service` 中既有門檻常數，於 UI 呈現為對應 Badge 與警示文字。

---

## 4. 免責聲明的強制顯示位置（CLAUDE.md §7）

| 內容 | 顯示位置 | 文案來源 |
|---|---|---|
| 投資組合分析（穿透曝險、集中度、警示） | Portfolio Builder 頁尾 SourceFooter 區塊 | `portfolio_service.DISCLAIMER`：「本分析僅供研究參考，依系統現有資料計算，不代表未來績效，亦非投資買賣建議。」 |
| 回測結果 | Backtest 頁，資產曲線圖正上方 + 頁尾 | `backtest_service.DISCLAIMER`：「回測結果不代表未來績效，僅供研究分析。」 |
| 未來資產推算 | Projection 頁，情境圖正上方 + 頁尾 | `projection_service.DISCLAIMER`：「未來模擬基於假設報酬率，不代表保證收益，僅供研究分析。」 |
| AI Assistant 回覆 | 每則 AI 回覆下方固定附註 | 引用資料來源與日期 + 「本回答僅為資料說明與風險提醒，不構成買賣建議」 |

**規則**：免責聲明文字不可由前端自行改寫，必須原樣顯示後端回傳的 `disclaimer` 欄位（若無則使用上表預設文案）。位置必須在使用者「視覺路徑」上會看到（非隱藏在 tooltip 或 modal 內）。

---

## 5. 資料可信度與「無資料」原則

- 所有頁面禁止顯示憑空捏造的數字。若 API 回傳 `null` / 空陣列，UI 必須走「空狀態」（見 05_STATES_AND_RESPONSIVE.md），而非顯示假資料或 0。
- 每個 ETF 卡片型內容（ETF Detail、Compare）必須顯示 `data_provenance`（source_name、data_date、confidence_level）。
- `confidence_level` 對應「資料可信度」Badge：高／中／低（見 02_DESIGN_SYSTEM.md Badge 分類）。

---

## 6. 本文件與其他規格的關係

| 文件 | 內容 |
|---|---|
| 01_INFORMATION_ARCHITECTURE.md | 站點地圖、導覽結構、路由與 API 對照 |
| 02_DESIGN_SYSTEM.md | 色彩、字體、間距、Badge、圖表庫選擇 |
| 03_COMPONENT_HIERARCHY.md | 元件清單與 props 來源 |
| 04_PAGE_SPECS.md | 各頁面詳細規格、wireframe、API 對應 |
| 05_STATES_AND_RESPONSIVE.md | 空/載入/錯誤狀態、RWD 規則 |
| 06_UX_REVIEW_CHECKLIST.md | Phase 11 驗收清單 |
