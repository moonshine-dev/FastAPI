import sqlalchemy
from sqlalchemy import Index
from sqlalchemy.orm import relationship

from database import Base


class Book(Base):
    __tablename__ = "books"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    title = sqlalchemy.Column(sqlalchemy.String(100))
    author = sqlalchemy.Column(sqlalchemy.String(100))
    price = sqlalchemy.Column(sqlalchemy.Float)
    stock = sqlalchemy.Column(sqlalchemy.Integer, default=1)
    description = sqlalchemy.Column(sqlalchemy.String(500), nullable=True)

    orders = relationship("Order", back_populates="book")

    __table_args__ = (
        Index("ix_books_title", "title", postgresql_using="btree"),
        Index("ix_books_author", "author", postgresql_using="btree"),
    )
