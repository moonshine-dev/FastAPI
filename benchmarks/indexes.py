"""Drop / recreate the secondary (non-PK) indexes defined in models.py."""

from sqlalchemy import text

from database import Base

import models  # noqa: F401  (populates Base.metadata with tables/indexes)

# Names of all non-primary-key indexes declared on the models.
SECONDARY_INDEXES = [
    ix.name
    for table in Base.metadata.tables.values()
    for ix in table.indexes
]


def drop_indexes(session) -> None:
    for name in SECONDARY_INDEXES:
        session.execute(text(f"DROP INDEX IF EXISTS {name}"))
    session.commit()


def recreate_indexes(engine) -> None:
    # Explicit per-index create: create_all skips indexes on already-existing tables.
    for table in Base.metadata.tables.values():
        for ix in table.indexes:
            ix.create(engine, checkfirst=True)
