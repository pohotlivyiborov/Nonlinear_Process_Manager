from .base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Null, func, TIMESTAMP, JSON, Enum as SQLEnum
from enum import Enum
from datetime import datetime
from typing import Any


class RolesTypesEnum(str, Enum):
    professor = "professor",
    student = "student",
    admin = "admin",


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    patronymic: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    role: Mapped[RolesTypesEnum] = mapped_column(SQLEnum(RolesTypesEnum), default=RolesTypesEnum.student,
                                                 nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    group: Mapped[Any] = mapped_column(JSON, nullable=False)
