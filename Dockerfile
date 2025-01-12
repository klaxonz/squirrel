# Stage 1: Build the frontend
FROM node:18-slim AS frontend-builder

WORKDIR /app/squirrel-frontend

# Install pnpm
RUN npm install -g pnpm

# Copy package files first to leverage cache
COPY squirrel-frontend/package.json squirrel-frontend/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code and build
COPY squirrel-frontend/ ./
RUN pnpm run build

# Stage 2: Build the backend
FROM python:3.11-slim-bullseye AS backend

WORKDIR /app

# Install system dependencies and FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb-dev \
    wget \
    xz-utils \
    && wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar xf ffmpeg-release-amd64-static.tar.xz \
    && mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ \
    && mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ \
    && rm -rf ffmpeg-*-amd64-static* \
    && apt-get purge -y wget \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pipenv

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

# Expose port
EXPOSE 8000

CMD ["python", "main.py"]