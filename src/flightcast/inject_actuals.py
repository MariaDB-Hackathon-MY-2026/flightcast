"""
Inject synthetic actuals into the forecasts table so empirical coverage
becomes computable on the Coverage Drift dashboard.

Synthetic actuals are drawn from the same multiplicative LogNormal(0, sigma)
noise distribution used during training (synth_demand.py uses sigma=0.10).
This validates that MAPIE's conformal intervals are correctly calibrated:
if the math is right, ~90% of actuals fall inside the [lower, upper] band.

For a more dramatic drift demo, the LATER batches (5, 6) get a wider sigma
to simulate distribution shift — empirical coverage will drop, demonstrating
that FOR SYSTEM_TIME ALL audit catches calibration drift.

Run:
  docker compose exec app python -m flightcast.inject_actuals
  docker compose exec app python -m flightcast.inject_actuals --no-drift
"""
from __future__ import annotations

import argparse
import sys
import numpy as np
import mariadb

from flightcast.db.connection import get_connection
from flightcast.audit import backfill_coverage_scores


# Per-tier calibrated sigma must match synth_demand.TIER_PARAMS["sigma"] so actuals
# are drawn from the same noise distribution the conformal model was calibrated on.
# After diagnosing Phase 2C-v1 (heterogeneous σ), we hold σ uniform at 0.10 across
# tiers — heterogeneous σ inflated the global MAPIE interval to ~99% calibrated
# coverage on hub/mid routes (over-conservative). Tier still differentiates SHAPE
# via A_year/A_week in synth_demand.py; only the noise level is uniform.
TIER_SIGMA_CALIBRATED: dict[str, float] = {
    "hub": 0.10,
    "mid": 0.10,
    "thin": 0.10,
}
# Drift sigma is 2.2× the calibrated sigma. With uniform calibrated σ=0.10,
# drift σ=0.22 — restores the original killer demo (91% → 58% coverage drop).
DRIFT_MULTIPLIER = 2.2

# Legacy fallbacks (used when a forecast row's tier cannot be resolved —
# e.g., legacy data inserted before the tier column existed).
SIGMA_CALIBRATED_DEFAULT = 0.10
SIGMA_SHIFTED_DEFAULT = 0.22
# Batch ids that experience the simulated distribution shift.
DRIFT_BATCH_IDS = {5, 6}


def inject_actuals(
    conn: mariadb.Connection,
    drift_batch_ids: set[int] | None = None,
    drift_multiplier: float = DRIFT_MULTIPLIER,
    seed: int = 1337,
) -> int:
    """
    Set forecasts.actual_demand = predicted_demand * exp(N(0, σ_tier)).

    σ_tier comes from TIER_SIGMA_CALIBRATED (matching the synth-demand training
    distribution). For batches in drift_batch_ids, σ_tier is multiplied by
    `drift_multiplier` to simulate a regime change. Coverage on calibrated
    batches should land near 90% across all tiers; coverage on drift batches
    drops dramatically.

    The forecast row's tier is resolved via JOIN with route_demand on route_id
    (each route has exactly one tier).

    Returns the number of rows updated.
    """
    if drift_batch_ids is None:
        drift_batch_ids = set()

    cur = conn.cursor()
    # Resolve tier per forecast row by joining with the route's tier label.
    # COALESCE falls back to 'mid' when route_demand was loaded before the
    # tier column existed (legacy data path).
    cur.execute(
        """
        SELECT f.forecast_id, f.forecast_run_id, f.predicted_demand,
               COALESCE(rd.tier, 'mid') AS tier
        FROM forecasts f
        LEFT JOIN (SELECT DISTINCT route_id, tier FROM route_demand) rd
               ON f.route_id = rd.route_id
        WHERE f.actual_demand IS NULL
        """
    )
    rows = cur.fetchall()
    if not rows:
        print("  All forecast rows already have actual_demand. Nothing to do.")
        return 0

    rng = np.random.default_rng(seed)

    updates = []
    counts: dict[tuple[str, str], int] = {}  # (tier, drift_status) -> count
    for forecast_id, run_id, predicted, tier in rows:
        tier_str = str(tier) if tier else "mid"
        sigma_calibrated = TIER_SIGMA_CALIBRATED.get(tier_str, SIGMA_CALIBRATED_DEFAULT)
        if int(run_id) in drift_batch_ids:
            sigma = sigma_calibrated * drift_multiplier
            counts[(tier_str, "drift")] = counts.get((tier_str, "drift"), 0) + 1
        else:
            sigma = sigma_calibrated
            counts[(tier_str, "calibrated")] = counts.get((tier_str, "calibrated"), 0) + 1
        # LogNormal multiplicative noise: actual = predicted * exp(epsilon)
        epsilon = rng.normal(0.0, sigma)
        actual = float(predicted) * float(np.exp(epsilon))
        actual = max(actual, 0.0)
        updates.append((actual, int(forecast_id)))

    print("  Per-tier breakdown of actuals to inject:")
    for (tier_str, status), n in sorted(counts.items()):
        sigma_calibrated = TIER_SIGMA_CALIBRATED.get(tier_str, SIGMA_CALIBRATED_DEFAULT)
        eff_sigma = sigma_calibrated * drift_multiplier if status == "drift" else sigma_calibrated
        print(f"    {tier_str:5s} {status:11s}: {n:5d} rows  (σ={eff_sigma:.3f})")

    cur.executemany(
        "UPDATE forecasts SET actual_demand = ? WHERE forecast_id = ?",
        updates,
    )
    conn.commit()
    return cur.rowcount


def print_coverage_summary(conn: mariadb.Connection) -> None:
    """Show per-batch empirical coverage so the user can verify the result."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT forecast_run_id,
               AVG(coverage_score) AS coverage,
               AVG(upper_bound - lower_bound) AS mean_width,
               COUNT(*) AS n
        FROM forecasts FOR SYSTEM_TIME ALL
        WHERE coverage_score IS NOT NULL
        GROUP BY forecast_run_id
        ORDER BY forecast_run_id
        """
    )
    rows = cur.fetchall()
    if not rows:
        print("\n  No coverage_score rows found. Did backfill_coverage_scores run?")
        return

    print("\n  Empirical coverage per batch:")
    print("  " + "-" * 60)
    print(f"  {'Run':<5}{'Coverage':<12}{'Width':<12}{'N':<8}{'vs 90% target'}")
    print("  " + "-" * 60)
    for run_id, cov, width, n in rows:
        cov_pct = f"{float(cov)*100:.1f}%"
        delta_pp = (float(cov) - 0.90) * 100
        delta_str = f"{delta_pp:+.1f}pp"
        flag = "OK" if abs(delta_pp) < 5 else "DRIFT"
        print(f"  {run_id:<5}{cov_pct:<12}{float(width):<12.1f}{int(n):<8}{delta_str:<10}{flag}")
    print("  " + "-" * 60)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inject synthetic actuals into forecasts.")
    parser.add_argument(
        "--no-drift",
        action="store_true",
        help="Use the calibrated sigma for ALL batches (no simulated drift).",
    )
    parser.add_argument(
        "--drift-multiplier", type=float, default=DRIFT_MULTIPLIER,
        help=f"Drift sigma is multiplier × tier-calibrated sigma (default {DRIFT_MULTIPLIER}).",
    )
    args = parser.parse_args(argv)

    print("Connecting to MariaDB...")
    conn = get_connection()

    drift_ids = set() if args.no_drift else DRIFT_BATCH_IDS

    print(f"\nInjecting synthetic actuals (drift batches: {sorted(drift_ids) or 'none'})...")
    n_updated = inject_actuals(
        conn,
        drift_batch_ids=drift_ids,
        drift_multiplier=args.drift_multiplier,
    )
    print(f"  Updated {n_updated} forecast rows with actual_demand.")

    print("\nComputing coverage_score from actuals...")
    n_coverage = backfill_coverage_scores(conn)
    print(f"  Computed coverage_score for {n_coverage} rows.")

    print_coverage_summary(conn)

    conn.close()
    print("\nDone. Refresh http://localhost:8501 → Coverage Drift to see live metrics.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
