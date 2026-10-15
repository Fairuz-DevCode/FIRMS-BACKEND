from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.features.temperature.service import TemperatureService

router = APIRouter(prefix="/api/temperature", tags=["Temperature (Suhu Udara)"])

@router.get("")
@router.get("/")
async def get_temperature_data(
    limit: int = Query(3000, ge=1, le=10000, description="Max grid sample points to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ERA5 Air Temperature dataset grid points directly from PostGIS database.
    """
    return await TemperatureService.get_temperature_grid_from_db(db=db, limit=limit)

@router.get("/sample")
async def sample_temperature(
    lat: float = Query(..., description="Latitude coordinate"),
    lon: float = Query(..., description="Longitude coordinate"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get nearest temperature record at specific lat, lon coordinates.
    """
    return await TemperatureService.get_temperature_at_point_from_db(db=db, lat=lat, lon=lon)
