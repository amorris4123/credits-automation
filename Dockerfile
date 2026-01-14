# Multi-stage build for efficient image
FROM python:3.9-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY docker-requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r docker-requirements.txt

# Copy application code
COPY src/ ./src/
COPY run_bot.py .
COPY "Verify - Credit Recommendation.ipynb" .

# Create directories for runtime
RUN mkdir -p /app/data/outputs /app/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Run as non-root user for security
RUN useradd -m -u 1000 creditbot && \
    chown -R creditbot:creditbot /app
USER creditbot

# Health check (optional - checks if Python can run)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)"

# Entry point
CMD ["python3", "run_bot.py"]
