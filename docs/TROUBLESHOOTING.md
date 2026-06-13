# 常見問題與排除指南 (TROUBLESHOOTING.md)

本文件針對使用 ETF Portfolio Lab 時的常見問題提供診斷與解決方案。

---

## Docker Compose 相關問題

### 問題：`docker compose up` 失敗，無法拉取映像

**症狀**：
```
ERROR: failed to fetch server certificate: x509: certificate signed by unknown authority
```

**原因**：Docker registry 被防火牆或代理伺服器阻擋。

**解決方案**：

1. **檢查網路連線**
   ```bash
   curl -I https://registry-1.docker.io/v2/
   ```

2. **設定 Docker 代理**（若公司有代理伺服器）
   ```bash
   # 編輯 ~/.docker/config.json（或 %APPDATA%\Docker\config.json）
   {
     "proxies": {
       "default": {
         "httpProxy": "http://proxy.example.com:8080",
         "httpsProxy": "http://proxy.example.com:8080",
         "noProxy": "localhost,127.0.0.1"
       }
     }
   }
   ```

3. **使用本地預製映像**（若無網路存取）
   - 從另一台機器手動導入 Docker 映像
   - 或使用預編譯的二進制檔案

4. **嘗試不同的 registry 鏡像**
   ```bash
   # 編輯 ~/.docker/daemon.json
   {
     "registry-mirrors": [
       "https://docker.mirrors.ustc.edu.cn"
     ]
   }
   ```

---

### 問題：`postgres service is not healthy`

**症狀**：
```
db | error: could not translate host name "postgres" to address: Name or service not known
backend exited with code 1
```

**原因**：PostgreSQL 容器初始化過慢或連線失敗。

**解決方案**：

1. **增加健康檢查等待時間**
   
   編輯 `docker-compose.yml`：
   ```yaml
   db:
     healthcheck:
       test: ["CMD-SHELL", "pg_isready -U etf"]
       interval: 10s
       timeout: 5s
       retries: 10  # 從 5 改為 10
   ```

2. **檢查 PostgreSQL 日誌**
   ```bash
   docker compose logs db
   ```

3. **手動檢查資料庫**
   ```bash
   docker compose exec db psql -U etf -c "SELECT 1"
   ```

4. **清理舊容器與卷**
   ```bash
   docker compose down -v
   docker compose up --build
   ```

---

### 問題：埠已被占用

**症狀**：
```
Error response from daemon: driver failed programming external connectivity on endpoint: bind: address already in use
```

**埠衝突**：
- 3000：Next.js 前端
- 8000：FastAPI 後端
- 5432：PostgreSQL 資料庫

**解決方案**：

1. **找出占用埠的進程**
   ```bash
   # macOS / Linux
   lsof -i :3000
   lsof -i :8000
   lsof -i :5432
   
   # Windows
   netstat -ano | findstr :3000
   taskkill /PID <PID> /F
   ```

2. **更改 docker-compose.yml 中的埠映射**
   ```yaml
   services:
     backend:
       ports:
         - "8001:8000"  # 改用 8001
     frontend:
       ports:
         - "3001:3000"  # 改用 3001
   ```

3. **停止其他容器**
   ```bash
   docker compose down
   docker ps -a  # 檢查其他執行中的容器
   ```

---

### 問題：資料庫遷移失敗

**症狀**：
```
FAILED: Can't operate on database before running the upgrade operation
ERROR: Failed to connect to database
```

**原因**：Alembic 遷移在容器啟動時未正確執行。

**解決方案**：

1. **手動執行遷移**
   ```bash
   docker compose exec backend alembic upgrade head
   ```

2. **檢查遷移檔案**
   ```bash
   ls -la backend/alembic/versions/
   ```

3. **重置資料庫**（警告：刪除所有資料）
   ```bash
   docker compose exec db psql -U etf -c "DROP DATABASE IF EXISTS etf; CREATE DATABASE etf;"
   docker compose exec backend alembic upgrade head
   ```

---

## 後端相關問題

### 問題：PostgreSQL 連線失敗

**症狀**：
```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**原因**：後端無法連至資料庫。

**解決方案**：

1. **檢查環境變數**
   ```bash
   # 確認 .env 中的 DATABASE_URL
   cat .env | grep DATABASE_URL
   ```

   應為：
   ```
   DATABASE_URL=postgresql+psycopg2://etf:etf@db:5432/etf  # Docker
   # 或
   DATABASE_URL=postgresql+psycopg2://etf:etf@localhost:5432/etf  # 本機
   ```

2. **測試連線**
   ```bash
   # Docker 環境
   docker compose exec backend python -c "from app.core.database import engine; engine.connect()"
   
   # 本機環境
   psql -U etf -h localhost -d etf -c "SELECT 1"
   ```

3. **檢查 PostgreSQL 狀態**
   ```bash
   # Docker
   docker compose logs db
   
   # 本機
   pg_isready -h localhost -U etf
   ```

4. **確認用戶名與密碼**
   - Docker Compose 預設：`etf:etf`
   - 本機需手動建立用戶（見 SETUP.md）

---

### 問題：模組匯入錯誤

**症狀**：
```
ModuleNotFoundError: No module named 'app'
```

**原因**：Python 路徑設定錯誤或未在虛擬環境中。

**解決方案**：

1. **確認虛擬環境**
   ```bash
   cd backend
   source venv/bin/activate  # macOS/Linux
   # 或
   venv\Scripts\activate     # Windows
   ```

2. **確認在 backend 目錄**
   ```bash
   pwd  # 應顯示 .../backend
   cd backend  # 若不在
   ```

3. **重新安裝專案**

   推薦使用 uv（若尚未安裝：`curl -LsSf https://astral.sh/uv/install.sh | sh`）：
   ```bash
   uv sync --extra dev
   ```

   或使用 pip：
   ```bash
   pip install --upgrade pip
   pip install -e .
   ```

4. **檢查 pyproject.toml**
   ```bash
   python -c "import app; print(app.__file__)"
   ```

---

### 問題：Uvicorn 伺服器無反應

**症狀**：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
# 但訪問 localhost:8000 無回應
```

**原因**：防火牆阻擋或伺服器掛起。

**解決方案**：

1. **檢查防火牆**
   ```bash
   # macOS
   sudo lsof -i :8000
   
   # Linux
   sudo iptables -L
   ```

2. **重啟 Uvicorn**
   ```bash
   pkill -f uvicorn
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **檢查應用日誌**
   ```bash
   # 若有 500 錯誤，查看詳細堆疊追蹤
   # Uvicorn 終端應顯示完整錯誤
   ```

4. **嘗試本地存取**
   ```bash
   curl http://127.0.0.1:8000/health
   ```

---

### 問題：回測執行時間過長或超時

**症狀**：
```
TimeoutError: Request timed out after 300s
```

**原因**：回測資料量大或計算複雜。

**解決方案**：

1. **減少回測期間**
   - 改用 1 年而非 10 年進行初始測試

2. **檢查價格資料完整性**
   ```bash
   psql -U etf -h localhost -d etf -c "
   SELECT etf_symbol, COUNT(*) as price_count, 
          MIN(trade_date) as earliest, MAX(trade_date) as latest
   FROM etf_price
   GROUP BY etf_symbol;"
   ```

3. **增加伺服器超時**（FastAPI）
   
   編輯 `backend/app/main.py`：
   ```python
   from fastapi import FastAPI
   from fastapi.middleware import Middleware
   from starlette.middleware.base import BaseHTTPMiddleware
   
   app = FastAPI()
   
   # 若使用代理伺服器，增加超時
   # 或在 nginx 中設定 proxy_read_timeout 600s;
   ```

4. **非同步背景工作**（Phase 2）
   - 目前回測同步執行
   - 未來可支援背景任務隊列

---

### 問題：AI 分析拋出錯誤

**症狀**：
```
ValueError: AI provider 'claude' not initialized
```

**原因**：`AI_PROVIDER=claude` 但未設定 API 金鑰。

**解決方案**：

1. **使用 Mock 提供商**（預設、推薦）
   ```bash
   # .env 中
   AI_PROVIDER=mock
   ```

2. **設定 Claude API**
   ```bash
   # .env 中
   AI_PROVIDER=claude
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
   ```

3. **檢查 API 金鑰有效性**
   ```bash
   python -c "
   from app.services.ai_analysis_service import get_provider
   provider = get_provider()
   print(f'Provider: {provider.__class__.__name__}')
   "
   ```

4. **查看 Mock 提供商行為**
   - Mock 提供商返回預定義的分析樣本
   - 用於開發與測試（不需網路）

---

## 前端相關問題

### 問題：Next.js 開發伺服器無法啟動

**症狀**：
```
error Command "next dev" not found
```

**原因**：Next.js 未安裝或依賴缺失。

**解決方案**：

1. **確認在 frontend 目錄**
   ```bash
   cd frontend
   ```

2. **安裝依賴**
   ```bash
   npm install
   ```

3. **檢查 Node 版本**
   ```bash
   node --version  # 應為 v20+
   npm --version   # 應為 10+
   ```

4. **清理快取並重新安裝**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   npm run dev
   ```

---

### 問題：API 請求被 CORS 阻擋

**症狀**：
```
Access to XMLHttpRequest at 'http://localhost:8000/api/etfs' from origin 'http://localhost:3000' has been blocked by CORS policy
```

**原因**：後端 CORS 設定不允許前端域名。

**解決方案**：

1. **檢查 CORS 設定**
   
   `backend/app/core/config.py`：
   ```python
   CORS_ORIGINS: list[str] = ["http://localhost:3000"]
   ```

2. **Docker 環境中允許所有來源（開發用）**
   ```python
   CORS_ORIGINS: list[str] = ["*"]
   ```

3. **生產環境設定具體域名**
   ```python
   CORS_ORIGINS: list[str] = [
       "http://localhost:3000",
       "https://etf-portfolio-lab.example.com"
   ]
   ```

4. **重啟後端**
   ```bash
   # Docker
   docker compose restart backend
   
   # 本機
   uvicorn app.main:app --reload
   ```

---

### 問題：前端頁面無法加載

**症狀**：
```
http://localhost:3000 顯示空白或 404
```

**原因**：Next.js 構建失敗或 API 連線失敗。

**解決方案**：

1. **檢查 Next.js 伺服器日誌**
   ```bash
   # 應看到 "Local: http://localhost:3000"
   npm run dev
   ```

2. **檢查 API 基址環境變數**
   ```bash
   # 編輯 .env.local 或 docker-compose.yml
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   ```

3. **測試 API 連線**
   ```bash
   curl http://localhost:8000/api/etfs
   # 若失敗，查看後端日誌
   ```

4. **清理 Next.js 快取**
   ```bash
   rm -rf .next
   npm run dev
   ```

5. **檢查瀏覽器控制台**
   - 按 F12 開啟開發者工具
   - 查看「Network」與「Console」分頁的錯誤

---

### 問題：頁面樣式錯亂（CSS 未應用）

**症狀**：
```
頁面顯示為純文字，無 Tailwind 樣式
```

**原因**：Tailwind CSS 構建失敗或未正確配置。

**解決方案**：

1. **重新構建樣式**
   ```bash
   cd frontend
   npm run build
   npm run dev
   ```

2. **檢查 tailwind.config.js**
   ```javascript
   // 應包括頁面路徑
   content: [
     "./app/**/*.{js,ts,jsx,tsx}",
     "./components/**/*.{js,ts,jsx,tsx}",
   ],
   ```

3. **清理並重新安裝**
   ```bash
   rm -rf node_modules .next
   npm install
   npm run dev
   ```

---

## 資料與資料庫問題

### 問題：匯入資料失敗

**症狀**：
```
ValueError: Could not decode 'etf_master.csv' using any of the tried encodings
```

**原因**：CSV 檔案編碼不符合預期。

**解決方案**：

1. **檢查檔案編碼**
   ```bash
   file -i etf_master.csv
   # 應為 text/plain; charset=utf-8
   ```

2. **轉換編碼**
   ```bash
   # Big5 → UTF-8
   iconv -f big5 -t utf-8 etf_master.csv > etf_master_utf8.csv
   
   # Windows 繁體 → UTF-8
   iconv -f cp950 -t utf-8 etf_master.csv > etf_master_utf8.csv
   ```

3. **使用文字編輯器轉存**
   - VS Code：右下角點擊編碼，選「UTF-8」，存檔
   - Excel：另存新檔，選「CSV UTF-8」

4. **使用 --dry-run 測試**
   ```bash
   python -m scripts.import_etf_master etf_master_utf8.csv --dry-run
   ```

---

### 問題：權重驗證失敗

**症狀**：
```
ValidationError: weights must sum to 1.0 (got 0.95)
```

**原因**：投資組合或成分股權重不和為 100%。

**解決方案**：

1. **檢查權重和**
   ```bash
   # 手動計算成分股權重
   # 0.60 + 0.40 = 1.0 ✓
   ```

2. **處理小數誤差**
   - 系統允許小數誤差（±1e-6）
   - 若超出，檢查是否遺漏「其他」類別

3. **成分股權重標準化**
   ```bash
   # 若權重為小數（0.195），系統自動轉換為百分比（19.5%）
   # 檢查 CSV 是否混用了兩種格式
   ```

4. **使用 API 驗證**
   ```bash
   curl -X POST http://localhost:8000/api/portfolios/analyze \
     -H "Content-Type: application/json" \
     -d '{"items": [{"etf_symbol":"0050","target_weight":0.60}]}'
   ```

---

### 問題：資料日期不連續

**症狀**：
```
回測失敗：missing data for dates 2025-12-25 to 2025-12-31
```

**原因**：股市休市日或資料缺失。

**解決方案**：

1. **檢查資料完整性**
   ```bash
   psql -U etf -h localhost -d etf -c "
   SELECT etf_symbol, COUNT(*) as count,
          MIN(trade_date) as start_date,
          MAX(trade_date) as end_date,
          CAST(COUNT(*) as FLOAT) / 
          EXTRACT(DAY FROM (MAX(trade_date) - MIN(trade_date))) * 252 as approx_annual_days
   FROM etf_price
   GROUP BY etf_symbol;"
   ```

2. **填補缺失日期**
   - 用前一個交易日的價格向前填充（forward fill）
   - 回測引擎應自動處理

3. **使用更寬泛的日期範圍**
   - 若無 2025-12-25 至 2025-12-31 資料，改用 2025-12-24 至 2026-01-02

---

### 問題：資料庫空間不足

**症狀**：
```
FATAL: remaining connection slots are reserved for non-replication superuser connections
```

**原因**：PostgreSQL 儲存空間滿或連線數上限。

**解決方案**：

1. **檢查磁碟空間**
   ```bash
   # Docker
   docker compose exec db df -h
   
   # 本機
   df -h
   ```

2. **清理資料庫**
   ```bash
   # 刪除舊的匯入紀錄
   psql -U etf -h localhost -d etf -c "
   DELETE FROM etf_price WHERE trade_date < '2020-01-01';"
   
   # 清理資料庫
   psql -U etf -h localhost -d etf -c "VACUUM ANALYZE;"
   ```

3. **擴展儲存**
   - Docker：增加卷大小或使用外部儲存
   - 本機：購買額外硬碟或清理系統

---

## 效能與最佳化

### 問題：API 回應緩慢

**症狀**：
```
API 端點耗時 >5 秒才回應
```

**原因**：資料量大、查詢未最佳化或資料庫索引缺失。

**解決方案**：

1. **檢查資料庫查詢**
   ```bash
   # 啟用 PostgreSQL 慢查詢日誌
   # docker-compose.yml 中的 db 服務加入：
   command: "postgres -c log_statement=all -c log_duration=on"
   
   # 查看日誌
   docker compose logs db | grep duration
   ```

2. **新增資料庫索引**
   ```bash
   psql -U etf -h localhost -d etf -c "
   CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON etf_holdings(etf_symbol);
   CREATE INDEX IF NOT EXISTS idx_holdings_date ON etf_holdings(holding_date);
   CREATE INDEX IF NOT EXISTS idx_price_symbol_date ON etf_price(etf_symbol, trade_date);
   "
   ```

3. **使用查詢優化器分析**
   ```bash
   psql -U etf -h localhost -d etf -c "
   EXPLAIN ANALYZE
   SELECT * FROM etf_holdings WHERE etf_symbol='0050';"
   ```

4. **限制回傳資料量**
   - 使用 `limit` 參數
   - 分頁查詢而非一次全部

---

### 問題：前端構建緩慢

**症狀**：
```
npm run build 耗時 5+ 分鐘
```

**原因**：依賴版本過舊或構建配置欠佳。

**解決方案**：

1. **更新依賴**
   ```bash
   cd frontend
   npm update
   npm audit fix
   ```

2. **啟用 SWC 編譯器**（Next.js 14 預設）
   ```javascript
   // next.config.mjs
   export default {
     swcMinify: true,  // 預設 true
   }
   ```

3. **檢查構建快取**
   ```bash
   rm -rf .next node_modules
   npm install
   npm run build
   ```

---

## 網路與安全

### 問題：HTTPS 憑證錯誤

**症狀**：
```
ERR_SSL_PROTOCOL_ERROR 或 NET::ERR_CERT_INVALID
```

**原因**：開發環境使用自簽憑證或生產環境 SSL 配置問題。

**解決方案**：

1. **開發環境**
   - 不需 HTTPS（使用 HTTP localhost）
   - 若需測試 HTTPS，使用 mkcert：
   ```bash
   mkcert localhost 127.0.0.1 ::1
   ```

2. **生產環境**
   - 使用 Let's Encrypt 免費憑證
   - 在 nginx/Apache 中配置 SSL

3. **停用 HTTPS 驗證**（開發用，不建議）
   ```bash
   # 瀏覽器：訪問 chrome://flags，搜尋「insecure origins treated as secure」
   ```

---

### 問題：API 金鑰外洩

**症狀**：
```
ANTHROPIC_API_KEY 被提交至 Git
```

**預防與補救**：

1. **立即撤銷金鑰**
   - 登入 https://console.anthropic.com
   - 刪除舊金鑰，生成新金鑰

2. **設定 .gitignore**
   ```bash
   echo ".env" >> .gitignore
   echo ".env.local" >> .gitignore
   ```

3. **從 Git 歷史中移除**
   ```bash
   git filter-branch --tree-filter 'rm -f .env' HEAD
   # 或使用 BFG Repo-Cleaner
   ```

4. **使用環境變數**
   - 不要在代碼中硬編碼金鑰
   - 所有敏感資訊放入 `.env`

---

## 獲取更多幫助

### 診斷資訊收集

若需求助，請收集以下資訊：

```bash
# 系統資訊
uname -a
docker --version
python --version
node --version

# 專案狀態
git log --oneline -5
git status

# 後端日誌
docker compose logs backend --tail 50

# 前端日誌
docker compose logs frontend --tail 50

# 資料庫狀態
docker compose exec db psql -U etf -c "\l"
docker compose exec db psql -U etf -d etf -c "\dt"
```

### 常用除錯指令

```bash
# 檢查所有容器狀態
docker compose ps

# 查看完整日誌
docker compose logs -f

# 進入後端容器
docker compose exec backend bash

# 進入資料庫容器
docker compose exec db psql -U etf -d etf

# 重啟特定服務
docker compose restart backend

# 完全重建
docker compose down -v
docker compose up --build
```

### 社區與支援

- **GitHub Issues**：https://github.com/your-repo/issues
- **本地文件**：[docs/](.) 目錄
- **API 文件**：http://localhost:8000/docs
