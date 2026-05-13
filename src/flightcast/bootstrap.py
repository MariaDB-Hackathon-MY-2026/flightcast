"""
Bootstrap script: loads OpenFlights data, generates synthetic demand,
and runs 6 historical prediction batches at wall-clock-separated timestamps.

Usage:
  docker compose exec app python -m flightcast.bootstrap
  docker compose exec app python -m flightcast.bootstrap --reset

★11: ROW_START is read back from MariaDB via SELECT MAX(ROW_START) after each
     commit. Python wall-clock != MariaDB commit time (timezone / clock skew).
★12: Batch mapping is persisted to batch_run_mapping table, NOT a JSON file.
     Both bootstrap and Streamlit containers share the DB connection.
★13: --reset flag DROPs and RE-ADDs system versioning to wipe history for clean reruns.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import time
import urllib.request
import mariadb
import numpy as np
import pandas as pd

from flightcast.config import load_db_config, CONFIDENCE_LEVEL, GLOBAL_SEED
from flightcast.db.connection import get_connection
from flightcast.data_pipeline import run_demand_pipeline, sample_routes, compute_hub_degrees
from flightcast.features import (
    engineer_features,
    build_future_features,
    build_future_features_recursive,
    FEATURE_COLS,
)
from flightcast.forecaster import train_and_wrap, generate_forecast_batch
from flightcast.audit import backfill_coverage_scores

# OpenFlights raw CSV URLs (github.com/jpatokal/openflights)
_OF_BASE = "https://raw.githubusercontent.com/jpatokal/openflights/master/data"
OPENFLIGHTS_URLS = {
    "airports": f"{_OF_BASE}/airports.dat",
    "airlines": f"{_OF_BASE}/airlines.dat",
    "routes":   f"{_OF_BASE}/routes.dat",
}


def _fetch_csv(url: str) -> list[list[str]]:
    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    return list(reader)


def _coerce_int(val: str) -> int | None:
    try:
        return int(val.strip())
    except (ValueError, AttributeError):
        return None


def _coerce_float(val: str) -> float | None:
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return None


def load_openflights(conn: mariadb.Connection) -> None:
    """
    Download and insert the three OpenFlights static tables.
    Idempotent: skips if rows already exist.
    Uses Python INSERT (not LOAD DATA INFILE) to avoid path/privilege issues.
    """
    cur = conn.cursor()

    # ── airports ──────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM airports")
    if cur.fetchone()[0] == 0:
        print("  Downloading airports.dat …")
        rows = _fetch_csv(OPENFLIGHTS_URLS["airports"])
        data = []
        for r in rows:
            if len(r) < 14:
                continue
            data.append((
                _coerce_int(r[0]),   # id
                r[1].strip(),        # name
                r[2].strip(),        # city
                r[3].strip(),        # country
                r[4].strip(),        # iata
                r[5].strip(),        # icao
                _coerce_float(r[6]), # latitude
                _coerce_float(r[7]), # longitude
                _coerce_int(r[8]),   # altitude
                _coerce_float(r[9]), # timezone
                r[10].strip(),       # dst
                r[11].strip(),       # tz
                r[12].strip(),       # type
                r[13].strip(),       # source
            ))
        cur.executemany(
            "INSERT IGNORE INTO airports "
            "(id,name,city,country,iata,icao,latitude,longitude,"
            "altitude,timezone,dst,tz,type,source) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            data,
        )
        conn.commit()
        print(f"  Inserted {cur.rowcount} airports")
    else:
        print("  airports already loaded — skipping")

    # ── airlines ──────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM airlines")
    if cur.fetchone()[0] == 0:
        print("  Downloading airlines.dat …")
        rows = _fetch_csv(OPENFLIGHTS_URLS["airlines"])
        data = []
        for r in rows:
            if len(r) < 8:
                continue
            data.append((
                _coerce_int(r[0]),  # id
                r[1].strip(),       # name
                r[2].strip(),       # alias
                r[3].strip(),       # iata
                r[4].strip(),       # icao
                r[5].strip(),       # callsign
                r[6].strip(),       # country
                r[7].strip(),       # active
            ))
        cur.executemany(
            "INSERT IGNORE INTO airlines "
            "(id,name,alias,iata,icao,callsign,country,active) "
            "VALUES (?,?,?,?,?,?,?,?)",
            data,
        )
        conn.commit()
        print(f"  Inserted {cur.rowcount} airlines")
    else:
        print("  airlines already loaded — skipping")

    # ── routes ────────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(*) FROM routes")
    if cur.fetchone()[0] == 0:
        print("  Downloading routes.dat …")
        rows = _fetch_csv(OPENFLIGHTS_URLS["routes"])
        data = []
        for r in rows:
            if len(r) < 9:
                continue
            data.append((
                r[0].strip(),        # airline
                _coerce_int(r[1]),   # airline_id
                r[2].strip(),        # src_airport
                _coerce_int(r[3]),   # src_airport_id
                r[4].strip(),        # dst_airport
                _coerce_int(r[5]),   # dst_airport_id
                r[6].strip(),        # codeshare
                _coerce_int(r[7]) or 0,  # stops
                r[8].strip(),        # equipment
            ))
        # Insert in chunks of 2000
        for i in range(0, len(data), 2000):
            cur.executemany(
                "INSERT IGNORE INTO routes "
                "(airline,airline_id,src_airport,src_airport_id,"
                "dst_airport,dst_airport_id,codeshare,stops,equipment) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                data[i:i+2000],
            )
            conn.commit()
        cur.execute("SELECT COUNT(*) FROM routes")
        print(f"  Inserted routes, total: {cur.fetchone()[0]}")
    else:
        print("  routes already loaded — skipping")


BATCH_CONFIGS = [
    # All batches use LGBMRegressor — labels reflect that honestly.
    # Minor/major version bumps (v1.0/v1.1, v2.0/v2.1) simulate model evolution
    # across retraining cycles. Per-batch differences are enforced via the
    # vary_batch_predictions.py post-hoc shift (will move to seed-per-batch in Phase 2).
    {"forecast_run_id": 1, "story_ts": "2026-01-01", "model_version": "lgbm-v1.0"},
    {"forecast_run_id": 2, "story_ts": "2026-01-15", "model_version": "lgbm-v1.0"},
    {"forecast_run_id": 3, "story_ts": "2026-02-01", "model_version": "lgbm-v1.1"},
    {"forecast_run_id": 4, "story_ts": "2026-02-15", "model_version": "lgbm-v2.0"},
    {"forecast_run_id": 5, "story_ts": "2026-03-01", "model_version": "lgbm-v2.0"},
    {"forecast_run_id": 6, "story_ts": "2026-03-15", "model_version": "lgbm-v2.1"},
]

TRAIN_FRAC = 0.70
CAL_FRAC = 0.14


def _split_data(df: pd.DataFrame):
    """70% train / 14% cal / rest test, time-ordered, per route."""
    groups = []
    for rid, grp in df.groupby("route_id"):
        grp = grp.sort_values("demand_date").reset_index(drop=True)
        n = len(grp)
        n_train = int(n * TRAIN_FRAC)
        n_cal = int(n * CAL_FRAC)
        groups.append(
            (grp.iloc[:n_train].copy(), grp.iloc[n_train : n_train + n_cal].copy())
        )
    train_all = pd.concat([g[0] for g in groups], ignore_index=True)
    cal_all = pd.concat([g[1] for g in groups], ignore_index=True)
    return train_all, cal_all


def _write_forecasts(
    conn: mariadb.Connection,
    df: pd.DataFrame,
    model_version: str,
    forecast_run_id: int,
    forecast_run_ts: str,
) -> None:
    cur = conn.cursor()
    rows = [
        (
            int(forecast_run_id),
            forecast_run_ts,
            int(r.route_id),
            r.forecast_date,
            float(r.predicted_demand),
            float(r.lower_bound),
            float(r.upper_bound),
            float(r.confidence_level),
            model_version,
        )
        for r in df.itertuples(index=False)
    ]
    cur.executemany(
        """INSERT INTO forecasts
           (forecast_run_id, forecast_run_ts, route_id, forecast_date,
            predicted_demand, lower_bound, upper_bound, confidence_level,
            model_version)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def _write_metrics(
    conn: mariadb.Connection,
    forecast_run_id: int,
    model_version: str,
    evaluation_date: str,
    mean_coverage: float,
    mean_width: float,
    mape: float,
    route_count: int,
    horizon_days: int = 30,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO model_metrics
           (evaluation_date, model_version, forecast_run_id,
            mean_coverage, mean_interval_width, mape, route_count, horizon_days)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON DUPLICATE KEY UPDATE
               mean_coverage = VALUES(mean_coverage),
               mean_interval_width = VALUES(mean_interval_width),
               mape = VALUES(mape)""",
        (evaluation_date, model_version, forecast_run_id,
         0.0 if (isinstance(mean_coverage, float) and mean_coverage != mean_coverage) else float(mean_coverage),
         0.0 if (isinstance(mean_width, float) and mean_width != mean_width) else float(mean_width),
         0.0 if (isinstance(mape, float) and mape != mape) else float(mape),
         route_count, horizon_days),
    )


def _reset_versioning(conn: mariadb.Connection) -> None:
    """Drop and re-add system versioning to wipe all history cleanly."""
    cur = conn.cursor()
    print("  Resetting system versioning on forecasts...")
    cur.execute("ALTER TABLE forecasts DROP SYSTEM VERSIONING")
    cur.execute("DELETE FROM forecasts")
    cur.execute("ALTER TABLE forecasts ADD SYSTEM VERSIONING")
    print("  Resetting system versioning on model_metrics...")
    cur.execute("ALTER TABLE model_metrics DROP SYSTEM VERSIONING")
    cur.execute("DELETE FROM model_metrics")
    cur.execute("ALTER TABLE model_metrics ADD SYSTEM VERSIONING")
    cur.execute("DELETE FROM batch_run_mapping")
    conn.commit()
    print("  Versioning reset complete.")


def main(reset: bool = False, seed_demand: bool = True) -> None:
    print("Connecting to MariaDB...")
    conn = get_connection()
    cur = conn.cursor()

    # ── Step 0: Load OpenFlights static data ─────────────────────────────────
    print("\n[Step 0] Loading OpenFlights data...")
    load_openflights(conn)

    # Sanity check
    cur.execute("SELECT COUNT(*) FROM routes")
    n_routes = cur.fetchone()[0]
    if n_routes == 0:
        print("ERROR: routes table is empty after load attempt. Check network access.")
        sys.exit(1)
    print(f"  routes: {n_routes} rows")

    if reset:
        _reset_versioning(conn)
    else:
        # Non-destructive: just clear any existing batches we will re-run
        for cfg in BATCH_CONFIGS:
            cur.execute("DELETE FROM forecasts WHERE forecast_run_id = ?",
                        (cfg["forecast_run_id"],))
        cur.execute("DELETE FROM batch_run_mapping")
        conn.commit()

    if seed_demand:
        # Check if route_demand is already seeded
        cur.execute("SELECT COUNT(*) FROM route_demand")
        (n_demand,) = cur.fetchone()
        if n_demand == 0:
            print("Seeding route_demand...")
            run_demand_pipeline(conn)
        else:
            print(f"route_demand already has {n_demand} rows — skipping seed.")

    # Load sampled routes (must match what's in route_demand)
    print("Loading hub degrees and sampled routes...")
    hub_degrees = compute_hub_degrees(conn)
    sampled_routes = sample_routes(conn, hub_degrees)
    print(f"  Using {len(sampled_routes)} routes")

    # Load full demand + engineer features once
    print("Loading features...")
    cur.execute(
        "SELECT route_id, demand_date, demand_volume, day_of_week, month, "
        "       is_holiday, hub_score_source, hub_score_dest "
        "FROM route_demand ORDER BY route_id, demand_date"
    )
    raw = pd.DataFrame(cur.fetchall(),
                       columns=["route_id", "demand_date", "demand_volume",
                                "day_of_week", "month", "is_holiday",
                                "hub_score_source", "hub_score_dest"])

    # Attach distance from DB
    cur2 = conn.cursor()
    cur2.execute(
        """SELECT r.id AS route_id,
                  ST_DISTANCE_SPHERE(POINT(a1.longitude,a1.latitude),
                                     POINT(a2.longitude,a2.latitude)) / 1000 AS distance_km
           FROM routes r
           JOIN airports a1 ON r.src_airport = a1.iata
           JOIN airports a2 ON r.dst_airport = a2.iata
           WHERE a1.latitude IS NOT NULL AND a2.latitude IS NOT NULL"""
    )
    dist_rows = cur2.fetchall()
    dist_df = pd.DataFrame(dist_rows, columns=[d[0] for d in cur2.description])
    raw = raw.merge(dist_df, on="route_id", how="left")
    raw["distance_km"] = raw["distance_km"].fillna(0.0)

    full_features = engineer_features(raw)
    # Encode route_id_cat globally so all batches use the same encoding
    route_codes = {rid: i for i, rid in enumerate(sorted(full_features["route_id"].unique()))}
    full_features["route_id_cat"] = full_features["route_id"].map(route_codes)

    for cfg in BATCH_CONFIGS:
        run_id = cfg["forecast_run_id"]
        story_ts = cfg["story_ts"]
        model_ver = cfg["model_version"]
        print(f"\nBatch {run_id}: story_ts={story_ts}, model={model_ver}")

        # Use only demand data before story_ts (no leakage)
        mask = full_features["demand_date"] < pd.Timestamp(story_ts)
        avail = full_features[mask].copy()
        if avail.empty:
            print(f"  WARNING: no features before {story_ts}, skipping")
            continue

        train_df, cal_df = _split_data(avail)
        feat_cols = [c for c in FEATURE_COLS if c in train_df.columns]

        X_train = train_df[feat_cols]
        y_train = train_df["demand_volume"].values
        X_cal = cal_df[feat_cols]
        y_cal = cal_df["demand_volume"].values

        if len(X_cal) < 50:
            print(f"  WARNING: only {len(X_cal)} calibration rows, skipping batch")
            continue

        # ★17 (Phase 2B): Per-batch seed makes each model genuinely distinct.
        # Replaces the post-hoc shift hack in vary_batch_predictions.py — the
        # Prediction Diff chart now shows real inter-version variation.
        per_batch_seed = GLOBAL_SEED + run_id
        print(f"  Training (n_train={len(X_train)}, n_cal={len(X_cal)}, seed={per_batch_seed})...")
        # ★18 (Phase 3): Receive both base and MAPIE — base is used by the
        # recursive feature builder for fast step-wise prediction; MAPIE
        # is applied at the end of the horizon to wrap with calibrated intervals.
        base_model, model = train_and_wrap(
            X_train, y_train, X_cal, y_cal,
            confidence_level=CONFIDENCE_LEVEL,
            seed=per_batch_seed,
            return_base=True,
        )

        # ★18 (Phase 3): Recursive feature builder — Day d's lag_1 is Day (d-1)'s
        # PREDICTION, not the frozen lag from before story_ts. Matches how the
        # model was trained (engineer_features uses pandas shift(1)/shift(7)/shift(30)
        # on real demand). Without this, all 30 forecast days saw identical lag
        # features and Day 1 vs Day 30 predictions barely differed.
        print(f"  Building future features (horizon=30 days, recursive)...")
        X_future = build_future_features_recursive(
            conn, sampled_routes, story_ts, base_model, horizon_days=30,
        )
        if X_future.empty:
            print("  WARNING: no future features, skipping")
            continue

        print(f"  Generating forecast ({len(X_future)} rows)...")
        forecast_df = generate_forecast_batch(model, X_future, CONFIDENCE_LEVEL)

        _write_forecasts(conn, forecast_df, model_ver, run_id, story_ts)
        conn.commit()

        # ★11: Read real ROW_START back from MariaDB — do NOT use datetime.utcnow()
        time.sleep(2)  # Guarantees strictly later ROW_START for next batch
        cur.execute(
            "SELECT MAX(ROW_START) FROM forecasts WHERE forecast_run_id = ?",
            (run_id,),
        )
        real_row_start = cur.fetchone()[0]
        print(f"  ROW_START={real_row_start} (story={story_ts})")

        # ★12: Persist mapping to DB table, NOT JSON file
        cur.execute(
            """INSERT INTO batch_run_mapping
                   (forecast_run_id, story_ts, row_start_ts, model_version)
               VALUES (?, ?, ?, ?)
               ON DUPLICATE KEY UPDATE
                   story_ts      = VALUES(story_ts),
                   row_start_ts  = VALUES(row_start_ts),
                   model_version = VALUES(model_version)""",
            (run_id, story_ts, real_row_start, model_ver),
        )

        # Write model metrics
        mean_width = float((forecast_df["upper_bound"] - forecast_df["lower_bound"]).mean())
        _write_metrics(
            conn, run_id, model_ver, story_ts,
            mean_coverage=float("nan"),  # actual coverage computed after actuals arrive
            mean_width=mean_width,
            mape=0.0,
            route_count=forecast_df["route_id"].nunique(),
        )
        conn.commit()
        print(f"  Batch {run_id} complete. {len(forecast_df)} forecast rows written.")

    # Final sanity check
    cur.execute("SELECT COUNT(DISTINCT forecast_run_id) FROM forecasts FOR SYSTEM_TIME ALL")
    (n_batches,) = cur.fetchone()
    print(f"\nDone. {n_batches} distinct batches in temporal history.")
    print("Open http://localhost:8501 to view the dashboard.")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FlightCast bootstrap")
    parser.add_argument(
        "--reset", action="store_true",
        help="Drop and recreate system versioning to wipe all history."
    )
    parser.add_argument(
        "--no-seed", action="store_true",
        help="Skip synthetic demand generation (use if route_demand is already populated)."
    )
    args = parser.parse_args()
    main(reset=args.reset, seed_demand=not args.no_seed)
