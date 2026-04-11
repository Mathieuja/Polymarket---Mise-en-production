# Multi-stage build for worker application
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory for build
WORKDIR /tmp

# Copy shared package to build context
COPY shared ./shared

# Copy requirements
COPY worker/requirements.txt .

# Install worker requirements (including ./shared)
RUN pip install --no-cache-dir --user -r requirements.txt


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
