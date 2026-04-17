from fastapi import APIRouter, status, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.users import UserResponse, UserCreate
from ..services.user_service import UserService
from ..database import get_db

router = APIRouter(prefix="/users",
                   tags=["users"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user(new_user: UserCreate, db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)
    created_user = await user_service.create_user(new_user)
    return created_user


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(id: int, db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)
    user = await user_service.delete_user(id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"user with id {id} does not exist"
        )

    return None


@router.get("/{id}", response_model=UserResponse)
async def get_user_by_id(id: int, db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)

    user = await user_service.get_user_by_id(id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"user with id {id} does not exist"
        )
    return user


@router.get("/emails/{email}", response_model=UserResponse)
async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    user_service = UserService(db)

    user = await user_service.get_user_by_email(email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"user with id {email} does not exist"
        )
    return user


