from sqlalchemy import Column, Integer, Float, String
from geoalchemy2 import Geometry
from app.core.database import Base

class Peatland(Base):
    __tablename__ = "peatlands"

    ogc_fid = Column(Integer, primary_key=True, index=True, autoincrement=True)
    objectid = Column(Integer, nullable=True)
    layer_revi = Column(String, nullable=True)
    shape_area = Column("shape_area", Float, nullable=True)
    geom = Column(Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True)
