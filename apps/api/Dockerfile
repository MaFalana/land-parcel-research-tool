FROM python:3.12-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first for better caching
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy only necessary application files
COPY main.py .
COPY worker.py .
COPY scheduler.py .
COPY routes/ ./routes/
COPY storage/ ./storage/
COPY models/ ./models/
COPY utils/ ./utils/
COPY scrapers/ ./scrapers/
COPY auth/ ./auth/
COPY config/ ./config/

# Create necessary directories
RUN mkdir -p assets

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Run uvicorn with proper configuration for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]