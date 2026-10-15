from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class HotspotApiResponse(BaseModel):
    status: str = "success"
    count: int = Field(..., description="Total number of returned hotspot points")
    columns: List[str] = Field(
        default=["lat", "lng", "brightness", "frp", "confidence", "acq_date", "acq_time"],
        description="Ordered column names of each row in the data matrix"
    )
    data: List[List[Union[float, str, int, None]]] = Field(
        ...,
        description="Matrix of hotspots formatted as [[lat, lng, brightness, frp, confidence, acq_date, acq_time], ...]"
    )
    message: Optional[str] = None

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

class HotspotSyncResponse(BaseModel):
    status: str
    message: str
    synced_count: int
