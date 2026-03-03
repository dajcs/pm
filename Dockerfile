# -- Build frontend --
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# -- Runtime --
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install gosu for privilege dropping in the entrypoint
RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a virtual environment (isolates from system Python)
COPY backend/pyproject.toml ./
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -r pyproject.toml

# Copy backend code
COPY backend/ ./

# Copy built frontend into static dir (replaces placeholder)
COPY --from=frontend-build /app/frontend/out ./static

# Create non-root user and data directory
RUN adduser --disabled-password --gecos '' appuser && \
    mkdir -p /app/data && chown appuser:appuser /app/data

# Entrypoint fixes data-dir ownership (handles pre-existing root-owned volumes)
# then drops to appuser via gosu
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/docker-entrypoint.sh"]
