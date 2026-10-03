import sqlalchemy
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    username = sqlalchemy.Column(sqlalchemy.String(50), unique=True, nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String(100), unique=True, nullable=False)
    hashed_password = sqlalchemy.Column(sqlalchemy.String(255), nullable=False)
    is_active = sqlalchemy.Column(sqlalchemy.Boolean, default=True)

    orders = relationship("Order", back_populates="user")
