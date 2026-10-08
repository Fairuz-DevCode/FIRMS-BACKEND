from fastapi import APIRouter, Query
from app.features.rainfall.service import RainfallService

router = APIRouter(prefix="/api/rainfall", tags=["Rainfall (Curah Hujan)"])

@router.get("")
@router.get("/")
async def get_rainfall_data(
    limit: int = Query(1000, ge=1, le=10000, description="Max grid sample points to return")
):
    """
    Get ERA5 Rainfall / Precipitation (Curah Hujan) dataset summary and grid points.
    """
    return RainfallService.get_rainfall_stats(limit=limit)

@router.get("/sample")
async def sample_rainfall(
    lat: float = Query(..., description="Latitude coordinate"),
    lon: float = Query(..., description="Longitude coordinate")
):
    """
    Get nearest rainfall record at specific lat, lon coordinates.
    """
    return RainfallService.get_rainfall_at_point(lat=lat, lon=lon)
