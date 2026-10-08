# Features package
from app.features.hotspot.router import router as hotspot_router
from app.features.peatland.router import router as peatland_router
from app.features.land_cover.router import router as land_cover_router
from app.features.temperature.router import router as temperature_router
from app.features.rainfall.router import router as rainfall_router
from app.features.soil_moisture.router import router as soil_moisture_router

__all__ = [
    "hotspot_router",
    "peatland_router",
    "land_cover_router",
    "temperature_router",
    "rainfall_router",
    "soil_moisture_router",
]
