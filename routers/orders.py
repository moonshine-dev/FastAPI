from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import crud, schemas
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

@router.get("/delayed", response_model=list[schemas.OrderResponse])
def get_delayed_orders(db: Session = Depends(get_db)):

    return crud.get_delayed_orders(db=db)