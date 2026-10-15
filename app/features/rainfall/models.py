from sqlalchemy import Column, Integer, Float, DateTime
from geoalchemy2 import Geometry
from app.core.database import Base

class Rainfall(Base):
    __tablename__ = "rainfall_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    waktu = Column(DateTime, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    curah_hujan_mm = Column(Float, nullable=True)
    
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

    def to_flat_array(self) -> list:
        return [
            float(self.longitude), 
            float(self.latitude), 
            float(self.curah_hujan_mm if self.curah_hujan_mm is not None else 0.0)
        ]