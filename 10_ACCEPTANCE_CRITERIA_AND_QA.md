# 10_ACCEPTANCE_CRITERIA_AND_QA.md — 驗收標準與 QA 清單

---

## 1. 全系統驗收標準

第一版完成時，必須符合：

- 可以本地啟動
- 可以匯入 sample data
- 可以查 ETF 主檔
- 可以查 ETF 成分股
- 可以計算單檔 ETF 產業占比
- 可以比較兩檔 ETF 重疊度
- 可以建立 Portfolio
- 可以計算 Portfolio 穿透曝險
- 可以執行簡易回測
- 可以執行財務模擬
- 可以在前端操作上述功能
- 有資料品質檢查
- 有 README
- 有基本測試

---

## 2. 啟動驗收

必須可以執行：

```bash
docker compose up
```

並開啟：

```text
Frontend: http://localhost:3000
Backend: http://localhost:8000/docs
```

---

## 3. 資料匯入驗收

必須可以匯入：

- ETF 主檔
- ETF 成分股
- 股票產業分類
- ETF 歷史價格
- ETF 配息

錯誤情況需處理：

- 檔案不存在
- 欄位缺失
- 日期格式錯誤
- 百分比格式錯誤
- 編碼錯誤
- ETF 代號不存在
- 股票代號不存在

---

## 4. 資料品質驗收

必須檢查：

- 持股權重是否接近 100%
- 是否缺少產業分類
- 是否缺少成分股代號
- 價格資料是否缺日期
- 配息資料是否重複
- 資料日期是否過舊
- 來源 metadata 是否存在

---

## 5. ETF 分析驗收

給定 ETF 成分股資料，系統必須能輸出：

- 前十大成分股
- 成分股數量
- Top 1 / 3 / 5 / 10 權重
- HHI
- 有效持股數
- 產業占比
- 最大產業
- 前三大產業

---

## 6. ETF 重疊度驗收

給定兩檔 ETF，系統必須能輸出：

- 重疊股票數量
- 重疊股票清單
- 重疊權重
- 加權重疊分數
- 共同前十大持股
- 產業曝險相似度

---

## 7. Portfolio Builder 驗收

給定：

```text
0050 40%
00878 30%
00679B 30%
```

系統必須輸出：

- 權重加總是否 100%
- 穿透後股票曝險
- 穿透後產業曝險
- 組合前十大股票
- 組合前十大產業
- 組合集中度
- 風險提示

---

## 8. 回測驗收

回測必須支援：

- 單筆投入
- 每月投入
- 配息再投入
- 再平衡
- 交易成本

必須輸出：

- 最終資產
- 總投入本金
- 投資收益
- CAGR
- MDD
- 年化波動
- Sharpe
- 年度報酬
- 資產曲線
- 回撤曲線

---

## 9. 財務模擬驗收

必須支援：

- 初始投入
- 每月投入
- 年化報酬
- 年限
- 目標金額

必須輸出：

- 未來資產
- 本金
- 收益
- 達標狀態
- 達標所需年數
- 達標所需每月投入
- 達標所需年化報酬率

---

## 10. 前端驗收

每個頁面必須具備：

- loading state
- empty state
- error state
- 資料來源顯示
- 資料日期顯示
- 繁體中文介面
- 表格可讀
- 圖表有說明
- 主任務清楚

---

## 11. UX 驗收

檢查：

- 使用者第一眼是否知道頁面目的？
- 是否有太多資訊同時出現？
- 關鍵結論是否在上方？
- 圖表是否有解釋？
- 指標是否有意義？
- 操作流程是否卡住？
- 表格是否容易比較？
- 配置權重錯誤是否有提示？
- 回測資料不足是否有提示？
- 資料過舊是否有警示？

---

## 12. AI 驗收

AI 回答必須：

- 基於系統資料
- 引用資料日期
- 引用資料來源
- 不直接給買賣建議
- 不保證未來績效
- 清楚說明限制
- 對資料缺失保持誠實

---

## 13. 測試最低要求

Backend：

- unit tests
- service tests
- API tests

Frontend：

- component smoke tests
- page smoke tests
- form validation tests

Quant：

- CAGR tests
- MDD tests
- portfolio exposure tests
- overlap tests
- projection formula tests

Data：

- import tests
- data quality tests
- duplicate detection tests
