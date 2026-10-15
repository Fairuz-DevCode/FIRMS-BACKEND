import csv
import datetime
import urllib.request
import urllib.error
from typing import Dict, Any, List
from sqlalchemy.dialects.postgresql import insert
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.utils.cache import cache
from app.features.hotspot.models import Hotspot

# Default bounding box for Indonesia region 
IDN_BBOX = "95,-11,141,6"

async def sync_nasa_firms_data(
    source: str = "VIIRS_SNPP_NRT",
    area: str = IDN_BBOX,
    day_range: int = 5
) -> Dict[str, Any]:
    """
    Synchronizes active fire data from NASA FIRMS API into PostgreSQL/PostGIS.
    Executes chunked bulk upsert (1000 records/chunk) with ON CONFLICT DO NOTHING,
    and performs event-driven cache invalidation immediately upon commit.
    """
    map_key = settings.MAP_KEY
    if not map_key:
        print("[FIRMS Sync Error] MAP_KEY is not set in environment or config.")
        return {
            "status": "error",
            "message": "MAP_KEY environment variable is not configured.",
            "synced_count": 0
        }

    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{source}/{area}/{day_range}"
    print(f"[FIRMS Sync] Fetching active fire data from NASA FIRMS ({source})...")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            lines = [line.decode("utf-8") for line in response.readlines()]
    except urllib.error.URLError as e:
        print(f"[FIRMS Sync Error] Failed to fetch data from NASA FIRMS: {e}")
        return {
            "status": "error",
            "message": f"HTTP network error while requesting NASA FIRMS API: {str(e)}",
            "synced_count": 0
        }
    except Exception as e:
        print(f"[FIRMS Sync Error] Unexpected error during fetch: {e}")
        return {
            "status": "error",
            "message": f"Unexpected fetch error: {str(e)}",
            "synced_count": 0
        }

    if not lines or len(lines) <= 1:
        print("[FIRMS Sync Info] No CSV rows returned from NASA FIRMS API.")
        return {
            "status": "success",
            "message": "No hotspot records returned from NASA FIRMS API.",
            "synced_count": 0
        }

    reader = csv.DictReader(lines)
    records_to_insert = []

    for row in reader:
        try:
            latitude = float(row["latitude"])
            longitude = float(row["longitude"])

            # Exclude Singapore & Malaysia (Peninsular Malaysia, Sarawak, Sabah)
            is_singapore = (103.60 <= longitude <= 104.05 and 1.20 <= latitude <= 1.48)
            is_west_malaysia = (99.8 <= longitude <= 104.5 and 1.25 <= latitude <= 6.8 and not (
                longitude <= 103.5 and latitude <= 2.5 and (latitude <= 0.6 * (longitude - 100.0) + 0.5)
            ))
            is_east_malaysia = (109.5 <= longitude <= 119.5 and (
                (longitude < 114.0 and latitude > 2.05) or
                (114.0 <= longitude < 115.5 and latitude > 1.2) or
                (longitude >= 115.5 and latitude > 4.25)
            ))

            if is_singapore or is_west_malaysia or is_east_malaysia:
                continue

            acq_date = datetime.datetime.strptime(row["acq_date"].strip(), "%Y-%m-%d").date()
            acq_time = row.get("acq_time", "").strip()
            brightness = float(row["bright_ti4"]) if "bright_ti4" in row and row["bright_ti4"] else (
                float(row["brightness"]) if "brightness" in row and row["brightness"] else None
            )
            confidence = row.get("confidence", "").strip()
            frp = float(row["frp"]) if "frp" in row and row["frp"] else None
            geom_wkb = from_shape(Point(longitude, latitude), srid=4326)

            records_to_insert.append({
                "latitude": latitude,
                "longitude": longitude,
                "brightness": brightness,
                "acq_date": acq_date,
                "acq_time": acq_time,
                "confidence": confidence,
                "frp": frp,
                "geom": geom_wkb
            })
        except (KeyError, ValueError):
            continue

    if not records_to_insert:
        print("[FIRMS Sync Info] Valid CSV rows count: 0.")
        return {
            "status": "success",
            "message": "No valid hotspot rows parsed from CSV.",
            "synced_count": 0
        }

    # Batch insert/upsert in chunks to handle duplicate constraints efficiently
    async with AsyncSessionLocal() as session:
        try:
            chunk_size = 1000
            inserted_count = 0
            for i in range(0, len(records_to_insert), chunk_size):
                chunk = records_to_insert[i:i + chunk_size]
                stmt = insert(Hotspot).values(chunk).on_conflict_do_nothing()
                res = await session.execute(stmt)
                inserted_count += res.rowcount if res.rowcount is not None and res.rowcount >= 0 else len(chunk)

            await session.commit()

            # Event-Driven Cache Invalidation: clear in-memory cache immediately upon committing new data
            cache.clear()
            print(f"✅ [FIRMS Sync Success] Successfully synced {inserted_count} hotspot records. In-memory cache invalidated.")

            return {
                "status": "success",
                "message": f"Successfully processed {len(records_to_insert)} records.",
                "synced_count": inserted_count
            }
        except Exception as e:
            await session.rollback()
            print(f"[FIRMS Sync Error] Database transaction failed: {e}")
            return {
                "status": "error",
                "message": f"Database insertion failed: {str(e)}",
                "synced_count": 0
            }
