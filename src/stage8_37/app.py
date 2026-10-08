"""Stage 8.37 Production Application Entrypoint.

Starts the FastAPI operational backend and web dashboard.
Run directly with:
    python -m src.stage8_37.app
or
    python src/stage8_37/app.py
"""

import logging
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import uvicorn

load_dotenv()

from src.stage8_37.api.routes import router as api_router
from src.live.routes import router as live_router
from src.live.scheduler import get_scheduler
from src.stage8_37.database.db import get_db
from src.stage8_37.inference.model_loader import get_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("d:/DATA PREPROCESSING")
FRONTEND_DIR = PROJECT_ROOT / "frontend"

def create_app() -> FastAPI:
    """Builds and configures the production FastAPI instance."""
    app = FastAPI(
        title="DS08 Operational Thermal-Source Attribution System",
        description="Real-Time Causal 4-Class Attribution of Satellite Thermal Anomalies (NASA FIRMS)",
        version="8.42.0"
    )

    # Initialize DB, Model, and Live Scheduler on startup
    @app.on_event("startup")
    def on_startup():
        logger.info("Initializing operational database...")
        get_db()
        logger.info("Pre-warming frozen neural model...")
        get_model()
        
        firms_key = os.getenv("FIRMS_MAP_KEY", "").strip()
        if firms_key:
            logger.info("FIRMS_MAP_KEY detected. Starting automatic 10-minute live NRT poller...")
            scheduler = get_scheduler()
            scheduler.start()
        else:
            logger.warning("FIRMS_MAP_KEY not configured. Live NRT automated polling is paused.")

        logger.info("Operational system ready.")

    @app.on_event("shutdown")
    def on_shutdown():
        logger.info("Shutting down live scheduler...")
        get_scheduler().stop()

    # Mount API routes
    app.include_router(api_router)
    app.include_router(live_router)

    # Mount static frontend assets
    if FRONTEND_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

        @app.get("/")
        @app.get("/dashboard")
        def serve_dashboard():
            return FileResponse(str(FRONTEND_DIR / "index.html"))

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    logger.info(f"Starting DS08 Operational Server on http://{host}:{port}")
    uvicorn.run("src.stage8_37.app:app", host=host, port=port, reload=False)
