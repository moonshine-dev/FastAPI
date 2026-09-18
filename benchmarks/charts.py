"""Benchmark result charts (matplotlib). All labels/text in English."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PLOT_SERIES = [
    ("median_ms", "p50"),
    ("p96_ms", "p96"),
    ("p99_ms", "p99"),
]

MODE_LABEL = {"with": "with indexes", "without": "without indexes"}
MODE_COLOR = {"with": "#1f77b4", "without": "#ff7f0e"}  # blue / orange
MODE_ORDER = ["with", "without"]


def _fmt_count(n: int) -> str:
    if n >= 1_000_000:
        value = n / 1_000_000
        return f"{value:g}M"
    if n >= 1_000:
        value = n / 1_000
        return f"{value:g}k"
    return str(n)


def _group_by_mode(rows: list) -> dict:
    groups = {}
    for row in rows:
        groups.setdefault(row["index_mode"], []).append(row)
    return groups


def _percentile_line_chart(groups: dict, column: str, label: str,
                           scenario: str, out_path: Path) -> None:
    """One line chart per statistic: with-indexes (blue) and without (orange)."""
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = None
    for mode in MODE_ORDER:
        rows = groups.get(mode)
        if not rows:
            continue
        rows = sorted(rows, key=lambda r: r["records"])
        x = [r["records"] for r in rows]
        ax.plot(x, [r[column] for r in rows], marker="o",
                color=MODE_COLOR[mode], label=MODE_LABEL[mode])
    if x is None:
        plt.close(fig)
        return
    ax.set_xscale("log")
    if x[0] and x[-1] / max(x[0], 1) > 100:
        ax.set_yscale("log")
    ax.set_title(f"{scenario} - {label} latency by record count")
    ax.set_xlabel("Record count")
    ax.set_ylabel("Latency (ms)")
    ax.set_xticks(x)
    ax.set_xticklabels([_fmt_count(v) for v in x])
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(title="Index mode")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _comparison_chart(with_rows: list, without_rows: list, out_path: Path) -> None:
    scenario = with_rows[0]["scenario"]
    with_rows = sorted(with_rows, key=lambda r: r["records"])
    without_rows = sorted(without_rows, key=lambda r: r["records"])
    counts = [r["records"] for r in with_rows]
    x_labels = [_fmt_count(c) for c in counts]
    positions = range(len(counts))
    bar_width = 0.38

    fig, axes = plt.subplots(1, len(PLOT_SERIES), figsize=(15, 5.5), sharey=False)
    for ax, (column, label) in zip(axes, PLOT_SERIES):
        with_vals = [r[column] for r in with_rows]
        without_vals = [r[column] for r in without_rows]
        ax.bar([p - bar_width / 2 for p in positions], with_vals, bar_width,
               label="with indexes", color=MODE_COLOR["with"])
        ax.bar([p + bar_width / 2 for p in positions], without_vals, bar_width,
               label="without indexes", color=MODE_COLOR["without"])
        ax.set_xticks(list(positions))
        ax.set_xticklabels(x_labels, rotation=30)
        ax.set_title(f"{label} latency")
        ax.set_xlabel("Record count")
        ax.set_ylabel("Latency (ms)")
        ax.grid(True, axis="y", alpha=0.3)
        if counts and max(max(with_vals), max(without_vals)) / max(min(min(with_vals), min(without_vals)), 0.01) > 100:
            ax.set_yscale("log")
    axes[0].legend()
    fig.suptitle(f"{scenario} - with vs without indexes")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def make_charts(rows: list, out_dir: Path, scenario_name: str) -> list:
    """One line chart per statistic (p50/p96/p99); when both modes exist, also a comparison chart."""
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = _group_by_mode(rows)
    paths = []

    has_both = "with" in groups and "without" in groups
    for column, label in PLOT_SERIES:
        if has_both:
            p = out_dir / f"{scenario_name}_{label}.png"
            _percentile_line_chart(groups, column, label, scenario_name, p)
        else:
            only_mode = "with" if "with" in groups else "without"
            p = out_dir / f"{scenario_name}_{label}_{only_mode}.png"
            _percentile_line_chart({only_mode: groups[only_mode]}, column, label, scenario_name, p)
        paths.append(p)

    if has_both:
        p = out_dir / f"{scenario_name}_comparison.png"
        _comparison_chart(groups["with"], groups["without"], p)
        paths.append(p)

    return paths
