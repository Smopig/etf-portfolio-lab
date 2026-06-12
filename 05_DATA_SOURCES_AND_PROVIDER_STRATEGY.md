# 05_DATA_SOURCES_AND_PROVIDER_STRATEGY.md — 資料來源與 Provider 策略

---

## 1. 資料來源優先順序

本專案資料來源採用：

```text
官方資料優先
投信資料補成分股
指數公司補換股
第三方資料只做備援
手動匯入永遠保留
```

---

## 2. ETF 清單與基本資料

### 優先來源

- TWSE ETF e添富
- TWSE OpenAPI
- TWSE ETF 商品資訊

### 可取得資料

- ETF 代號
- ETF 名稱
- 發行投信
- 上市日期
- ETF 類別
- 標的指數
- 資產規模
- 收盤價
- 年初至今日均成交值
- 年初至今日均成交量
- 受益人數

---

## 3. ETF 成分股與權重

### 優先來源

各家投信官網：

- 元大投信
- 國泰投信
- 富邦投信
- 復華投信
- 群益投信
- 凱基投信
- 永豐投信
- 兆豐投信
- 統一投信
- 野村投信
- 中信投信
- 新光投信

### 可取得資料

- 成分股代號
- 成分股名稱
- 成分股權重
- 股數
- 市值
- 淨值 NAV
- 折溢價
- 配息紀錄
- 月報
- 公開說明書
- 投資策略

---

## 4. ETF 類型、主動 / 被動、選股規則

### 來源

- TWSE ETF 資料
- 投信官網
- 公開說明書
- ETF 月報
- 指數公司文件

### 需取得資料

- 管理方式：主動 / 被動 / Smart Beta
- 資產類別：股票 / 債券 / 商品 / 期貨 / 槓桿 / 反向
- 投資風格：市值 / 高股息 / 低波 / 主題 / ESG / 多因子
- 追蹤指數
- 指數公司
- 選股規則
- 加權方式
- 成分股調整頻率
- 複製方式

---

## 5. 股票產業分類

### 優先來源

- TWSE 上市公司基本資料
- 政府開放資料平台
- TPEx 上櫃公司基本資料

### 欄位

- 股票代號
- 股票名稱
- 市場別
- 官方產業分類
- 上市 / 上櫃日期

### 自訂分類

官方分類可能太粗，因此系統需支援自訂分類：

- industry_level_1
- industry_level_2
- industry_level_3
- custom_sector
- custom_theme

例如：

```text
半導體
├── 晶圓代工
├── IC 設計
├── 封測
└── 設備材料
```

---

## 6. ETF 歷史價格與配息

### 來源

- TWSE
- TPEx
- Yahoo Finance
- 投信官網
- 第三方備援

### 欄位

- 日期
- 開盤價
- 最高價
- 最低價
- 收盤價
- 還原收盤價
- 成交量
- 成交值
- 除息日
- 配息金額
- 發放日

---

## 7. 指數調整與換股事件

### 優先來源

- 臺灣指數公司
- FTSE Russell
- MSCI
- S&P Dow Jones
- 投信公告
- 指數公告

### 可取得資料

- 公告日期
- 生效日期
- 新增成分股
- 刪除成分股
- 權重調整
- 指數審核結果

### 若找不到公告

使用快照差異比對：

```text
本週 ETF 持股快照
vs
上週 ETF 持股快照
↓
新增 / 刪除 / 權重變化
```

---

## 8. 第三方資料來源

第三方只作為備援，不作為唯一主資料源。

可考慮：

- MoneyDJ / FundDJ
- Yahoo 股市
- Goodinfo
- 玩股網
- 鉅亨網
- CMoney
- 券商資料頁

需注意：

- 授權
- 資料穩定性
- 是否可大量抓取
- 是否與官方資料衝突

---

## 9. Provider 架構

### Base Provider

所有資料來源必須實作相同介面：

```python
class BaseDataProvider:
    def fetch_etf_master(self): ...
    def fetch_holdings(self, symbol: str): ...
    def fetch_prices(self, symbol: str): ...
    def fetch_dividends(self, symbol: str): ...
    def fetch_metadata(self, symbol: str): ...
```

---

## 10. 第一版 Provider 順序

### MVP 必做

1. CSV Provider
2. Excel Provider
3. Manual Upload Provider

### 第二階段

4. Yahoo Finance Provider
5. TWSE Provider

### 第三階段

6. Fund Company Provider
7. Index Company Provider

---

## 11. 資料品質檢查

每次匯入後需檢查：

- 權重加總是否接近 100%
- ETF 代號是否存在
- 股票代號是否存在
- 產業分類是否缺失
- 價格日期是否連續
- 配息資料是否重複
- 資料日期是否過舊
- 同一資料不同來源是否衝突

---

## 12. 每筆資料都需記錄

每筆關鍵資料需記錄：

- source_name
- source_url
- fetched_at
- data_date
- confidence_level
- raw_file_path
- parser_version
