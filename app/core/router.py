from datetime import datetime
from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "service": "NASA FIRMS Hotspot FastAPI Python Backend",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
