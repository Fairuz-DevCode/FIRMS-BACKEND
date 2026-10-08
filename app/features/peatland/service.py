import os
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from shapely.geometry import Point
import geopandas as gpd
from app.core.utils.cache import cache
from app.features.hotspot.service import get_hotspots_from_db

async def get_peatland_geojson_from_db(db: AsyncSession) -> Dict[str, Any]:
    cache_key = "peatland_geojson_featurecollection"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        query = text("""
            SELECT jsonb_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(
                    jsonb_agg(
                        jsonb_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(geom)::jsonb,
                            'properties', jsonb_build_object(
                                'ogc_fid', ogc_fid,
                                'objectid', objectid,
                                'layer_revi', layer_revi,
                                'shape_length', shape_length,
                                'shape_area', shape_area
                            )
                        )
                    ),
                    '[]'::jsonb
                )
            ) AS geojson
            FROM peatlands;
        """)
        result = await db.execute(query)
        geojson = result.scalar()

        if geojson and isinstance(geojson, dict):
            cache.set(cache_key, geojson, 300)
            return geojson

        return {"type": "FeatureCollection", "features": []}
    except Exception as e:
        print(f"[PeatlandService Warning] PostGIS query failed: {e}")
        return {"type": "FeatureCollection", "features": []}

async def analyze_peatland_hotspots_db(db: AsyncSession, days: int = 30) -> Optional[Dict[str, Any]]:
    """
    Executes high-performance PostGIS Spatial Join (ST_Intersects / GiST Index)
    between Hotspots points and Peatlands polygons directly in the database.
    """
    try:
        query = text("""
            WITH recent_hotspots AS (
                SELECT h.id, h.latitude, h.longitude, h.brightness, h.frp, h.acq_date::text, h.geom
                FROM hotspots h
                WHERE h.acq_date >= (SELECT COALESCE(MAX(acq_date), CURRENT_DATE) FROM hotspots) - (INTERVAL '1 day' * :days)
            ),
            joined AS (
                SELECT DISTINCT h.id, h.latitude, h.longitude, h.brightness, h.frp, h.acq_date
                FROM recent_hotspots h
                JOIN peatlands p ON ST_Intersects(h.geom, p.geom)
            )
            SELECT
                (SELECT COUNT(*) FROM recent_hotspots) AS total_hotspots,
                (SELECT COUNT(*) FROM joined) AS hotspots_in_peatland,
                COALESCE(
                    (SELECT json_agg(j) FROM joined j WHERE j.frp > 50),
                    '[]'::json
                ) AS high_risk;
        """)
        result = await db.execute(query.bindparams(days=days))
        row = result.first()
        if row and row.total_hotspots > 0:
            total = row.total_hotspots or 0
            in_peatland = row.hotspots_in_peatland or 0
            pct = round((in_peatland / total * 100.0), 2) if total > 0 else 0.0
            high_risk = row.high_risk if isinstance(row.high_risk, list) else []
            return {
                "total_hotspots": total,
                "hotspots_in_peatland": in_peatland,
                "percentage_in_peatland": pct,
                "high_risk_hotspots": high_risk[:50],
                "source": "postgis_spatial_index"
            }
    except Exception as e:
        print(f"[PeatlandService PostGIS Warning] {e}")
    return None

def analyze_peatland_hotspots_gpd(hotspot_features: List[Dict[str, Any]], peatland_geojson_path: str) -> Dict[str, Any]:
    """
    Fallback using GeoPandas & Shapely to perform Spatial Intersection (Point-in-Polygon).
    """
    if not hotspot_features:
        return {
            "total_hotspots": 0,
            "hotspots_in_peatland": 0,
            "percentage_in_peatland": 0.0,
            "high_risk_hotspots": []
        }

    records = []
    for feat in hotspot_features:
        props = feat.get("properties", {})
        coords = feat.get("geometry", {}).get("coordinates", [0, 0])
        pt = Point(coords[0], coords[1])
        records.append({
            "geometry": pt,
            "id": props.get("id"),
            "latitude": props.get("latitude"),
            "longitude": props.get("longitude"),
            "brightness": props.get("brightness", 0.0),
            "frp": props.get("frp", 0.0),
            "confidence": props.get("confidence", "n/a"),
            "acq_date": props.get("acq_date")
        })

    hotspots_gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
    in_peatland_count = 0
    high_risk = []

    if os.path.exists(peatland_geojson_path):
        try:
            peatland_gdf = gpd.read_file(peatland_geojson_path)
            joined = gpd.sjoin(hotspots_gdf, peatland_gdf, how="inner", predicate="within")
            in_peatland_count = len(joined)

            high_risk_gdf = joined[joined["frp"] > 50]
            high_risk = high_risk_gdf[["id", "latitude", "longitude", "brightness", "frp", "acq_date"]].to_dict(orient="records")
        except Exception as e:
            print(f"[PeatlandService GeoPandas Warning] {e}")

    total = len(hotspots_gdf)
    pct = round((in_peatland_count / total * 100.0), 2) if total > 0 else 0.0

    return {
        "total_hotspots": total,
        "hotspots_in_peatland": in_peatland_count,
        "percentage_in_peatland": pct,
        "high_risk_hotspots": high_risk[:50],
        "source": "geopandas_fallback"
    }
