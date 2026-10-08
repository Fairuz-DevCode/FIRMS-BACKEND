from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class HotspotGeometry(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: List[float] = Field(..., description="[longitude, latitude]")

class HotspotProperties(BaseModel):
    id: int
    latitude: float
    longitude: float
    brightness: float
    acq_date: str
    acq_time: str
    confidence: str
    frp: float

class HotspotFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: HotspotGeometry
    properties: HotspotProperties

class HotspotFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[HotspotFeature]

class HotspotApiResponse(BaseModel):
    status: str = "success"
    count: int
    totalCount: int
    source: str
    data: HotspotFeatureCollection

class HotspotStatsSummary(BaseModel):
    total_hotspots: int = 0
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    avg_brightness: float = 0.0
    avg_frp: float = 0.0
    max_frp: float = 0.0

class HotspotStatsResponse(BaseModel):
    status: str = "success"
    summary: Dict[str, Any]
    confidenceBreakdown: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    error: Optional[str] = None
