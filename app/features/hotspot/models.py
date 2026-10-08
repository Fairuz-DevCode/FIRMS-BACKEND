from sqlalchemy import Column, Integer, Float, String, Date
from geoalchemy2 import Geometry
from app.core.database import Base

class Hotspot(Base):
    __tablename__ = "hotspots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    brightness = Column(Float, nullable=True)
    acq_date = Column(Date, nullable=False, index=True)
    acq_time = Column(String(10), nullable=True)
    confidence = Column(String(10), nullable=True, index=True)
    frp = Column(Float, nullable=True)
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    def to_geojson_feature(self) -> dict:
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(self.longitude), float(self.latitude)]
            },
            "properties": {
                "id": self.id,
                "latitude": float(self.latitude),
                "longitude": float(self.longitude),
                "brightness": float(self.brightness or 0.0),
                "acq_date": str(self.acq_date),
                "acq_time": self.acq_time or "0000",
                "confidence": self.confidence or "n/a",
                "frp": float(self.frp or 0.0)
            }
        }
