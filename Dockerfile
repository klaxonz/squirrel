# Stage 1: Build the frontend
FROM node:18 AS frontend-builder

WORKDIR /app/frontend

# Install pnpm
RUN npm install -g pnpm

# Copy frontend source code
COPY media-subscribe-front/package.json media-subscribe-front/pnpm-lock.yaml ./
COPY media-subscribe-front/ ./

# Install dependencies and build the frontend
RUN pnpm install --frozen-lockfile && pnpm run build

# Stage 2: Build the backend
FROM python:3.11-slim

# Install FFmpeg
COPY --from=jrottenberg/ffmpeg:6.0-ubuntu /usr/local /usr/local

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb-dev \
    libssl1.1 \
    && rm -rf /var/lib/apt/lists/*

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipfile and Pipfile.lock
COPY media-subscribe/Pipfile media-subscribe/Pipfile.lock ./

# Install project dependencies
RUN pipenv install --deploy --system

# Copy the rest of the application code
COPY media-subscribe /app/media-subscribe

# Copy the built frontend files to the backend's static directory
COPY --from=frontend-builder /app/frontend/dist /app/media-subscribe/static

# Set the Python path to include the media-subscribe directory
ENV PYTHONPATH=/app/media-subscribe:$PYTHONPATH

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["python", "media-subscribe/main.py"]