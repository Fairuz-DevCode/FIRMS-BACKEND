from typing import Optional
from fastapi import APIRouter, Query
from app.features.land_cover.service import LandCoverService

router = APIRouter(prefix="/api/land-cover", tags=["Land Cover"])

@router.get("/sample")
async def sample_land_cover(
    lat: float = Query(..., description="Latitude coordinate"),
    lon: float = Query(..., description="Longitude coordinate"),
    file: Optional[str] = Query(None, description="Specific GeoTIFF raster file name")
):
    """
    Sample land cover class at given coordinates (lat, lon) using GeoTIFF rasters.
    """
    return LandCoverService.sample_land_cover(lat=lat, lon=lon, geotiff_path=file)

@router.get("/rasters")
async def list_rasters():
    """
    List available GeoTIFF land cover raster files.
    """
    return {
        "status": "success",
        "total": len(LandCoverService.get_available_rasters()),
        "rasters": LandCoverService.get_available_rasters()
    }
