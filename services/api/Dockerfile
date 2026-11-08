# Multi-stage optimized Python 3.11-slim container for Fraud Detection Service
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install minimal OS dependencies for compilation and healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy models, features, datasets, microservice code, and compiled frontend SPA
COPY models/ /app/models/
COPY features/ /app/features/
COPY data/ /app/data/
COPY services/ /app/services/
COPY frontend/dist/ /app/frontend/dist/

# Set environment variables for runtime module resolution
ENV PYTHONPATH="/app"
ENV FEAST_REPO_PATH="/app/features"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Container liveness health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
