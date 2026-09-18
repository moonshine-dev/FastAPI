"""HTTP benchmark runner.

Executes N requests per (scenario, records-count, index-mode) combination
with httpx against a running FastAPI server and collects latency statistics.
"""

import math
import random
import statistics
import time

import httpx

import models
from benchmarks.indexes import drop_indexes, recreate_indexes
from benchmarks.scenarios import Scenario
from seed import SeedError, count_of, seed

TITLES_SAMPLE_SIZE = 200


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #

STAT_COLUMNS = [
    "mean_ms", "q1_ms", "median_ms", "q3_ms", "p96_ms", "p99_ms", "min_ms", "max_ms",
]


def _percentile(sorted_vals: list, q: float) -> float:
    """Linear-interpolation percentile (q in 0..100), numpy-compatible."""
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = (n - 1) * q / 100
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def summarize(durations_ms: list) -> dict:
    ordered = sorted(durations_ms)
    return {
        "mean_ms": round(statistics.mean(ordered), 3),
        "q1_ms": round(_percentile(ordered, 25), 3),
        "median_ms": round(_percentile(ordered, 50), 3),
        "q3_ms": round(_percentile(ordered, 75), 3),
        "p96_ms": round(_percentile(ordered, 96), 3),
        "p99_ms": round(_percentile(ordered, 99), 3),
        "min_ms": round(ordered[0], 3),
        "max_ms": round(ordered[-1], 3),
    }


# --------------------------------------------------------------------------- #
# Data preparation
# --------------------------------------------------------------------------- #

def ensure_seed(session, seed_model: str, count: int) -> None:
    seed(session, count, model=seed_model)


def sample_titles(session, sample_size: int = TITLES_SAMPLE_SIZE) -> list:
    total = count_of(session, models.Book)
    if total == 0:
        raise SeedError("books table is empty - run seed before benchmarking.")
    sample_size = min(sample_size, total)
    # ids are contiguous because seeding only appends (see seed.py top-up rule)
    ids = random.sample(range(1, total + 1), sample_size)
    rows = session.query(models.Book.id, models.Book.title).filter(models.Book.id.in_(ids)).all()
    titles = [t for _, t in rows]
    if not titles:
        raise SeedError("Could not sample any book titles.")
    return titles


# --------------------------------------------------------------------------- #
# Request execution
# --------------------------------------------------------------------------- #

def run_phase(client: httpx.Client, scenario: Scenario, titles: list,
              requests: int, warmup: int, label: str) -> list:
    durations = []
    failures = 0
    for i in range(-warmup, requests):
        params = scenario.build_params(titles)
        start = time.perf_counter()
        resp = client.request(scenario.method, scenario.path, params=params)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if i < 0:
            continue  # warm-up, not measured
        if resp.status_code != 200:
            failures += 1
            if failures <= 3:
                print(f"  WARNING: non-200 response ({resp.status_code}) - excluded from stats")
            continue
        durations.append(elapsed_ms)
    if not durations:
        raise RuntimeError(f"All requests failed for {label}. Is the server running at the given URL?")
    if failures:
        print(f"  {failures}/{requests} requests failed and were excluded from stats")
    return durations


# --------------------------------------------------------------------------- #
# Suite orchestration
# --------------------------------------------------------------------------- #

def run_suite(engine, session, base_url: str, scenario: Scenario, counts: list,
              requests: int = 100, indexes_mode: str = "both", warmup: int = 5) -> list:
    """Run the benchmark suite. Returns one result row per (count, index_mode)."""
    if indexes_mode not in ("with", "without", "both"):
        raise ValueError(f"Invalid --indexes value: {indexes_mode!r} (use: with | without | both)")

    phases = ["with", "without"] if indexes_mode == "both" else [indexes_mode]
    rows = []

    try:
        for count in sorted(counts):
            print(f"\n=== Record count: {count} ===")
            ensure_seed(session, scenario.seed_model, count)
            titles = sample_titles(session)

            for phase in phases:
                if phase == "without":
                    print("Dropping secondary indexes ...")
                    drop_indexes(session)
                else:
                    print("Ensuring secondary indexes exist ...")
                    recreate_indexes(engine)

                label = f"{scenario.name} / {phase} / {count}"
                print(f"--- {label} ---")
                with httpx.Client(base_url=base_url, timeout=60.0) as client:
                    durations = run_phase(client, scenario, titles, requests, warmup, label)

                stats = summarize(durations)
                rows.append({
                    "scenario": scenario.name,
                    "index_mode": phase,
                    "records": count,
                    "requests": len(durations),
                    **stats,
                })
                print(
                    f"records={count} mode={phase} "
                    f"mean={stats['mean_ms']}ms p50={stats['median_ms']}ms "
                    f"p96={stats['p96_ms']}ms p99={stats['p99_ms']}ms"
                )
    finally:
        # Always leave the database in its default (indexed) state.
        print("\nRestoring secondary indexes ...")
        recreate_indexes(engine)

    return rows
