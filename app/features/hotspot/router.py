from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.features.hotspot.service import get_hotspots_from_db, get_hotspot_stats_from_db
from app.features.hotspot.sync import sync_nasa_firms_data
from app.features.hotspot.schemas import HotspotApiResponse, HotspotStatsResponse, HotspotSyncResponse

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
    limit: int = Query(20000, description="Max point limit (1-100000)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch NASA FIRMS hotspot Flat Array Matrix from PostGIS database with high performance.
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
        if res.get("status") == "error":
            raise HTTPException(status_code=400, detail=res.get("message", "Error querying hotspots"))
        return res
    except HTTPException:
        raise
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

@router.get("/hotspots/context")
async def get_hotspot_environmental_context(
    lat: float = Query(..., description="Latitude of hotspot"),
    lng: float = Query(..., description="Longitude of hotspot"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get environmental factors (peatland intersection, temperature, soil moisture, rainfall)
    for a specific clicked hotspot point.
    """
    from app.features.hotspot.service import get_environmental_context_at_point
    return await get_environmental_context_at_point(db=db, lat=lat, lng=lng)

@router.post("/hotspots/sync-now", response_model=HotspotSyncResponse)
async def trigger_hotspot_sync(
    sensor: str = Query("VIIRS_SNPP_NRT", description="Sensor type"),
    days: int = Query(5, ge=1, le=5, description="Number of past days to fetch (1-5)")
):
    """
    Manually trigger NASA FIRMS data sync to update local database and invalidate cache.
    """
    try:
        res = await sync_nasa_firms_data(source=sensor, day_range=days)
        if res.get("status") == "error":
            raise HTTPException(status_code=500, detail=res.get("message"))
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute NASA FIRMS sync: {str(e)}")
