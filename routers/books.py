from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import crud, schemas
from database import get_db

router = APIRouter(prefix="/books", tags=["Books"])

@router.post("/", response_model=schemas.BookResponse)
def add_new_book(book: schemas.BookCreate, db: Session = Depends(get_db)):

    return crud.create_book(db=db, book=book)

@router.get("/", response_model=list[schemas.BookResponse])
def get_all_books(db: Session = Depends(get_db)):
    
    return crud.get_books(db=db)