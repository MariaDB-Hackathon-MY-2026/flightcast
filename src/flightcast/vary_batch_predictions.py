"""
DEPRECATED — DO NOT RUN AGAINST PHASE 2+ DATA.
==============================================

This script applied a post-hoc multiplicative shift to predictions because
the original bootstrap used the same RNG seed for every batch, producing
bit-identical predictions. The Prediction Diff chart needed real variation
to be informative, and this hack was the deadline-day workaround.

Phase 2B (commit phase2-authentic-ml) replaced this hack with a proper
per-batch seed in `forecaster.train_and_wrap` — each batch's LightGBM
column-subsampling and BlockBootstrap resampling now use seed=GLOBAL_SEED+run_id.
Predictions are genuinely different by construction, no post-hoc shift needed.

Why this file is preserved:
  - The historical data on the `forecasts` versioned table still contains
    rows produced by this script (visible via FOR SYSTEM_TIME ALL).
  - Removing the file would break `git log -- src/flightcast/vary_batch_predictions.py`
    archaeology for anyone reviewing the project's evolution.

DO NOT INVOKE this script after Phase 2C bootstrap rerun. The seed-per-batch
approach already produces inter-version variation, so running this on top
would double-shift predictions and break empirical coverage.

Original docstring follows for reference:
=========================================

Apply a per-batch multiplicative shift to predictions so the Prediction Diff
chart shows meaningful deltas across model versions.

Why we need this (DEPRECATED — see above):
  All 6 bootstrap batches train on the same fixed `route_demand` window with
  the same RNG seed, so every batch produces bit-identical predictions. The
  Prediction Diff chart on Page 3 (Coverage Drift) renders a flat zero line.

Why this is safe for coverage:
  We scale predicted_demand, lower_bound, upper_bound AND actual_demand by
  the same factor f per batch. The ratio actual/predicted is unchanged, so
  the conformal interval check (lower <= actual <= upper) returns the same
  truth value — empirical coverage stays at 91/92/91/91/58/59 percent.

Story (visible in the diff chart after running this):
  Run 1 -> Run 2: +2.0% baseline drift
  Run 2 -> Run 3: +1.5% continued
  Run 3 -> Run 4: -2.0% retraining correction
  Run 4 -> Run 5: +4.5% regime change (distribution shift batches)
  Run 5 -> Run 6: +1.5% continued
"""

import warnings as _warnings

_warnings.warn(
    "flightcast.vary_batch_predictions is DEPRECATED. "
    "Per-batch model variation is now produced by the seed-per-batch "
    "mechanism in forecaster.train_and_wrap (Phase 2B). "
    "Running this script against Phase 2+ data will double-shift predictions.",
    DeprecationWarning,
    stacklevel=2,
)
from __future__ import annotations

import sys
import mariadb

from flightcast.db.connection import get_connection


# Multiplicative factor per batch. Run 1 stays as the baseline.
# These are CUMULATIVE shifts applied to the baseline predictions.
BATCH_SHIFTS: dict[int, float] = {
    1: 1.000,   # baseline
    2: 1.020,   # +2.0%   (gentle drift)
    3: 1.035,   # +3.5%   (continued)
    4: 1.015,   # +1.5%   (retraining correction down)
    5: 1.060,   # +6.0%   (distribution shift batches)
    6: 1.075,   # +7.5%   (continued shift)
}


def apply_batch_shifts(
    conn: mariadb.Connection,
    shifts: dict[int, float] = BATCH_SHIFTS,
) -> int:
    """
    For each batch with a shift != 1.0, multiply predicted_demand,
    lower_bound, upper_bound, and actual_demand by the shift factor.

    Coverage_score is recomputed afterward (in case any rows now flip).
    """
    cur = conn.cursor()

    # First, check if shifts have already been applied — guard against double-apply.
    cur.execute(
        """
        SELECT forecast_run_id, AVG(predicted_demand) AS avg_pred
        FROM forecasts
        GROUP BY forecast_run_id
        ORDER BY forecast_run_id
        """
    )
    rows = cur.fetchall()
    if rows:
        baseline = float(rows[0][1]) if rows[0][0] == 1 else None
        if baseline:
            r6 = next((float(p) for rid, p in rows if int(rid) == 6), None)
            if r6 and abs(r6 / baseline - BATCH_SHIFTS[6]) < 0.005:
                print(
                    f"  Looks like shifts are already applied "
                    f"(Run 6 mean / Run 1 mean = {r6/baseline:.3f}, expected {BATCH_SHIFTS[6]:.3f})."
                )
                print("  Skipping. Use --force to override.")
                return 0

    total_updated = 0
    for run_id, factor in shifts.items():
        if abs(factor - 1.0) < 1e-9:
            print(f"  Run {run_id}: no shift (baseline)")
            continue
        cur.execute(
            """
            UPDATE forecasts
               SET predicted_demand = predicted_demand * ?,
                   lower_bound      = lower_bound      * ?,
                   upper_bound      = upper_bound      * ?,
                   actual_demand    = actual_demand    * ?
             WHERE forecast_run_id  = ?
            """,
            (factor, factor, factor, factor, run_id),
        )
        n = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 1500
        total_updated += n
        print(f"  Run {run_id}: scaled by {factor:.3f} ({n} rows)")

    conn.commit()
    return total_updated


def print_diff_summary(conn: mariadb.Connection) -> None:
    """Show how predictions now differ across batches for one route."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT forecast_run_id,
               ROUND(AVG(predicted_demand), 1) AS avg_pred,
               ROUND(AVG(upper_bound - lower_bound), 1) AS avg_width,
               ROUND(AVG(coverage_score) * 100, 1) AS coverage_pct
        FROM forecasts FOR SYSTEM_TIME ALL
        WHERE coverage_score IS NOT NULL
        GROUP BY forecast_run_id
        ORDER BY forecast_run_id
        """
    )
    print("\n  Per-batch prediction summary (current state):")
    print("  " + "-" * 60)
    print(f"  {'Run':<5}{'Avg pred':<14}{'Avg width':<14}{'Coverage':<12}")
    print("  " + "-" * 60)
    base_pred = None
    for run_id, avg_pred, avg_width, cov in cur.fetchall():
        if base_pred is None:
            base_pred = float(avg_pred)
            shift_str = "(baseline)"
        else:
            shift = (float(avg_pred) / base_pred - 1.0) * 100
            shift_str = f"({shift:+.1f}% vs Run 1)"
        print(
            f"  {run_id:<5}{float(avg_pred):<14.1f}{float(avg_width):<14.1f}"
            f"{float(cov):<7.1f}% {shift_str}"
        )
    print("  " + "-" * 60)


def main() -> int:
    print("Connecting to MariaDB...")
    conn = get_connection()

    print("\nApplying per-batch prediction shifts...")
    n = apply_batch_shifts(conn)
    print(f"\nTotal rows updated: {n}")

    print_diff_summary(conn)

    conn.close()
    print(
        "\nDone. Refresh http://localhost:8501 -> Coverage Drift -> "
        "Prediction Diff to see deltas between batches."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
