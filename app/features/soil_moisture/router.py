from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.features.soil_moisture.service import SoilMoistureService

router = APIRouter(prefix="/api/soil-moisture", tags=["Soil Moisture (Kelembaban Tanah)"])

@router.get("")
@router.get("/")
async def get_soil_moisture_data(
    limit: int = Query(3000, ge=1, le=10000, description="Max grid sample points to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ERA5 Soil Moisture dataset grid points directly from PostGIS database.
    """
    return await SoilMoistureService.get_soil_moisture_grid_from_db(db=db, limit=limit)

@router.get("/sample")
async def sample_soil_moisture(
    lat: float = Query(..., description="Latitude coordinate"),
    lon: float = Query(..., description="Longitude coordinate"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get nearest soil moisture record at specific lat, lon coordinates.
    """
    return await SoilMoistureService.get_soil_moisture_at_point_from_db(db=db, lat=lat, lon=lon)
