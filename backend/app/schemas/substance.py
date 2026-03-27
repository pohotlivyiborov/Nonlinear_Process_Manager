from pydantic import BaseModel


class BaseSubstance(BaseModel):
    name: str
    short_name: str
    mcl: float
    density: float
    settling_velocity: float


class SubstanceCreate(BaseSubstance):
    pass


class SubstanceResponse(BaseSubstance):
    id: int

    class Config:
        from_attributes = True
