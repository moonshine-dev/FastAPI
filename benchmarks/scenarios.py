"""Benchmark scenario registry.

Each scenario describes one HTTP request pattern. Add new scenarios to
SCENARIOS and they become available in the CLI via --scenario <name>.
"""

import random
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    method: str
    path: str
    seed_model: str  # which table must be seeded before running ("books", ...)
    default_counts: tuple
    build_params: Callable[[list], dict]  # (title pool) -> request params


def _search_books_params(titles: list) -> dict:
    return {
        "title": random.choice(titles),
        "page": 1,
        "size": 10,
    }


SCENARIOS = {
    "search_books": Scenario(
        name="search_books",
        description="GET /books/search - exact title match search",
        method="GET",
        path="/books/search",
        seed_model="books",
        default_counts=(1000, 2000, 3000, 50000, 10000000),
        build_params=_search_books_params,
    ),
}
