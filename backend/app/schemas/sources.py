from pydantic import BaseModel, Field
from pydantic_extra_types.coordinate import Longitude, Latitude
from typing import Annotated, Optional, List
from ..models.sources import SourceTypeEnum


class SourcesBase(BaseModel):
    name: str
    type: SourceTypeEnum = SourceTypeEnum.point
    latitude: Latitude
    longitude: Longitude
    height: Annotated[float, Field(gt=0, lt=8000)]
    emission_rate: float
    coordinates: Optional[List[List[float]]] = None


class SourcesResponse(SourcesBase):
    id: int

    class Config:
        from_attributes = True


class SourcesCreate(SourcesBase):
    pass
