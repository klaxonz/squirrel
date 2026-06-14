# syntax=docker/dockerfile:1.7

ARG PYTHON_IMAGE=python:3.11-slim-bookworm

# ========================================
# runtime-base: 运行时系统依赖（chromium / ffmpeg / node）
# ========================================
FROM ${PYTHON_IMAGE} AS runtime-base

ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive \
    CHROME_PATH=/usr/bin/chromium \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_PATH=/usr/lib/node_modules

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    set -eux; \
    case "${TARGETARCH}" in \
        amd64) ffmpeg_arch='amd64' ;; \
        arm64) ffmpeg_arch='arm64' ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        chromium \
        chromium-driver \
        curl \
        gnupg \
        xz-utils; \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -; \
    apt-get install -y --no-install-recommends nodejs; \
    curl -fsSL "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-${ffmpeg_arch}-static.tar.xz" -o /tmp/ffmpeg.tar.xz; \
    mkdir -p /tmp/ffmpeg; \
    tar -xJf /tmp/ffmpeg.tar.xz -C /tmp/ffmpeg --strip-components=1; \
    mv /tmp/ffmpeg/ffmpeg /usr/local/bin/ffmpeg; \
    mv /tmp/ffmpeg/ffprobe /usr/local/bin/ffprobe; \
    ln -sf /usr/bin/chromium /usr/bin/google-chrome; \
    apt-get purge -y curl gnupg xz-utils; \
    apt-get autoremove -y; \
    rm -rf /var/lib/apt/lists/* /tmp/ffmpeg /tmp/ffmpeg.tar.xz

# ========================================
# build-base: 编译工具（runtime-base + build-essential / pipenv）
# ========================================
FROM runtime-base AS build-base

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        libmariadb-dev \
        libpq-dev; \
    pip install --no-cache-dir build pipenv

# ========================================
# frontend-builder: 构建 Vue 前端
# ========================================
FROM build-base AS frontend-builder

WORKDIR /app/squirrel-frontend

COPY squirrel-frontend/package.json squirrel-frontend/package-lock.json ./

RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci

COPY squirrel-frontend/ ./

RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm run build

# ========================================
# youtube-node-builder: 安装 YouTube runtime 的 node 生产依赖
# ========================================
FROM build-base AS youtube-node-builder

WORKDIR /app/squirrel-site-runtimes/youtube/src/squirrel_youtube/node

COPY squirrel-site-runtimes/youtube/src/squirrel_youtube/node/package.json squirrel-site-runtimes/youtube/src/squirrel_youtube/node/package-lock.json ./

RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci --omit=dev

COPY squirrel-site-runtimes/youtube/src/squirrel_youtube/node/ ./

# ========================================
# python-builder: 安装 Python 依赖 + 构建 SDK / 插件 wheels
# ========================================
FROM build-base AS python-builder

WORKDIR /app

COPY squirrel-backend/Pipfile squirrel-backend/Pipfile.lock /app/squirrel-backend/

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    cd /app/squirrel-backend && pipenv install --deploy --system

COPY squirrel-sdk /app/squirrel-sdk
COPY squirrel-site-runtimes /app/squirrel-site-runtimes

RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    set -eux; \
    mkdir -p /tmp/wheels; \
    python -m build /app/squirrel-sdk --wheel --outdir /tmp/wheels; \
    find /app/squirrel-site-runtimes -mindepth 2 -maxdepth 2 -name pyproject.toml -print0 | while IFS= read -r -d '' pyproject; do \
        plugin_dir="$(dirname "${pyproject}")"; \
        echo "Building plugin wheel: ${plugin_dir}"; \
        python -m build "${plugin_dir}" --wheel --outdir /tmp/wheels; \
    done; \
    pip install --no-cache-dir /tmp/wheels/*.whl; \
    rm -rf /tmp/wheels

# ========================================
# final: 运行时镜像（不含编译工具，基于 runtime-base）
# ========================================
FROM runtime-base AS final

WORKDIR /app/squirrel-backend

COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

COPY squirrel-backend ./
COPY squirrel-sdk /app/squirrel-sdk
COPY squirrel-site-runtimes /app/squirrel-site-runtimes

COPY --from=frontend-builder /app/squirrel-frontend/dist ./static
COPY --from=youtube-node-builder /app/squirrel-site-runtimes/youtube/src/squirrel_youtube/node /app/squirrel-site-runtimes/youtube/src/squirrel_youtube/node

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
