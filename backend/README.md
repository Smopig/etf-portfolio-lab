# ETF Portfolio Lab — Backend

FastAPI backend skeleton (Phase 0).

## Local development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Tests

```bash
pytest
```

## Environment variables

Copy `.env.example` to `.env` and adjust as needed:

- `DATABASE_URL` (default: `postgresql+psycopg2://etf:etf@db:5432/etf`)
- `APP_ENV` (default: `development`)
- `CORS_ORIGINS` (default: `["http://localhost:3000"]`)

## Docker

```bash
docker build -t etf-portfolio-lab-backend .
docker run -p 8000:8000 etf-portfolio-lab-backend
```
