from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..database import get_db
from ..schemas.substance import SubstanceCreate, SubstanceResponse
from ..services.substance_service import SubstanceService

router = APIRouter(prefix="/api/substances", tags=["substances"])


@router.get("", response_model=List[SubstanceResponse])
async def get_all_substances(db: AsyncSession = Depends(get_db)):
    substance_service = SubstanceService(db)
    result = await substance_service.get_all_substances()
    return result


@router.get("/{id}", response_model=SubstanceResponse)
async def get_substance_by_id(id: int, db: AsyncSession = Depends(get_db)):
    substance_service = SubstanceService(db)
    result = await substance_service.get_substance_by_id(id)
    return result


@router.post("", response_model=SubstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_substance(substance: SubstanceCreate, db: AsyncSession = Depends(get_db)):
    substance_service = SubstanceService(db)
    result = await substance_service.add_substance(substance)
    return result