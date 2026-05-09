"""
Coverage drift and empirical calibration audit utilities.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import mariadb


def compute_live_coverage(df: pd.DataFrame) -> float:
    """Fraction of rows in df where actual_demand falls within [lower, upper]."""
    if df.empty or "actual_demand" not in df.columns:
        return float("nan")
    valid = df.dropna(subset=["actual_demand"])
    if valid.empty:
        return float("nan")
    covered = (
        (valid["actual_demand"] >= valid["lower_bound"])
        & (valid["actual_demand"] <= valid["upper_bound"])
    ).mean()
    return float(covered)


def compute_calibration_drift(conn: mariadb.Connection) -> pd.DataFrame:
    """
    Per-batch empirical coverage vs the 0.90 target.
    Uses FOR SYSTEM_TIME ALL to see all historical versions.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT forecast_run_id,
               AVG(coverage_score)              AS mean_coverage,
               AVG(winkler_score)               AS mean_winkler,
               AVG(upper_bound - lower_bound)   AS mean_width,
               COUNT(*)                         AS n_rows
        FROM forecasts FOR SYSTEM_TIME ALL
        WHERE coverage_score IS NOT NULL
        GROUP BY forecast_run_id
        ORDER BY forecast_run_id
        """
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["target"] = 0.90
        df["drift"] = df["mean_coverage"] - df["target"]
    return df


def backfill_coverage_scores(conn: mariadb.Connection, alpha: float = 0.10) -> int:
    """
    For rows that now have actual_demand, compute and write:
      - coverage_score: binary 1.0 if actual is inside [lower, upper], else 0.0.
      - winkler_score: continuous interval score (lower = better) per Winkler 1972 /
        FPP3 §5.9 / Gneiting & Raftery 2007.
            width = upper - lower
            winkler = width                                  if lower ≤ actual ≤ upper
                    = width + (2/α) × (lower - actual)       if actual < lower
                    = width + (2/α) × (actual - upper)       if actual > upper

    Coverage answers "did the interval contain the actual?" (yes/no).
    Winkler answers "how good was the interval?" (continuous, penalises both
    over-wide intervals and missed coverage proportional to the miss distance).
    Mean Winkler is the standard ML-forecasting metric; lower is better.

    Returns the number of rows updated.
    """
    cur = conn.cursor()
    # Single UPDATE computes both scores in one pass for efficiency.
    cur.execute(
        f"""
        UPDATE forecasts
        SET coverage_score = CASE
                WHEN actual_demand >= lower_bound AND actual_demand <= upper_bound THEN 1.0
                ELSE 0.0
            END,
            winkler_score = CASE
                WHEN actual_demand >= lower_bound AND actual_demand <= upper_bound
                    THEN (upper_bound - lower_bound)
                WHEN actual_demand < lower_bound
                    THEN (upper_bound - lower_bound) + ({2.0 / alpha}) * (lower_bound - actual_demand)
                ELSE -- actual_demand > upper_bound
                    (upper_bound - lower_bound) + ({2.0 / alpha}) * (actual_demand - upper_bound)
            END
        WHERE actual_demand IS NOT NULL AND coverage_score IS NULL
        """
    )
    conn.commit()
    return cur.rowcount
