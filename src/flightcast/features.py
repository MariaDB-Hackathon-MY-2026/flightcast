"""
Feature engineering for the MAPIE forecaster.
Lag / rolling / calendar features with proper group-by to prevent cross-route leakage.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MAJOR_HOLIDAYS = {
    "01-01", "12-25", "12-26",
    "07-04", "11-11",
    "08-31", "02-01",
    "04-15", "07-15", "10-15",
}

FEATURE_COLS = [
    "distance_km",
    "hub_degree_src",
    "hub_degree_dst",
    "day_of_week",
    "month",
    "is_weekend",
    "is_holiday",
    "lag_1",
    "lag_7",
    "lag_30",
    "roll_mean_7",
    "roll_mean_30",
    "route_id_cat",
]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input: demand DataFrame with columns route_id, demand_date, demand_volume,
           day_of_week, month, hub_score_source, hub_score_dest.
    Output: same DataFrame enriched with lag/rolling/calendar features, NaN rows dropped.
    """
    df = df.copy()
    df["demand_date"] = pd.to_datetime(df["demand_date"])
    df = df.sort_values(["route_id", "demand_date"]).reset_index(drop=True)

    df["day_of_week"] = df["demand_date"].dt.dayofweek
    df["month"] = df["demand_date"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_holiday"] = df["demand_date"].dt.strftime("%m-%d").isin(MAJOR_HOLIDAYS).astype(int)

    if "hub_score_source" in df.columns:
        df = df.rename(columns={"hub_score_source": "hub_degree_src",
                                 "hub_score_dest": "hub_degree_dst"})

    grp = df.groupby("route_id")["demand_volume"]
    df["lag_1"] = grp.shift(1)
    df["lag_7"] = grp.shift(7)
    df["lag_30"] = grp.shift(30)
    df["roll_mean_7"] = grp.transform(lambda x: x.shift(1).rolling(7).mean())
    df["roll_mean_30"] = grp.transform(lambda x: x.shift(1).rolling(30).mean())

    # Categorical route_id for LightGBM
    df["route_id_cat"] = df["route_id"].astype("category").cat.codes

    if "distance_km" not in df.columns:
        df["distance_km"] = 0.0

    df = df.dropna(subset=["lag_30", "roll_mean_30"]).reset_index(drop=True)
    return df


def build_future_features(
    conn,
    sampled_routes: pd.DataFrame,
    story_ts: str,
    horizon_days: int = 30,
) -> pd.DataFrame:
    """
    DEPRECATED in favour of build_future_features_recursive — kept for backwards
    compatibility with tests / experimental scripts that don't have a base model
    in scope.

    Build feature rows for the next horizon_days after story_ts for all sampled routes.
    Uses last known demand values for lag/rolling features — these values are FROZEN
    across all 30 forecast days, which means Day 1 and Day 30 predictions see the
    same lag_1, lag_7, lag_30 inputs. That is the bug Phase 3 fixes via
    build_future_features_recursive.
    """
    from datetime import date, timedelta
    import mariadb

    story_date = pd.Timestamp(story_ts).date()
    future_dates = [story_date + timedelta(days=d + 1) for d in range(horizon_days)]

    records = []
    cur = conn.cursor(named_tuple=True) if hasattr(conn, "cursor") else None

    for _, route in sampled_routes.iterrows():
        rid = int(route["route_id"])

        if cur is not None:
            cur.execute(
                """
                SELECT demand_volume FROM route_demand
                WHERE route_id = ? AND demand_date < ?
                ORDER BY demand_date DESC LIMIT 30
                """,
                (rid, str(story_date)),
            )
            hist = [r.demand_volume for r in cur.fetchall()]
        else:
            hist = []

        lag_1 = hist[0] if len(hist) >= 1 else 100.0
        lag_7 = hist[6] if len(hist) >= 7 else 100.0
        lag_30 = hist[29] if len(hist) >= 30 else 100.0
        roll_mean_7 = float(np.mean(hist[:7])) if len(hist) >= 7 else 100.0
        roll_mean_30 = float(np.mean(hist[:30])) if len(hist) >= 30 else 100.0

        for d in future_dates:
            records.append(
                {
                    "route_id": rid,
                    "forecast_date": d,
                    "distance_km": float(route.get("distance_km", 0.0)),
                    "hub_degree_src": float(route.get("hub_degree_src", 1.0)),
                    "hub_degree_dst": float(route.get("hub_degree_dst", 1.0)),
                    "day_of_week": d.weekday(),
                    "month": d.month,
                    "is_weekend": int(d.weekday() in [5, 6]),
                    "is_holiday": int(d.strftime("%m-%d") in MAJOR_HOLIDAYS),
                    "lag_1": lag_1,
                    "lag_7": lag_7,
                    "lag_30": lag_30,
                    "roll_mean_7": roll_mean_7,
                    "roll_mean_30": roll_mean_30,
                    "route_id_cat": rid,
                }
            )

    df = pd.DataFrame(records)
    if df.empty:
        return df

    # Re-encode route_id_cat consistently
    route_codes = {rid: i for i, rid in enumerate(sorted(df["route_id"].unique()))}
    df["route_id_cat"] = df["route_id"].map(route_codes)
    return df


def build_future_features_recursive(
    conn,
    sampled_routes: pd.DataFrame,
    story_ts: str,
    base_model,
    horizon_days: int = 30,
) -> pd.DataFrame:
    """
    Recursive multi-step feature builder (Phase 3 fix for the frozen-lag bug).

    For each forecast day d in [1..horizon_days]:
      1. Build the feature row using lag values from `history` (last 30 days,
         which initially is the actual demand window before story_ts but
         grows by appending each step's prediction).
      2. Call base_model.predict on the single feature row to get a point
         estimate on log scale.
      3. Inverse-transform via expm1 to get the demand prediction.
      4. Append that prediction to `history` so day d+1's lag_1 is day d's
         prediction (rather than a frozen lag_1 from before story_ts).

    The model was TRAINED on one-step-ahead features (engineer_features uses
    pandas shift(1)/shift(7)/shift(30) on actual demand). At inference, for
    Day 1 we have actual lag_1 (yesterday's demand). For Day 2 we use Day 1's
    PREDICTION as lag_1, since Day 1 hasn't actually happened yet. This is
    standard recursive autoregression — the canonical multi-step forecast
    pattern in skforecast / nixtla / FPP3.

    ★18: We use base_model.predict (not MAPIE.predict) inside the loop because
    MAPIE's bootstrap aggregation is 20× slower per call and we only need
    POINT estimates for lag propagation. After all 30 days have feature rows,
    bootstrap.py calls generate_forecast_batch(mapie_model, df) once on the
    full DataFrame to get calibrated prediction intervals.

    Args:
        conn: MariaDB connection (used to fetch the initial history window).
        sampled_routes: DataFrame with route_id, hub_degree_src/dst,
                        distance_km, etc.
        story_ts: ISO date string. Forecast starts at story_ts + 1 day.
        base_model: Fitted LGBMRegressor, used for step-wise point prediction.
        horizon_days: Forecast horizon (default 30).

    Returns:
        DataFrame with one row per (route, forecast_date) and all FEATURE_COLS
        populated with RECURSIVE lag values (different per day, not frozen).
    """
    from datetime import timedelta

    story_date = pd.Timestamp(story_ts).date()
    future_dates = [story_date + timedelta(days=d + 1) for d in range(horizon_days)]

    # Precompute the route_id → route_id_cat mapping once
    sampled_route_ids = sorted(int(r) for r in sampled_routes["route_id"].unique())
    route_id_cat_map = {rid: i for i, rid in enumerate(sampled_route_ids)}

    records: list[dict] = []
    cur = conn.cursor() if hasattr(conn, "cursor") else None

    for _, route in sampled_routes.iterrows():
        rid = int(route["route_id"])

        # Fetch the last 30 days of actual demand BEFORE story_ts (chronological order).
        if cur is not None:
            cur.execute(
                """
                SELECT demand_volume FROM route_demand
                WHERE route_id = ? AND demand_date < ?
                ORDER BY demand_date DESC LIMIT 30
                """,
                (rid, str(story_date)),
            )
            # DESC order; reverse to get oldest-first so history[-1] is yesterday.
            hist_desc = [float(row[0]) for row in cur.fetchall()]
            history: list[float] = list(reversed(hist_desc))
        else:
            history = []

        # Pad history if we have fewer than 30 days available (defensive).
        while len(history) < 30:
            history.insert(0, 100.0)

        # Static features per route
        distance_km = float(route.get("distance_km", 0.0))
        hub_src = float(route.get("hub_degree_src", 1.0))
        hub_dst = float(route.get("hub_degree_dst", 1.0))
        route_id_cat = route_id_cat_map.get(rid, 0)

        # Recursive loop: build one feature row, predict, append, repeat
        for d in future_dates:
            # Lags reference history end (most recent values)
            lag_1 = history[-1]
            lag_7 = history[-7]
            lag_30 = history[-30]
            roll_mean_7 = float(np.mean(history[-7:]))
            roll_mean_30 = float(np.mean(history[-30:]))

            row = {
                "route_id": rid,
                "forecast_date": d,
                "distance_km": distance_km,
                "hub_degree_src": hub_src,
                "hub_degree_dst": hub_dst,
                "day_of_week": d.weekday(),
                "month": d.month,
                "is_weekend": int(d.weekday() in [5, 6]),
                "is_holiday": int(d.strftime("%m-%d") in MAJOR_HOLIDAYS),
                "lag_1": lag_1,
                "lag_7": lag_7,
                "lag_30": lag_30,
                "roll_mean_7": roll_mean_7,
                "roll_mean_30": roll_mean_30,
                "route_id_cat": route_id_cat,
            }
            records.append(row)

            # Step-wise point prediction on log scale, then expm1 back to demand scale.
            # The model expects features in FEATURE_COLS order.
            feat_array = np.array([[row[c] for c in FEATURE_COLS]], dtype=float)
            y_log_pred = float(base_model.predict(feat_array)[0])
            y_pred = float(np.expm1(y_log_pred))
            # Guard against nonsense; demand is always non-negative
            y_pred = max(y_pred, 0.0)

            # Append prediction to history; trim to keep window length at 30
            history.append(y_pred)
            if len(history) > 60:  # cap memory; lag_30 only needs last 30
                history = history[-60:]

    df = pd.DataFrame(records)
    return df
