from .base import Base
from sqlalchemy import Column, String, SmallInteger, func, TIMESTAMP, Float


class SimulationParams(Base):
    __tablename__ = "simulation_params"

    id = Column(SmallInteger, primary_key=True, nullable=False)
    wind_speed = Column(Float, nullable=False)
    wind_direction = Column(Float, nullable=False) # Тут будет измеряться вградусах
    stability_class = Column(String, nullable=False)
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
