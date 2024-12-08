# Stage 1: Build the frontend
FROM node:18-slim AS frontend-builder

WORKDIR /app/frontend

# Install pnpm
RUN npm install -g pnpm

# Copy package files first to leverage cache
COPY media-subscribe-front/package.json media-subscribe-front/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code and build
COPY media-subscribe-front/ ./
RUN pnpm run build

# Stage 2: Build the backend
FROM python:3.11-slim-bullseye AS backend

WORKDIR /app

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

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

WORKDIR /app/media-subscribe

# Copy Pipfile files first to leverage cache
COPY media-subscribe/Pipfile media-subscribe/Pipfile.lock ./

# Install dependencies
RUN pipenv install --deploy --system

# Copy application code
COPY media-subscribe ./
COPY media-subscribe/temp/bilibili.py /usr/local/lib/python3.11/site-packages/yt_dlp/extractor/bilibili.py

# Copy frontend build
COPY --from=frontend-builder /app/frontend/dist ./static

# Set environment variables
ENV PYTHONPATH=/app/media-subscribe:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Change ownership of application files
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

CMD ["python", "main.py"]