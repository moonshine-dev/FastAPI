"""
Shared fixtures for integration tests over an HTTP client.

- Instead of the real PostgreSQL database, we use a test database
  and override the get_db dependency across the whole app.
- All requests are sent via TestClient (httpx), meaning we go
  from the HTTP layer down through CRUD to the test database.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture()
def test_db():
    """Create and then drop tables for each test (full isolation)."""
    Base.metadata.create_all(bind=test_engine)
    yield TestSessionLocal()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(test_db):
    """HTTP client that redirects get_db to the test session."""

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper fixtures — ready-made user, book and order created over HTTP
# ---------------------------------------------------------------------------

@pytest.fixture()
def created_user(client):
    """Returns a registered user created via the API."""
    payload = {
        "username": "ali_rezaei",
        "email": "ali@example.com",
        "password": "S3cretPass!",
    }
    resp = client.post("/api/v1/users/", json=payload)
    assert resp.status_code == 200, resp.text
    return {"payload": payload, "user": resp.json()}


@pytest.fixture()
def created_book(client):
    """Returns a book with 3 copies in stock, created via the API."""
    payload = {
        "title": "Test-Driven Development",
        "author": "Kent Beck",
        "price": 45.5,
        "stock": 3,
        "description": "A book about TDD.",
    }
    resp = client.post("/api/v1/books/", json=payload)
    assert resp.status_code == 200, resp.text
    return {"payload": payload, "book": resp.json()}


@pytest.fixture()
def created_order(client, created_user, created_book):
    """Returns a book-borrowing order created via the API."""
    payload = {
        "user_id": created_user["user"]["id"],
        "book_id": created_book["book"]["id"],
        "return_deadline": "2099-01-01T00:00:00",
    }
    resp = client.post("/api/v1/orders/borrow", json=payload)
    assert resp.status_code == 200, resp.text
    return {"payload": payload, "order": resp.json()}


@pytest.fixture()
def backdate_order(test_db):
    """Moves an existing order's return_deadline into the past (DB level)."""

    def _backdate(order_id: int, deadline: datetime | None = None) -> int:
        from app.orders.models import Order

        when = deadline or datetime(2000, 1, 1)
        test_db.query(Order).filter(Order.id == order_id).update(
            {"return_deadline": when}, synchronize_session=False
        )
        test_db.commit()
        return order_id

    return _backdate
