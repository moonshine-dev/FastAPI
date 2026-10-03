from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.users import models
from app.users.schemas import UserCreate
from app.users.security import get_password_hash
from pagination import Pagination
from repository import BaseRepository


class UserRepository(BaseRepository[models.User]):
    model = models.User

    @staticmethod
    def with_orders() -> tuple:
        return (selectinload(models.User.orders),)

    def create(self, user: UserCreate) -> models.User:
        new_user = models.User(
            username=user.username,
            email=user.email,
            hashed_password=get_password_hash(user.password),
        )
        return self.add(new_user)

    def get_by_username(
        self, username: str, options: Sequence = ()
    ) -> Optional[models.User]:
        stmt = select(models.User).where(models.User.username == username)
        for option in options:
            stmt = stmt.options(option)
        return self.db.execute(stmt).scalars().first()

    def get_by_id(
        self, user_id: int, *, include_orders: bool = False
    ) -> Optional[models.User]:
        options = self.with_orders() if include_orders else ()
        return self.get(user_id, options)

    def list_users(
        self, pagination: Pagination, *, include_orders: bool = False
    ) -> tuple[list[models.User], int]:
        options = self.with_orders() if include_orders else ()
        return self.list(pagination, options)
