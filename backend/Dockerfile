FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv

WORKDIR /code

COPY pyproject.toml uv.lock /code/

# 安裝執行期依賴（不含 dev 套件），先不安裝專案本身（app 目錄尚未複製）
RUN uv sync --frozen --no-dev --no-install-project

COPY app /code/app

# migration 與資料載入所需檔案（entrypoint 會用到）
COPY alembic.ini /code/alembic.ini
COPY alembic /code/alembic
COPY scripts /code/scripts
COPY entrypoint.sh /code/entrypoint.sh
RUN chmod +x /code/entrypoint.sh

# 安裝專案本身
RUN uv sync --frozen --no-dev

ENV PATH="/code/.venv/bin:$PATH"

EXPOSE 8000

# 先跑 migration（可選 seed）再啟動 uvicorn
CMD ["/code/entrypoint.sh"]
