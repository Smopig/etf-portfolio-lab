# 本機開發設定指南

本文件說明如何在本機（不使用 Docker）開發與執行 ETF Portfolio Lab。

## 環境前置條件

- **Python 3.11+**：下載自 https://www.python.org/
- **Node.js 20+**：下載自 https://nodejs.org/
- **PostgreSQL 16+**：下載自 https://www.postgresql.org/
- **Git**

驗證安裝：
```bash
python --version          # Python 3.11 or higher
node --version            # v20 or higher
npm --version             # 10 or higher
psql --version            # 16 or higher
```

## 第 1 步：後端設定

### 1.1 進入後端目錄

```bash
cd backend
```

### 1.2 建立環境並安裝依賴（推薦：uv）

本專案推薦使用 [uv](https://docs.astral.sh/uv/) 管理 Python 環境與依賴，速度快且會產生鎖定檔（`uv.lock`）確保版本一致。

若尚未安裝 uv：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

建立虛擬環境並安裝依賴（含 dev 工具）：
```bash
uv venv
uv sync --extra dev
```

驗證：
```bash
uv run python -c "import fastapi; print(fastapi.__version__)"
```

#### 或使用 pip（備用方案）

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

pip install --upgrade pip
pip install -e .           # 安裝專案及其依賴
pip install -e ".[dev]"    # 包含開發工具（pytest 等）
```

驗證：
```bash
python -c "import fastapi; print(fastapi.__version__)"
```

### 1.4 設定環境變數

在專案根目錄建立 `.env` 檔案：

```bash
cp ../.env.example ../.env
```

編輯 `../.env`，確保以下變數正確：

```env
# 資料庫
DATABASE_URL=postgresql+psycopg2://etf:etf@localhost:5432/etf

# 應用環境
APP_ENV=development

# PostgreSQL 本機設定
POSTGRES_USER=etf
POSTGRES_PASSWORD=etf
POSTGRES_DB=etf

# 前端 API 基 URL（開發時保持為 localhost:8000）
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# AI 提供商（預設 mock，離線）
# AI_PROVIDER=mock
# AI_PROVIDER=claude
# ANTHROPIC_API_KEY=sk-ant-...   # 若使用 Claude API 則取消註解並填入金鑰
```

### 1.5 初始化資料庫

**前置**：確保 PostgreSQL 伺服器執行中，且可以用 `etf:etf` 連線到 localhost:5432

#### 建立資料庫（首次）

```bash
createdb -U etf -h localhost etf
```

#### 執行 Alembic 遷移

```bash
uv run alembic upgrade head
# 或使用 pip 安裝的環境：alembic upgrade head
```

驗證：
```bash
psql -U etf -h localhost -d etf -c "\dt"
```

應看到類似輸出（多個表格）：
```
             List of relations
 Schema |            Name            | Type  | Owner
--------+----------------------------+-------+-------
 public | alembic_version            | table | etf
 public | data_quality_check         | table | etf
 public | data_source_registry       | table | etf
 public | etf_dividend               | table | etf
 ...
```

### 1.6 載入樣本資料（選擇性）

```bash
# 匯入 ETF 基本資料
uv run python -m scripts.import_etf_master ../data/samples/etf_master.csv

# 匯入成分股資料
uv run python -m scripts.import_holdings ../data/samples/0050_holdings.csv

# 匯入價格資料
uv run python -m scripts.import_prices ../data/samples/0050_prices.csv

# 匯入分紅資料
uv run python -m scripts.import_dividends ../data/samples/0050_dividends.csv

# 匯入產業分類
uv run python -m scripts.import_industry ../data/samples/stock_industry.csv
```

> 或使用 pip：將 `uv run python` 替換為 `python`（venv 已啟用）。

驗證：
```bash
# 檢查 ETF 資料
psql -U etf -h localhost -d etf -c "SELECT count(*) FROM etf_master;"

# 應返回 3（etf_master.csv 中有 3 個 ETF）
```

### 1.7 執行後端伺服器

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# 或使用 pip 安裝的環境（確保已啟用 venv）：
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

輸出應顯示：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

訪問 http://localhost:8000/docs 確認 API 文件可用。

## 第 2 步：前端設定

### 2.1 進入前端目錄

在新終端機視窗：
```bash
cd frontend
```

### 2.2 安裝依賴

```bash
npm install
```

### 2.3 設定環境變數

在 `frontend/` 目錄建立 `.env.local`：

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 2.4 執行開發伺服器

```bash
npm run dev
```

輸出應顯示：
```
▲ Next.js 14.2.5
- Local:        http://localhost:3000
```

訪問 http://localhost:3000 確認前端可用。

## 第 3 步：驗證完整系統

1. **後端健康檢查**：
   ```bash
   curl http://localhost:8000/health
   # 應返回 {"status":"ok"}
   ```

2. **前端載入**：
   ```bash
   curl http://localhost:3000
   # 應返回 HTML
   ```

3. **API 互動測試**：
   訪問 http://localhost:8000/docs，嘗試執行：
   - `GET /api/etfs` - 列出 ETF
   - `GET /api/dashboard/summary` - 資料可用性摘要

4. **前端功能檢查**：
   訪問 http://localhost:3000，確認以下頁面可載入：
   - `/` - 主頁（儀表板）
   - `/etf` - ETF 瀏覽
   - `/portfolio` - 投資組合
   - `/backtest` - 回測工具

## 測試

### 執行後端測試

```bash
cd backend
uv run pytest tests/ -v

# 或執行特定測試檔案
uv run pytest tests/test_api.py -v

# 測試涵蓋範圍
uv run pytest tests/ --cov=app --cov-report=html
```

> 或使用 pip 安裝的環境（venv 已啟用）：將 `uv run pytest` 替換為 `pytest`。

### 常見測試結果

所有測試應通過。若失敗，檢查：
- PostgreSQL 是否正在執行
- `.env` 中的 `DATABASE_URL` 是否正確
- 是否執行過 `alembic upgrade head`

### 執行前端測試（如有）

```bash
cd frontend
npm run lint
```

## 開發工作流

### 後端開發循環

1. 編輯 `backend/app/` 中的 Python 檔案
2. 由於 `--reload` 選項，Uvicorn 會自動重新載入
3. 訪問 http://localhost:8000/docs 測試 API

### 前端開發循環

1. 編輯 `frontend/app/` 或 `frontend/components/` 中的檔案
2. 由於 Next.js HMR（熱模組重新載入），變更會自動反映
3. 刷新 http://localhost:3000 查看變更

### 資料庫遷移

若需新增表格或欄位：

```bash
# 建立遷移檔案
alembic revision --autogenerate -m "describe change"

# 檢查生成的遷移檔案 (backend/alembic/versions/)
# 視需要手動調整

# 執行遷移
alembic upgrade head
```

詳見 [SQLAlchemy 文件](https://docs.sqlalchemy.org/en/20/)

## 環境變數參考

### 必需變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+psycopg2://etf:etf@localhost:5432/etf` | 本機 PostgreSQL 連線字串 |
| `APP_ENV` | `development` | 執行環境 |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | 前端連至後端的基 URL |

### 選擇性變數（AI 分析）

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `AI_PROVIDER` | `mock` | `mock`（離線）或 `claude`（需 API 金鑰） |
| `AI_MODEL` | `claude-opus-4-8` | Claude 模型版本 |
| `ANTHROPIC_API_KEY` | - | Anthropic API 金鑰（若 `AI_PROVIDER=claude`） |

## 常見問題

### PostgreSQL 連線失敗

**症狀**：`psycopg2.OperationalError: could not connect to server`

**解決**：
1. 確認 PostgreSQL 伺服器執行中：
   ```bash
   pg_isready -h localhost -U etf
   # 應返回 accepting connections
   ```
2. 檢查 `.env` 中的 `DATABASE_URL` 是否正確
3. 若 PostgreSQL 在非標準連接埠，更新連線字串

### 模組未找到

**症狀**：`ModuleNotFoundError: No module named 'app'`

**解決**：
```bash
# 確保在虛擬環境中
source venv/bin/activate

# 確保在 backend 目錄
cd backend

# 重新安裝專案
pip install -e .
```

### Port 已占用

**症狀**：`Address already in use`

**解決**：
```bash
# 尋找佔用連接埠的進程並刪除，或使用不同連接埠
# 後端：
uvicorn app.main:app --port 8001

# 前端（編輯 next.config.mjs 或傳遞選項）
npm run dev -- -p 3001
```

### 資料匯入錯誤

**症狀**：匯入指令失敗或資料不完整

**解決**：
```bash
# 使用 --dry-run 檢查匯入（不實際寫入）
python -m scripts.import_etf_master ../data/samples/etf_master.csv --dry-run

# 檢查資料品質
python -m scripts.run_quality_checks
```

詳見 [docs/DATA_IMPORT.md](DATA_IMPORT.md)

## 更新與清理

### 更新依賴

```bash
# 後端
cd backend
pip install --upgrade pip
pip install -e .

# 前端
cd frontend
npm update
```

### 清理資料庫（重新開始）

```bash
# 警告：刪除所有資料！
dropdb -U etf -h localhost etf
createdb -U etf -h localhost etf
alembic upgrade head
```

### 清理 Python 快取

```bash
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

## 後續步驟

- 閱讀 [docs/API.md](API.md) 了解可用端點
- 閱讀 [docs/DATA_IMPORT.md](DATA_IMPORT.md) 匯入自有資料
- 閱讀 [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) 解決問題
