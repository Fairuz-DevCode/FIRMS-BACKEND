# Features package
from app.features.hotspot.models import Hotspot
from app.features.peatland.models import Peatland
from app.features.temperature.models import Temperature
from app.features.rainfall.models import Rainfall
from app.features.soil_moisture.models import SoilMoisture

from app.features.hotspot.router import router as hotspot_router
from app.features.peatland.router import router as peatland_router
from app.features.land_cover.router import router as land_cover_router
from app.features.temperature.router import router as temperature_router
from app.features.rainfall.router import router as rainfall_router
from app.features.soil_moisture.router import router as soil_moisture_router

__all__ = [
    "Hotspot",
    "Peatland",
    "Temperature",
    "Rainfall",
    "SoilMoisture",
    "hotspot_router",
    "peatland_router",
    "land_cover_router",
    "temperature_router",
    "rainfall_router",
    "soil_moisture_router",
]
