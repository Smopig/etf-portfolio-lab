# 06. UX Review Checklist — Phase 11 逐頁驗收清單

依據 `07_UX_UI_DESIGN_SPEC.md` §7，每頁實作完成後必須逐項打勾，由 Opus 審查通過才能視為完成。

## 通用檢查（每頁皆須通過）

| # | 檢查項 | 通過標準 |
|---|---|---|
| 1 | 主任務是否明確？ | PageHeader 副標清楚說明本頁唯一主任務（對照 04 §每頁「主任務」） |
| 2 | 第一眼是否知道要做什麼？ | 進入頁面 3 秒內，無需 scroll 即可看到關鍵結論區與下一步操作入口 |
| 3 | 關鍵結論是否在上方？ | 遵循「先摘要、再展開」骨架，MetricCard/Badge 群位於頁面最上方 |
| 4 | 表格是否可讀？ | 數字右對齊+千分位/百分比格式化、sticky 第一欄、列高一致、排序/搜尋可用 |
| 5 | 圖表是否有意義？ | 每個 ChartCard 具備標題、單位、tooltip、資料日期、一句話解讀文字（07 §6.2） |
| 6 | 指標是否有解釋？ | 每個 MetricCard 顯示數值＋等級 Badge＋說明文字（00 §3） |
| 7 | 空狀態是否有引導？ | 對照 05 文件對應頁面的 Empty 定義，提供具體下一步操作（連結/按鈕） |
| 8 | 錯誤狀態是否友善？ | 錯誤訊息使用 05 §1 映射表中文文案，不外露原始 stack/英文 code |
| 9 | loading 是否清楚？ | 使用對應 LoadingSkeleton variant，無「白屏無回應」情況 |
| 10 | 繁體中文是否自然？ | 無簡體字、無機翻語感、無遺留英文 placeholder（除 NOT_IMPLEMENTED 狀態） |
| 11 | 是否太像普通後台？ | 深色主題、資訊密度、配色一致性符合 02 設計系統；非純白卡片堆疊 |
| 12 | 顏色一致性 | 同一產業/ETF/系列在跨圖表使用相同顏色（02 §1.5） |
| 13 | 免責聲明到位 | 依 00 §4 表格，本頁所需的免責聲明文字已顯示在指定位置且不可被隱藏 |
| 14 | SourceFooter 完整 | `source_name`、`data_date`、`confidence_level` 皆顯示（若 API 提供 null，顯示「未提供」而非留空） |
| 15 | 回測/模擬用語 | 凡涉及回測或推算結果，文案不得使用「保證」「一定」「未來會」等斷言語氣 |
| 16 | RWD 行為 | 依 05 §4 對應 breakpoint 行為實測（desktop/tablet/mobile 三尺寸截圖） |

---

## 逐頁額外檢查

### Dashboard
- [ ] 4 個排行卡點擊可正確導向對應 ETF Detail
- [ ] 資料品質警告數量與 `/data-quality` 實際筆數一致
- [ ] 「快速入口」涵蓋全部 7 個其他頁面路由
- [ ] 若排行卡所需聚合端點未完成（04 §1 Backend gaps），明確標示「資料籌備中」而非顯示假資料

### ETF Detail
- [ ] level 1/2 產業切換正確重打 API 並更新圖表顏色對應
- [ ] 全部成分股表格在 `num_holdings` 超過 10 時可正確顯示全部並支援搜尋
- [ ] 持股變化 Timeline 顯示「功能尚未提供」而非空白或假資料
- [ ] AI 摘要區清楚標示「即將推出」

### ETF Compare
- [ ] 2 檔模式顯示重疊明細表+產業相似度；3+ 檔模式正確切換為純 Heatmap
- [ ] Heatmap 對角線（自己對自己）處理合理（不顯示或顯示 100%/說明）
- [ ] 移除其中一檔 ETF 後其他區塊正確更新，無殘留資料

### Portfolio Builder
- [ ] 權重總和即時顯示 PASS/WARN/FAIL 對應顏色與文字
- [ ] `unknown_symbols`/`duplicate_symbols` 警告正確顯示
- [ ] 草稿分析（`/portfolios/analyze`）與已存分析（`/portfolios/{id}/...`）切換不造成資料錯亂
- [ ] 模板套用標示「建議起點，請自行確認成分」

### Backtest
- [ ] 免責聲明在結果出現前後皆可見（不因 scroll 消失）
- [ ] `rebalance_frequency` 下拉僅包含 5 個合法值
- [ ] 8 個摘要指標皆有解釋＋等級（風險類指標等級門檻待確認則先標示「等級評估中」而非無說明）
- [ ] 資產曲線與回撤曲線共用同一時間軸、可同步 hover

### Projection
- [ ] 三情境（保守/中性/樂觀）切換流暢且不重打 API
- [ ] `target_achieved` 狀態文字與 Badge 一致
- [ ] 免責聲明於圖表下方常駐顯示
- [ ] 目標倒推三模式（years/monthly_contribution/annual_return）皆可操作並顯示對應結果

### Data Sources
- [ ] `reliability_level`/`status`/`enabled` Badge 顏色符合 02 §1.4/§7 對應
- [ ] 篩選器（dataset_type/status）正確帶入 query params
- [ ] 「手動匯入」區塊明確標示為「即將推出」並提供 CLI 說明，不誤導使用者以為可上傳

### AI Assistant
- [ ] 整頁清楚標示「即將推出」Badge
- [ ] 輸入框/送出按鈕為 disabled 狀態且有 tooltip 說明原因
- [ ] 上下文選擇器（ETF/Portfolio）可操作以便未來無縫銜接
- [ ] 頁面說明文字涵蓋：將附資料來源/日期、不提供買賣指令

---

## 簽核

每頁完成後，由負責的 Sonnet agent 在 PR/任務說明中列出以上清單逐項勾選結果，Opus 審查時隨機抽查至少 3 項並實際操作驗證後再簽核「通過」。
