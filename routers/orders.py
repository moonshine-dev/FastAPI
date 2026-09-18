from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import crud, schemas
from config import settings
from database import get_db

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/borrow", response_model=schemas.OrderResponse)
def borrow_book(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    
    new_order = crud.create_order(db=db, order=order)
    
    if not new_order:
        raise HTTPException(status_code=400, detail="Book not found or not in stock.")
        
    return new_order

@router.put("/{order_id}/return", response_model=schemas.OrderResponse)
def return_book(order_id: int, db: Session = Depends(get_db)):

    returned_order = crud.return_book(db=db, order_id=order_id)
    
    if not returned_order:
        raise HTTPException(status_code=400, detail="Order not found or has already been returned.")
        
    return returned_order

@router.get("/delayed", response_model=schemas.PageResponse[schemas.OrderResponse])
def get_delayed_orders(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"),
    db: Session = Depends(get_db),
):

    items, total = crud.get_delayed_orders(db=db, skip=(page - 1) * size, limit=size)
    return schemas.PageResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )