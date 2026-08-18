from datetime import datetime, timezone
import sqlalchemy
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    username = sqlalchemy.Column(sqlalchemy.String(50), unique=True, index=True)
    email = sqlalchemy.Column(sqlalchemy.String(100), unique=True, index=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String(255))
    is_active = sqlalchemy.Column(sqlalchemy.Boolean, default=True)

    orders = relationship("Order", back_populates="user")


class Book(Base):
    __tablename__ = "books"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    title = sqlalchemy.Column(sqlalchemy.String(100), index=True)
    author = sqlalchemy.Column(sqlalchemy.String(100), index=True)
    price = sqlalchemy.Column(sqlalchemy.Float)
    stock = sqlalchemy.Column(sqlalchemy.Integer, default=1)
    description = sqlalchemy.Column(sqlalchemy.String(500), nullable=True)

    orders = relationship("Order", back_populates="book")


class Order(Base):
    __tablename__ = "orders"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer,sqlalchemy.ForeignKey("users.id"), index=True)
    book_id = sqlalchemy.Column(sqlalchemy.Integer,sqlalchemy.ForeignKey("books.id"), index=True)
    order_date = sqlalchemy.Column(sqlalchemy.DateTime, default=lambda: datetime.now(timezone.utc))
    delivery_date = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    return_deadline = sqlalchemy.Column(sqlalchemy.DateTime)

    user = relationship("User", back_populates="orders")
    book = relationship("Book", back_populates="orders")

