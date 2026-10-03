"""Database seeding with faker.

Usable both as a library (import the `seed` function) and from the CLI:
    python -m benchmarks.cli seed --count 10000 --model all
"""

import os
import random
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from faker import Faker
from sqlalchemy import func, insert

from app.books.models import Book
from app.orders.models import Order
from app.users.models import User

fake = Faker("en_US")

BATCH_SIZE = 10_000           # rows per INSERT/commit; also the progress print interval
PARALLEL_THRESHOLD = 500_000  # rows below which worker processes don't pay off (spawn ~1.5s)
CHUNK_SIZE = 5_000           # rows generated per chunk (one per worker task)
MAX_WORKERS = 8

# users : books : orders  (used when model="all")
ALL_RATIO = (1, 3, 10)

DUMMY_PASSWORD = "benchmark-password"


class SeedError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _pools() -> dict:
    """Pre-generated Faker values, reused across rows (built once per process).

    Generating per-row with faker (~8 provider calls/row) dominates seeding
    time; drawing from these pools keeps the data looking the same while
    making row generation several times cheaper.
    """
    return {
        "words": [fake.word() for _ in range(2000)],
        "first_names": [fake.first_name() for _ in range(1000)],
        "last_names": [fake.last_name() for _ in range(1000)],
        "sentences": [fake.sentence() for _ in range(500)],
    }


def count_of(session, model) -> int:
    return session.query(func.count(model.id)).scalar() or 0


def _bulk_insert(session, model, row_iter, label: str) -> int:
    # Insert via the Table, not the ORM class: session.execute(insert(Model),
    # rows) routes through the ORM bulk-persistence layer, which splits rows
    # into tiny groups (by NULL-ness of values) and issues row-at-a-time
    # RETURNING inserts — ~40x more driver round-trips for the same data.
    stmt = insert(model.__table__)
    total = 0
    printed = 0
    batch = []
    for row in row_iter:
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            session.execute(stmt, batch)
            session.commit()
            total += len(batch)
            printed = total
            print(f"  {label}: {total} rows inserted")
            batch = []
    if batch:
        session.execute(stmt, batch)
        session.commit()
        total += len(batch)
    if total != printed:
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
    from app.users.security import get_password_hash

    return get_password_hash(DUMMY_PASSWORD)


# --------------------------------------------------------------------------- #
# Row generators (serial)
# --------------------------------------------------------------------------- #

def _user_rows(count: int, start_index: int, password_hash: str):
    pools = _pools()
    first_names = pools["first_names"]
    last_names = pools["last_names"]
    for i in range(start_index + 1, start_index + count + 1):
        first = random.choice(first_names).lower()
        last = random.choice(last_names).lower()
        yield {
            "username": f"{first}.{last}.{i}",
            "email": f"{first}.{last}.{i}@example.com",
            "hashed_password": password_hash,
            "is_active": random.random() < 0.9,
        }


def _book_rows(count: int, start_index: int):
    pools = _pools()
    words = pools["words"]
    first_names = pools["first_names"]
    last_names = pools["last_names"]
    sentences = pools["sentences"]
    for i in range(start_index + 1, start_index + count + 1):
        yield {
            "title": (
                f"{random.choice(words).title()} {random.choice(words)} "
                f"{random.choice(words)} No. {i}"
            ),
            "author": f"{random.choice(first_names)} {random.choice(last_names)}",
            "price": round(random.uniform(5.0, 200.0), 2),
            "stock": random.randint(0, 100),
            "description": random.choice(sentences) if random.random() < 0.7 else None,
        }


def _order_rows(count: int, user_range, book_range):
    now = datetime.now(timezone.utc)
    for _ in range(count):
        order_date = now - timedelta(
            days=random.randint(1, 730), seconds=random.randint(0, 86400)
        )
        delivered = random.random() < 0.6
        delivery_date = (
            order_date + timedelta(days=random.randint(1, 10)) if delivered else None
        )
        return_deadline = order_date + timedelta(days=random.randint(14, 60))
        yield {
            "user_id": random.randint(user_range[0], user_range[1]),
            "book_id": random.randint(book_range[0], book_range[1]),
            "order_date": order_date.replace(tzinfo=None),
            "delivery_date": delivery_date.replace(tzinfo=None) if delivery_date else None,
            "return_deadline": return_deadline.replace(tzinfo=None),
        }


# --------------------------------------------------------------------------- #
# Chunked / parallel generation
# --------------------------------------------------------------------------- #

def _book_chunk(spec):
    start_index, count = spec
    return list(_book_rows(count, start_index))


def _user_chunk(spec):
    start_index, count, password_hash = spec
    return list(_user_rows(count, start_index, password_hash))


def _order_chunk(spec):
    count, user_range, book_range = spec
    return list(_order_rows(count, user_range, book_range))


def _offset_specs(total: int, start_index: int = 0) -> list:
    """[(start, size), ...] covering `total` rows in CHUNK_SIZE pieces."""
    specs = []
    offset = 0
    while offset < total:
        size = min(CHUNK_SIZE, total - offset)
        specs.append((start_index + offset, size))
        offset += size
    return specs


def _chunked(worker, specs: list, total: int):
    """Yield rows from `worker(spec)` for every spec.

    Below PARALLEL_THRESHOLD the chunks are generated in-process (worker
    processes cost ~1s each to start on spawn platforms); above it each
    chunk is generated by a worker process while earlier chunks are being
    inserted, so generation overlaps with I/O.
    """
    workers = min(len(specs), os.cpu_count() or 1, MAX_WORKERS)
    if total < PARALLEL_THRESHOLD or workers <= 1:
        for spec in specs:
            yield from worker(spec)
        return
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for rows in pool.map(worker, specs):
            yield from rows


# --------------------------------------------------------------------------- #
# Seeding
# --------------------------------------------------------------------------- #

def seed_users(session, count: int) -> int:
    current = count_of(session, User)
    need = _need(count, current, "users")
    if need == 0:
        return current
    password_hash = _password_hash()
    specs = [(start, size, password_hash) for start, size in _offset_specs(need, current)]
    return _bulk_insert(session, User, _chunked(_user_chunk, specs, need), "users")


def seed_books(session, count: int) -> int:
    current = count_of(session, Book)
    need = _need(count, current, "books")
    if need == 0:
        return current
    specs = _offset_specs(need, current)
    return _bulk_insert(session, Book, _chunked(_book_chunk, specs, need), "books")


def seed_orders(session, count: int) -> int:
    current = count_of(session, Order)
    need = _need(count, current, "orders")
    if need == 0:
        return current
    user_range = _id_range(session, User)
    book_range = _id_range(session, Book)
    specs = [(size, user_range, book_range) for _, size in _offset_specs(need)]
    return _bulk_insert(session, Order, _chunked(_order_chunk, specs, need), "orders")


def _id_range(session, model):
    lo, hi = session.query(func.min(model.id), func.max(model.id)).one()
    if lo is None:
        raise SeedError(
            f"No {model.__name__} records exist. Seed users and books first."
        )
    return lo, hi


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
