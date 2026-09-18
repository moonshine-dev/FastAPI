"""Project CLI (typer).

Usage examples:
    python -m benchmarks.cli resetdb --yes
    python -m benchmarks.cli seed --count 10000 --model all
    python -m benchmarks.cli benchmark --scenario search_books \
        --counts 1000 2000 3000 50000 --requests 100 --indexes both \
        --url http://localhost:8000
"""

from pathlib import Path

import typer
from sqlalchemy import text

from database import Base, engine, SessionLocal
import models  # noqa: F401  (populates Base.metadata)

app = typer.Typer(help="Database reset / seed / benchmark utilities.", no_args_is_help=True)


@app.command()
def resetdb(yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt.")):
    """Drop all tables and recreate them from the models."""
    if not yes:
        confirm = typer.confirm("This will DROP all tables and their data. Continue?")
        if not confirm:
            raise typer.Abort()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    typer.echo("All tables dropped and recreated successfully.")


@app.command()
def seed(
    count: int = typer.Option(1000, "--count", "-c", min=1, help="Number of records to create."),
    model: str = typer.Option("all", "--model", "-m", help="users | books | orders | all"),
):
    """Seed the database with faker-generated records (tops up to --count)."""
    from seed import SeedError, seed as seed_db

    session = SessionLocal()
    try:
        result = seed_db(session, count, model=model)
        for name, total in result.items():
            typer.echo(f"{name}: {total} rows")
    except SeedError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    finally:
        session.close()


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def benchmark(
    ctx: typer.Context,
    scenario_name: str = typer.Option(
        "search_books", "--scenario", "-s", help="Scenario name (see --list-scenarios)."
    ),
    counts: str = typer.Option(
        None, "--counts", "-n",
        help='Record counts to benchmark, e.g. --counts 1000 2000 50000 (or comma separated). '
             'Defaults to the scenario\'s own list.',
    ),
    requests: int = typer.Option(100, "--requests", "-r", min=1, help="Requests per data point."),
    indexes: str = typer.Option(
        "both", "--indexes", "-i", help="with | without | both - which index modes to run."
    ),
    url: str = typer.Option("http://localhost:8000", "--url", "-u", help="Base URL of the running server."),
    out: Path = typer.Option(
        Path("results") / "benchmark_results.csv", "--out", "-o", help="CSV output file path."
    ),
    charts: bool = typer.Option(True, "--charts/--no-charts", help="Also generate PNG charts."),
    charts_dir: Path = typer.Option(
        Path("results") / "charts", "--charts-dir", help="Directory for chart PNG files."
    ),
    list_scenarios: bool = typer.Option(False, "--list-scenarios", help="List available scenarios and exit."),
    warmup: int = typer.Option(5, "--warmup", min=0, help="Unmeasured warm-up requests per data point."),
):
    """Run the HTTP benchmark suite against a running server."""
    from benchmarks.charts import make_charts
    from benchmarks.runner import run_suite
    from benchmarks.scenarios import SCENARIOS
    from seed import SeedError

    if list_scenarios:
        for name, scenario in SCENARIOS.items():
            typer.echo(f"{name}: {scenario.description}")
            typer.echo(f"  default counts: {' '.join(map(str, scenario.default_counts))}")
        return

    if scenario_name not in SCENARIOS:
        typer.secho(
            f"Unknown scenario '{scenario_name}'. Available: {', '.join(SCENARIOS)}",
            fg=typer.colors.RED, err=True,
        )
        raise typer.Exit(code=1)
    scenario = SCENARIOS[scenario_name]

    if indexes not in ("with", "without", "both"):
        typer.secho(f"Invalid --indexes value: {indexes!r} (use: with | without | both)",
                    fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    parsed_counts = []
    tokens = []
    if counts:
        tokens.extend(counts.replace(",", " ").split())
    # Allow unquoted space-separated values: --counts 1000 2000 50000
    tokens.extend(ctx.args)
    for token in tokens:
        if not token.lstrip("+-").isdigit():
            typer.secho(f"Invalid record count: {token!r} (must be a positive integer)",
                        fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        parsed_counts.append(int(token))
    effective_counts = sorted(set(parsed_counts)) if parsed_counts else list(scenario.default_counts)

    # Sanity check: server must be reachable before doing any heavy work.
    import httpx

    try:
        httpx.get(url.rstrip("/") + "/", timeout=10.0)
    except httpx.HTTPError as exc:
        typer.secho(f"Server is not reachable at {url}: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Scenario: {scenario_name} | counts: {effective_counts} | "
               f"requests: {requests} | indexes: {indexes}")
    session = SessionLocal()
    try:
        rows = run_suite(
            engine, session, base_url=url.rstrip("/"),
            scenario=scenario, counts=effective_counts,
            requests=requests, indexes_mode=indexes, warmup=warmup,
        )
    except SeedError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    finally:
        session.close()

    # CSV output
    import csv

    fieldnames = list(rows[0].keys())
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    typer.echo(f"\nResults written to {out}")

    # Charts
    if charts:
        paths = make_charts(rows, charts_dir, scenario_name)
        for path in paths:
            typer.echo(f"Chart written to {path}")


if __name__ == "__main__":
    app()
