"""Database seeding with faker.

Usable both as a library (import the `seed` function) and from the CLI:
    python -m benchmarks.cli seed --count 10000 --model all
"""

import random
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy import func, insert

import models

fake = Faker("en_US")

BATCH_SIZE = 100000

# users : books : orders  (used when model="all")
ALL_RATIO = (1, 3, 10)

DUMMY_PASSWORD = "benchmark-password"


class SeedError(RuntimeError):
    pass


def count_of(session, model) -> int:
    return session.query(func.count(model.id)).scalar() or 0


def _bulk_insert(session, model, row_iter, label: str) -> int:
    total = 0
    batch = []
    for row in row_iter:
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            session.execute(insert(model), batch)
            session.commit()
            total += len(batch)
            print(f"  {label}: {total} rows inserted")
            batch = []
    if batch:
        session.execute(insert(model), batch)
        session.commit()
        total += len(batch)
    print(f"  {label}: {total} rows inserted")
    return total


def _need(count: int, current: int, label: str) -> int:
    need = count - current
    if need < 0:
        raise SeedError(
            f"{label} table already has {current} rows (> {count} requested). "
            f"Run `python -m benchmarks.cli resetdb --yes` first."
        )
    if need == 0:
        print(f"  {label}: already has {count} rows, nothing to do")
    return need


def _password_hash() -> str:
    # One bcrypt call per process; reused for every seeded user.
    from crud import get_password_hash

    return get_password_hash(DUMMY_PASSWORD)


def _user_rows(count: int, start_index: int, password_hash: str):
    for i in range(start_index + 1, start_index + count + 1):
        first = fake.first_name().lower()
        last = fake.last_name().lower()
        yield {
            "username": f"{first}.{last}.{i}",
            "email": f"{first}.{last}.{i}@example.com",
            "hashed_password": password_hash,
            "is_active": fake.boolean(90),
        }


def seed_users(session, count: int) -> int:
    current = count_of(session, models.User)
    need = _need(count, current, "users")
    if need == 0:
        return current
    return _bulk_insert(session, models.User, _user_rows(need, current, _password_hash()), "users")


def _book_rows(count: int, start_index: int):
    for i in range(start_index + 1, start_index + count + 1):
        yield {
            "title": f"{fake.word().title()} {fake.word()} {fake.word()} No. {i}",
            "author": f"{fake.first_name()} {fake.last_name()}",
            "price": round(random.uniform(5.0, 200.0), 2),
            "stock": fake.random_int(0, 100),
            "description": fake.sentence() if fake.boolean(70) else None,
        }


def seed_books(session, count: int) -> int:
    current = count_of(session, models.Book)
    need = _need(count, current, "books")
    if need == 0:
        return current
    return _bulk_insert(session, models.Book, _book_rows(need, current), "books")


def _id_range(session, model):
    lo, hi = session.query(func.min(model.id), func.max(model.id)).one()
    if lo is None:
        raise SeedError(
            f"No {model.__name__} records exist. Seed users and books first."
        )
    return lo, hi


def _order_rows(count: int, user_range, book_range):
    now = datetime.now(timezone.utc)
    for _ in range(count):
        order_date = now - timedelta(
            days=fake.random_int(1, 730), seconds=fake.random_int(0, 86400)
        )
        delivered = fake.boolean(60)
        delivery_date = (
            order_date + timedelta(days=fake.random_int(1, 10)) if delivered else None
        )
        return_deadline = order_date + timedelta(days=fake.random_int(14, 60))
        yield {
            "user_id": fake.random_int(user_range[0], user_range[1]),
            "book_id": fake.random_int(book_range[0], book_range[1]),
            "order_date": order_date.replace(tzinfo=None),
            "delivery_date": delivery_date.replace(tzinfo=None) if delivery_date else None,
            "return_deadline": return_deadline.replace(tzinfo=None),
        }


def seed_orders(session, count: int) -> int:
    current = count_of(session, models.Order)
    need = _need(count, current, "orders")
    if need == 0:
        return current
    user_range = _id_range(session, models.User)
    book_range = _id_range(session, models.Book)
    return _bulk_insert(session, models.Order, _order_rows(need, user_range, book_range), "orders")


def seed(session, count: int, model: str = "all") -> dict:
    """Seed `count` records.

    model: "users" | "books" | "orders" | "all"
    Tops up the table to `count` rows (never shrinks it).
    """
    if model == "users":
        return {"users": seed_users(session, count)}
    if model == "books":
        return {"books": seed_books(session, count)}
    if model == "orders":
        return {"orders": seed_orders(session, count)}
    if model == "all":
        r_u, r_b, r_o = ALL_RATIO
        ratio_sum = sum(ALL_RATIO)
        n_users = max(1, round(count * r_u / ratio_sum))
        n_books = max(1, round(count * r_b / ratio_sum))
        n_orders = max(0, count - n_users - n_books)
        return {
            "users": seed_users(session, n_users),
            "books": seed_books(session, n_books),
            "orders": seed_orders(session, n_orders),
        }
    raise SeedError(f"Unknown model '{model}'. Use: users | books | orders | all")
