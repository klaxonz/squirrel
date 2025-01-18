FROM ghcr.io/klaxonz/squirrel-base:latest AS base

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