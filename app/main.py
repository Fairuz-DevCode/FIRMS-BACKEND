import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.core.database import async_engine, Base
from app.core.router import router as core_router
from app.features import (
    hotspot_router,
    peatland_router,
    land_cover_router,
    temperature_router,
    rainfall_router,
    soil_moisture_router
)

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
    
    yield

    # Shutdown
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
