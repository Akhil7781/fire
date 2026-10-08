# Deployment Guide: DS08 Operational System

## 1. Local Development Execution (Single Command)
To run the system locally using the embedded SQLite database:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
python -m src.stage8_37.app
```
Access the service at:
- Web Dashboard: `http://localhost:8000/`
- API Documentation: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/health`

---

## 2. Docker & Docker Compose Deployment
To deploy the full containerized stack with PostgreSQL + PostGIS:

```bash
# Navigate to the repository root
docker compose -f docker/docker-compose.yml up --build -d
```

### Container Services:
1. `db`: PostGIS 15 database initialized with `database/schema.sql` on port 5432.
2. `api`: Python 3.10 slim FastAPI container serving inference and static assets on port 8000.

---

## 3. Production Health Monitoring
The container includes a health check running every 30 seconds:
```bash
curl -f http://localhost:8000/health
```
If the model checkpoint or database fails, the endpoint returns an HTTP 500 error.
