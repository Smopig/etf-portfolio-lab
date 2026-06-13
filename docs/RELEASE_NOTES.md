# Release Notes — ETF Portfolio Lab MVP

> 本工具為 **ETF 投資研究與教育用途**，非交易系統。所有回測與推算結果**不代表未來績效**，亦**不構成買賣建議**（詳見 CLAUDE.md §7、README 免責聲明）。

## MVP（首個可交付版本）

依「資料優先 → 分析 → API → 前端 → AI」順序完成，全程遵循 CLAUDE.md 的模型分工（Opus 架構/審查、Sonnet 實作、Haiku 文件/資料）與 §6（前端先 UX 規格後實作）、§7（AI 與分析以系統資料為本）。

### 後端（FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL）
- **資料模型**：15 張表（ETF 主檔、持股、持股快照/變動、股票產業、價格、配息、投資組合、回測/推算紀錄、資料來源登錄、資料品質檢查、擷取紀錄），每張關鍵表含資料來源與資料日期欄位。
- **資料匯入**：CSV/Excel 匯入腳本（etf_master / holdings / prices / dividends / stock_industry），多編碼容錯（utf-8 / utf-8-sig / cp950 / big5）、冪等 upsert、原始檔保存。
- **資料品質**：8 項檢查（權重加總、缺漏、產業覆蓋、價格日期斷層、配息重複、資料新鮮度、主檔必填、來源完整性）。
- **金融計算**：HHI / 有效持股數 / TopN 集中度、CAGR、最大回撤、年化波動、Sharpe、XIRR；皆經手算驗證。
- **分析服務**：集中度、產業曝險（含 Unclassified）、反向查詢、ETF 卡、重疊度（加權重疊/Jaccard/多檔比較）、投資組合穿透曝險與風險提醒、回測引擎（純函式 + JSONB 持久化隔離）、財務推算（情境 保守/中性/樂觀、目標倒推）、儀表板排行。
- **資料 Provider 自動化（Phase 12）**：Provider 抽象（檔案 / Yahoo / TWSE，可注入 HTTP、失敗不捏造）、`fetch_logs` 紀錄、orchestrator（沿用匯入 upsert）+ CLI。
- **AI 分析（Phase 13）**：Provider 抽象（預設離線 Mock、可選 Claude `claude-opus-4-8`）；服務嚴格落實 §7——僅依系統資料、引用來源/日期、資料不足短路、禁買賣指令、回測/推算警語、安全拒絕阻止輸出。
- **API**：統一回應信封（成功 `{data,meta}` / 錯誤 `{error:{code,message}}`），涵蓋 ETF、產業、投資組合、回測、推算、資料來源、匯入、AI、儀表板。

### 前端（Next.js 14 App Router + TypeScript + Tailwind + ECharts）
- 深色金融研究終端風格、繁體中文、高資訊密度。
- 頁面：儀表板、ETF 瀏覽/詳情、比較、投資組合建構/詳情、回測、財務推算、資料來源（含擷取紀錄）、**AI 助手**。
- 共用：typed API client（解析信封、`ApiError`）、泛型 `DataTable`、ECharts 圖表、空/載入/錯誤狀態與友善訊息。
- AI 面板依 §6 先產 UX 規格後實作；§7 行為：免責常駐、安全拒絕原文不進 DOM、資料不足以資訊性呈現。

### 文件
- README、SETUP、API、DATA_IMPORT、TROUBLESHOOTING、SCHEMA、UX 規格（00–07）、本 release notes。
- 依賴管理採 **uv**（保留 pip 作為替代）。

## 測試
- 後端：155 passed（SQLite、離線；含 provider/orchestrator/AI/錯誤路徑）。
- 前端：`tsc --noEmit` 乾淨。

## 已知限制
- 樣本資料為開發示意值，非權威市場資料。
- Yahoo/TWSE provider 的遠端格式假設待真實外網環境驗證（本開發環境的網路政策封鎖外連，採離線 fixture 測試）。
- 真實 PostgreSQL 端到端（`docker compose up` + migration + seed）受 image registry 封鎖，改以 Alembic 離線 SQL 與 SQLite 測試驗證。
- AI 為單輪請求/回應（後端不儲存對話歷史）。

## 升級 / 啟動
```bash
cp .env.example .env
docker compose up --build          # 前端 :3000、後端 :8000/docs
# 或本機：見 docs/SETUP.md（uv venv / uv sync / uv run ...）
```
