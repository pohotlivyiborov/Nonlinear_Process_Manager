from pydantic import BaseModel, EmailStr
from typing import Optional
from ..models.users import RolesTypesEnum


class UserBase(BaseModel):
    first_name: str
    last_name: str
    role: RolesTypesEnum
    patronymic: Optional[str] = None
    group: list[str]


class UserCreate(UserBase):
    password: str
    email: EmailStr


class UserResponse(UserBase):
    class Config:
        from_attributes = True
