from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.books import models
from app.books.schemas import BookCreate
from pagination import Pagination, paginate
from repository import BaseRepository


class BookRepository(BaseRepository[models.Book]):
    model = models.Book

    def create(self, book: BookCreate) -> models.Book:
        new_book = models.Book(
            title=book.title,
            author=book.author,
            price=book.price,
            stock=book.stock,
            description=book.description,
        )
        return self.add(new_book)

    def search_by_title(
        self, title: str, pagination: Pagination
    ) -> tuple[list[models.Book], int]:
        stmt = (
            select(models.Book)
            .where(models.Book.title == title)
            .order_by(models.Book.id)
        )
        return paginate(self.db, stmt, pagination)
