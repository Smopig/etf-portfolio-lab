# 02. Design System — 深色研究終端設計系統

## 1. 色彩 Tokens

### 1.1 背景分層（CSS variables，沿用並擴充 `globals.css`）

| Token | 值 | 用途 |
|---|---|---|
| `--bg-base` | `#0b0e14`（既有 `--background`） | 最底層頁面背景 |
| `--bg-surface` | `#11161f` | 卡片 / ChartCard / DataTable 容器 |
| `--bg-surface-raised` | `#171d29` | hover、modal、dropdown |
| `--bg-inset` | `#0e1219` | 表格 sticky header、code block |
| `--border-subtle` | `#232a38` | 一般分隔線、表格 row border |
| `--border-strong` | `#323b4e` | 卡片外框、focus ring 基底 |

### 1.2 文字

| Token | 值 | 用途 |
|---|---|---|
| `--text-primary` | `#e5e9f0`（既有 `--foreground`） | 主要文字 |
| `--text-secondary` | `#9aa5b8` | 說明文字、欄位標籤 |
| `--text-muted` | `#6b7484` | 次要提示、時間戳、SourceFooter |
| `--text-link` | `--accent-primary` | 連結 |

### 1.3 Accent / 互動色

| Token | 值 | 用途 |
|---|---|---|
| `--accent-primary` | `#3b82f6`（藍） | 主要按鈕、連結、選中狀態、focus ring |
| `--accent-primary-hover` | `#5b9bf8` | hover |
| `--accent-secondary` | `#8b5cf6`（紫） | 次要強調（如 AI Assistant 標識） |

### 1.4 語意色（資料品質 / 風險 Badge）

| Token | 值 | 用途 |
|---|---|---|
| `--status-success` | `#22c55e`（綠） | 可信度高、PASS、目標達成 |
| `--status-warning` | `#f59e0b`（橙） | 可信度中、WARN、集中度中高 |
| `--status-error` | `#ef4444`（紅） | 可信度低、FAIL、高風險、ERROR |
| `--status-info` | `#38bdf8`（淺藍） | NOT_IMPLEMENTED / 即將推出 / 中性提示 |
| `--status-neutral` | `#475569` | 未分類（Unclassified）、停用 |

語意色用於 Badge 背景時使用 12% alpha（例如 `rgba(34,197,94,0.12)`）+ 對應文字色，避免大面積實色破壞深色主題。

### 1.5 圖表系列色（Series Palette）

固定 10 色循環，用於產業占比、持股權重、ETF 比較等分類圖表，確保「同一產業/ETF 在不同圖表使用相同顏色」：

```
series-1  #3b82f6  series-2  #22c55e  series-3  #f59e0b  series-4  #ef4444
series-5  #8b5cf6  series-6  #06b6d4  series-7  #eab308  series-8  #ec4899
series-9  #84cc16  series-10 #f97316
unclassified  #475569（固定灰，永遠代表 Unclassified / 未分類）
```

**一致性規則**：產業分類（`industry_level_1`）依字母/固定清單排序後指派色票索引，跨頁面（ETF Detail、Compare、Portfolio Builder）對同一產業使用相同 series 顏色；`Unclassified` 永遠使用 `unclassified` 灰色，不進入循環。ETF 比較圖則依「使用者選取順序」指派 series 顏色給每個 symbol。

---

## 2. 字級 Typography Scale

| Token | 大小 / 行高 | 用途 |
|---|---|---|
| `text-display` | 28px / 36px, 600 | 頁面主標題（PageHeader） |
| `text-h2` | 20px / 28px, 600 | 區塊標題（ChartCard/DataTable 標題） |
| `text-h3` | 16px / 24px, 600 | MetricCard 標題、子區塊 |
| `text-body` | 14px / 20px, 400 | 一般文字、表格內容 |
| `text-small` | 12px / 16px, 400 | 說明文字、Badge、SourceFooter |
| `text-mono` | 13px / 18px, JetBrains Mono / monospace | 數字、百分比、代號（symbol） |

數字一律使用 `text-mono`，並以等寬字呈現以利表格對齊比較。

---

## 3. 間距 Spacing Scale

採 4px 基準（對應 Tailwind 預設）：

| Token | 值 | 用途 |
|---|---|---|
| `space-1` | 4px | icon 與文字間距 |
| `space-2` | 8px | Badge 內距、表格 cell 垂直間距 |
| `space-3` | 12px | 表單欄位間距 |
| `space-4` | 16px | 卡片內距、元件間距 |
| `space-6` | 24px | 區塊間距（上方摘要區 ↔ 圖表區） |
| `space-8` | 32px | 頁面區段間距（PageHeader ↔ 內容） |

---

## 4. Border / Radius

| Token | 值 | 用途 |
|---|---|---|
| `radius-sm` | 4px | Badge、輸入框 |
| `radius-md` | 8px | 卡片、ChartCard、DataTable 容器 |
| `radius-lg` | 12px | Modal、彈出面板 |
| `border-width-default` | 1px solid `var(--border-subtle)` | 卡片外框 |
| `border-width-focus` | 2px solid `var(--accent-primary)` | focus ring |

---

## 5. 表格樣式規則（對應 07 §6.1）

| 規則 | 說明 |
|---|---|
| Header | sticky top，背景 `--bg-inset`，文字 `--text-secondary`，`text-small` 大寫字距 |
| 第一欄（symbol/名稱） | sticky left（橫向 scroll 時固定），`text-mono` |
| 數字欄位 | 右對齊、`text-mono`、千分位、百分比固定小數位（如 `12.34%`） |
| 排序 | column header 可點擊，顯示 ▲▼ icon |
| 篩選/搜尋 | 表格上方工具列，輸入框 + 下拉篩選（如資產類別） |
| 列高 | 36px（高密度），hover 高亮 `--bg-surface-raised` |
| 空狀態 | 表格中央顯示圖示＋文字＋（若適用）操作按鈕，見 05 文件 |
| CSV 匯出 | 工具列右側按鈕，僅在「全部成分股表格」「回測年度報酬」「資料品質列表」等長表格提供 |

---

## 6. 圖表規則與圖表庫選型

### 6.1 選型：ECharts（優於 Recharts）

| 考量 | ECharts | Recharts |
|---|---|---|
| 熱力圖（重疊度 Heatmap，5.4 必須） | 原生支援 `heatmap` series | 無原生支援，需自製 |
| 大量資料/高密度（資產曲線+回撤+多系列） | 效能較佳，支援 dataZoom | 較吃力 |
| Tooltip 客製化（顯示資料日期/單位/解釋） | formatter 彈性高 | 中等 |
| 深色主題 | 內建 theme 機制，可整批套用 token | 需逐元件設定 |

**決定：採用 ECharts（透過 `echarts-for-react` 或官方 React wrapper）**，理由：Compare 頁的重疊度熱力圖、Backtest 的多系列資產曲線+回撤雙軸圖、Projection 的堆疊本金/收益圖都是 ECharts 的強項，且能用一份 theme 設定檔套用全站深色配色，符合「顏色一致」（07 §6.2）的硬性要求。

### 6.2 圖表共同規則（07 §6.2，落地為 ChartCard 強制 props）

每個圖表必須具備：
1. **標題**（中文，描述這是什麼）
2. **單位**（%、TWD、年化…，顯示於軸標籤或副標）
3. **Tooltip**（hover 顯示精確數值＋日期）
4. **資料日期**（取自 API 回應的 `holding_date` / `data_date` / backtest `start_date~end_date`）
5. **一段文字解釋**（圖表下方一句話說明如何解讀）
6. **顏色依 1.5 一致性規則**

---

## 7. Badge 分類體系

| Badge 分組 | 可能值 | 顏色映射 | 資料來源欄位 |
|---|---|---|---|
| 主動 / 被動 | 主動型 / 被動型 | 中性灰（資訊性，非好壞判斷） | `management_type` |
| 資產類別 | 股票型 / 債券型 / 其他 | 中性灰 | `asset_class` |
| 投資風格 | 高股息 / 市值型 / 低波 / 其他 | accent-secondary（紫，風格標籤） | `investment_style` |
| 資料可信度 | 高 / 中 / 低 | 高=success(綠) / 中=warning(橙) / 低=error(紅) | `data_provenance.confidence_level` |
| 集中度等級 | 低 / 中 / 中高 / 高 | 低=success / 中=info / 中高=warning / 高=error | 由 `hhi` 依 00 §3 等級規則推導（**門檻待 Opus/後端確認，列為 gap**） |
| 重疊度等級 | 極低重疊 / 低度重疊 / 中度重疊 / 高度重疊 | 極低=success / 低=info / 中=warning / 高=error | `overlap_rating.label`（後端直出，前端不重算） |
| 風險等級（回測） | 低 / 中 / 高 | success / warning / error | 由 `max_drawdown`/`annualized_volatility` 推導（**門檻待確認，列為 gap**） |
| API 狀態 | 即將推出（NOT_IMPLEMENTED） | info（淺藍） | HTTP 501 / `error.code === "NOT_IMPLEMENTED"` |

---

## 8. Tailwind 對應建議（供 Phase 11 實作）

```js
// tailwind.config.ts 摘要（示意，非最終程式碼）
colors: {
  bg: { base: 'var(--bg-base)', surface: 'var(--bg-surface)', raised: 'var(--bg-surface-raised)', inset: 'var(--bg-inset)' },
  border: { subtle: 'var(--border-subtle)', strong: 'var(--border-strong)' },
  text: { primary: 'var(--text-primary)', secondary: 'var(--text-secondary)', muted: 'var(--text-muted)' },
  accent: { primary: 'var(--accent-primary)', 'primary-hover': 'var(--accent-primary-hover)', secondary: 'var(--accent-secondary)' },
  status: { success: 'var(--status-success)', warning: 'var(--status-warning)', error: 'var(--status-error)', info: 'var(--status-info)', neutral: 'var(--status-neutral)' },
}
```

所有 token 以 CSS variable 定義於 `globals.css :root`，Tailwind 僅做語意化映射，方便日後換主題。
