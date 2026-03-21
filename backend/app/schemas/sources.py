from pydantic import BaseModel


class SourcesBase:
    name: str
    type: str
    latitude: float
    longitude: float
    height: float
    emission_rate: float


class SourcesResponse(SourcesBase):

    class Config:
        from_attributes: True


class SourcesCreate(SourcesBase):
    pass
