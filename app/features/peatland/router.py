import os
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.features.hotspot.service import get_hotspots_from_db
from app.features.peatland.service import (
    get_peatland_geojson_from_db,
    analyze_peatland_hotspots_db,
    analyze_peatland_hotspots_gpd
)

router = APIRouter(prefix="/api/peatland", tags=["Peatland"])

@router.get("")
@router.get("/")
async def get_peatland_geojson(db: AsyncSession = Depends(get_db)):
    """
    Serve Indonesia Peatland GeoJSON vector dataset directly from PostGIS database.
    """
    return await get_peatland_geojson_from_db(db)

@router.post("/hotspot-intersection")
async def analyze_peatland_intersection(
    days: int = Query(30, description="Days filter for hotspots"),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes PostGIS (or GeoPandas + Shapely fallback) Point-in-Polygon spatial join between hotspots and peatlands.
    """
    db_analysis = await analyze_peatland_hotspots_db(db, days)
    if db_analysis:
        return {
            "status": "success",
            "analysis": db_analysis
        }

    res = await get_hotspots_from_db(db=db, days=days, limit=10000)
    features = res.get("data", {}).get("features", [])

    peatland_path = "/app/data/Indonesia_Peat_Lands.geojson"
    if not os.path.exists(peatland_path):
        peatland_path = os.path.join(os.getcwd(), "data/Indonesia_Peat_Lands.geojson")

    analysis = analyze_peatland_hotspots_gpd(features, peatland_path)
    return {
        "status": "success",
        "analysis": analysis
    }
