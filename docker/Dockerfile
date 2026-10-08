# Stage 8.37 Production Inference Container
# Python 3.10 Slim with PyTorch CPU & FastAPI

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (build-essential, curl, libgomp1 for PyTorch)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code, frontend, and frozen model packages
COPY src /app/src
COPY frontend /app/frontend
COPY models/stage8_36 /app/models/stage8_36
COPY data/reference/ds08/manifests/stage8_25/industrial_facility_database.json /app/data/reference/ds08/manifests/stage8_25/industrial_facility_database.json

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "src.stage8_37.app"]
