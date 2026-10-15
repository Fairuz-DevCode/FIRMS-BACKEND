from sqlalchemy import Column, Integer, Float, DateTime
from geoalchemy2 import Geometry
from app.core.database import Base

class Temperature(Base) : 
  __tablename__ = "temperature"

  id = Column(Integer, primary_key=True, index=True, autoincrement=True)
  waktu = Column(DateTime, nullable=False, index=True)
  latitude = Column(Float, nullable=False)
  longitude = Column(Float, nullable=False)
  suhu_celsius = Column(Float, nullable=True)
  geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True)

  def to_flat_array(self) -> list:
    return [
      float(self.longitude), 
      float(self.latitude), 
      float(self.suhu_celsius if self.suhu_celsius is not None else 0.0)
    ]