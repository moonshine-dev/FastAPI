"""Generic repository base shared by the entity repositories."""

from typing import Generic, Optional, Sequence, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from pagination import Pagination, paginate

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Generic select/pagination/create helpers; entity repos add domain logic."""

    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def base_select(self, options: Sequence = ()) -> Select:
        stmt = select(self.model)
        for option in options:
            stmt = stmt.options(option)
        return stmt

    def get(self, entity_id: int, options: Sequence = ()) -> Optional[ModelT]:
        stmt = self.base_select(options).where(self.model.id == entity_id)
        return self.db.execute(stmt).scalars().first()

    def list(
        self,
        pagination: Pagination,
        options: Sequence = (),
        order_by=None,
    ) -> tuple[list[ModelT], int]:
        ordering = self.model.id if order_by is None else order_by
        stmt = self.base_select(options).order_by(ordering)
        return paginate(self.db, stmt, pagination)

    def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
