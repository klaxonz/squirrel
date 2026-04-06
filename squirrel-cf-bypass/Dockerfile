FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8001

CMD ["uvicorn", "squirrel_cf_bypass.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
