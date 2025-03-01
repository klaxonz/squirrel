FROM ghcr.io/klaxonz/squirrel-base:latest AS base

# Stage 1: Build the frontend
FROM base AS frontend-builder

# 环境变量设置
ENV SHELL=/bin/bash \
    PNPM_HOME="$HOME/.local/share/pnpm" \
    PATH="${PATH}:${PNPM_HOME}" \
    NODE_PATH=/usr/lib/node_modules

WORKDIR /app/squirrel-frontend

RUN pnpm setup && \
    . $HOME/.bashrc && \
    pnpm install -g youtube-po-token-generator

# Copy package files first to leverage cache
COPY squirrel-frontend/package.json squirrel-frontend/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code and build
COPY squirrel-frontend/ ./
RUN pnpm run build

# Stage 2: Build the backend
FROM base AS backend

WORKDIR /app/squirrel-backend

# Copy Pipfile files first to leverage cache
COPY squirrel-backend/Pipfile squirrel-backend/Pipfile.lock ./

# Install dependencies
RUN pipenv install --deploy --system

# Copy application code
COPY squirrel-backend ./

# Copy frontend build
COPY --from=frontend-builder /app/squirrel-frontend/dist ./static

# Set environment variables
ENV PYTHONPATH=/app/squirrel-backend:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["python", "main.py"]