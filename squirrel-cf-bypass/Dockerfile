FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY scripts ./scripts
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

# camoufox 构建期下载需访问 GitHub API，匿名易触发限流（403）后走有 bug 的 fallback。
# 通过 --build-arg GITHUB_TOKEN=xxx 传入 PAT 鉴权（仅此 RUN 构建期可见，不进运行镜像）。
ARG GITHUB_TOKEN=""

RUN pip install --no-cache-dir . \
    && GITHUB_TOKEN="${GITHUB_TOKEN}" python scripts/fetch_camoufox.py

ENV CF_BYPASS_PORT=8002

EXPOSE 8002

CMD ["sh", "-c", "uvicorn squirrel_cf_bypass.app.main:app --host 0.0.0.0 --port ${CF_BYPASS_PORT:-8002}"]
