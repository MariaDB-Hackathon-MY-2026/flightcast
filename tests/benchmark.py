"""
Performance benchmark: native system-versioned FOR SYSTEM_TIME AS OF
vs a manually-managed valid_from/valid_to history table.

Run:
  docker compose exec app python tests/benchmark.py

Writes:
  tests/benchmark_results.csv   — raw timing data
  docs/benchmark_chart.png      — bar chart for Elegant.md
"""
from __future__ import annotations

import csv
import pathlib
import statistics
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

import mariadb
from flightcast.db.connection import get_connection

REPS_SELECT = 100
REPS_INSERT = 30
WARMUP = 10
RESULTS_CSV = pathlib.Path(__file__).parent / "benchmark_results.csv"
CHART_PATH = pathlib.Path(__file__).parents[1] / "docs" / "benchmark_chart.png"
CHART_PATH.parent.mkdir(parents=True, exist_ok=True)


# ── Setup ─────────────────────────────────────────────────────────────────────

def _setup_manual_table(conn: mariadb.Connection) -> None:
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS forecasts_manual_history")
    cur.execute(
        """
        CREATE TABLE forecasts_manual_history (
            id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            forecast_run_id  INT UNSIGNED    NOT NULL,
            route_id         INT             NOT NULL,
            forecast_date    DATE            NOT NULL,
            predicted_demand DOUBLE          NOT NULL,
            lower_bound      DOUBLE          NOT NULL,
            upper_bound      DOUBLE          NOT NULL,
            model_version    VARCHAR(32)     NOT NULL,
            valid_from       DATETIME(6)     NOT NULL,
            valid_to         DATETIME(6)     NOT NULL DEFAULT '9999-12-31 00:00:00',
            PRIMARY KEY (id),
            -- Covering index matching the native query pattern
            INDEX idx_manual (route_id, forecast_date, valid_from, valid_to,
                              predicted_demand, lower_bound, upper_bound, model_version)
        ) ENGINE=InnoDB
        """
    )
    conn.commit()


def _copy_data_to_manual(conn: mariadb.Connection) -> None:
    """Mirror the current live forecasts rows into the manual table."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO forecasts_manual_history
            (forecast_run_id, route_id, forecast_date, predicted_demand,
             lower_bound, upper_bound, model_version, valid_from, valid_to)
        SELECT forecast_run_id, route_id, forecast_date, predicted_demand,
               lower_bound, upper_bound, model_version,
               ROW_START AS valid_from, ROW_END AS valid_to
        FROM forecasts FOR SYSTEM_TIME ALL
        """
    )
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM forecasts_manual_history")
    print(f"  Manual table seeded: {cur.fetchone()[0]} rows")


# ── Timing harness ────────────────────────────────────────────────────────────

def _time_query(conn: mariadb.Connection, sql: str, params: tuple, reps: int) -> list[float]:
    cur = conn.cursor()
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        cur.execute(sql, params)
        cur.fetchall()
        times.append((time.perf_counter() - t0) * 1000)
    return times


def _warmup(conn: mariadb.Connection, sql: str, params: tuple) -> None:
    cur = conn.cursor()
    for _ in range(WARMUP):
        cur.execute(sql, params)
        cur.fetchall()


# ── Scenarios ─────────────────────────────────────────────────────────────────

def _get_as_of_ts(conn: mariadb.Connection) -> str:
    cur = conn.cursor()
    cur.execute(
        "SELECT row_start_ts FROM batch_run_mapping ORDER BY row_start_ts LIMIT 1 OFFSET 2"
    )
    row = cur.fetchone()
    if row:
        return str(row[0])
    return "2026-02-01 00:00:00"


def _get_route_id(conn: mariadb.Connection) -> int:
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT route_id FROM forecasts LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else 1


def run_benchmarks(conn: mariadb.Connection) -> list[dict]:
    as_of = _get_as_of_ts(conn)
    rid = _get_route_id(conn)
    print(f"  as_of={as_of}, route_id={rid}")

    results = []

    # ── (b) Point lookup ──────────────────────────────────────────────────────
    sql_native = (
        "SELECT route_id, forecast_date, predicted_demand, lower_bound, upper_bound, model_version "
        "FROM forecasts FOR SYSTEM_TIME AS OF ? WHERE route_id = ? ORDER BY forecast_date"
    )
    sql_manual = (
        "SELECT route_id, forecast_date, predicted_demand, lower_bound, upper_bound, model_version "
        "FROM forecasts_manual_history "
        "WHERE valid_from <= ? AND valid_to > ? AND route_id = ? ORDER BY forecast_date"
    )
    print("  Warming up (b) point lookup...")
    _warmup(conn, sql_native, (as_of, rid))
    _warmup(conn, sql_manual, (as_of, as_of, rid))

    t_native = _time_query(conn, sql_native, (as_of, rid), REPS_SELECT)
    t_manual = _time_query(conn, sql_manual, (as_of, as_of, rid), REPS_SELECT)
    results.append({
        "scenario": "(b) Point lookup",
        "variant": "native", "median_ms": statistics.median(t_native),
        "p95_ms": sorted(t_native)[int(0.95 * len(t_native))],
    })
    results.append({
        "scenario": "(b) Point lookup",
        "variant": "manual", "median_ms": statistics.median(t_manual),
        "p95_ms": sorted(t_manual)[int(0.95 * len(t_manual))],
    })
    print(f"    native median={statistics.median(t_native):.2f}ms  "
          f"manual median={statistics.median(t_manual):.2f}ms")

    # ── (c) Audit sweep (10 timestamps) ───────────────────────────────────────
    cur = conn.cursor()
    cur.execute(
        "SELECT row_start_ts FROM batch_run_mapping ORDER BY row_start_ts"
    )
    timestamps = [str(r[0]) for r in cur.fetchall()]
    if not timestamps:
        timestamps = [as_of]

    def _audit_sweep_native():
        t0 = time.perf_counter()
        for ts in timestamps:
            cur.execute(sql_native, (ts, rid))
            cur.fetchall()
        return (time.perf_counter() - t0) * 1000

    def _audit_sweep_manual():
        t0 = time.perf_counter()
        for ts in timestamps:
            cur.execute(sql_manual, (ts, ts, rid))
            cur.fetchall()
        return (time.perf_counter() - t0) * 1000

    print("  Running (c) audit sweep...")
    sweep_native = [_audit_sweep_native() for _ in range(REPS_SELECT)]
    sweep_manual = [_audit_sweep_manual() for _ in range(REPS_SELECT)]
    results.append({
        "scenario": f"(c) Audit sweep ({len(timestamps)} ts)",
        "variant": "native", "median_ms": statistics.median(sweep_native),
        "p95_ms": sorted(sweep_native)[int(0.95 * len(sweep_native))],
    })
    results.append({
        "scenario": f"(c) Audit sweep ({len(timestamps)} ts)",
        "variant": "manual", "median_ms": statistics.median(sweep_manual),
        "p95_ms": sorted(sweep_manual)[int(0.95 * len(sweep_manual))],
    })
    print(f"    native median={statistics.median(sweep_native):.2f}ms  "
          f"manual median={statistics.median(sweep_manual):.2f}ms")

    # ── (e) Full snapshot ─────────────────────────────────────────────────────
    sql_full_native = (
        "SELECT route_id, forecast_date, predicted_demand, model_version "
        "FROM forecasts FOR SYSTEM_TIME AS OF ?"
    )
    sql_full_manual = (
        "SELECT route_id, forecast_date, predicted_demand, model_version "
        "FROM forecasts_manual_history WHERE valid_from <= ? AND valid_to > ?"
    )
    print("  Running (e) full snapshot...")
    _warmup(conn, sql_full_native, (as_of,))
    _warmup(conn, sql_full_manual, (as_of, as_of))
    t_fn = _time_query(conn, sql_full_native, (as_of,), REPS_SELECT)
    t_fm = _time_query(conn, sql_full_manual, (as_of, as_of), REPS_SELECT)
    results.append({
        "scenario": "(e) Full snapshot",
        "variant": "native", "median_ms": statistics.median(t_fn),
        "p95_ms": sorted(t_fn)[int(0.95 * len(t_fn))],
    })
    results.append({
        "scenario": "(e) Full snapshot",
        "variant": "manual", "median_ms": statistics.median(t_fm),
        "p95_ms": sorted(t_fm)[int(0.95 * len(t_fm))],
    })
    print(f"    native median={statistics.median(t_fn):.2f}ms  "
          f"manual median={statistics.median(t_fm):.2f}ms")

    # ── Storage comparison ────────────────────────────────────────────────────
    cur.execute(
        """
        SELECT TABLE_NAME,
               ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024, 1) AS total_kb,
               TABLE_ROWS
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN ('forecasts', 'forecasts_manual_history')
        """
    )
    for row in cur.fetchall():
        print(f"  Storage: {row[0]}  {row[1]} KB  {row[2]} rows")

    return results


# ── Chart ─────────────────────────────────────────────────────────────────────

def render_chart(results: list[dict]) -> None:
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
    except ImportError:
        print("matplotlib not available — skipping chart render")
        return

    df = pd.DataFrame(results)
    pivot = df.pivot(index="scenario", columns="variant", values="median_ms")

    fig, ax = plt.subplots(figsize=(10, 5))
    pivot.plot(kind="bar", ax=ax, color=["#2563EB", "#DC2626"], width=0.6)
    ax.set_ylabel("Median latency (ms)")
    ax.set_xlabel("")
    ax.set_title("Native System-Versioned vs Manual History Table\n(lower = faster)")
    ax.legend(["Native (MariaDB temporal)", "Manual valid_from/valid_to"])
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(str(CHART_PATH), dpi=150)
    print(f"  Chart saved to {CHART_PATH}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Connecting to MariaDB...")
    conn = get_connection()

    print("Checking for forecast data...")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM forecasts FOR SYSTEM_TIME ALL")
    n = cur.fetchone()[0]
    if n == 0:
        print("ERROR: No forecast data. Run bootstrap first:")
        print("  docker compose exec app python -m flightcast.bootstrap")
        sys.exit(1)
    print(f"  {n} total forecast rows in history")

    print("\nSetting up manual history table...")
    _setup_manual_table(conn)
    _copy_data_to_manual(conn)

    print("\nRunning benchmarks...")
    results = run_benchmarks(conn)

    # Write CSV
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario", "variant", "median_ms", "p95_ms"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResults saved to {RESULTS_CSV}")

    print("Rendering chart...")
    render_chart(results)

    # Cleanup
    cur.execute("DROP TABLE IF EXISTS forecasts_manual_history")
    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
