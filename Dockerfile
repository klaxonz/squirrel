# Stage 0: Base image with all dependencies
FROM python:3.11-slim-bullseye AS base

# Install system dependencies, Node.js and FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb-dev \
    wget \
    xz-utils \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar xf ffmpeg-release-amd64-static.tar.xz \
    && mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ \
    && mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ \
    && rm -rf ffmpeg-*-amd64-static* \
    && npm install -g pnpm \
    && pip install --no-cache-dir pipenv \
    && apt-get purge -y wget gnupg \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Stage 1: Build the frontend
FROM base AS frontend-builder

WORKDIR /app/squirrel-frontend

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