# Multi-stage build optimization: separate layer for dependencies
# This allows Docker to cache the dependency layer independently from the application code
FROM python:3.11-slim as builder

# Set environment variables to prevent Python from writing bytecode and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install only necessary system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to isolate dependencies
WORKDIR /tmp
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Final stage: lean runtime image
FROM python:3.11-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: prevent .pyc file creation (reduces image size)
# PYTHONUNBUFFERED: ensure stdout/stderr are sent directly to logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory for the application
WORKDIR /app

# Copy the virtual environment from builder stage
# This significantly reduces the final image size by excluding build dependencies
COPY --from=builder /root/.local /root/.local

# Update PATH to use the virtual environment
ENV PATH=/root/.local/bin:$PATH

# Copy the application code
# This layer is cached separately from dependencies, enabling faster rebuilds during development
COPY . .

# Expose the port used by the FastAPI backend
EXPOSE 8000

# Health check to monitor container health
# This allows orchestrators to restart unhealthy containers
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Default command: run uvicorn application server
# The app will bind to 0.0.0.0:8000 to accept connections from other containers
CMD ["uvicorn", "app.backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
