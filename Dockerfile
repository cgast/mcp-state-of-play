FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY register_server.py ./register_server.py

# Create logs directory
RUN mkdir -p logs

# Expose ports
EXPOSE 3000 8000

# Set default mode to web server
ENV RUN_MODE=web

# Run the application
CMD ["python", "-m", "src.main"]