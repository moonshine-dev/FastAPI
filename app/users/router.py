from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.users import schemas
from app.users.repository import UserRepository
from database import get_db
from pagination import PageResponse, Pagination, build_page

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

IncludeParam = Annotated[
    Optional[list[Literal["orders"]]],
    Query(description="Related resources to embed, e.g. 'orders'."),
]


def get_user_repository(db: Annotated[Session, Depends(get_db)]) -> UserRepository:
    return UserRepository(db)


def _wants(include: Optional[list[str]], resource: str) -> bool:
    return bool(include) and resource in include


@router.post("/", response_model=schemas.UserResponse)
def register_user(
    user: schemas.UserCreate,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
):
    db_user = repo.get_by_username(username=user.username)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="This username already exists. Please choose a different username.",
        )

    return schemas.UserResponse.model_validate(repo.create(user))


@router.get(
    "/",
    response_model=PageResponse[schemas.UserResponse]
    | PageResponse[schemas.UserWithOrders],
)
def list_users(
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    pagination: Annotated[Pagination, Depends()],
    include: IncludeParam = None,
):
    include_orders = _wants(include, "orders")
    users, total = repo.list_users(pagination, include_orders=include_orders)
    model = schemas.UserWithOrders if include_orders else schemas.UserResponse
    return build_page(model, users, total, pagination)


@router.get(
    "/{user_id}",
    response_model=schemas.UserResponse | schemas.UserWithOrders,
)
def get_user_profile(
    user_id: int,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    include: IncludeParam = None,
):
    include_orders = _wants(include, "orders")
    db_user = repo.get_by_id(user_id, include_orders=include_orders)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if include_orders:
        return schemas.UserWithOrders.model_validate(db_user)
    return schemas.UserResponse.model_validate(db_user)
