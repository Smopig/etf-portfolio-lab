# 07. AI Assistant Spec — `/ai`

依 CLAUDE.md §6，本文件為 `/ai` 頁面實作前必須完成的 UX 規格。所有欄位對應 Phase 13 四個 AI 端點之真實回應，不臆測未提供之欄位。

---

## 0. 後端事實（設計基礎）

四個端點皆為 `POST /api/ai/...`，皆回傳 `{data: AIAnalysisResponse}`：

```ts
interface AIAnalysisResponse {
  analysis_text: string;
  provider: string | null;   // "mock" | "claude" | null
  model: string | null;
  refused: boolean;
  data_sources: string[];
  data_dates: string[];
  disclaimer: string;        // 永遠存在
}
```

| 端點 | body |
|---|---|
| `POST /api/ai/analyze-etf` | `{ symbol, question? }` |
| `POST /api/ai/analyze-portfolio` | `{ portfolio_id?, items?, question? }`（二者擇一，否則 400 `VALIDATION_ERROR`） |
| `POST /api/ai/explain-backtest` | `{ result: BacktestResult, question? }` |
| `POST /api/ai/explain-projection` | `{ result: ProjectionResult, question? }` |

特殊情形：
- **資料不足**：`analysis_text` 以「資料不足，無法分析」開頭、`provider=null`，未呼叫 LLM → 視為**資訊性回應**，非錯誤。
- **`refused=true`**：Claude 安全拒絕 → **不得顯示** `analysis_text` 原文，改顯示安全提示。
- 預設 provider 為 `"mock"`（離線、確定性、無需金鑰）。

---

## 1. UX Flow Specification

```text
進入 /ai
  └─ 1. 選擇分析情境（ContextPicker，四選一）
       ├─ ETF：從下拉/搜尋選擇 symbol（GET /api/etfs）
       ├─ Portfolio：從下拉選擇已存組合（GET /api/portfolios）→ portfolio_id
       ├─ 回測結果：使用者須「已在本次 session 執行過回測」
       │            → 選擇器列出本 session 暫存的回測結果（依名稱/時間）
       │            → 無暫存則導引「請先到 /backtest 執行一次回測」
       └─ 推算結果：同上，須先在 /projection 取得 ProjectionResult
  └─ 2.（可選）輸入自由文字問題 QuestionInput
  └─ 3. 送出 → 依情境呼叫對應端點
  └─ 4. AnalysisResultPanel 顯示：
       ├─ analysis_text（或資料不足/refused 的替代內容）
       ├─ ProviderBadge（mock/claude/—）
       ├─ CitationList（data_sources × data_dates）
       └─ DisclaimerBanner（disclaimer，常駐）
```

**單輪限制（重要設計約束）**：後端不提供對話歷史儲存，每次送出皆為**獨立、無記憶**的單輪請求/回應。UI 不得呈現「對話串」或暗示 AI 記得上一輪內容；每次送出視為一次全新分析請求（可保留「上一次結果」於畫面供對照，但不餵回模型）。

### 回測/推算情境取得方式
- `/backtest`、`/projection` 頁面執行成功後，將該次 `result` 物件存入前端 session 暫存（如 `sessionStorage` 或全域 store），並提供「以 AI 解釋此結果」按鈕，點擊後導向 `/ai?context=backtest`（或 `projection`）並帶入該次結果。
- `/ai` 頁面若無暫存結果，「回測結果」「推算結果」選項顯示為可選但 disabled，附文字「請先至『回測』/『資產推算』頁執行一次計算」+ 連結。

---

## 2. Information Architecture

- 路由：`/ai`（SideNav 第 8 項，沿用既有命名「AI 助手」）
- 頁面僅一個主任務，無子頁籤；情境切換透過 ContextPicker 內的四個分頁式選項（非路由切換，保留輸入問題與結果）
- ContextPicker 狀態決定下方表單欄位：
  - ETF → ETF 搜尋/下拉
  - Portfolio → Portfolio 下拉（`GET /api/portfolios`）
  - 回測結果 → session 暫存結果選擇（若有多筆，列名稱+時間）
  - 推算結果 → 同上
- 頁面不出現在全站搜尋之外的全域導覽變動；TopBar/SideNav 不變

---

## 3. Page Task Definition

> **主任務（單一）**：基於系統資料解釋分析結果。

PageHeader：
- `title`：「AI 助手」
- `subtitle`：「針對 ETF、投資組合、回測或推算結果，取得基於系統資料的研究說明（非投資建議）」

---

## 4. Component Hierarchy

```text
<page /ai>
├─ PageHeader（title/subtitle 如上）
├─ DisclaimerBanner（常駐，§5 樣式）── 進入頁面即顯示，非結果出現後才顯示
├─ [左欄 / 上方] ContextPicker
│   ├─ Tabs: ETF | Portfolio | 回測結果 | 推算結果
│   ├─ ETF: SearchSelect（GET /api/etfs → symbol,name）
│   ├─ Portfolio: Select（GET /api/portfolios → id,name）
│   ├─ 回測結果: Select（session 暫存列表，可能為空→disabled+引導）
│   └─ 推算結果: 同上
├─ QuestionInput
│   └─ 多行文字框（可選），placeholder：「想了解什麼？（可留空，AI 將提供一般性解讀）」
├─ 送出按鈕「開始分析」
├─ [右欄 / 下方] AnalysisResultPanel
│   ├─ ProviderBadge（provider/model 或「—」）
│   ├─ 內容區（依狀態切換，見 §8）
│   │   ├─ 正常：analysis_text（純文字/Markdown 簡單渲染）
│   │   ├─ 資料不足：InfoState（資訊性，非錯誤樣式）
│   │   └─ refused：SafetyNotice（不顯示原文）
│   ├─ CitationList（基於 SourceFooter 延伸：data_sources[] × data_dates[]）
│   └─ DisclaimerBanner（重複顯示於結果下方，§5）
└─ SourceFooter（若 data_sources 非空，整合進 CitationList；否則顯示「本次分析無外部資料來源」）
```

對應既有元件：
- `ProviderBadge` → 新元件，基於 `Badge`（tone: mock=`neutral`，claude=`info`，null=`neutral`「未呼叫模型」）
- `CitationList` → 基於 `SourceFooter` 的清單變體：每筆 `data_sources[i]` 配對 `data_dates[i]`（若長度不一致，分別列出兩個區塊「資料來源」「資料日期」）
- `DisclaimerBanner` → 基於現有免責聲明樣式（00 §4），但加上「常駐不可關閉」屬性
- `InfoState` / `SafetyNotice` → 基於 `EmptyState` 變體（不同 icon/tone）
- `ContextPicker` / `QuestionInput` / `AnalysisResultPanel` → 新元件，內部使用 `Select`、`SearchSelect`（沿用 ETF 選擇器既有實作）、`Badge`

---

## 5. Design System Rules

- 配色、間距、字級沿用 02 設計系統，不新增 token。
- **AnalysisResultPanel 主文字**：使用 `--text-primary`，行高 1.7（長文字易讀），段落間距 1em。
- **ProviderBadge**：
  - `provider==="mock"` → tone `neutral`，label「模擬模式（mock）」+ tooltip「目前使用離線模擬回應，非即時 AI 模型」
  - `provider==="claude"` → tone `info`，label「AI 模型：{model}」
  - `provider===null` → tone `neutral`，label「未呼叫 AI 模型」
- **CitationList**：清單樣式，每筆來源前綴圖示，`data_dates[i]` 以 `（資料日期：YYYY-MM-DD）` 附加；視覺上低於主文字一階（`--text-secondary`，字級小一級）
- **DisclaimerBanner**：
  - 固定於頁面頂部（進入頁面即顯示，不因結果出現/消失而隱藏）與結果下方各一份
  - 背景使用 `--bg-surface-raised` + 左側色條（`info` 色），icon + 文字
  - 內容＝後端 `disclaimer` 欄位（有結果時）；無結果時顯示頁面靜態版本：「AI 分析僅基於系統現有資料，不提供買賣建議，回測與推算結果不代表未來績效。」
  - 不可被使用者關閉/收合
- **SafetyNotice**（refused=true）：tone `warning`，背景使用 warning 色階，文字固定：「此次回應已被安全機制標記，內容未顯示。您可調整問題後重新嘗試。」不渲染 `analysis_text`。
- **InfoState**（資料不足）：tone `info`，非 error 樣式（不使用紅色/ErrorPanel），文字顯示 `analysis_text` 原文（已是「資料不足，無法分析...」開頭的友善說明），並附「您可以前往對應頁面確認資料是否已匯入」連結（連 `/data-sources`）。

---

## 6. Empty State

- 初次進入頁面，尚未送出任何請求：
  - DisclaimerBanner（靜態版）正常顯示
  - ContextPicker 預設選中「ETF」分頁，下拉未選擇任何值
  - AnalysisResultPanel 顯示 `EmptyState`：
    - icon：分析/對話類圖示
    - title：「尚未開始分析」
    - description：「請於上方選擇分析對象（ETF / 投資組合 / 回測結果 / 推算結果），可選填問題後點擊『開始分析』」
    - 無 action 按鈕（引導已在上方）
- 「回測結果」「推算結果」分頁若無 session 暫存：
  - 該分頁內容區顯示 `EmptyState`：「尚未有可分析的回測/推算結果」+ 按鈕連到 `/backtest` 或 `/projection`

---

## 7. Loading State

- 送出後：
  - 「開始分析」按鈕進入 loading（spinner + disabled + 文字「分析中...」）
  - AnalysisResultPanel 區域顯示 `LoadingSkeleton variant="text"`（3-4 行）+ ProviderBadge 位置顯示骨架
  - 因 mock provider 通常 <200ms、claude provider 可能數秒，**統一顯示 loading 狀態至少維持可感知時間**（避免閃爍：若 <150ms 完成仍短暫顯示 skeleton 一輪動畫）
  - ContextPicker 與 QuestionInput 於送出期間 disabled，避免重複送出

---

## 8. Error State

依 05 文件 §1 映射表，並新增本頁特例：

| 情況 | 顯示方式 |
|---|---|
| `NETWORK_ERROR` / 網路錯誤 | ErrorPanel：「無法連線到伺服器，請確認後端服務是否啟動。」+ 重試按鈕（重送上次請求） |
| `VALIDATION_ERROR`（400，Portfolio 情境未提供 `portfolio_id`/`items`） | 表單層級錯誤，不顯示於結果區；於 ContextPicker 下方顯示 inline 錯誤：「請選擇一個投資組合」，並阻擋送出（前端應先行驗證避免送出） |
| `NOT_FOUND`（如 ETF symbol 不存在） | ErrorPanel：「找不到資料，可能尚未匯入或代號輸入錯誤。」 |
| 後端回應 `analysis_text` 以「資料不足，無法分析」開頭、`provider=null` | **非錯誤**。視為 §5 InfoState，正常顯示於 AnalysisResultPanel，附 ProviderBadge「未呼叫 AI 模型」 |
| `refused === true` | **不顯示 `analysis_text`**。顯示 §5 SafetyNotice，仍顯示 DisclaimerBanner；CitationList 可選擇性隱藏（無意義） |
| 其他 `INTERNAL_ERROR`（500） | ErrorPanel：「系統發生錯誤，請稍後再試。」+ 重試按鈕 |

所有 ApiError 一律經 `errorToFriendlyMessage` 轉換，不顯示原始英文/code。

---

## 9. Responsive Behavior

- **Desktop（≥1280px）**：雙欄
  - 左欄（約 35%）：ContextPicker + QuestionInput + 送出按鈕
  - 右欄（約 65%）：AnalysisResultPanel
  - DisclaimerBanner 橫跨全寬，置於兩欄之上
- **Tablet（768–1279px）**：左欄與右欄各自全寬，垂直堆疊（ContextPicker 在上、結果在下），ContextPicker 的 Tabs 維持橫向
- **Mobile（<768px）**：
  - 全部垂直堆疊
  - ContextPicker 的 Tabs 改為下拉選單（避免 4 個 Tab 擠壓）
  - 「開始分析」按鈕 sticky 於底部（同 05 §4.6 表單慣例）
  - CitationList 文字換行顯示，不橫向 scroll

---

## 10. CLAUDE.md §7 合規檢查清單

- [x] 每次回應皆顯示 `disclaimer`（DisclaimerBanner 常駐，§5）
- [x] `data_sources` / `data_dates` 以 CitationList 呈現（§4、§5）
- [x] `provider`／`model` 以 ProviderBadge 標示，明確區分 mock 與 claude（§5）
- [x] 「資料不足，無法分析」情境以資訊性 InfoState 呈現，不偽裝為錯誤或捏造內容（§8）
- [x] `refused=true` 時不顯示原文，改顯示安全提示（§5、§8）
- [x] 全程不提供買賣指令；`disclaimer` 文字本身已包含此限制，前端不額外加註「建議買入/賣出」類文案
- [x] 回測/推算相關文字一律使用後端提供之 `disclaimer`，前端不自行改寫弱化語氣（呼應 05 §1 「回測/模擬用語」規範）

---

## 11. UX Review Checklist（對照 06 §通用檢查）

| # | 檢查項 | 本頁結果 |
|---|---|---|
| 1 | 主任務明確？ | PageHeader subtitle 明確說明「基於系統資料解釋分析結果」 |
| 2 | 第一眼知道要做什麼？ | ContextPicker + 送出按鈕位於首屏，無需 scroll |
| 3 | 關鍵結論在上方？ | AnalysisResultPanel 緊鄰 ContextPicker，雙欄同高顯示 |
| 4 | 表格可讀？ | 本頁無表格（N/A） |
| 5 | 圖表有意義？ | 本頁無圖表（N/A） |
| 6 | 指標有解釋？ | 本頁無 MetricCard（N/A）；改以 ProviderBadge + CitationList 提供脈絡 |
| 7 | 空狀態有引導？ | §6 EmptyState 明確引導選擇情境；回測/推算分頁無資料時導向對應頁面 |
| 8 | 錯誤狀態友善？ | §8 全部走 errorToFriendlyMessage 中文映射 |
| 9 | loading 清楚？ | §7 skeleton + 按鈕 loading 文字 |
| 10 | 繁中自然？ | 全文案繁中，無簡體/機翻 |
| 11 | 是否太像普通後台？ | 雙欄深色版面，沿用既有設計系統，非純白卡片 |
| 12 | 顏色一致性 | Badge tone 沿用 02 §1.4 既定色票，不新增色彩語意 |
| 13 | 免責聲明到位 | 常駐頂部 + 結果下方，不可關閉（§5） |
| 14 | SourceFooter/Citation 完整 | data_sources/data_dates 皆顯示；空陣列時顯示「本次分析無外部資料來源」 |
| 15 | 回測/模擬用語 | 直接採用後端 `disclaimer`，不弱化或改寫斷言語氣 |
| 16 | RWD 行為 | §9 desktop 雙欄 / tablet 堆疊 / mobile 下拉+sticky 按鈕 |

逐頁額外檢查（AI Assistant，更新自 06 文件原「即將推出」版本，Phase 13 上線後生效）：
- [ ] ContextPicker 四個分頁皆可正確帶出對應 API 請求 body
- [ ] `refused=true` 時確認原文未出現在 DOM（非僅 CSS 隱藏）
- [ ] 「資料不足」回應不誤判為錯誤（樣式上與 ErrorPanel 明確區分）
- [ ] mock/claude 切換時 ProviderBadge 正確反映後端實際回應之 `provider`

---

## 12. Out of Scope / Open Questions

- **無對話歷史**：後端不提供 AI 對話儲存端點，本頁恆為單輪請求/回應；不得實作「繼續對話」「AI 記得上下文」等 UI 暗示。若使用者連續提問，每次皆視為獨立請求（可重複帶入相同情境，但 `question` 各自獨立送出）。
- **回測/推算結果的 session 暫存機制**：暫存於前端（`sessionStorage` 或 store），重新整理頁面後可能遺失；是否需要更持久的機制（如暫存於後端 `POST /api/backtests?persist=true` 後以 id 引用）留待 Opus 評估，Phase 13 先以前端暫存實作。
- **Markdown 渲染範圍**：`analysis_text` 是否含 Markdown 語法（粗體/列點）目前未知；若 mock provider 僅回傳純文字，Phase 13 初版可先以純文字（保留換行）渲染，待確認後再評估是否需要 Markdown parser。
- **多筆回測/推算暫存的排序與命名**：若使用者在 session 中執行多次回測，選擇器如何命名/排序（依時間？依表單參數摘要？）為待定細節，不影響核心流程，留待實作時依現有 UI 慣例決定。
