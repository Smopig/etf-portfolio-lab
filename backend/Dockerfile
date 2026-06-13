FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv

WORKDIR /code

COPY pyproject.toml uv.lock /code/

# 安裝執行期依賴（不含 dev 套件），先不安裝專案本身（app 目錄尚未複製）
RUN uv sync --frozen --no-dev --no-install-project

COPY app /code/app

# 安裝專案本身
RUN uv sync --frozen --no-dev

ENV PATH="/code/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
