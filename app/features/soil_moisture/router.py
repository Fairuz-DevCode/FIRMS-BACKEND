from fastapi import APIRouter, Query
from app.features.soil_moisture.service import SoilMoistureService

router = APIRouter(prefix="/api/soil-moisture", tags=["Soil Moisture (Kelembaban Tanah)"])

@router.get("")
@router.get("/")
async def get_soil_moisture_data(
    limit: int = Query(1000, ge=1, le=10000, description="Max grid sample points to return")
):
    """
    Get ERA5 Soil Moisture (Kelembaban Tanah) dataset summary and grid points.
    """
    return SoilMoistureService.get_soil_moisture_stats(limit=limit)

@router.get("/sample")
async def sample_soil_moisture(
    lat: float = Query(..., description="Latitude coordinate"),
    lon: float = Query(..., description="Longitude coordinate")
):
    """
    Get nearest soil moisture record at specific lat, lon coordinates.
    """
    return SoilMoistureService.get_soil_moisture_at_point(lat=lat, lon=lon)
