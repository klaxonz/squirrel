# ========================================
# Squirrel 多阶段构建 Dockerfile
# ========================================

FROM ghcr.io/klaxonz/squirrel-base:latest AS base

# ========================================
# 阶段 1: 构建前端
# ========================================
FROM base AS frontend-builder

WORKDIR /app/squirrel-frontend

COPY squirrel-frontend/package.json squirrel-frontend/package-lock.json ./

RUN npm ci

COPY squirrel-frontend/ ./

RUN npm run build && \
    echo "Frontend build completed at $(date)" && \
    ls -lh dist/

# ========================================
# 阶段 2: 构建插件包
# ========================================
FROM base AS plugin-builder

WORKDIR /app

COPY squirrel-sdk ./squirrel-sdk
COPY squirrel-plugins ./squirrel-plugins

RUN cd squirrel-sdk && \
    pip install --no-cache-dir build && \
    python -m build && \
    pip install --no-cache-dir dist/*.whl && \
    echo "SDK installed successfully"

RUN for plugin_dir in squirrel-plugins/*/; do \
        if [ -f "$plugin_dir/pyproject.toml" ]; then \
            echo "Building plugin: $plugin_dir"; \
            cd "/app/$plugin_dir" && \
            python -m build && \
            pip install --no-cache-dir dist/*.whl; \
        fi; \
    done && \
    pip list | grep squirrel

# ========================================
# 阶段 3: 最终运行镜像
# ========================================
FROM base AS final

WORKDIR /app/squirrel-backend

COPY squirrel-backend/Pipfile squirrel-backend/Pipfile.lock ./

RUN pipenv install --deploy --system && \
    pip list

COPY --from=plugin-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

COPY squirrel-backend ./
COPY squirrel-sdk /app/squirrel-sdk
COPY squirrel-plugin-runner /app/squirrel-plugin-runner
COPY squirrel-plugins /app/squirrel-plugins

COPY --from=frontend-builder /app/squirrel-frontend/dist ./static

RUN cd /app/squirrel-plugins/youtube/src/squirrel_youtube/node && \
    npm ci

RUN npm install --global youtube-po-token-generator

RUN mkdir -p /app/config /app/logs /downloads /thumbnails && \
    chmod -R 755 /app && \
    echo "Squirrel Docker Image Built at $(date)" > /app/BUILD_INFO

ENV PYTHONPATH=/app/squirrel-backend:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_PATH=/usr/lib/node_modules \
    TZ=Asia/Shanghai \
    CHROME_PATH=/usr/bin/chromium

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; import sys; urllib.request.urlopen('http://localhost:8000/health', timeout=5).read(); sys.exit(0)" || exit 1

CMD ["python", "main.py"]
