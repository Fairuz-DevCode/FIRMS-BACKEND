from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.features.hotspot.service import get_hotspots_from_db, get_hotspot_stats_from_db
from app.features.hotspot.schemas import HotspotApiResponse, HotspotStatsResponse

router = APIRouter(prefix="/api", tags=["Hotspots"])

@router.get("/hotspots", response_model=HotspotApiResponse)
async def read_hotspots(
    sensor: str = Query("VIIRS_SNPP_NRT", description="Sensor type"),
    days: Optional[int] = Query(None, description="Filter by number of past days"),
    date: Optional[str] = Query(None, description="Exact acquisition date YYYY-MM-DD"),
    startDate: Optional[str] = Query(None, description="Start date range YYYY-MM-DD"),
    endDate: Optional[str] = Query(None, description="End date range YYYY-MM-DD"),
    confidence: Optional[str] = Query(None, description="Confidence level filter"),
    minBrightness: Optional[float] = Query(None, description="Minimum brightness value"),
    minFrp: Optional[float] = Query(None, description="Minimum Fire Radiative Power (FRP)"),
    limit: int = Query(20000, description="Max feature limit (1-100000)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch NASA FIRMS hotspot GeoJSON feature collection from PostGIS database.
    """
    try:
        res = await get_hotspots_from_db(
            db=db,
            sensor=sensor,
            days=days,
            date=date,
            startDate=startDate,
            endDate=endDate,
            confidence=confidence,
            minBrightness=minBrightness,
            minFrp=minFrp,
            limit=limit
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch hotspot data: {str(e)}")

@router.get("/hotspots/stats", response_model=HotspotStatsResponse)
async def read_hotspot_stats(db: AsyncSession = Depends(get_db)):
    """
    Fetch aggregate statistics and analytical summaries for NASA FIRMS hotspots.
    """
    try:
        return await get_hotspot_stats_from_db(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute hotspot statistics: {str(e)}")
