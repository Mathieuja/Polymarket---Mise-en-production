FROM python:3.11-slim

WORKDIR /app

# Copy shared package first
COPY shared ./shared

# Copy requirements from frontend
COPY app/frontend/requirements.txt .

# Install frontend requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend application
COPY app/frontend .

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit application
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
