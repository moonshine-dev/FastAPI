from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.orders import schemas
from app.orders.repository import OrderRepository
from database import get_db
from pagination import PageResponse, Pagination, build_page

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


def get_order_repository(db: Annotated[Session, Depends(get_db)]) -> OrderRepository:
    return OrderRepository(db)


@router.post("/borrow", response_model=schemas.OrderResponse)
def borrow_book(
    order: schemas.OrderCreate,
    repo: Annotated[OrderRepository, Depends(get_order_repository)],
):
    new_order = repo.create(order)

    if not new_order:
        raise HTTPException(status_code=400, detail="Book not found or not in stock.")

    return schemas.OrderResponse.model_validate(new_order)


@router.put("/{order_id}/return", response_model=schemas.OrderResponse)
def return_book(
    order_id: int,
    repo: Annotated[OrderRepository, Depends(get_order_repository)],
):
    returned_order = repo.return_book(order_id)

    if not returned_order:
        raise HTTPException(
            status_code=400,
            detail="Order not found or has already been returned.",
        )

    return schemas.OrderResponse.model_validate(returned_order)


@router.get("/delayed", response_model=PageResponse[schemas.OrderResponse])
def get_delayed_orders(
    repo: Annotated[OrderRepository, Depends(get_order_repository)],
    pagination: Annotated[Pagination, Depends()],
):
    items, total = repo.list_delayed(pagination)
    return build_page(schemas.OrderResponse, items, total, pagination)
