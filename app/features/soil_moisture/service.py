from typing import Dict, Any, Optional, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.utils.cache import cache

class SoilMoistureService:
    @classmethod
    async def get_soil_moisture_grid_from_db(cls, db: AsyncSession, limit: int = 3000) -> Dict[str, Any]:
        """
        Get latest soil moisture grid and stats directly from PostGIS database.
        """
        cache_key = f"soil_moisture_grid_{limit}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            query = text("""
                WITH latest AS (
                    SELECT latitude, longitude, soil_moisture
                    FROM soil_moisture_data
                    WHERE waktu = (SELECT MAX(waktu) FROM soil_moisture_data)
                    LIMIT :limit
                )
                SELECT 
                    json_agg(json_build_array(ROUND(latitude::numeric, 2), ROUND(longitude::numeric, 2), ROUND(soil_moisture::numeric, 3))) as grid,
                    (SELECT count(*) FROM latest) as total_count,
                    (SELECT round(avg(soil_moisture)::numeric, 3) FROM latest) as avg_val,
                    (SELECT round(min(soil_moisture)::numeric, 3) FROM latest) as min_val,
                    (SELECT round(max(soil_moisture)::numeric, 3) FROM latest) as max_val
                FROM latest;
            """)
            result = await db.execute(query.bindparams(limit=limit))
            row = result.first()
            if row and row.grid:
                res = {
                    "status": "success",
                    "total_records": row.total_count or 0,
                    "summary": {
                        "mean_soil_moisture": float(row.avg_val or 0.28),
                        "min_soil_moisture": float(row.min_val or 0.05),
                        "max_soil_moisture": float(row.max_val or 0.55),
                        "unit": "m³/m³"
                    },
                    "data": row.grid
                }
                cache.set(cache_key, res, 3600)
                return res
        except Exception as e:
            print(f"[SoilMoistureService Error] {e}")

        return {"status": "error", "data": []}

    @classmethod
    async def get_soil_moisture_at_point_from_db(cls, db: AsyncSession, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get nearest soil moisture record at specified lat, lon using PostGIS KNN.
        """
        try:
            query = text("""
                SELECT 
                    ROUND(latitude::numeric, 4) as lat,
                    ROUND(longitude::numeric, 4) as lon,
                    ROUND(soil_moisture::numeric, 3) as moisture,
                    waktu
                FROM soil_moisture_data
                WHERE waktu = (SELECT MAX(waktu) FROM soil_moisture_data)
                ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                LIMIT 1;
            """)
            result = await db.execute(query.bindparams(lat=lat, lon=lon))
            row = result.first()
            if row:
                val = float(row.moisture)
                category = "Sangat Kering (Kritis)" if val < 0.2 else ("Cukup Lembab" if val <= 0.35 else "Lembab / Jenuh Air")
                return {
                    "status": "success",
                    "target_lat": lat,
                    "target_lon": lon,
                    "nearest_lat": float(row.lat),
                    "nearest_lon": float(row.lon),
                    "soil_moisture": val,
                    "category": category,
                    "timestamp": str(row.waktu),
                    "unit": "m³/m³"
                }
        except Exception as e:
            print(f"[SoilMoisture Point Error] {e}")

        return {"status": "error", "target_lat": lat, "target_lon": lon}
