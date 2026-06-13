# 資料匯入指南 (DATA_IMPORT.md)

本文件說明如何將 ETF、成分股、價格、分紅等資料匯入 ETF Portfolio Lab。

---

## 概述

資料匯入分為兩個階段：

1. **Phase 1（目前）**：CLI 指令式匯入（`python -m scripts.import_*`）
2. **Phase 2（規劃）**：Web UI 檔案上傳（暫未實作）

所有匯入工具都支援：
- CSV 與 Excel 檔案（.xlsx, .xls）
- 自動字元編碼偵測（UTF-8, UTF-8-BOM, CP950, Big5）
- 原始檔案備份至 `/data/raw/<dataset_type>/`
- 資料品質自動檢查
- `--dry-run` 測試模式（不實際寫入）

---

## 快速開始

```bash
cd backend

# 匯入 ETF 基本資料
python -m scripts.import_etf_master ../data/samples/etf_master.csv

# 匯入成分股
python -m scripts.import_holdings ../data/samples/0050_holdings.csv

# 匯入價格資料
python -m scripts.import_prices ../data/samples/0050_prices.csv

# 匯入分紅資料
python -m scripts.import_dividends ../data/samples/0050_dividends.csv

# 匯入產業分類
python -m scripts.import_industry ../data/samples/stock_industry.csv

# 運行資料品質檢查
python -m scripts.run_quality_checks
```

---

## 1. ETF 主檔（etf_master）

### 功能

匯入 ETF 基本資訊、管理特徵、費用結構、追蹤指數。

### 檔案格式

**檔名**：任意，建議 `etf_master.csv` 或 `etf_master.xlsx`

**必需欄位**：
| 欄位 | 類型 | 說明 |
|------|------|------|
| symbol | TEXT | ETF 代碼（唯一鍵） |
| name | TEXT | ETF 名稱 |

**選擇性欄位**：
| 欄位 | 類型 | 說明 | 預設 |
|------|------|------|------|
| issuer | TEXT | 發行商 | NULL |
| listing_date | DATE (YYYY-MM-DD) | 上市日期 | NULL |
| management_type | TEXT | 主動/被動/混合 | NULL |
| asset_class | TEXT | 股票/債券/商品 | NULL |
| investment_style | TEXT | 大型股/小型股/高股息等 | NULL |
| strategy_type | TEXT | 指數追蹤/主動選股等 | NULL |
| tracking_index | TEXT | 追蹤指數名稱 | NULL |
| index_provider | TEXT | 指數提供商 | NULL |
| selection_method | TEXT | 成分股選取方式 | NULL |
| weighting_method | TEXT | 市值加權/等權/股利加權 | NULL |
| rebalance_frequency | TEXT | 每月/每季/每年 | NULL |
| replication_method | TEXT | 完全複製/最佳化複製 | NULL |
| expense_ratio | DECIMAL | 費用率（%） | NULL |
| management_fee | DECIMAL | 管理費（%） | NULL |
| custody_fee | DECIMAL | 保管費（%） | NULL |
| dividend_frequency | TEXT | 季配/半年配/年配 | NULL |
| source_name | TEXT | 資料來源名稱 | --source-name 參數或 NULL |
| source_url | TEXT | 資料來源網址 | --source-url 參數或 NULL |
| data_date | DATE (YYYY-MM-DD) | 資料日期 | 今天 |
| confidence_level | TEXT | 高/中/低 | --confidence 參數或 NULL |

### CSV 範本

```csv
symbol,name,issuer,listing_date,management_type,asset_class,investment_style,strategy_type,tracking_index,index_provider,selection_method,weighting_method,rebalance_frequency,replication_method,expense_ratio,management_fee,custody_fee,dividend_frequency,source_name,source_url,data_date,confidence_level
0050,元大台灣50,元大投信,2003-06-30,被動,股票,大型股,指數追蹤,台灣50指數,台灣證券交易所,市值篩選,市值加權,每半年,完全複製,0.32,0.30,0.02,季配,公開資訊觀測站,https://mops.twse.gov.tw,2026-06-01,高
006208,富邦台50,富邦投信,2012-12-03,被動,股票,大型股,指數追蹤,台灣50指數,台灣證券交易所,市值篩選,市值加權,每半年,完全複製,0.20,,0.02,季配,投信公司官網,https://www.fubonquant.com.tw,2026-06-01,中
00878,國泰永續高股息,國泰投信,2020-04-23,被動,股票,高股息,篩選策略,台灣高股息指數,臺灣永續指數公司,獲利與股利篩選,股利加權,每年,最佳化複製,0.50,0.45,0.05,季配,公開資訊觀測站,https://mops.twse.gov.tw,2026-06-01,中
```

### 匯入指令

```bash
python -m scripts.import_etf_master <file> [options]

選項：
  --source-name TEXT       資料來源名稱（若未在 CSV 中指定）
  --source-url TEXT        資料來源網址（若未在 CSV 中指定）
  --confidence TEXT        可信度等級（若未在 CSV 中指定）
  --dry-run               測試模式（只驗證，不寫入）
```

### 範例

```bash
# 直接匯入
python -m scripts.import_etf_master ../data/samples/etf_master.csv

# 指定來源
python -m scripts.import_etf_master etf_data.csv \
  --source-name "Yahoo Finance" \
  --source-url "https://finance.yahoo.com" \
  --confidence "中"

# 測試模式
python -m scripts.import_etf_master etf_data.csv --dry-run
```

### 重要說明

- **唯一鍵**：`symbol`。若該 ETF 代碼已存在，會跳過該列。
- **日期格式**：所有日期欄位必須是 `YYYY-MM-DD` 格式
- **數值格式**：費用率等數值欄位接受小數點（例如 `0.32`, `0.5`）
- **編碼**：CSV 檔案支援 UTF-8、UTF-8-BOM、CP950、Big5 自動偵測

---

## 2. ETF 成分股（etf_holdings）

### 功能

記錄特定日期 ETF 的持股組成，包含標的代碼、權重、市值。

### 檔案格式

**檔名**：任意，建議 `<ETF_SYMBOL>_holdings.csv`

**必需欄位**：
| 欄位 | 類型 | 說明 |
|------|------|------|
| etf_symbol | TEXT | ETF 代碼（必須存在於 etf_master） |
| holding_date | DATE (YYYY-MM-DD) | 持股日期 |
| asset_symbol | TEXT | 標的代碼（股票、基金代碼） |
| asset_name | TEXT | 標的名稱 |
| weight | DECIMAL | 權重（百分比，0-100） |

**選擇性欄位**：
| 欄位 | 類型 | 說明 | 預設 |
|------|------|------|------|
| asset_type | TEXT | 股票/債券/基金 | NULL |
| shares | DECIMAL | 持股數量 | NULL |
| market_value | DECIMAL | 市值 | NULL |
| source_name | TEXT | 資料來源名稱 | --source-name 或 NULL |
| source_url | TEXT | 資料來源網址 | --source-url 或 NULL |
| confidence_level | TEXT | 高/中/低 | --confidence 或 NULL |

### CSV 範本

```csv
etf_symbol,holding_date,asset_symbol,asset_name,asset_type,weight,shares,market_value,source_name,source_url,confidence_level
0050,2026-06-01,2330,台積電,股票,19.50,,,"公開資訊觀測站",https://mops.twse.gov.tw,中
0050,2026-06-01,2317,鴻海,股票,9.80,,,"公開資訊觀測站",https://mops.twse.gov.tw,中
0050,2026-06-01,2454,聯發科,股票,7.40,,,"公開資訊觀測站",https://mops.twse.gov.tw,中
0050,2026-06-01,2308,台達電,股票,3.20,,,"公開資訊觀測站",https://mops.twse.gov.tw,中
```

### 匯入指令

```bash
python -m scripts.import_holdings <file> [options]

選項：
  --source-name TEXT       資料來源名稱
  --source-url TEXT        資料來源網址
  --confidence TEXT        可信度等級
  --dry-run               測試模式
```

### 範例

```bash
python -m scripts.import_holdings ../data/samples/0050_holdings.csv

python -m scripts.import_holdings holdings.csv \
  --source-name "公開資訊觀測站" \
  --source-url "https://mops.twse.gov.tw" \
  --dry-run
```

### 重要說明

- **唯一鍵**：`(etf_symbol, holding_date, asset_symbol)`
- **權重標準化**：權重必須是 0-100 之間的小數。系統自動判斷是否需轉換（例如 0.195 → 19.5%）
- **外鍵約束**：`etf_symbol` 必須已存在於 `etf_master` 表
- **多個持股日期**：同一 ETF 可有多個不同的 `holding_date` 記錄

---

## 3. 股票價格（etf_prices）

### 功能

記錄 ETF 的歷史日價格（開盤、收盤、最高、最低、成交量）。

### 檔案格式

**檔名**：任意，建議 `<ETF_SYMBOL>_prices.csv`

**必需欄位**：
| 欄位 | 類型 | 說明 |
|------|------|------|
| etf_symbol | TEXT | ETF 代碼（必須存在於 etf_master） |
| trade_date | DATE (YYYY-MM-DD) | 交易日期 |
| close_price | DECIMAL | 收盤價 |

**選擇性欄位**：
| 欄位 | 類型 | 說明 | 預設 |
|------|------|------|------|
| open_price | DECIMAL | 開盤價 | NULL |
| high_price | DECIMAL | 最高價 | NULL |
| low_price | DECIMAL | 最低價 | NULL |
| volume | INTEGER | 成交量（股數） | NULL |
| source_name | TEXT | 資料來源名稱 | --source-name 或 NULL |
| source_url | TEXT | 資料來源網址 | --source-url 或 NULL |

### CSV 範本

```csv
etf_symbol,trade_date,open_price,high_price,low_price,close_price,volume,source_name,source_url
0050,2026-06-01,185.5,186.0,184.5,185.8,5000000,Yahoo Finance,https://finance.yahoo.com
0050,2026-05-31,185.0,185.7,184.8,185.2,4800000,Yahoo Finance,https://finance.yahoo.com
0050,2026-05-30,184.5,185.5,184.0,185.1,5100000,Yahoo Finance,https://finance.yahoo.com
```

### 匯入指令

```bash
python -m scripts.import_prices <file> [options]

選項：
  --source-name TEXT       資料來源名稱
  --source-url TEXT        資料來源網址
  --dry-run               測試模式
```

### 範例

```bash
python -m scripts.import_prices ../data/samples/0050_prices.csv

python -m scripts.import_prices prices.xlsx \
  --source-name "Yahoo Finance" \
  --source-url "https://finance.yahoo.com"
```

### 重要說明

- **唯一鍵**：`(etf_symbol, trade_date)`
- **外鍵約束**：`etf_symbol` 必須已存在於 `etf_master` 表
- **價格必須為正數**：所有價格欄位 > 0
- **日期排序**：建議按 `trade_date` 升序排列，以便回測計算

---

## 4. 配息記錄（etf_dividends）

### 功能

記錄 ETF 的配息紀錄，包括配息日期、配息金額、配息率。

### 檔案格式

**檔名**：任意，建議 `<ETF_SYMBOL>_dividends.csv`

**必需欄位**：
| 欄位 | 類型 | 說明 |
|------|------|------|
| etf_symbol | TEXT | ETF 代碼（必須存在於 etf_master） |
| ex_date | DATE (YYYY-MM-DD) | 除息日 |
| dividend_per_unit | DECIMAL | 單位配息 |

**選擇性欄位**：
| 欄位 | 類型 | 說明 | 預設 |
|------|------|------|------|
| pay_date | DATE (YYYY-MM-DD) | 配息日期 | NULL |
| dividend_type | TEXT | 普通配息/特別配息 | NULL |
| source_name | TEXT | 資料來源名稱 | --source-name 或 NULL |
| source_url | TEXT | 資料來源網址 | --source-url 或 NULL |

### CSV 範本

```csv
etf_symbol,ex_date,dividend_per_unit,pay_date,dividend_type,source_name,source_url
0050,2026-06-10,1.50,2026-06-30,普通配息,公開資訊觀測站,https://mops.twse.gov.tw
0050,2026-03-10,1.45,2026-03-30,普通配息,公開資訊觀測站,https://mops.twse.gov.tw
0050,2025-12-10,1.42,2025-12-30,普通配息,公開資訊觀測站,https://mops.twse.gov.tw
```

### 匯入指令

```bash
python -m scripts.import_dividends <file> [options]

選項：
  --source-name TEXT       資料來源名稱
  --source-url TEXT        資料來源網址
  --dry-run               測試模式
```

### 範例

```bash
python -m scripts.import_dividends ../data/samples/0050_dividends.csv

python -m scripts.import_dividends dividends.csv --dry-run
```

### 重要說明

- **唯一鍵**：`(etf_symbol, ex_date)`
- **外鍵約束**：`etf_symbol` 必須已存在於 `etf_master` 表
- **配息金額正數**：`dividend_per_unit` > 0

---

## 5. 股票產業分類（stock_industry）

### 功能

記錄股票的產業分類（一級、二級、三級產業，GICS 標準），用於計算組合產業曝露。

### 檔案格式

**檔名**：任意，建議 `stock_industry.csv`

**必需欄位**：
| 欄位 | 類型 | 說明 |
|------|------|------|
| stock_symbol | TEXT | 股票代碼（唯一鍵） |
| stock_name | TEXT | 股票名稱 |
| industry_level_1 | TEXT | 一級產業（例如「資訊科技」） |

**選擇性欄位**：
| 欄位 | 類型 | 說明 | 預設 |
|------|------|------|------|
| market | TEXT | 市場（例如「台灣」、「NASDAQ」） | NULL |
| industry_level_2 | TEXT | 二級產業（例如「半導體」） | NULL |
| industry_level_3 | TEXT | 三級產業（例如「半導體製造」） | NULL |
| custom_sector | TEXT | 自訂業別分類 | NULL |
| custom_theme | TEXT | 自訂主題標籤 | NULL |
| source_name | TEXT | 資料來源名稱 | NULL |
| source_url | TEXT | 資料來源網址 | NULL |

### CSV 範本

```csv
stock_symbol,stock_name,market,industry_level_1,industry_level_2,industry_level_3,source_name,source_url
2330,台積電,台灣,資訊科技,半導體,半導體製造,TWSE,https://mops.twse.gov.tw
2317,鴻海,台灣,資訊科技,電子零件,電子零件製造,TWSE,https://mops.twse.gov.tw
2454,聯發科,台灣,資訊科技,半導體,無晶圓廠設計,TWSE,https://mops.twse.gov.tw
2882,國泰金,台灣,金融,銀行,銀行,TWSE,https://mops.twse.gov.tw
```

### 匯入指令

```bash
python -m scripts.import_industry <file> [options]

選項：
  --dry-run               測試模式
```

### 範例

```bash
python -m scripts.import_industry ../data/samples/stock_industry.csv

python -m scripts.import_industry industry_data.xlsx --dry-run
```

### 重要說明

- **唯一鍵**：`stock_symbol`（若已存在則跳過）
- **三級分類標準**：建議遵循 GICS（全球產業分類標準）或台灣證交所標準
- **非必填**：`industry_level_2` 和 `industry_level_3` 可留空

---

## 資料匯入工作流

### 推薦順序

1. **ETF 基本資料**（etf_master）
   ```bash
   python -m scripts.import_etf_master etf_master.csv --dry-run
   python -m scripts.import_etf_master etf_master.csv
   ```

2. **股票產業分類**（stock_industry）
   ```bash
   python -m scripts.import_industry stock_industry.csv --dry-run
   python -m scripts.import_industry stock_industry.csv
   ```

3. **ETF 成分股**（etf_holdings）
   ```bash
   python -m scripts.import_holdings 0050_holdings.csv --dry-run
   python -m scripts.import_holdings 0050_holdings.csv
   ```

4. **股票價格**（etf_prices）
   ```bash
   python -m scripts.import_prices 0050_prices.csv --dry-run
   python -m scripts.import_prices 0050_prices.csv
   ```

5. **配息紀錄**（etf_dividends）
   ```bash
   python -m scripts.import_dividends 0050_dividends.csv --dry-run
   python -m scripts.import_dividends 0050_dividends.csv
   ```

6. **檢查資料品質**
   ```bash
   python -m scripts.run_quality_checks
   ```

### 驗證匯入

```bash
# 檢查 ETF 計數
psql -U etf -h localhost -d etf -c "SELECT COUNT(*) FROM etf_master;"

# 檢查成分股計數
psql -U etf -h localhost -d etf -c "SELECT COUNT(*) FROM etf_holdings;"

# 檢查價格記錄
psql -U etf -h localhost -d etf -c "SELECT COUNT(*) FROM etf_price;"

# 查看品質檢查結果
psql -U etf -h localhost -d etf -c "SELECT * FROM data_quality_check ORDER BY id DESC LIMIT 10;"
```

---

## 常見問題

### Q：CSV 檔案編碼錯誤
**A**：系統會自動嘗試 UTF-8、UTF-8-BOM、CP950、Big5。若仍失敗，請檢查：
```bash
file -i your_file.csv
iconv -f big5 -t utf-8 your_file.csv > your_file_utf8.csv
```

### Q：日期格式錯誤
**A**：所有日期必須是 `YYYY-MM-DD` 格式。不接受 `MM/DD/YYYY` 或 `DD-MM-YYYY`。

### Q：權重不和為 100%
**A**：系統會校驗權重總和。如確實權重不足 100%，請檢查：
- 是否有「其他」或「現金」類別遺漏
- CSV 中的權重是否正確
- 使用 `--dry-run` 檢查錯誤訊息

### Q：如何更新已匯入的資料？
**A**：
- **覆蓋**：刪除舊資料，重新匯入
  ```bash
  psql -U etf -h localhost -d etf -c "DELETE FROM etf_holdings WHERE etf_symbol='0050' AND holding_date='2026-06-01';"
  python -m scripts.import_holdings updated_holdings.csv
  ```
- **追加**：直接匯入新日期的資料（不會覆蓋舊記錄）

### Q：如何備份原始檔案？
**A**：所有匯入的檔案自動備份至 `/data/raw/<dataset_type>/`。
```bash
ls -la /data/raw/etf_master/
# 輸出：20260612T100000__etf_master.csv
```

### Q：匯入失敗，如何診斷？
**A**：
1. 使用 `--dry-run` 檢查驗證錯誤（不寫入）
2. 檢查 PostgreSQL 連線：`psql -U etf -h localhost -d etf`
3. 檢查資料表是否存在：`psql -U etf -h localhost -d etf -c "\dt"`
4. 查看最新的品質檢查報告：`python -m scripts.run_quality_checks`

---

## 樣本資料

以下範本檔案位於 `data/samples/`，可作為參考：

| 檔案 | 用途 | 記錄數 |
|------|------|--------|
| etf_master.csv | ETF 基本資料 | 3 個 ETF |
| 0050_holdings.csv | 0050 成分股 | 10 檔 |
| 0050_prices.csv | 0050 歷史價格 | 樣本記錄 |
| 0050_dividends.csv | 0050 配息紀錄 | 樣本記錄 |
| stock_industry.csv | 股票產業分類 | 樣本記錄 |
| data_source_registry.csv | 資料來源登記 | 參考用 |

---

## 進階用法

### 批量匯入多個 ETF

```bash
#!/bin/bash
for etf_symbol in 0050 006208 00878; do
  python -m scripts.import_holdings ${etf_symbol}_holdings.csv
  python -m scripts.import_prices ${etf_symbol}_prices.csv
  python -m scripts.import_dividends ${etf_symbol}_dividends.csv
done
```

### 排程匯入（cron）

```bash
# 每天早上 9 點執行匯入
0 9 * * * cd /home/user/etf-portfolio-lab/backend && python -m scripts.import_prices /path/to/latest_prices.csv
```

### 自訂資料品質檢查

```bash
python -m scripts.run_quality_checks --verbose
```

---

## 資料來源建議

| 資料類型 | 來源 | 網址 |
|---------|------|------|
| 台灣 ETF 基本資料 | 公開資訊觀測站 | https://mops.twse.gov.tw |
| 台灣 ETF 成分股 | 投信公司官網 | 各投信官方網站 |
| 歷史價格 | Yahoo Finance | https://finance.yahoo.com |
| 全球 ETF 資料 | ETFDB | https://www.etfdb.com |
| 產業分類 | 台灣證交所 | https://www.twse.gov.tw |
| GICS 標準 | MSCI | https://www.msci.com/gics |

---

## 後續步驟

- 完成匯入後，訪問 http://localhost:3000 查看前端儀表板
- 使用 API 文件 ([docs/API.md](API.md)) 查詢匯入的資料
- 查看「資料來源」頁面驗證資料來源與日期
