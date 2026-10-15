import datetime
import hashlib
import json
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func, cast, Integer, case, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.hotspot.models import Hotspot
from app.core.utils.cache import cache

# Default cache TTL: 12 hours (43,200 seconds) for long-duration read caching
DEFAULT_CACHE_TTL = 43200

COLUMNS_HEADER = ["lat", "lng", "brightness", "frp", "confidence", "acq_date", "acq_time"]

def _parse_iso_date(date_str: str, field_name: str) -> datetime.date:
    if not date_str or not isinstance(date_str, str):
        raise ValueError(f"Missing or invalid string value for date parameter '{field_name}'.")
    try:
        return datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date format for '{field_name}': '{date_str}'. Expected format is 'YYYY-MM-DD'.")

async def get_hotspots_from_db(
    db: AsyncSession,
    sensor: str = "VIIRS_SNPP_NRT",
    days: Optional[int] = None,
    date: Optional[str] = None,
    startDate: Optional[str] = None,
    endDate: Optional[str] = None,
    confidence: Optional[str] = None,
    minBrightness: Optional[float] = None,
    minFrp: Optional[float] = None,
    limit: int = 20000
) -> Dict[str, Any]:
    max_limit = min(max(int(limit or 20000), 1), 100000)

    # 1. Build deterministic MD5 cache key from sorted parameter dictionary
    cache_params = {
        "sensor": sensor,
        "days": days,
        "date": date,
        "startDate": startDate,
        "endDate": endDate,
        "confidence": confidence,
        "minBrightness": minBrightness,
        "minFrp": minFrp,
        "limit": max_limit
    }
    serialized_params = json.dumps(cache_params, sort_keys=True, default=str)
    cache_hash = hashlib.md5(serialized_params.encode("utf-8")).hexdigest()
    cache_key = f"hotspots_matrix_{cache_hash}"

    # Check in-memory cache
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        # 2. Select only scalar columns (bypasses full ORM overhead & geometry serialization)
        query = select(
            Hotspot.latitude,
            Hotspot.longitude,
            Hotspot.brightness,
            Hotspot.frp,
            Hotspot.confidence,
            Hotspot.acq_date,
            Hotspot.acq_time
        )

        conditions = []

        # 3. Date filtering with strict validation (no silent 'except: pass')
        if startDate and endDate:
            s_dt = _parse_iso_date(startDate, "startDate")
            e_dt = _parse_iso_date(endDate, "endDate")
            if s_dt > e_dt:
                raise ValueError(f"startDate '{startDate}' cannot be after endDate '{endDate}'.")
            conditions.append(Hotspot.acq_date.between(s_dt, e_dt))
        elif date:
            target_dt = _parse_iso_date(date, "date")
            conditions.append(Hotspot.acq_date == target_dt)
        elif days is not None and int(days) > 0:
            today_dt = datetime.date.today()
            start_dt = today_dt - datetime.timedelta(days=int(days))
            conditions.append(Hotspot.acq_date >= start_dt)
        else:
            # Default behavior when no date params provided: today's hotspots
            today_dt = datetime.date.today()
            conditions.append(Hotspot.acq_date == today_dt)

        # 4. Confidence filtering without unsafe integer casts on string columns
        if confidence and confidence.strip().lower() not in ["all", ""]:
            conf_val = confidence.strip().lower()

            # Safe conditional cast: only cast to Integer when text matches strictly digits (0-9)
            safe_numeric_conf = case(
                (Hotspot.confidence.op("~")(r"^\d+$"), cast(Hotspot.confidence, Integer)),
                else_=None
            )

            if conf_val in ["h", "high"]:
                conditions.append(
                    or_(
                        Hotspot.confidence.in_(["h", "H"]),
                        safe_numeric_conf >= 80
                    )
                )
            elif conf_val in ["n", "nominal", "m", "medium"]:
                conditions.append(
                    or_(
                        Hotspot.confidence.in_(["n", "N"]),
                        and_(safe_numeric_conf >= 30, safe_numeric_conf < 80)
                    )
                )
            elif conf_val in ["l", "low"]:
                conditions.append(
                    or_(
                        Hotspot.confidence.in_(["l", "L"]),
                        and_(safe_numeric_conf > 0, safe_numeric_conf < 30)
                    )
                )
            else:
                conditions.append(Hotspot.confidence.ilike(confidence.strip()))

        # 5. Brightness & FRP filtering
        if minBrightness is not None:
            conditions.append(Hotspot.brightness >= float(minBrightness))
        if minFrp is not None:
            conditions.append(Hotspot.frp >= float(minFrp))

        # 6. Apply filter list via generator/sequence unpacking
        if conditions:
            query = query.where(*conditions)

        query = query.order_by(Hotspot.acq_date.desc(), Hotspot.id.desc()).limit(max_limit)

        result = await db.execute(query)
        rows = result.all()

        # 7. Construct Flat Array Matrix
        data_matrix: List[List[Any]] = [
            [
                float(row.latitude),
                float(row.longitude),
                float(row.brightness) if row.brightness is not None else None,
                float(row.frp) if row.frp is not None else None,
                str(row.confidence) if row.confidence is not None else "",
                row.acq_date.isoformat() if hasattr(row.acq_date, "isoformat") else str(row.acq_date),
                str(row.acq_time) if row.acq_time else ""
            ]
            for row in rows
        ]

        response_data = {
            "status": "success",
            "count": len(data_matrix),
            "columns": COLUMNS_HEADER,
            "data": data_matrix
        }

        # Cache with long-lived TTL (12 hours)
        cache.set(cache_key, response_data, ttl_seconds=DEFAULT_CACHE_TTL)
        return response_data

    except ValueError as val_err:
        print(f"[HotspotService Validation Error] {val_err}")
        return {
            "status": "error",
            "count": 0,
            "columns": COLUMNS_HEADER,
            "data": [],
            "message": str(val_err)
        }
    except Exception as e:
        print(f"[HotspotService Error] Database query failed: {e}")
        return {
            "status": "error",
            "count": 0,
            "columns": COLUMNS_HEADER,
            "data": [],
            "message": f"Database query failed: {str(e)}"
        }

async def get_hotspot_stats_from_db(db: AsyncSession) -> Dict[str, Any]:
    """
    Fetch aggregate statistics and analytical summaries for NASA FIRMS hotspots.
    """
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
        print(f"[HotspotStats Error] {e}")
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

async def get_environmental_context_at_point(
    db: AsyncSession,
    lat: float,
    lng: float
) -> Dict[str, Any]:
    """
    Query PostGIS directly for environmental factors at given lat, lng:
    1. Peatland intersection (ST_Intersects)
    2. Nearest ERA5 Temperature
    3. Nearest ERA5 Soil Moisture
    4. Nearest ERA5 Rainfall
    """
    try:
        from sqlalchemy import text
        query = text("""
            SELECT 
                EXISTS(
                    SELECT 1 FROM peatlands 
                    WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                    LIMIT 1
                ) as is_peatland,
                (
                    SELECT suhu_celsius 
                    FROM temperature 
                    WHERE waktu = (SELECT MAX(waktu) FROM temperature)
                    ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) 
                    LIMIT 1
                ) as temperature,
                (
                    SELECT soil_moisture 
                    FROM soil_moisture_data 
                    WHERE waktu = (SELECT MAX(waktu) FROM soil_moisture_data)
                    ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) 
                    LIMIT 1
                ) as soil_moisture,
                (
                    SELECT curah_hujan_mm 
                    FROM rainfall_data 
                    WHERE waktu = (SELECT MAX(waktu) FROM rainfall_data)
                    ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) 
                    LIMIT 1
                ) as rainfall;
        """)
        result = await db.execute(query.bindparams(lat=lat, lng=lng))
        row = result.first()
        if row:
            temp_val = round(float(row.temperature), 1) if row.temperature is not None else None
            sm_val = round(float(row.soil_moisture), 3) if row.soil_moisture is not None else None
            rain_val = round(float(row.rainfall), 1) if row.rainfall is not None else None

            # Category labels
            temp_desc = "Panas Ekstrem" if temp_val and temp_val > 32 else ("Hangat" if temp_val and temp_val >= 26 else "Sejuk")
            sm_desc = "Sangat Kering (Kritis)" if sm_val and sm_val < 0.2 else ("Cukup Lembab" if sm_val and sm_val <= 0.35 else "Lembab / Jenuh Air")
            rain_desc = "Kering / Sangat Ringan" if rain_val and rain_val < 5 else ("Hujan Sedang" if rain_val and rain_val <= 20 else "Hujan Lebat")

            return {
                "status": "success",
                "lat": lat,
                "lng": lng,
                "is_peatland": bool(row.is_peatland),
                "temperature": {
                    "value": temp_val,
                    "unit": "°C",
                    "category": temp_desc
                } if temp_val is not None else None,
                "soil_moisture": {
                    "value": sm_val,
                    "unit": "m³/m³",
                    "category": sm_desc
                } if sm_val is not None else None,
                "rainfall": {
                    "value": rain_val,
                    "unit": "mm",
                    "category": rain_desc
                } if rain_val is not None else None
            }
        return {"status": "not_found", "is_peatland": False}
    except Exception as e:
        print(f"[EnvironmentalContext Error] {e}")
        return {"status": "error", "error": str(e), "is_peatland": False}

