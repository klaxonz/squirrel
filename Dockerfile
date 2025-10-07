# ========================================
# Squirrel 多阶段构建 Dockerfile
# ========================================

# 基础镜像（包含 Python、Node.js、FFmpeg 等依赖）
FROM ghcr.io/klaxonz/squirrel-base:latest AS base

# ========================================
# 阶段 1: 构建前端
# ========================================
FROM base AS frontend-builder

WORKDIR /app/squirrel-frontend

# 复制依赖配置文件（利用 Docker 缓存）
COPY squirrel-frontend/package.json squirrel-frontend/pnpm-lock.yaml ./

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制源代码并构建
COPY squirrel-frontend/ ./
RUN pnpm run build && \
    echo "Frontend build completed at $(date)" && \
    ls -lh dist/

# ========================================
# 阶段 2: 构建后端（最终镜像）
# ========================================
FROM base AS final

# 设置工作目录
WORKDIR /app

# 复制 squirrel-sdk（后端依赖）
COPY squirrel-sdk ./squirrel-sdk

# 切换到后端目录
WORKDIR /app/squirrel-backend

# 复制后端依赖配置文件
COPY squirrel-backend/Pipfile squirrel-backend/Pipfile.lock ./

# 安装 squirrel-sdk 和后端依赖
RUN pip install --no-cache-dir /app/squirrel-sdk && \
    pipenv install --deploy --system && \
    pip list

# 复制后端应用代码
COPY squirrel-backend ./

# 复制前端构建产物到静态文件目录
COPY --from=frontend-builder /app/squirrel-frontend/dist ./static

# 安装 YouTube token 生成器
RUN npm install --global youtube-po-token-generator

# 创建必要的目录
RUN mkdir -p /app/config /app/logs /downloads /app/squirrel-backend/plugins_ext && \
    chmod -R 755 /app && \
    echo "Squirrel Docker Image Built at $(date)" > /app/BUILD_INFO

# 设置环境变量
ENV PYTHONPATH=/app/squirrel-backend:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_PATH=/usr/lib/node_modules \
    TZ=Asia/Shanghai

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; import sys; urllib.request.urlopen('http://localhost:8000/health', timeout=5).read(); sys.exit(0)" || exit 1

# 设置默认命令
CMD ["python", "main.py"]