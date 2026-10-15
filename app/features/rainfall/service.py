from typing import Dict, Any, Optional, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.utils.cache import cache

class RainfallService:
    @classmethod
    async def get_rainfall_grid_from_db(cls, db: AsyncSession, limit: int = 3000) -> Dict[str, Any]:
        """
        Get latest rainfall grid and stats directly from PostGIS database.
        """
        cache_key = f"rainfall_grid_{limit}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            query = text("""
                WITH latest AS (
                    SELECT latitude, longitude, curah_hujan_mm
                    FROM rainfall_data
                    WHERE waktu = (SELECT MAX(waktu) FROM rainfall_data)
                    LIMIT :limit
                )
                SELECT 
                    json_agg(json_build_array(ROUND(latitude::numeric, 2), ROUND(longitude::numeric, 2), ROUND(curah_hujan_mm::numeric, 1))) as grid,
                    (SELECT count(*) FROM latest) as total_count,
                    (SELECT round(avg(curah_hujan_mm)::numeric, 1) FROM latest) as avg_val,
                    (SELECT round(min(curah_hujan_mm)::numeric, 1) FROM latest) as min_val,
                    (SELECT round(max(curah_hujan_mm)::numeric, 1) FROM latest) as max_val
                FROM latest;
            """)
            result = await db.execute(query.bindparams(limit=limit))
            row = result.first()
            if row and row.grid:
                res = {
                    "status": "success",
                    "total_records": row.total_count or 0,
                    "summary": {
                        "mean_rainfall_mm": float(row.avg_val or 3.2),
                        "min_rainfall_mm": float(row.min_val or 0.0),
                        "max_rainfall_mm": float(row.max_val or 25.0),
                        "unit": "mm"
                    },
                    "data": row.grid
                }
                cache.set(cache_key, res, 3600)
                return res
        except Exception as e:
            print(f"[RainfallService Error] {e}")

        return {"status": "error", "data": []}

    @classmethod
    async def get_rainfall_at_point_from_db(cls, db: AsyncSession, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get nearest rainfall record at specified lat, lon using PostGIS KNN.
        """
        try:
            query = text("""
                SELECT 
                    ROUND(latitude::numeric, 4) as lat,
                    ROUND(longitude::numeric, 4) as lon,
                    ROUND(curah_hujan_mm::numeric, 1) as curah_hujan,
                    waktu
                FROM rainfall_data
                WHERE waktu = (SELECT MAX(waktu) FROM rainfall_data)
                ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                LIMIT 1;
            """)
            result = await db.execute(query.bindparams(lat=lat, lon=lon))
            row = result.first()
            if row:
                val = float(row.curah_hujan)
                category = "Kering / Sangat Ringan" if val < 5 else ("Hujan Sedang" if val <= 20 else "Hujan Lebat")
                return {
                    "status": "success",
                    "target_lat": lat,
                    "target_lon": lon,
                    "nearest_lat": float(row.lat),
                    "nearest_lon": float(row.lon),
                    "rainfall_mm": val,
                    "category": category,
                    "timestamp": str(row.waktu),
                    "unit": "mm"
                }
        except Exception as e:
            print(f"[Rainfall Point Error] {e}")

        return {"status": "error", "target_lat": lat, "target_lon": lon}
