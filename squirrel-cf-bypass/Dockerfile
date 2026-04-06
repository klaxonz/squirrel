FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

ENV CF_BYPASS_PORT=8002

EXPOSE 8002

CMD ["sh", "-c", "uvicorn squirrel_cf_bypass.app.main:app --host 0.0.0.0 --port ${CF_BYPASS_PORT:-8002}"]
