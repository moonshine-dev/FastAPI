"""Pagination helpers: validated `page`/`size` query params + page envelope."""

from typing import Annotated, Generic, Sequence, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from config import settings

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)
    pages: int = Field(ge=0)


class Pagination:
    """Reusable dependency: validates `page` and `size` for every list endpoint."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(
            settings.DEFAULT_PAGE_SIZE,
            ge=1,
            le=settings.MAX_PAGE_SIZE,
            description="Items per page",
        ),
    ):
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    def pages_for(self, total: int) -> int:
        return (total + self.size - 1) // self.size


PaginationDep = Annotated[Pagination, Depends()]


def paginate(db: Session, stmt: Select, pagination: Pagination) -> tuple[list, int]:
    """Return (items, total) for `stmt` limited to the requested page."""
    count_stmt = select(func.count()).select_from(stmt.order_by().subquery())
    total = db.execute(count_stmt).scalar_one()
    items = db.execute(
        stmt.offset(pagination.offset).limit(pagination.size)
    ).scalars().all()
    return list(items), total


def build_page(
    model: type[T],
    objects: Sequence,
    total: int,
    pagination: Pagination,
) -> PageResponse[T]:
    """Validate ORM rows into `model` and wrap them in a page envelope."""
    items = [model.model_validate(obj) for obj in objects]
    return PageResponse[model](
        items=items,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pagination.pages_for(total),
    )
