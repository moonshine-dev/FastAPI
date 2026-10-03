"""Direct repository tests (no HTTP layer)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.books.repository import BookRepository
from app.books.schemas import BookCreate
from app.orders.repository import OrderRepository
from app.orders.schemas import OrderCreate
from app.users.repository import UserRepository
from app.users.schemas import UserCreate
from pagination import Pagination

pytestmark = pytest.mark.repositories


def make_user(repo: UserRepository, username: str = "repo_user"):
    return repo.create(
        UserCreate(
            username=username,
            email=f"{username}@example.com",
            password="Str0ng!pass",
        )
    )


def make_book(repo: BookRepository, title: str = "Repo Book", stock: int = 3):
    return repo.create(
        BookCreate(title=title, author="Author", price=12.5, stock=stock)
    )


class TestUserRepository:
    def test_create_and_get_by_username(self, test_db):
        repo = UserRepository(test_db)
        user = make_user(repo)

        assert user.id >= 1
        found = repo.get_by_username(user.username)
        assert found is not None
        assert found.id == user.id
        assert found.hashed_password != "Str0ng!pass"

    def test_get_by_username_missing(self, test_db):
        repo = UserRepository(test_db)
        assert repo.get_by_username("nobody") is None

    def test_get_by_id(self, test_db):
        repo = UserRepository(test_db)
        user = make_user(repo)

        assert repo.get_by_id(user.id).id == user.id
        assert repo.get_by_id(99999) is None

    def test_get_by_id_include_orders(self, test_db):
        users = UserRepository(test_db)
        books = BookRepository(test_db)
        orders = OrderRepository(test_db)
        user = make_user(users, "with_orders")
        book = make_book(books)
        orders.create(
            OrderCreate(
                user_id=user.id,
                book_id=book.id,
                return_deadline=datetime.now(timezone.utc) + timedelta(days=7),
            )
        )

        loaded = users.get_by_id(user.id, include_orders=True)
        assert len(loaded.orders) == 1

        plain = users.get_by_id(user.id, include_orders=False)
        assert plain is not None

    def test_list_pagination(self, test_db):
        repo = UserRepository(test_db)
        for i in range(5):
            make_user(repo, f"paged_user_{i}")

        items, total = repo.list_users(Pagination(page=1, size=2))
        assert total == 5
        assert len(items) == 2

        items, total = repo.list_users(Pagination(page=3, size=2))
        assert len(items) == 1

    def test_list_include_orders(self, test_db):
        users = UserRepository(test_db)
        books = BookRepository(test_db)
        orders = OrderRepository(test_db)
        user = make_user(users, "eager_user")
        book = make_book(books)
        orders.create(
            OrderCreate(
                user_id=user.id,
                book_id=book.id,
                return_deadline=datetime.now(timezone.utc) + timedelta(days=7),
            )
        )

        items, total = users.list_users(Pagination(page=1, size=10), include_orders=True)
        assert total == 1
        assert len(items[0].orders) == 1


class TestBookRepository:
    def test_create_and_get(self, test_db):
        repo = BookRepository(test_db)
        book = make_book(repo)

        found = repo.get(book.id)
        assert found is not None
        assert found.title == "Repo Book"
        assert found.stock == 3

    def test_list_pagination(self, test_db):
        repo = BookRepository(test_db)
        for i in range(5):
            make_book(repo, f"Book {i}")

        items, total = repo.list(Pagination(page=2, size=2))
        assert total == 5
        assert len(items) == 2

    def test_search_by_title_exact(self, test_db):
        repo = BookRepository(test_db)
        target = make_book(repo, "Exact Match")
        make_book(repo, "Other")

        items, total = repo.search_by_title("Exact Match", Pagination(page=1, size=10))
        assert total == 1
        assert items[0].id == target.id

    def test_search_by_title_no_match(self, test_db):
        repo = BookRepository(test_db)
        make_book(repo)

        items, total = repo.search_by_title("Nope", Pagination(page=1, size=10))
        assert total == 0
        assert items == []


class TestOrderRepository:
    def _setup(self, test_db, stock=3):
        users = UserRepository(test_db)
        books = BookRepository(test_db)
        orders = OrderRepository(test_db)
        user = make_user(users)
        book = make_book(books, stock=stock)
        return users, books, orders, user, book

    def _deadline(self, days=7):
        return datetime.now(timezone.utc) + timedelta(days=days)

    def test_create_decrements_stock(self, test_db):
        _, books, orders, user, book = self._setup(test_db, stock=3)

        order = orders.create(
            OrderCreate(user_id=user.id, book_id=book.id, return_deadline=self._deadline())
        )
        assert order is not None
        assert books.get(book.id).stock == 2

    def test_create_without_stock_returns_none(self, test_db):
        _, books, orders, user, book = self._setup(test_db, stock=0)

        order = orders.create(
            OrderCreate(user_id=user.id, book_id=book.id, return_deadline=self._deadline())
        )
        assert order is None
        assert books.get(book.id).stock == 0

    def test_return_book_restores_stock(self, test_db):
        _, books, orders, user, book = self._setup(test_db, stock=2)
        order = orders.create(
            OrderCreate(user_id=user.id, book_id=book.id, return_deadline=self._deadline())
        )
        assert books.get(book.id).stock == 1

        returned = orders.return_book(order.id)
        assert returned.delivery_date is not None
        assert books.get(book.id).stock == 2

    def test_return_twice_returns_none(self, test_db):
        _, books, orders, user, book = self._setup(test_db, stock=2)
        order = orders.create(
            OrderCreate(user_id=user.id, book_id=book.id, return_deadline=self._deadline())
        )

        assert orders.return_book(order.id) is not None
        assert orders.return_book(order.id) is None
        assert books.get(book.id).stock == 2

    def test_return_missing_order_returns_none(self, test_db):
        _, _, orders, _, _ = self._setup(test_db)
        assert orders.return_book(99999) is None

    def test_list_delayed(self, test_db):
        _, books, orders, user, book = self._setup(test_db, stock=5)
        order = orders.create(
            OrderCreate(user_id=user.id, book_id=book.id, return_deadline=self._deadline())
        )

        # not delayed yet
        items, total = orders.list_delayed(Pagination(page=1, size=10))
        assert total == 0

        # move deadline into the past at DB level
        from app.orders.models import Order

        test_db.query(Order).filter(Order.id == order.id).update(
            {"return_deadline": datetime(2000, 1, 1)}, synchronize_session=False
        )
        test_db.commit()

        items, total = orders.list_delayed(Pagination(page=1, size=10))
        assert total == 1
        assert items[0].id == order.id

    def test_delayed_excludes_returned_orders(self, test_db):
        _, _, orders, user, book = self._setup(test_db, stock=5)
        order = orders.create(
            OrderCreate(user_id=user.id, book_id=book.id, return_deadline=self._deadline())
        )

        from app.orders.models import Order

        test_db.query(Order).filter(Order.id == order.id).update(
            {"return_deadline": datetime(2000, 1, 1)}, synchronize_session=False
        )
        test_db.commit()

        orders.return_book(order.id)
        items, total = orders.list_delayed(Pagination(page=1, size=10))
        assert total == 0
