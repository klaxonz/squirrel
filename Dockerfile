# syntax=docker/dockerfile:1.7

ARG BUILD_BASE_IMAGE=ghcr.io/klaxonz/squirrel-base:build
ARG RUNTIME_BASE_IMAGE=ghcr.io/klaxonz/squirrel-base:runtime

FROM ${BUILD_BASE_IMAGE} AS frontend-builder

WORKDIR /app/squirrel-frontend

COPY squirrel-frontend/package.json squirrel-frontend/package-lock.json ./

RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci

COPY squirrel-frontend/ ./

RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm run build

FROM ${BUILD_BASE_IMAGE} AS youtube-node-builder

WORKDIR /app/squirrel-plugins/youtube/src/squirrel_youtube/node

COPY squirrel-plugins/youtube/src/squirrel_youtube/node/package.json squirrel-plugins/youtube/src/squirrel_youtube/node/package-lock.json ./

RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci --omit=dev

COPY squirrel-plugins/youtube/src/squirrel_youtube/node/ ./

FROM ${BUILD_BASE_IMAGE} AS python-builder

WORKDIR /app

COPY squirrel-backend/Pipfile squirrel-backend/Pipfile.lock /app/squirrel-backend/

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    cd /app/squirrel-backend && pipenv install --deploy --system

COPY squirrel-sdk /app/squirrel-sdk
COPY squirrel-plugins /app/squirrel-plugins

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    set -eux; \
    mkdir -p /tmp/wheels; \
    python -m build /app/squirrel-sdk --wheel --outdir /tmp/wheels; \
    find /app/squirrel-plugins -mindepth 2 -maxdepth 2 -name pyproject.toml -print0 | while IFS= read -r -d '' pyproject; do \
        plugin_dir="$(dirname "${pyproject}")"; \
        echo "Building plugin wheel: ${plugin_dir}"; \
        python -m build "${plugin_dir}" --wheel --outdir /tmp/wheels; \
    done; \
    pip install --no-cache-dir /tmp/wheels/*.whl; \
    rm -rf /tmp/wheels

FROM ${RUNTIME_BASE_IMAGE} AS final

WORKDIR /app/squirrel-backend

COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

COPY squirrel-backend ./
COPY squirrel-sdk /app/squirrel-sdk
COPY squirrel-plugins /app/squirrel-plugins

COPY --from=frontend-builder /app/squirrel-frontend/dist ./static
COPY --from=youtube-node-builder /app/squirrel-plugins/youtube/src/squirrel_youtube/node /app/squirrel-plugins/youtube/src/squirrel_youtube/node

RUN mkdir -p /app/config /app/logs /downloads /thumbnails \
    && chmod -R 755 /app \
    && echo "Squirrel Docker Image Built at $(date)" > /app/BUILD_INFO

ENV PYTHONPATH=/app/squirrel-backend:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_PATH=/usr/lib/node_modules \
    PORT=8001 \
    TZ=Asia/Shanghai \
    CHROME_PATH=/usr/bin/chromium

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os; import urllib.request; import sys; port = os.getenv('PORT', '8001'); urllib.request.urlopen(f'http://localhost:{port}/health', timeout=5).read(); sys.exit(0)" || exit 1

CMD ["python", "main.py"]
