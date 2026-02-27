# -- Build frontend (enabled in Part 3) --
# FROM node:22-slim AS frontend-build
# WORKDIR /app/frontend
# COPY frontend/package.json frontend/package-lock.json ./
# RUN npm ci
# COPY frontend/ ./
# RUN npm run build

# -- Runtime --
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install Python dependencies
COPY backend/pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

# Copy backend code
COPY backend/ ./

# Part 3 will replace this with the built frontend:
# COPY --from=frontend-build /app/frontend/out ./static

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
