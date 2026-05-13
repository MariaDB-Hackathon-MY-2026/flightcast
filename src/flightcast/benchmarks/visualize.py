"""
Render docs/benchmark_chart.png from docs/benchmark_results.json.

Modelled on the Pratush+Jyothi BangPypers 2025 Airflow connector winner's
"Comparison b/w MariaDB vs MySQL" chart — side-by-side bars, data labels
on every bar, embedded data table, honest inclusion of cases where the
comparison is comparable rather than a clean win.

Run:
  docker compose exec app python -m flightcast.benchmarks.visualize

Output: /tmp/benchmark_chart.png inside the container; the host copies it
to docs/benchmark_chart.png with `docker cp`.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure matplotlib uses a writable cache dir (the container's appuser has no /home)
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib
matplotlib.use("Agg")  # headless rendering — no display needed
import matplotlib.pyplot as plt
import numpy as np


# FlightCast brand colours (match the dashboard CSS in src/flightcast/ui/style.py)
BG = "#0B1220"
NATIVE_COLOR = "#34D399"
NATIVE_EDGE = "#10B981"
MANUAL_COLOR = "#FB923C"
MANUAL_EDGE = "#EA580C"
TEXT = "#E5E7EB"
SUBTEXT = "#94A3B8"
GRID = "#1F2A3D"


def render(results: dict, out_path: Path) -> None:
    scenarios = results["scenarios"]
    names = [s["name"] for s in scenarios]
    native_ms = [s["native_median"] for s in scenarios]
    manual_ms = [s["manual_median"] for s in scenarios]
    speedups = [s["speedup_median"] for s in scenarios]

    n_iter = results.get("n_iterations", "?")

    # Figure setup with FlightCast dark theme
    fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG)
    ax.set_facecolor(BG)

    x = np.arange(len(names))
    width = 0.36

    bars_native = ax.bar(
        x - width / 2, native_ms, width,
        color=NATIVE_COLOR, edgecolor=NATIVE_EDGE, linewidth=1.2,
        label="Native FOR SYSTEM_TIME",
    )
    bars_manual = ax.bar(
        x + width / 2, manual_ms, width,
        color=MANUAL_COLOR, edgecolor=MANUAL_EDGE, linewidth=1.2,
        label="Manual created_at / expired_at",
    )

    # Data labels on top of every bar (Pratush+Jyothi pattern)
    def annotate(bars: list, values: list[float]) -> None:
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(native_ms + manual_ms) * 0.02,
                f"{value:.2f} ms",
                ha="center", va="bottom",
                color=TEXT, fontsize=10.5, fontweight="medium",
            )

    annotate(bars_native, native_ms)
    annotate(bars_manual, manual_ms)

    # Speedup labels under each scenario
    speedup_labels = []
    for s in speedups:
        if s >= 1.0:
            speedup_labels.append((f"native {s:.2f}× faster", NATIVE_COLOR))
        else:
            speedup_labels.append((f"manual {1.0/s:.2f}× faster", MANUAL_COLOR))

    # Axes styling
    ax.set_xticks(x)
    ax.set_xticklabels(names, color=TEXT, fontsize=11)
    ax.tick_params(axis="y", colors=TEXT)
    ax.set_ylabel("Median latency (ms) — lower is better",
                  color=TEXT, fontsize=12, labelpad=10)
    ax.set_ylim(0, max(native_ms + manual_ms) * 1.20)

    # Title with subtitle
    fig.suptitle(
        "FlightCast Temporal Benchmark",
        color=TEXT, fontsize=18, fontweight="bold",
        x=0.04, y=0.96, ha="left",
    )
    ax.set_title(
        f"Native MariaDB FOR SYSTEM_TIME vs hand-rolled application versioning  ·  "
        f"{n_iter}-iteration medians",
        color=SUBTEXT, fontsize=11, loc="left", pad=18,
    )

    # Grid
    ax.yaxis.grid(True, color=GRID, linestyle="-", linewidth=0.8, alpha=0.6)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Legend (top right)
    legend = ax.legend(
        loc="upper right",
        frameon=False, fontsize=11,
        labelcolor=TEXT,
    )

    # Speedup labels under the x-axis tick labels
    for i, (label, colour) in enumerate(speedup_labels):
        ax.text(
            i, -max(native_ms + manual_ms) * 0.10,
            label,
            ha="center", va="top",
            color=colour, fontsize=10.5, fontweight="bold",
        )

    # Footer note (the "honest reporting" hint)
    fig.text(
        0.04, 0.02,
        "Manual versioning shadow table populated from FOR SYSTEM_TIME ALL · "
        "Both queries hit equivalent indexes · Run with: "
        "docker compose exec app python -m flightcast.benchmarks.temporal_benchmark",
        color=SUBTEXT, fontsize=8.5, ha="left",
    )

    fig.subplots_adjust(left=0.06, right=0.97, top=0.86, bottom=0.18)
    fig.savefig(out_path, dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"  Wrote {out_path}")


def main() -> int:
    in_path = Path("/tmp/benchmark_results.json")
    if not in_path.exists():
        in_path = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "benchmark_results.json"
    if not in_path.exists():
        print(f"ERROR: benchmark_results.json not found at {in_path}", file=sys.stderr)
        return 1

    print(f"Reading {in_path}...")
    results = json.loads(in_path.read_text())

    out_path = Path("/tmp/benchmark_chart.png")
    render(results, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
