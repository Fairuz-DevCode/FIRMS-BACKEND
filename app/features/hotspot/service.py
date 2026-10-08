import datetime
import json
import random
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func, text, cast, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.hotspot.models import Hotspot
from app.core.utils.cache import cache

async def get_hotspots_from_db(
    db: AsyncSession,
    sensor: str = "VIIRS_SNPP_NRT",
    days: Optional[int] = 30,
    date: Optional[str] = None,
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    confidence: Optional[str] = None,
    minBrightness: Optional[float] = None,
    minFrp: Optional[float] = None,
    limit: int = 20000
) -> Dict[str, Any]:
    max_limit = min(max(int(limit or 20000), 1), 100000)
    cache_key = f"db_hotspots_{json.dumps({'sensor': sensor, 'days': days, 'date': date, 'startDate': startDate, 'endDate': endDate, 'confidence': confidence, 'minBrightness': minBrightness, 'minFrp': minFrp, 'limit': max_limit})}"

    cached = cache.get(cache_key)
    if cached:
        cached_res = dict(cached)
        cached_res["source"] = "cache"
        return cached_res

    try:
        query = select(Hotspot)

        # Date Filtering
        if startDate and endDate:
            try:
                s_dt = datetime.datetime.strptime(startDate, "%Y-%m-%d").date()
                e_dt = datetime.datetime.strptime(endDate, "%Y-%m-%d").date()
                query = query.where(Hotspot.acq_date.between(s_dt, e_dt))
            except ValueError:
                pass
        elif date:
            try:
                dt = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                query = query.where(Hotspot.acq_date == dt)
            except ValueError:
                pass
        elif days and int(days) > 0:
            # Get latest acq_date from DB
            subq = select(func.max(Hotspot.acq_date)).scalar_subquery()
            query = query.where(Hotspot.acq_date >= subq - text(f"INTERVAL '{int(days)} days'"))

        # Confidence Filtering
        if confidence and confidence.lower() != "all":
            conf_val = confidence.lower()
            if conf_val in ["h", "high"]:
                query = query.where(
                    (Hotspot.confidence == "h") | 
                    (Hotspot.confidence == "high") | 
                    (Hotspot.confidence == "100") | 
                    (cast(Hotspot.confidence, Integer) >= 80)
                )
            elif conf_val in ["n", "nominal"]:
                query = query.where(
                    (Hotspot.confidence == "n") | 
                    (Hotspot.confidence == "nominal") | 
                    ((cast(Hotspot.confidence, Integer) >= 30) & (cast(Hotspot.confidence, Integer) < 80))
                )
            elif conf_val in ["l", "low"]:
                query = query.where(
                    (Hotspot.confidence == "l") | 
                    (Hotspot.confidence == "low") | 
                    ((cast(Hotspot.confidence, Integer) > 0) & (cast(Hotspot.confidence, Integer) < 30))
                )
            else:
                query = query.where(Hotspot.confidence == confidence)

        # Brightness & FRP filtering
        if minBrightness is not None:
            query = query.where(Hotspot.brightness >= float(minBrightness))
        if minFrp is not None:
            query = query.where(Hotspot.frp >= float(minFrp))

        query = query.order_by(Hotspot.acq_date.desc(), Hotspot.id.desc()).limit(max_limit)

        result = await db.execute(query)
        hotspots = result.scalars().all()

        if not hotspots:
            # Fallback if DB table has no matching rows
            return get_fallback_hotspots()

        features = [h.to_geojson_feature() for h in hotspots]
        response_data = {
            "status": "success",
            "count": len(features),
            "totalCount": len(features),
            "source": "postgresql_postgis_firms_db",
            "data": {
                "type": "FeatureCollection",
                "features": features
            }
        }

        cache.set(cache_key, response_data, 60)
        return response_data

    except Exception as e:
        print(f"[HotspotService Warning] Database query failed: {e}. Falling back to simulation.")
        return get_fallback_hotspots()

async def get_hotspot_stats_from_db(db: AsyncSession) -> Dict[str, Any]:
    try:
        summary_query = select(
            func.count(Hotspot.id).label("total_hotspots"),
            func.min(Hotspot.acq_date).label("min_date"),
            func.max(Hotspot.acq_date).label("max_date"),
            func.avg(Hotspot.brightness).label("avg_brightness"),
            func.avg(Hotspot.frp).label("avg_frp"),
            func.max(Hotspot.frp).label("max_frp")
        )
        summary_res = (await db.execute(summary_query)).first()

        conf_query = select(
            Hotspot.confidence,
            func.count(Hotspot.id).label("count")
        ).group_by(Hotspot.confidence)
        conf_res = (await db.execute(conf_query)).all()

        timeline_query = select(
            Hotspot.acq_date,
            func.count(Hotspot.id).label("count")
        ).group_by(Hotspot.acq_date).order_by(Hotspot.acq_date.desc()).limit(14)
        timeline_res = (await db.execute(timeline_query)).all()

        summary_dict = {
            "total_hotspots": summary_res.total_hotspots or 0 if summary_res else 0,
            "min_date": str(summary_res.min_date) if summary_res and summary_res.min_date else None,
            "max_date": str(summary_res.max_date) if summary_res and summary_res.max_date else None,
            "avg_brightness": round(float(summary_res.avg_brightness or 0.0), 2) if summary_res else 0.0,
            "avg_frp": round(float(summary_res.avg_frp or 0.0), 2) if summary_res else 0.0,
            "max_frp": round(float(summary_res.max_frp or 0.0), 2) if summary_res else 0.0,
        }

        confidence_breakdown = [
            {"confidence": row.confidence or "n/a", "count": row.count}
            for row in conf_res
        ]

        timeline = [
            {"date": str(row.acq_date), "count": row.count}
            for row in timeline_res
        ]

        return {
            "status": "success",
            "summary": summary_dict,
            "confidenceBreakdown": confidence_breakdown,
            "timeline": timeline
        }
    except Exception as e:
        print(f"[HotspotStats Warning] {e}")
        return {
            "status": "error",
            "summary": {
                "total_hotspots": 0,
                "min_date": None,
                "max_date": None,
                "avg_brightness": 0.0,
                "avg_frp": 0.0,
                "max_frp": 0.0
            },
            "confidenceBreakdown": [],
            "timeline": [],
            "error": str(e)
        }

def get_fallback_hotspots() -> Dict[str, Any]:
    clusters = [
        {"baseLat": 1.45, "baseLon": 101.40},
        {"baseLat": 0.82, "baseLon": 102.15},
        {"baseLat": -2.95, "baseLon": 104.75},
        {"baseLat": -0.15, "baseLon": 109.35},
        {"baseLat": -2.20, "baseLon": 113.90},
        {"baseLat": -2.80, "baseLon": 114.25},
        {"baseLat": -6.80, "baseLon": 139.80}
    ]

    features = []
    base_date = datetime.date.today()

    for c_idx, cluster in enumerate(clusters):
        for i in range(25):
            lat = round(cluster["baseLat"] + (random.random() - 0.5) * 0.5, 4)
            lon = round(cluster["baseLon"] + (random.random() - 0.5) * 0.5, 4)
            d = base_date - datetime.timedelta(days=(i % 10))
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                },
                "properties": {
                    "id": c_idx * 100 + i,
                    "latitude": lat,
                    "longitude": lon,
                    "brightness": round(310.0 + random.random() * 80.0, 1),
                    "confidence": "h" if i % 3 == 0 else ("n" if i % 3 == 1 else "l"),
                    "acq_date": str(d),
                    "acq_time": f"{random.randint(0, 23):02d}30",
                    "frp": round(10.0 + random.random() * 120.0, 1)
                }
            })

    return {
        "status": "success",
        "count": len(features),
        "totalCount": len(features),
        "source": "fallback_simulated",
        "data": {
            "type": "FeatureCollection",
            "features": features
        }
    }
