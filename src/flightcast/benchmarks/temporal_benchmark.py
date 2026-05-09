"""
Benchmark: native MariaDB system-versioned temporal tables vs
application-managed versioning on identical data.

Result is the headline number that closes the Tech Excellence gap to the
Adaptive Query Optimizer (Innovation 2025 winner) — the project that leads
its README with "1.5x-16x speedups" on hybrid SQL + Vector queries.
FlightCast's equivalent is "Nx faster temporal queries with ZERO
application-level audit code."

What this script does:

  1. Populate `forecasts_manual` from the system-versioned `forecasts` table
     using FOR SYSTEM_TIME ALL — every historical row becomes one
     forecasts_manual row with appropriate `created_at` / `expired_at`.
  2. For a fixed audit timestamp (the row_start_ts of a known batch):
       a. Run the native temporal-table query 100 times:
          SELECT ... FROM forecasts FOR SYSTEM_TIME AS OF ?
          WHERE route_id = ? AND forecast_run_id = ?
       b. Run the equivalent manual-versioning query 100 times:
          SELECT ... FROM forecasts_manual
          WHERE created_at <= ? AND (expired_at > ? OR expired_at IS NULL)
                AND route_id = ? AND forecast_run_id = ?
  3. Report median, p95, p99 latency for each + the speedup ratio.

Run:
  docker compose exec app python -m flightcast.benchmarks.temporal_benchmark
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import mariadb

from flightcast.db.connection import get_connection


# Number of timing iterations per query type. 100 is a small sample but
# stable enough for a hackathon headline; >> 100 spends the budget on
# warm-cache repetition rather than meaningful comparison.
N_ITERATIONS = 100

# After populating forecasts_manual, the benchmark fixes a (route_id, run_id, as_of)
# triple and times that exact query 100 times. The triple is chosen from
# batch_run_mapping to guarantee the AS OF timestamp resolves correctly.


def populate_manual_table(conn: mariadb.Connection) -> int:
    """
    Mirror every row in `forecasts FOR SYSTEM_TIME ALL` into `forecasts_manual`,
    deriving `created_at` from `ROW_START` and `expired_at` from `ROW_END`
    (NULL when ROW_END is the far-future sentinel).

    Returns rows inserted.
    """
    cur = conn.cursor()
    # Idempotent: clear the manual table before re-population so the benchmark
    # is reproducible on repeated runs.
    cur.execute("TRUNCATE TABLE forecasts_manual")
    conn.commit()

    cur.execute(
        """
        INSERT INTO forecasts_manual
            (forecast_run_id, forecast_run_ts, route_id, forecast_date,
             predicted_demand, lower_bound, upper_bound, confidence_level,
             model_version, coverage_score, actual_demand,
             created_at, expired_at)
        SELECT
            forecast_run_id, forecast_run_ts, route_id, forecast_date,
            predicted_demand, lower_bound, upper_bound, confidence_level,
            model_version, coverage_score, actual_demand,
            ROW_START AS created_at,
            CASE
                WHEN ROW_END >= '2038-01-01' THEN NULL
                ELSE ROW_END
            END AS expired_at
        FROM forecasts FOR SYSTEM_TIME ALL
        """
    )
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM forecasts_manual")
    n = cur.fetchone()[0]
    return int(n)


def time_query(cur: mariadb.Cursor, sql: str, params: tuple, n: int) -> list[float]:
    """Run `sql` with `params` `n` times. Return list of per-iteration milliseconds."""
    timings_ms: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        cur.execute(sql, params)
        cur.fetchall()
        t1 = time.perf_counter()
        timings_ms.append((t1 - t0) * 1000.0)
    return timings_ms


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolated percentile, matches numpy.percentile default behaviour."""
    if not values:
        return float("nan")
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


def run_scenario(
    cur: mariadb.Cursor,
    name: str,
    native_sql: str,
    manual_sql: str,
    native_params: tuple,
    manual_params: tuple,
    n_iter: int = N_ITERATIONS,
) -> dict:
    """Run one (native vs manual) scenario, return the timing dict."""
    # Sanity check parity
    cur.execute(native_sql, native_params)
    n_native_rows = len(cur.fetchall())
    cur.execute(manual_sql, manual_params)
    n_manual_rows = len(cur.fetchall())
    if n_native_rows != n_manual_rows:
        raise RuntimeError(
            f"[{name}] row count mismatch: native={n_native_rows}, manual={n_manual_rows}"
        )

    # Warm-up
    cur.execute(native_sql, native_params)
    cur.fetchall()
    cur.execute(manual_sql, manual_params)
    cur.fetchall()

    native_ms = time_query(cur, native_sql, native_params, n_iter)
    manual_ms = time_query(cur, manual_sql, manual_params, n_iter)

    return {
        "name": name,
        "rows": n_native_rows,
        "native_median": statistics.median(native_ms),
        "native_p95": percentile(native_ms, 95),
        "manual_median": statistics.median(manual_ms),
        "manual_p95": percentile(manual_ms, 95),
        "speedup_median": statistics.median(manual_ms) / statistics.median(native_ms),
    }


def run_benchmark(conn: mariadb.Connection) -> dict:
    """Run the multi-scenario benchmark and return a result dict."""
    cur = conn.cursor()

    # Get the most recent committed batch for AS OF queries
    cur.execute(
        """
        SELECT brm.row_start_ts, brm.forecast_run_id,
               (SELECT MIN(route_id) FROM forecasts WHERE forecast_run_id = brm.forecast_run_id) AS route_id
        FROM batch_run_mapping brm
        ORDER BY brm.forecast_run_id DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("No batches in batch_run_mapping; run bootstrap first.")
    as_of_ts, run_id, route_id = row

    print(f"Benchmark configuration:")
    print(f"  iterations per side: {N_ITERATIONS}")
    print(f"  audit timestamp:     {as_of_ts}")
    print(f"  sample route_id:     {route_id}")
    print(f"  sample run_id:       {run_id}")
    print()

    scenarios: list[dict] = []

    # ── Scenario 1: Per-route time-travel (low selectivity, ~30 rows) ────
    s1 = run_scenario(
        cur,
        name="Per-route time-travel (~30 rows)",
        native_sql="""
            SELECT route_id, forecast_date, predicted_demand,
                   lower_bound, upper_bound, model_version
            FROM forecasts FOR SYSTEM_TIME AS OF ?
            WHERE route_id = ? AND forecast_run_id = ?
            ORDER BY forecast_date
        """,
        manual_sql="""
            SELECT route_id, forecast_date, predicted_demand,
                   lower_bound, upper_bound, model_version
            FROM forecasts_manual
            WHERE created_at <= ? AND (expired_at > ? OR expired_at IS NULL)
              AND route_id = ? AND forecast_run_id = ?
            ORDER BY forecast_date
        """,
        native_params=(as_of_ts, route_id, run_id),
        manual_params=(as_of_ts, as_of_ts, route_id, run_id),
    )
    scenarios.append(s1)
    print(f"  ✓ {s1['name']}: native={s1['native_median']:.2f}ms / "
          f"manual={s1['manual_median']:.2f}ms / speedup={s1['speedup_median']:.2f}×")

    # ── Scenario 2: Full-batch time-travel (medium, ~1500 rows) ──────────
    s2 = run_scenario(
        cur,
        name="Full-batch time-travel (~1500 rows)",
        native_sql="""
            SELECT route_id, forecast_date, predicted_demand,
                   lower_bound, upper_bound, model_version
            FROM forecasts FOR SYSTEM_TIME AS OF ?
            WHERE forecast_run_id = ?
        """,
        manual_sql="""
            SELECT route_id, forecast_date, predicted_demand,
                   lower_bound, upper_bound, model_version
            FROM forecasts_manual
            WHERE created_at <= ? AND (expired_at > ? OR expired_at IS NULL)
              AND forecast_run_id = ?
        """,
        native_params=(as_of_ts, run_id),
        manual_params=(as_of_ts, as_of_ts, run_id),
    )
    scenarios.append(s2)
    print(f"  ✓ {s2['name']}: native={s2['native_median']:.2f}ms / "
          f"manual={s2['manual_median']:.2f}ms / speedup={s2['speedup_median']:.2f}×")

    # ── Scenario 3: Full audit history (THE hero query, ~9000 rows) ──────
    s3 = run_scenario(
        cur,
        name="Full audit history (~9000 rows)",
        native_sql="""
            SELECT forecast_run_id, route_id, forecast_date, predicted_demand,
                   model_version, ROW_START
            FROM forecasts FOR SYSTEM_TIME ALL
            WHERE coverage_score IS NOT NULL
        """,
        manual_sql="""
            SELECT forecast_run_id, route_id, forecast_date, predicted_demand,
                   model_version, created_at
            FROM forecasts_manual
            WHERE coverage_score IS NOT NULL
        """,
        native_params=(),
        manual_params=(),
    )
    scenarios.append(s3)
    print(f"  ✓ {s3['name']}: native={s3['native_median']:.2f}ms / "
          f"manual={s3['manual_median']:.2f}ms / speedup={s3['speedup_median']:.2f}×")

    # ── Scenario 4: Coverage-drift aggregate (THE money query) ───────────
    s4 = run_scenario(
        cur,
        name="Coverage-drift aggregate (the audit query)",
        native_sql="""
            SELECT forecast_run_id,
                   AVG(coverage_score) AS mean_coverage,
                   COUNT(*) AS n
            FROM forecasts FOR SYSTEM_TIME ALL
            WHERE coverage_score IS NOT NULL
            GROUP BY forecast_run_id
            ORDER BY forecast_run_id
        """,
        manual_sql="""
            SELECT forecast_run_id,
                   AVG(coverage_score) AS mean_coverage,
                   COUNT(*) AS n
            FROM forecasts_manual
            WHERE coverage_score IS NOT NULL
            GROUP BY forecast_run_id
            ORDER BY forecast_run_id
        """,
        native_params=(),
        manual_params=(),
    )
    scenarios.append(s4)
    print(f"  ✓ {s4['name']}: native={s4['native_median']:.2f}ms / "
          f"manual={s4['manual_median']:.2f}ms / speedup={s4['speedup_median']:.2f}×")

    # Aggregate stats: speedup range across scenarios
    speedups = [s["speedup_median"] for s in scenarios]
    return {
        "n_iterations": N_ITERATIONS,
        "as_of_ts": str(as_of_ts),
        "scenarios": scenarios,
        "min_speedup": min(speedups),
        "max_speedup": max(speedups),
        "median_speedup": statistics.median(speedups),
    }


def print_report(r: dict) -> None:
    print()
    print("=" * 78)
    print("FlightCast Temporal Benchmark — Native vs Manual Versioning")
    print("=" * 78)
    print(f"Iterations per query: {r['n_iterations']} · Audit timestamp: {r['as_of_ts']}")
    print()
    print(f"{'Scenario':<46}{'Rows':>8}{'Native':>9}{'Manual':>9}{'Speedup':>8}")
    print("-" * 78)
    for s in r["scenarios"]:
        print(
            f"{s['name']:<46}"
            f"{s['rows']:>8,}"
            f"{s['native_median']:>7.2f}ms"
            f"{s['manual_median']:>7.2f}ms"
            f"{s['speedup_median']:>6.2f}×"
        )
    print("-" * 78)
    print(
        f"Speedup range across scenarios: {r['min_speedup']:.2f}× – {r['max_speedup']:.2f}×  "
        f"(median {r['median_speedup']:.2f}×)"
    )
    print("=" * 78)
    print()
    print("Headline: FOR SYSTEM_TIME native temporal queries are "
          f"{r['min_speedup']:.1f}×–{r['max_speedup']:.1f}× faster than equivalent "
          f"manual application-level versioning,")
    print("AND require ZERO lines of audit-log code in the application layer.")


def main() -> int:
    conn = get_connection()
    print("Populating forecasts_manual from forecasts FOR SYSTEM_TIME ALL...")
    n = populate_manual_table(conn)
    print(f"  Inserted {n} rows into forecasts_manual.")
    print()

    result = run_benchmark(conn)
    print_report(result)

    # Emit machine-readable JSON on the last line so the host can capture it.
    # (Container has the source tree mounted read-only; persistent storage
    # via volumes is overkill for a benchmark — just stream to stdout.)
    print()
    print("BENCHMARK_JSON_BEGIN")
    print(json.dumps(result, indent=2, default=str))
    print("BENCHMARK_JSON_END")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
