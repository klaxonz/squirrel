FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        fonts-liberation \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcairo2 \
        libdbus-glib-1-2 \
        libdrm2 \
        libgbm1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        libxshmfence1 \
        libxt6 \
    && rm -rf /var/lib/apt/lists/*

ENV XDG_CACHE_HOME=/root/.cache

RUN pip install --no-cache-dir . \
    && python -m camoufox fetch

ENV CF_BYPASS_PORT=8002

EXPOSE 8002

CMD ["sh", "-c", "uvicorn squirrel_cf_bypass.app.main:app --host 0.0.0.0 --port ${CF_BYPASS_PORT:-8002}"]
