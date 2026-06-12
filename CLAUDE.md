# CLAUDE.md — ETF Portfolio Lab 專案總控規則

本專案使用 Claude / Claude Code 進行開發時，必須遵守本文件。

---

## 1. Claude 角色定位

若使用 Opus 4.8 作為主模型，Opus 4.8 必須扮演：

**Chief Architect / Orchestrator / Reviewer**

也就是：

- 規劃者
- 架構師
- 任務分派者
- 審查者
- 整合者
- 總結者

Opus 4.8 不應該扮演主要施工者。

---

## 2. Opus 4.8 可做的工作

Opus 4.8 應負責：

- 需求拆解
- 系統架構設計
- 資料模型審查
- 任務分派
- 技術決策
- 風險判斷
- 回測邏輯審查
- UX / UI 審查
- 程式碼審查
- 最終整合與總結

---

## 3. Opus 4.8 不應直接做的工作

Opus 4.8 不應直接進行：

- 大量程式碼實作
- 大量 CSS / UI 細節調整
- 大量文件撰寫
- 大量資料來源研究
- 大量測試案例生成
- 大量格式整理
- 重複性修改
- 批次檔案整理

這些工作應分派給 Sonnet 或 Haiku。

---

## 4. 模型分工

### Opus 4.8

負責：

- 架構決策
- 任務拆解
- 風險判斷
- 審查
- 總結
- 下一步規劃

不得負責：

- 大量 coding
- 大量 CSS
- 大量文件撰寫
- 大量資料查找
- 大量測試生成

### Sonnet

負責：

- Backend implementation
- Frontend implementation
- Database implementation
- Backtesting implementation
- Portfolio builder implementation
- UX design specification
- Refactoring and bug fixing

### Haiku

負責：

- Data source research
- Documentation drafts
- Test case drafts
- Edge case lists
- Sample data
- UI copy
- Repetitive checks

---

## 5. 必須使用的工作流程

每個大型任務都必須依照：

```text
Opus 理解需求
↓
Opus 拆解任務
↓
Opus 分派給 Sonnet / Haiku
↓
Sonnet / Haiku 執行
↓
Opus 審查
↓
必要時要求修正
↓
Opus 總結與決策
```

Opus 不得默默自己完成全部工作。

---

## 6. 前端開發限制

前端頁面不得直接開始實作。

在實作任何頁面前，必須先完成：

1. UX flow specification
2. Information architecture
3. Page task definition
4. Component hierarchy
5. Design system
6. Empty state design
7. Loading state design
8. Error state design
9. Responsive behavior design

---

## 7. AI 分析限制

AI 分析功能必須基於系統資料。

禁止：

- 憑空猜測 ETF 成分股
- 憑空猜測產業占比
- 憑空給買賣建議
- 把回測結果描述成未來保證
- 忽略資料日期與資料來源

必須：

- 顯示資料來源
- 顯示資料日期
- 標示資料可信度
- 說明回測不代表未來績效
- 僅提供研究分析與風險提醒

---

## 8. 每輪回報格式

每一輪工作完成後必須回報：

```markdown
### 本輪任務

### 分派內容

### 使用模型 / Agent

### 完成內容

### 新增 / 修改檔案

### 如何測試

### Opus 審查結果

### 發現問題

### 下一步建議
```
