# ETF Portfolio Lab — Frontend

Next.js 14 (App Router) + React 18 + TypeScript + Tailwind CSS

## 開發環境執行

```bash
npm install
npm run dev
```

開啟 http://localhost:3000

## 環境變數

建立 `.env.local`（可選）：

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

預設值為 `http://localhost:8000`。

## 建置與啟動

```bash
npm run build
npm run start
```

## Lint

```bash
npm run lint
```

## Docker

```bash
docker build -t etf-portfolio-lab-frontend .
docker run -p 3000:3000 etf-portfolio-lab-frontend
```

## 目錄結構

- `app/` — 頁面（App Router）
- `components/` — UI 元件（charts, tables, etf, portfolio, layout）
- `lib/` — 共用函式（API client、格式化）
