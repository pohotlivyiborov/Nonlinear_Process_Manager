from sqlalchemy import Column, Integer, String, SmallInteger, Float
from ..database import Base


class Substances(Base):
    __tablename__ = "substances"

    id = Column(SmallInteger, nullable=False, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    short_name = Column(String, nullable=False, unique=True, index=True)
    mcl = Column(Float, nullable=False)  # MCL = ПДК
    density = Column(Float, nullable=False)
    settling_velocity = Column(Float, nullable=False)  # скорость оседания
    # hazard_level = Column(Integer, nullable=False) - может понадобиться если будем пилить справочную информацию
    # custom_color=Column(String, default="#E74C3C")-если захочется шлейф задавать кастомным цветом для каждого вещества
