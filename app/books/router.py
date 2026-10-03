from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.books import schemas
from app.books.repository import BookRepository
from database import get_db
from pagination import PageResponse, Pagination, build_page

router = APIRouter(prefix="/api/v1/books", tags=["Books"])


def get_book_repository(db: Annotated[Session, Depends(get_db)]) -> BookRepository:
    return BookRepository(db)


@router.post("/", response_model=schemas.BookResponse)
def add_new_book(
    book: schemas.BookCreate,
    repo: Annotated[BookRepository, Depends(get_book_repository)],
):
    return schemas.BookResponse.model_validate(repo.create(book))


@router.get("/search", response_model=PageResponse[schemas.BookResponse])
def search_books(
    repo: Annotated[BookRepository, Depends(get_book_repository)],
    pagination: Annotated[Pagination, Depends()],
    title: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Exact book title to search for",
    ),
):
    items, total = repo.search_by_title(title=title, pagination=pagination)
    return build_page(schemas.BookResponse, items, total, pagination)


@router.get("/", response_model=PageResponse[schemas.BookResponse])
def get_all_books(
    repo: Annotated[BookRepository, Depends(get_book_repository)],
    pagination: Annotated[Pagination, Depends()],
):
    items, total = repo.list(pagination)
    return build_page(schemas.BookResponse, items, total, pagination)
