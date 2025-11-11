FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with increased timeout and retries
ENV PIP_DEFAULT_TIMEOUT=300
ENV PIP_RETRIES=5
RUN pip install --no-cache-dir -r requirements.txt || \
    (sleep 10 && pip install --no-cache-dir -r requirements.txt)

# Copy application code and data
COPY src/ ./src/
COPY data/ ./data/

# Set the container's entrypoint to run the application
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
