from fastapi import APIRouter, Query
from app.features.temperature.service import TemperatureService

router = APIRouter(prefix="/api/temperature", tags=["Temperature (Suhu Udara)"])

@router.get("")
@router.get("/")
async def get_temperature_data(
    limit: int = Query(1000, ge=1, le=10000, description="Max grid sample points to return")
):
    """
    Get ERA5 Air Temperature (Suhu Udara) dataset summary and grid points.
    """
    return TemperatureService.get_temperature_stats(limit=limit)

@router.get("/sample")
async def sample_temperature(
    lat: float = Query(..., description="Latitude coordinate"),
    lon: float = Query(..., description="Longitude coordinate")
):
    """
    Get nearest temperature record at specific lat, lon coordinates.
    """
    return TemperatureService.get_temperature_at_point(lat=lat, lon=lon)
