# 05. Empty / Loading / Error States & Responsive Behavior

## 1. 錯誤狀態：API 錯誤碼 → 友善文案映射

所有頁面共用 `ErrorPanel`，依後端 `{"error":{"code","message"}}` 映射：

| `error.code` | HTTP | 友善文案（zh-Hant） | 建議操作 |
|---|---|---|---|
| `NOT_FOUND` | 404 | 「找不到資料，可能尚未匯入或代號輸入錯誤。」 | 顯示「返回」或「前往資料來源」連結 |
| `VALIDATION_ERROR` | 400 | 「輸入內容有誤，請檢查欄位後重試。」（若 `message` 有具體欄位資訊，附加顯示原始訊息） | 高亮對應表單欄位 |
| `NOT_IMPLEMENTED` | 501 | 「此功能即將推出，敬請期待。」 | 不顯示重試按鈕 |
| `INTERNAL_ERROR` | 500 | 「系統發生錯誤，請稍後再試。」 | 顯示「重試」按鈕 |
| 網路錯誤（fetch 失敗，無 envelope） | — | 「無法連線到伺服器，請確認後端服務是否啟動。」 | 顯示「重試」按鈕 |

`ErrorPanel` 一律不顯示原始英文錯誤堆疊；`message` 僅在 `VALIDATION_ERROR` 時可選擇性附加（已是英文時仍以中文前綴包裝）。

---

## 2. 各頁狀態定義

### 2.1 Dashboard
- **Empty**：`GET /api/etfs` 回傳空陣列 → 整頁顯示大型 EmptyState：「尚未匯入任何 ETF 資料」+ 按鈕「前往資料來源頁了解 CLI 匯入方式」（連 `/data-sources`）。排行卡與品質警告區一併隱藏。
- **Loading**：4 個 MetricCard skeleton（灰塊）+ 4 張排行卡 skeleton + 表格 skeleton（5 rows）。
- **Error**：`GET /api/etfs` 失敗 → 整頁 ErrorPanel（INTERNAL_ERROR / 網路錯誤），其餘區塊不渲染。資料品質表格獨立 try/catch，單獨失敗不影響其他區塊。

### 2.2 ETF Detail
- **Empty**：
  - `GET /api/etfs/{symbol}` 回 404 (`NOT_FOUND`) → 整頁 EmptyState：「找不到代號 {symbol} 的 ETF，請確認代號是否正確」+「返回 Dashboard」按鈕。
  - 持股相關 (`holdings`/`concentration`/`industry-exposure`) 回傳 `num_holdings: 0` 或空陣列 → 對應區塊顯示 EmptyState：「此 ETF 尚未匯入成分股資料」，MetricCard 顯示「—」並標註「無資料」。
  - 持股變化 Timeline（gap）→ 固定顯示 EmptyState：「持股變化紀錄功能尚未提供」。
- **Loading**：策略卡 skeleton（文字塊）、ConcentrationPanel 6 張 MetricCard skeleton、2 個 ChartCard skeleton、表格 skeleton。
- **Error**：主卡 404 → 同 Empty 處理；其他子請求 500 → 該 ChartCard/DataTable 顯示局部 ErrorPanel + 重試按鈕，不影響其他區塊。

### 2.3 ETF Compare
- **Empty**：
  - 未選擇任何 ETF → 顯示引導：「請從上方選擇至少 2 檔 ETF 開始比較」，所有圖表/表格區域為空白引導卡。
  - 僅選 1 檔 → 提示：「請再選擇至少 1 檔 ETF 以進行比較」。
- **Loading**：選擇變更後，所有受影響區塊（Heatmap、比較表、產業圖）同時顯示 skeleton。
- **Error**：任一 ETF `GET /api/etfs/{symbol}` 404 → 該欄位顯示「{symbol} 找不到」並從比較中標記為無效（不阻擋其他 ETF 顯示）。`/etfs/compare` 整體失敗 → Heatmap 區塊 ErrorPanel。

### 2.4 Portfolio Builder
- **Empty**：
  - 列表頁 (`GET /api/portfolios` 空)：EmptyState「尚未建立任何投資組合」+「建立第一個組合」按鈕。
  - 編輯頁尚未加入任何 ETF：WeightAllocator 顯示「請加入至少一檔 ETF 開始配置」，下方分析區隱藏。
- **Loading**：`POST /portfolios/analyze` debounce 期間，圖表/表格區顯示輕量 spinner（非整頁 skeleton，避免閃爍打字體驗）。
- **Error**：
  - `validation.status === "FAIL"` → 非 API error，而是業務狀態，WeightAllocator 顯示紅色 Badge + `validation.message`，分析區仍嘗試顯示（依後端是否仍回傳資料而定）。
  - `unknown_symbols` 非空 → PortfolioWarningsList 顯示對應 `UNKNOWN_ETF` warning。
  - API 500/404（如 portfolio_id 不存在）→ ErrorPanel + 「返回投資組合列表」。

### 2.5 Backtest
- **Empty**：尚未執行 → 表單下方顯示提示卡：「填寫表單並點擊『執行回測』查看結果」，不顯示空的 ChartCard。
- **Loading**：點擊「執行回測」後，按鈕進入 loading 狀態（spinner+disabled），結果區顯示 skeleton（8 張 MetricCard + 1 大圖表 + 1 表格）。回測可能耗時，按鈕需顯示「計算中...」。
- **Error**：
  - `VALIDATION_ERROR`（如日期區間無資料、權重總和錯誤）→ 表單上方 ErrorPanel，文案使用映射表 + 顯示原始 `message`（通常已是中文或可理解的技術訊息，需前端補充中文前綴）。
  - `NOT_FOUND`（portfolio_id 不存在）→ 提示「找不到所選投資組合，請重新選擇」。

### 2.6 Projection
- **Empty**：初次進入，表單為預設值，尚未送出 → 顯示預設情境的「範例」結果（直接呼叫一次預設參數的 `scenarios`），標註「以下為範例，請輸入您的條件」。
- **Loading**：送出後 ScenarioToggle 區與圖表 skeleton（通常很快，<1s，仍需 loading 狀態避免閃爍）。
- **Error**：`VALIDATION_ERROR`（如年限為負數）→ 表單欄位下方 inline 錯誤訊息 + 上方 ErrorPanel。

### 2.7 Data Sources
- **Empty**：
  - `GET /api/data-sources` 空 → EmptyState：「尚未設定任何資料來源」。
  - `GET /api/data-quality` 空 → DataQualityTable 顯示「目前沒有資料品質檢查紀錄」（正向訊息，非錯誤）。
- **Loading**：兩個表格各自 skeleton（5 rows）。
- **Error**：個別表格 API 失敗 → 該表格局部 ErrorPanel + 重試，不影響另一表格。

### 2.8 AI Assistant
- **Empty**：本頁本身即為「功能即將推出」常態，主內容區永遠顯示「即將推出」說明卡（非錯誤觸發的 empty state）。
- **Loading**：N/A（輸入框 disabled，不會觸發載入）。
- **Error**：若使用者透過 API 直接呼叫並在前端顯示結果（理論上不會發生，因按鈕 disabled）→ 映射 `NOT_IMPLEMENTED` → 「此功能即將推出，敬請期待。」

---

## 3. Loading Skeleton 規範（對應 `LoadingSkeleton` 元件）

| Variant | 樣式 |
|---|---|
| `card` | 矩形灰塊（`--bg-surface-raised`），含標題列（短條）+ 數值列（長條），脈動動畫 |
| `table` | 表頭固定不變，body 顯示 N 列灰色長條（依 `rows` prop，預設 5） |
| `chart` | 整個 ChartCard 區域顯示灰色矩形 + 置中 spinner |
| `text` | 1-3 行灰色短條，用於策略卡文字欄位 |

動畫：`opacity` 在 0.4↔0.8 間 1.2s 循環（subtle pulse），避免過度炫目。

---

## 4. Responsive Behavior（桌面優先研究終端）

### 4.1 Breakpoints

| 名稱 | 寬度 | 對應裝置 |
|---|---|---|
| `desktop` | ≥ 1280px | 主要設計目標：完整側欄+多欄圖表/表格 |
| `tablet` | 768px–1279px | 側欄收合為 icon-only，圖表改為單欄堆疊 |
| `mobile` | < 768px | 側欄變為底部/抽屜導覽，表格橫向 scroll，圖表全寬 |

### 4.2 SideNav
- desktop：固定展開（圖示+文字，寬度約 220px）
- tablet：收合為僅圖示（約 64px），hover 顯示文字 tooltip
- mobile：隱藏，改為 TopBar 漢堡選單觸發的抽屜（Drawer）

### 4.3 表格（DataTable）
- desktop：完整欄位顯示，sticky 第一欄
- tablet：欄位數量過多時允許橫向 scroll，sticky 第一欄保留
- mobile：橫向 scroll 必選；考慮將次要欄位（如 `asset_name`）改為點擊展開的次行顯示，僅保留 symbol + 主數值欄

### 4.4 圖表（ChartCard / ECharts）
- desktop：多圖並排（如 Compare 頁產業占比 N 檔並排）
- tablet：並排圖表改為單欄垂直堆疊，圖表高度維持，寬度 100%
- mobile：圖表簡化 — 大型 Heatmap（N×N，N>3）在 mobile 顯示「請使用較大螢幕檢視此圖表」+ 提供改用表格形式的替代呈現

### 4.5 MetricCard Grid
- desktop：4 欄 grid（一列 4 張）
- tablet：2 欄 grid
- mobile：1 欄堆疊

### 4.6 表單（Backtest / Projection / Portfolio Builder）
- desktop：表單欄位橫向多欄排列
- tablet/mobile：表單欄位改為單欄垂直堆疊，提交按鈕固定於底部（sticky footer）以便長表單操作

### 4.7 整體原則
本產品定位為桌面優先的研究終端（00 §1）。Mobile 支援以「可用、不崩版」為底線，不要求 mobile 上達到與 desktop 相同的資訊密度；複雜視覺化（Heatmap、多系列疊圖）在 mobile 可降級為文字摘要或提示切換裝置。
