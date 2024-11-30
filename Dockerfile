# Stage 1: Build the frontend
FROM node:18 AS frontend-builder

WORKDIR /app/frontend

# Install pnpm
RUN npm install -g pnpm

# Copy frontend source code
COPY media-subscribe-front/ ./

# Install dependencies and build the frontend
RUN pnpm install --frozen-lockfile && pnpm run build

# Stage 2: Build the backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies and FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb-dev \
    wget \
    xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar xvf ffmpeg-release-amd64-static.tar.xz \
    && mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ \
    && mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ \
    && rm -rf ffmpeg-*-amd64-static* \
    && apt-get purge -y wget

WORKDIR /app/media-subscribe

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy the rest of the application code
COPY media-subscribe /app/media-subscribe

# Install project dependencies
RUN pipenv install --deploy --system

# Copy the built frontend files to the backend's static directory
COPY --from=frontend-builder /app/frontend/dist /app/media-subscribe/static

# Set the Python path to include the media-subscribe directory
ENV PYTHONPATH=/app/media-subscribe:$PYTHONPATH

# Expose the port the app runs on
EXPOSE 8000


RUN chmod +x start.sh

CMD ["./start.sh"]