# Multi-stage build for worker application
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy shared package FIRST (needed for editable install)
COPY shared /shared

# Copy requirements
WORKDIR /tmp
COPY worker/requirements.txt .

# Install worker requirements
RUN pip install --no-cache-dir --user -r requirements.txt

# Install shared package
RUN pip install --no-cache-dir --user /shared


# Runtime stage
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy virtual environment
COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local/bin:$PATH

# Copy shared package
COPY shared /app/shared

# Copy worker application
COPY worker /app/worker

# Default command: run worker
CMD ["python", "-m", "worker.app.main"]
