from ..database import Base
from sqlalchemy import Column, String, Integer, func, TIMESTAMP, Float, JSON, ForeignKey, SmallInteger, Enum as SQLEnum
from enum import Enum
from sqlalchemy.orm import relationship


class SourceTypeEnum(str, Enum):
    point = "point"
    line = "line"
    polygon = "polygon"


class Sources(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    type = Column(SQLEnum(SourceTypeEnum), default=SourceTypeEnum.point, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    emission_rate = Column(Float, nullable=False)
    substance_id = Column(SmallInteger, ForeignKey("substances.id", ondelete="CASCADE"), nullable=False)
    substance = relationship("Substances", lazy="selectin")
    coordinates = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

