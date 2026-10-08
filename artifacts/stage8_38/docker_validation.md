# Stage 8.38 — Docker & Containerization Validation Report

## 1. Overview
The DS08 Operational System provides complete containerization assets under `docker/` allowing single-command deployment via Docker Compose or standalone container execution.

## 2. Container Assets Audited

### `docker/Dockerfile`
- **Base Image:** `python:3.10-slim` (minimal attack surface, standard Debian Bookworm/Bullseye base).
- **System Dependencies:** `build-essential`, `curl` (for healthcheck), `libgomp1` (required by PyTorch OpenMP threading). Cleaned via `rm -rf /var/lib/apt/lists/*`.
- **Application Context:** Copies `requirements.txt`, `src/`, `frontend/`, `models/stage8_36/` (frozen neural model weights, schema, scalers), and reference facility database.
- **Healthcheck:** Configured with `curl -f http://localhost:8000/health || exit 1` (`interval: 30s`, `timeout: 5s`, `retries: 3`).
- **Entrypoint:** `python -m src.stage8_37.app`.

### `docker/docker-compose.yml`
- **Multi-Service Architecture:**
  - `db`: PostgreSQL 15 + PostGIS 3.3 (`postgis/postgis:15-3.3`). Auto-initializes schema from `database/schema.sql`. Includes healthcheck via `pg_isready`.
  - `api`: DS08 FastAPI backend + Leaflet GIS dashboard. Depends on healthy database container. Port mapped to `8000:8000`. Persistent volume mounts for data and audit logs.

## 3. Configuration & Environment Variables

| Variable | Default Value | Description |
|:---|:---|:---|
| `HOST` | `0.0.0.0` | API binding address |
| `PORT` | `8000` | HTTP listening port |
| `DATABASE_URL` | `sqlite:///data/operational.db` or PostgreSQL URI | Storage connection string |
| `PYTHONUNBUFFERED` | `1` | Real-time container log output |

## 4. Verification Checkpoints

1. **Deterministic Frozen Model Loading:**
   - The container copies `models/stage8_36/` into `/app/models/stage8_36`.
   - On container startup, `model_loader.py` validates SHA-256 hash `5bdbfbd503a3c0acbd50caefd2b1c88b5e0190a7176d70a517165814722bcff2` before serving requests.

2. **Causality Protection:**
   - All historical lookups use container-local parquet archives bounded by $t \le t_0 - 7\text{ days}$.
   - No external internet connectivity is required during model inference.

3. **Storage Abstraction:**
   - Container operates cleanly with lightweight internal SQLite (standalone mode) or enterprise PostGIS (production clustered mode).

## 5. Deployment Instructions

### Option A: Standalone Docker Run
```bash
docker build -t ds08-attribution -f docker/Dockerfile .
docker run -p 8000:8000 -v $(pwd)/data:/app/data ds08-attribution
```

### Option B: Production Docker Compose (with PostGIS)
```bash
docker-compose -f docker/docker-compose.yml up -d
```
Dashboard available at `http://localhost:8000/dashboard`.
API documentation available at `http://localhost:8000/docs`.
