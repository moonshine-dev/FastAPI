from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.books.models import Book
from app.orders import models
from app.orders.schemas import OrderCreate
from pagination import Pagination, paginate
from repository import BaseRepository


class OrderRepository(BaseRepository[models.Order]):
    model = models.Order

    def create(self, order: OrderCreate) -> Optional[models.Order]:
        """Atomically reserve a copy (stock > 0) then insert the order."""
        rows = self.db.execute(
            update(Book)
            .where(Book.id == order.book_id, Book.stock > 0)
            .values(stock=Book.stock - 1)
        ).rowcount

        if rows == 0:
            self.db.rollback()
            return None

        new_order = models.Order(
            user_id=order.user_id,
            book_id=order.book_id,
            return_deadline=order.return_deadline,
        )

        try:
            self.db.add(new_order)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(new_order)
        return new_order

    def return_book(self, order_id: int) -> Optional[models.Order]:
        """Atomically mark an active order returned, then restore stock."""
        rows = self.db.execute(
            update(models.Order)
            .where(
                models.Order.id == order_id,
                models.Order.delivery_date.is_(None),
            )
            .values(delivery_date=datetime.now(timezone.utc))
        ).rowcount

        if rows == 0:
            self.db.rollback()
            return None

        book_id = self.db.execute(
            select(models.Order.book_id).where(models.Order.id == order_id)
        ).scalar_one()

        try:
            self.db.execute(
                update(Book)
                .where(Book.id == book_id)
                .values(stock=Book.stock + 1)
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return self.get(order_id)

    def list_delayed(self, pagination: Pagination) -> tuple[list[models.Order], int]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(models.Order)
            .where(
                models.Order.delivery_date.is_(None),
                models.Order.return_deadline < now,
            )
            .order_by(models.Order.id)
        )
        return paginate(self.db, stmt, pagination)
