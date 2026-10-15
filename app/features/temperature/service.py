from typing import Dict, Any, Optional, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.utils.cache import cache

class TemperatureService:
    @classmethod
    async def get_temperature_grid_from_db(cls, db: AsyncSession, limit: int = 3000) -> Dict[str, Any]:
        """
        Get latest air temperature grid and stats directly from PostGIS database.
        """
        cache_key = f"temperature_grid_{limit}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            query = text("""
                WITH latest AS (
                    SELECT latitude, longitude, suhu_celsius
                    FROM temperature
                    WHERE waktu = (SELECT MAX(waktu) FROM temperature)
                    LIMIT :limit
                )
                SELECT 
                    json_agg(json_build_array(ROUND(latitude::numeric, 2), ROUND(longitude::numeric, 2), ROUND(suhu_celsius::numeric, 1))) as grid,
                    (SELECT count(*) FROM latest) as total_count,
                    (SELECT round(avg(suhu_celsius)::numeric, 1) FROM latest) as avg_val,
                    (SELECT round(min(suhu_celsius)::numeric, 1) FROM latest) as min_val,
                    (SELECT round(max(suhu_celsius)::numeric, 1) FROM latest) as max_val
                FROM latest;
            """)
            result = await db.execute(query.bindparams(limit=limit))
            row = result.first()
            if row and row.grid:
                res = {
                    "status": "success",
                    "total_records": row.total_count or 0,
                    "summary": {
                        "mean_celsius": float(row.avg_val or 25.0),
                        "min_celsius": float(row.min_val or 18.0),
                        "max_celsius": float(row.max_val or 34.0),
                        "unit": "°C"
                    },
                    "data": row.grid
                }
                cache.set(cache_key, res, 3600)
                return res
        except Exception as e:
            print(f"[TemperatureService Error] {e}")

        return {"status": "error", "data": []}

    @classmethod
    async def get_temperature_at_point_from_db(cls, db: AsyncSession, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get nearest air temperature record at specified lat, lon using PostGIS KNN.
        """
        try:
            query = text("""
                SELECT 
                    ROUND(latitude::numeric, 4) as lat,
                    ROUND(longitude::numeric, 4) as lon,
                    ROUND(suhu_celsius::numeric, 1) as suhu,
                    waktu
                FROM temperature
                WHERE waktu = (SELECT MAX(waktu) FROM temperature)
                ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                LIMIT 1;
            """)
            result = await db.execute(query.bindparams(lat=lat, lon=lon))
            row = result.first()
            if row:
                val = float(row.suhu)
                category = "Panas Ekstrem" if val > 32 else ("Hangat" if val >= 26 else "Sejuk")
                return {
                    "status": "success",
                    "target_lat": lat,
                    "target_lon": lon,
                    "nearest_lat": float(row.lat),
                    "nearest_lon": float(row.lon),
                    "temperature_celsius": val,
                    "category": category,
                    "timestamp": str(row.waktu),
                    "unit": "°C"
                }
        except Exception as e:
            print(f"[Temperature Point Error] {e}")

        return {"status": "error", "target_lat": lat, "target_lon": lon}
