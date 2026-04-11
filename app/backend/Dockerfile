# Multi-stage build for optimized Docker image
# Builder stage: install dependencies
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies needed for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared package FIRST
COPY shared /shared

# Copy requirements from backend
WORKDIR /tmp
COPY app/backend/requirements.txt .

# Install backend requirements
RUN pip install --no-cache-dir --user -r requirements.txt

# Install shared package
RUN pip install --no-cache-dir --user /shared


# Final stage: lean runtime image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

# Copy shared package
COPY shared /app/shared

# Copy backend application
COPY app/backend /app/app/backend

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Start uvicorn server
CMD ["uvicorn", "app.backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
