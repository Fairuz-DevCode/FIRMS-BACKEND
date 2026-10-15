import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import async_engine, Base
from app.core.router import router as core_router
from app.features.hotspot.sync import sync_nasa_firms_data
from app.features import (
    hotspot_router,
    peatland_router,
    land_cover_router,
    temperature_router,
    rainfall_router,
    soil_moisture_router
)

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure PostGIS extension and database tables exist
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database connection & PostGIS tables initialized successfully.")
    except Exception as e:
        print(f"⚠️ Startup Warning: Database initialization deferred or waiting for container: {e}")
    
    # Start APScheduler for FIRMS sync (twice a day: 00:00 and 12:00)
    try:
        scheduler.add_job(
            sync_nasa_firms_data,
            CronTrigger(hour="0,12", minute="0"),
            id="nasa_firms_sync_job",
            replace_existing=True
        )
        scheduler.start()
        print("⏰ [Scheduler] APScheduler started for NASA FIRMS sync (scheduled daily at 00:00 & 12:00).")
    except Exception as e:
        print(f"⚠️ [Scheduler Warning] Failed to start APScheduler: {e}")

    yield

    # Shutdown scheduler & database engine
    try:
        scheduler.shutdown()
        print("🛑 [Scheduler] APScheduler shut down gracefully.")
    except Exception as e:
        print(f"⚠️ [Scheduler Warning] Exception during scheduler shutdown: {e}")

    await async_engine.dispose()

app = FastAPI(
    title="NASA FIRMS Hotspot & Climate WebGIS API",
    description="Python FastAPI backend for Hotspots, Peatlands, Land Cover, Temperature, Rainfall & Soil Moisture.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(core_router)
app.include_router(hotspot_router)
app.include_router(peatland_router)
app.include_router(land_cover_router)
app.include_router(temperature_router)
app.include_router(rainfall_router)
app.include_router(soil_moisture_router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
