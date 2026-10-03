from datetime import datetime, timezone

import sqlalchemy
from sqlalchemy import Index
from sqlalchemy.orm import relationship

from database import Base


class Order(Base):
    __tablename__ = "orders"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    book_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("books.id"))
    order_date = sqlalchemy.Column(
        sqlalchemy.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    delivery_date = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    return_deadline = sqlalchemy.Column(sqlalchemy.DateTime)

    user = relationship("User", back_populates="orders")
    book = relationship("Book", back_populates="orders")

    __table_args__ = (
        Index("ix_orders_user_id", "user_id", postgresql_using="btree"),
        Index("ix_orders_book_id", "book_id", postgresql_using="btree"),
        Index("ix_orders_return_deadline", "return_deadline", postgresql_using="btree"),
    )
