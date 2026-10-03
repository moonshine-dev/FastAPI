"""Library Management System application package.

Importing this package registers every SQLAlchemy model on the shared Base,
so ``Base.metadata`` is complete for create_all / seeding / benchmarks.
"""

from app.books.models import Book  # noqa: F401
from app.orders.models import Order  # noqa: F401
from app.users.models import User  # noqa: F401

__all__ = ["User", "Book", "Order"]
