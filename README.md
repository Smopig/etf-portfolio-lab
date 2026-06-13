# ETF 投資組合研究實驗室 (ETF Portfolio Lab)

一套專為 ETF 投資研究設計的開源分析平台，提供成分股查詢、回測、財務模擬、及 AI 驅動分析功能。

**重要提醒**：本工具為研究與教育用途，不構成投資建議。回測結果不代表未來績效，所有投資決策請結合專業意見。

## 核心功能

### 📊 ETF 基本分析
- **ETF 搜索與詳情**：瀏覽資料庫中的 ETF，查詢費用率、發行商、追蹤指數等
- **成分股分析**：查看 ETF 內含持股及其權重、集中度度量（Herfindahl、Top-10 比例）
- **產業曝露**：一級及二級產業分類分析，快速掌握產業風險敞口
- **多 ETF 比較**：計算 ETF 之間的持股重疊率、產業相似度

### 💼 投資組合工具
- **投資組合構建**：自定義組合，輸入成分 ETF 與目標權重
- **穿透分析**：計算組合內所有 ETF 的實際成分股與產業敞口
- **風險評估**：集中度分析、持股重疊風險識別、權重驗證
- **反向查詢**：按產業或股票反向搜索包含該成分的 ETF

### 📈 回測與財務模擬
- **歷史回測**：基於真實歷史價格的多 ETF 組合績效回測
  - 支援初始投入、定期定額、配息再投資、交易成本、再平衡設定
  - 計算年化報酬率、波動率、最大回撤、夏普比等風險指標
- **財務模擬**：預測未來投資情景
  - 目標金額達成、所需年報酬率、所需月投資額等反向計算
  - 多情景模擬（保守/中性/樂觀場景，自訂報酬率）
- **結果解讀**：AI 自動生成回測與模擬結果摘要（可選）

### 🤖 AI 分析
- **ETF 分析**：自動總結成分特徵、產業風險、優缺點
- **投資組合分析**：識別產業集中度、重疊風險、結構特點
- **結果解讀**：用自然語言解釋回測與模擬結果
- **模式**：預設使用離線 Mock 提供商（無需 API 金鑰）；可配置 Anthropic Claude API 進階分析
- **重要說明**：AI 分析基於系統資料（不編造持股），輸出不代表投資建議

### 📁 資料管理
- **資料來源追蹤**：每個資料點記錄來源、日期、可信度等級
- **品質檢查**：自動驗證匯入資料的完整性、正確性、重複性
- **樣本資料**：提供 CSV/Excel 格式範本（etf_master、holdings、prices、dividends、stock_industry）
- **導入工具**：CLI 指令輕鬆匯入 ETF、成分、價格、分紅、產業資料

## 🔒 重要免責聲明

> **本工具為研究與教育用途，不構成投資建議。**
>
> - **回測結果不代表未來績效**：基於歷史資料，市場環境與未來不同
> - **AI 分析僅供參考**：不替代專業財務顧問與分析師意見
> - **投資風險自負**：所有投資決策應自行評估，結合專業建議
> - **資料可信度**：查看「資料來源」頁面了解各數據集的來源與更新頻率

## 快速開始

### 用 Docker Compose 啟動（推薦）

```bash
# 1. 複製環境設定
cp .env.example .env

# 2. 啟動所有服務（PostgreSQL + 後端 + 前端）
docker compose up --build

# 3. 訪問應用
# 前端：          http://localhost:3000
# 後端 API 基址：   http://localhost:8000
# API 互動文件：   http://localhost:8000/docs
# 健康檢查：       http://localhost:8000/health
```

初次啟動時，資料庫會自動遷移，預設為空。可選擇在資料庫初始化後手動匯入樣本資料。

### 本機開發（無容器）

詳見 [docs/SETUP.md](docs/SETUP.md) 詳細步驟。

## 技術堆疊

| 層級 | 技術 |
|------|------|
| **後端 API** | Python 3.11 / FastAPI / SQLAlchemy 2.0 |
| **資料庫** | PostgreSQL 16 + Alembic 遷移 |
| **前端** | Next.js 14 App Router / TypeScript / React 18 / Tailwind CSS |
| **圖表** | ECharts 6.1 |
| **AI（可選）** | Anthropic Claude API；預設 Mock 提供商（離線） |

## 專案結構

```
etf-portfolio-lab/
├── backend/
│   ├── app/
│   │   ├── api/              # REST 路由（etfs、portfolios、backtests 等）
│   │   ├── models/           # SQLAlchemy ORM 模型
│   │   ├── services/         # 業務邏輯層（分析、回測、投影）
│   │   ├── schemas/          # Pydantic 請求/回應結構
│   │   ├── utils/            # 通用工具（CSV 導入、資料驗證）
│   │   ├── core/             # 應用設定、資料庫初始化
│   │   └── main.py           # FastAPI 應用入口
│   ├── scripts/              # CLI 資料導入指令
│   ├── alembic/              # 資料庫遷移檔案
│   ├── tests/                # Pytest 測試套件
│   ├── Dockerfile            # 後端容器構建檔
│   └── pyproject.toml        # Python 依賴設定
├── frontend/
│   ├── app/                  # Next.js App Router 頁面（內部路由）
│   │   ├── page.tsx              # 首頁（儀表板）
│   │   ├── etf/page.tsx          # ETF 瀏覽
│   │   ├── etf/[symbol]/page.tsx # ETF 詳情
│   │   ├── portfolio/page.tsx     # 投資組合列表
│   │   ├── portfolio/[id]/page.tsx # 投資組合詳情
│   │   ├── compare/page.tsx       # ETF 比較
│   │   ├── backtest/page.tsx      # 回測工具
│   │   ├── projection/page.tsx    # 財務模擬
│   │   ├── ai/page.tsx           # AI 分析
│   │   └── data-sources/page.tsx  # 資料來源透明度
│   ├── components/           # React 可復用元件
│   ├── public/               # 靜態資源
│   ├── Dockerfile            # 前端容器構建檔（多階段）
│   └── package.json          # Node.js 依賴設定
├── data/
│   ├── raw/                  # 導入的原始檔案備份（按類型分目錄）
│   ├── processed/            # 計算結果輸出目錄
│   └── samples/              # CSV/Excel 範本文件
├── docs/                     # 使用者與開發文件
│   ├── SETUP.md              # 本機開發詳細指南
│   ├── API.md                # REST API 端點參考
│   ├── DATA_IMPORT.md        # 資料匯入格式與流程
│   ├── TROUBLESHOOTING.md    # 常見問題排除
│   ├── SCHEMA.md             # 資料庫表結構說明
│   └── ux/                   # UX 設計文檔
├── .env.example              # 環境變數範本
├── docker-compose.yml        # 容器編排設定
├── CLAUDE.md                 # 開發工作流與模型分工規則
└── README.md                 # 本檔案
```

## 文件導航

| 文件 | 用途 |
|------|------|
| [docs/SETUP.md](docs/SETUP.md) | 本機開發設定、venv、資料庫初始化、測試執行 |
| [docs/API.md](docs/API.md) | REST API 完整端點目錄、參數說明、回應範例 |
| [docs/DATA_IMPORT.md](docs/DATA_IMPORT.md) | CSV/Excel 匯入格式、CLI 指令用法、樣本檔案說明 |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Docker、資料庫、網路等常見問題與解決方案 |
| [docs/SCHEMA.md](docs/SCHEMA.md) | 15 個資料表結構、欄位定義、外鍵關係 |

## 功能演示流程

1. **首次使用**：訪問 http://localhost:3000，查看儀表板資料摘要
2. **瀏覽 ETF**：在「ETF 瀏覽」頁面搜索、篩選、檢視成分與產業分析
3. **構建組合**：在「投資組合」頁面新增自訂組合，查看穿透分析
4. **執行回測**：在「回測」頁面設定時間範圍、投資方式，查看績效指標
5. **財務模擬**：在「財務模擬」頁面計算目標達成時間或所需報酬率
6. **AI 解讀**：在「AI 分析」頁面獲取自動生成的分析摘要（需有資料）
7. **檢查資料**：在「資料來源」頁面查看每個資料集的來源、日期、可信度

## 一鍵抓取真實 ETF 清單與價格

```bash
docker compose exec backend python -m scripts.fetch_all
```

從 TWSE ISIN 公告網頁抓取全部台灣 ETF（上市＋上櫃）清單，並從 Yahoo Finance 抓取近期每日價格。
需數分鐘完成；成分股（持股）尚未包含在此階段。詳見 [docs/DATA_IMPORT.md](docs/DATA_IMPORT.md)。

## 測試與品質檢查

### 執行後端測試

```bash
cd backend
uv run pytest tests/
# 或使用 pip 安裝的環境（venv 已啟用）：pytest tests/
```

### API 互動測試

訪問 http://localhost:8000/docs，使用 Swagger UI 測試所有端點。

### 資料品質檢查

```bash
cd backend
python -m scripts.run_quality_checks
```

詳見 [docs/SETUP.md](docs/SETUP.md) 的「測試」章節。

## 開發模式

### 後端開發循環
1. 編輯 `backend/app/` 中的 Python 檔案
2. Uvicorn 自動重新載入（`--reload` 選項）
3. 訪問 http://localhost:8000/docs 測試 API

### 前端開發循環
1. 編輯 `frontend/app/` 或 `frontend/components/` 中的檔案
2. Next.js 自動熱更新（HMR）
3. 刷新 http://localhost:3000 查看變更

### 資料庫遷移

```bash
cd backend
# 建立遷移
alembic revision --autogenerate -m "describe your change"
# 執行遷移
alembic upgrade head
```

## 資料隱私與許可

- **無用戶資料存儲**：本系統不存儲交易記錄或個人財務資訊
- **樣本資料來源**：取自公開資訊（台灣證券交易所、Yahoo Finance 等）
- **開源許可**：MIT 許可，歡迎自由使用、修改、分享

## 開發工作流

本專案遵守 [CLAUDE.md](CLAUDE.md) 中的模型分工政策：
- **Opus 4.8**：架構設計、任務分派、審查決策
- **Sonnet**：後端與前端實作
- **Haiku**：文件撰寫、資料研究、測試用例

## 聯絡與貢獻

如有建議、發現問題或想貢獻代碼，歡迎提交 Issue 或 Pull Request。感謝社區支持！
