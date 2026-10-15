from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.features.rainfall.service import RainfallService

router = APIRouter(prefix="/api/rainfall", tags=["Rainfall (Curah Hujan)"])

@router.get("")
@router.get("/")
async def get_rainfall_data(
    limit: int = Query(3000, ge=1, le=10000, description="Max grid sample points to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ERA5 Rainfall dataset grid points directly from PostGIS database.
    """
    return await RainfallService.get_rainfall_grid_from_db(db=db, limit=limit)

@router.get("/sample")
async def sample_rainfall(
    lat: float = Query(..., description="Latitude coordinate"),
    lon: float = Query(..., description="Longitude coordinate"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get nearest rainfall record at specific lat, lon coordinates.
    """
    return await RainfallService.get_rainfall_at_point_from_db(db=db, lat=lat, lon=lon)
