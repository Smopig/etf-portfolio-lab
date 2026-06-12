FROM python:3.11-slim

WORKDIR /code

COPY pyproject.toml /code/pyproject.toml
RUN pip install --no-cache-dir .

COPY app /code/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
