from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import crud, schemas
from config import settings
from database import get_db

router = APIRouter(prefix="/books", tags=["Books"])

@router.post("/", response_model=schemas.BookResponse)
def add_new_book(book: schemas.BookCreate, db: Session = Depends(get_db)):

    return crud.create_book(db=db, book=book)

@router.get("/", response_model=schemas.PageResponse[schemas.BookResponse])
def get_all_books(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"),
    db: Session = Depends(get_db),
):

    items, total = crud.get_books(db=db, skip=(page - 1) * size, limit=size)
    return schemas.PageResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )