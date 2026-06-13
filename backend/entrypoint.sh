#!/bin/sh
# Container entrypoint: apply DB migrations (and optionally seed sample data)
# before starting the API server. Keeps the database schema in sync on every
# `docker compose up` so the app never queries non-existent tables.
set -e

echo "[entrypoint] Applying database migrations (alembic upgrade head)..."
alembic upgrade head

if [ "${SEED_SAMPLE_DATA:-false}" = "true" ]; then
  echo "[entrypoint] SEED_SAMPLE_DATA=true -> seeding sample data..."
  python -m scripts.seed || echo "[entrypoint] seed step skipped/failed (continuing)."
fi

echo "[entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
