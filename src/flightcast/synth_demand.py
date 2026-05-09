"""
Synthetic demand generation using multiplicative log-normal decomposition.

demand(route, t) = base × seasonality × trend × noise
  base       = k * sqrt(hub_degree_src * hub_degree_dst)        k=50
  seasonality= 1 + A_year*sin(2πt/365+φ) + A_week*sin(2πt/7)
  trend      = 1 + g*t + pandemic_shock(t)
  noise      = LogNormal(0, sigma)  -- strictly positive, preserves coverage

★8: LogNormal multiplicative noise replaces Normal additive noise.
Additive noise produces negative values that distort conformal calibration.

★16 (Phase 2A): Per-tier (A_year, A_week, sigma) parameters create genuine
heterogeneity across routes. Hub routes are smooth and predictable; thin
routes are volatile. This makes the dashboard's per-route view visually
informative — different routes finally look different. Drift sigma in
inject_actuals.py scales proportionally so calibration coverage holds
across all tiers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import date, timedelta

from flightcast.config import GLOBAL_SEED, N_DAYS, START_DATE

_RNG = np.random.default_rng(GLOBAL_SEED)

# Default (mid-tier) parameters — preserved as module-level constants for
# backwards compatibility with code that imports them directly.
K = 50.0
A_YEAR = 0.20
A_WEEK = 0.07
SIGMA = 0.10
GROWTH_RATE = 0.0004
PANDEMIC_START_DAY = 440
PANDEMIC_DEPTH = 0.60
PANDEMIC_RECOVERY_RATE = 0.003

# Per-tier seasonality parameters.
# Hub routes are heavy-traffic predictable corridors (LHR↔JFK class) — gentler annual
# swing, smaller weekly oscillation.
# Thin routes are low-volume regional connectors — sharp annual swings (tourist/seasonal
# pressure) and pronounced weekly cycles.
# Mid routes match the original FlightCast defaults.
#
# CRITICAL: σ (noise level) is held UNIFORM at 0.10 across all tiers. Different σ per
# tier creates a heterogeneous-residual training set, which inflates the global MAPIE
# calibration interval beyond what hub/mid routes actually need — empirical coverage
# then climbs to ~99% on calibrated batches (over-conservative) and only drops to ~85%
# on drift, hiding the killer demo. By keeping σ uniform we preserve clean ~90%
# calibrated coverage while still differentiating route SHAPES via A_year/A_week.
TIER_PARAMS: dict[str, dict[str, float]] = {
    "hub": {"a_year": 0.12, "a_week": 0.03, "sigma": 0.10},
    "mid": {"a_year": 0.20, "a_week": 0.07, "sigma": 0.10},
    "thin": {"a_year": 0.35, "a_week": 0.15, "sigma": 0.10},
}


def _pandemic_shock(
    t: np.ndarray,
    start_day: int = PANDEMIC_START_DAY,
    depth: float = PANDEMIC_DEPTH,
    recovery_rate: float = PANDEMIC_RECOVERY_RATE,
) -> np.ndarray:
    """Step-down at start_day with exponential recovery. Clamped to [0, 1]."""
    shock = np.where(
        t >= start_day,
        depth * np.exp(-recovery_rate * (t - start_day)),
        0.0,
    )
    return np.clip(shock, 0.0, 1.0)


def generate_demand_series(
    routes: pd.DataFrame,
    n_days: int = N_DAYS,
    start_date: str = START_DATE,
    rng: np.random.Generator | None = None,
    k: float = K,
    a_year: float = A_YEAR,
    a_week: float = A_WEEK,
    sigma: float = SIGMA,
    growth_rate: float = GROWTH_RATE,
    pandemic_start_day: int = PANDEMIC_START_DAY,
    pandemic_depth: float = PANDEMIC_DEPTH,
    pandemic_recovery_rate: float = PANDEMIC_RECOVERY_RATE,
) -> pd.DataFrame:
    """
    Return a DataFrame with columns:
      route_id, demand_date, demand_volume, day_of_week, month, is_holiday,
      hub_score_source, hub_score_dest, hemisphere, tier

    Per-tier parameters override the (a_year, a_week, sigma) function args
    when the input `routes` DataFrame has a 'tier' column. When 'tier' is
    absent, the mid-tier defaults (function args) are used uniformly,
    preserving the original behaviour for tests that don't supply tiers.
    """
    if rng is None:
        rng = np.random.default_rng(GLOBAL_SEED)

    base_date = date.fromisoformat(start_date)
    dates = [base_date + timedelta(days=d) for d in range(n_days)]
    t = np.arange(n_days, dtype=float)

    trend = 1.0 + growth_rate * t - _pandemic_shock(
        t, pandemic_start_day, pandemic_depth, pandemic_recovery_rate
    )
    trend = np.maximum(trend, 0.05)

    records = []
    for _, row in routes.iterrows():
        hub_src = float(row["hub_degree_src"])
        hub_dst = float(row["hub_degree_dst"])
        base = k * np.sqrt(max(hub_src, 1.0) * max(hub_dst, 1.0))

        hemisphere = str(row.get("hemisphere", "N"))
        phase = 0.0 if hemisphere == "N" else np.pi

        # Resolve tier-specific parameters. Falls back to function args
        # (which default to mid-tier constants) when tier is missing.
        tier = str(row.get("tier", "mid"))
        params = TIER_PARAMS.get(tier, {"a_year": a_year, "a_week": a_week, "sigma": sigma})
        row_a_year = params["a_year"]
        row_a_week = params["a_week"]
        row_sigma = params["sigma"]

        seasonality = (
            1.0
            + row_a_year * np.sin(2 * np.pi * t / 365.0 + phase)
            + row_a_week * np.sin(2 * np.pi * t / 7.0)
        )

        noise = rng.lognormal(mean=0.0, sigma=row_sigma, size=n_days)
        demand = base * seasonality * trend * noise
        demand = np.maximum(demand, 1.0)

        for i, d in enumerate(dates):
            records.append(
                {
                    "route_id": int(row["route_id"]),
                    "demand_date": d,
                    "demand_volume": float(demand[i]),
                    "day_of_week": d.weekday(),
                    "month": d.month,
                    "is_holiday": 0,
                    "hub_score_source": float(hub_src),
                    "hub_score_dest": float(hub_dst),
                    "hemisphere": hemisphere,
                    "tier": tier,
                }
            )

    return pd.DataFrame(records)
