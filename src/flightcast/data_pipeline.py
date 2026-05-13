"""
OpenFlights load + synthetic demand pipeline.

DAG:
  airports, routes (loaded by initdb SQL)
    -> compute_hub_degrees()
    -> sample_routes(n=50)   [stratified: 10 hub-hub, 25 mid, 15 thin]
    -> generate_demand_series(n_days=730)
    -> apply_holiday_flags()
    -> bulk_insert_demand(chunk=1000)
    -> [route_demand populated]
"""
from __future__ import annotations

import mariadb
import numpy as np
import pandas as pd

from flightcast.config import GLOBAL_SEED, N_ROUTES
from flightcast.synth_demand import generate_demand_series

MAJOR_HOLIDAYS = {
    "01-01", "12-25", "12-26",
    "07-04", "11-11",
    "08-31",  # Malaysia Merdeka
    "02-01",  # Chinese New Year approx
    "04-15", "07-15", "10-15",
}


def compute_hub_degrees(conn: mariadb.Connection) -> dict[str, int]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT src_airport, COUNT(*) AS cnt FROM routes GROUP BY src_airport
        UNION ALL
        SELECT dst_airport, COUNT(*) AS cnt FROM routes GROUP BY dst_airport
        """
    )
    degrees: dict[str, int] = {}
    for airport, cnt in cur.fetchall():
        degrees[airport] = degrees.get(airport, 0) + cnt
    return degrees


def sample_routes(
    conn: mariadb.Connection,
    hub_degrees: dict[str, int],
    n: int = N_ROUTES,
    seed: int = GLOBAL_SEED,
) -> pd.DataFrame:
    """
    Stratified sample: top 10 hub-hub, mid 25, bottom 15.
    Returns DataFrame with: route_id, src_airport, dst_airport,
    hub_degree_src, hub_degree_dst, hemisphere
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.id AS route_id, r.src_airport, r.dst_airport,
               a1.latitude AS src_lat, a2.latitude AS dst_lat
        FROM routes r
        JOIN airports a1 ON r.src_airport = a1.iata
        JOIN airports a2 ON r.dst_airport = a2.iata
        WHERE a1.latitude IS NOT NULL AND a2.latitude IS NOT NULL
          AND a1.iata != '' AND a2.iata != ''
          AND r.src_airport != r.dst_airport
        """
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        raise RuntimeError("No routes with valid airport coordinates found")

    df["hub_degree_src"] = df["src_airport"].map(hub_degrees).fillna(1).astype(int)
    df["hub_degree_dst"] = df["dst_airport"].map(hub_degrees).fillna(1).astype(int)
    df["hub_score"] = df["hub_degree_src"] * df["hub_degree_dst"]
    df = df.sort_values("hub_score", ascending=False).reset_index(drop=True)

    # hemisphere from source airport latitude
    df["hemisphere"] = np.where(df["src_lat"] >= 0, "N", "S")

    n_total = len(df)
    n_hub = min(10, n_total // 3)
    n_thin = min(15, n_total // 3)
    n_mid = n - n_hub - n_thin

    rng = np.random.default_rng(seed)

    hub_sample = df.iloc[:n_hub].copy()
    hub_sample["tier"] = "hub"
    thin_sample = df.iloc[-n_thin:].copy()
    thin_sample["tier"] = "thin"
    mid_pool = df.iloc[n_hub : len(df) - n_thin]
    mid_sample = mid_pool.sample(min(n_mid, len(mid_pool)), random_state=seed).copy()
    mid_sample["tier"] = "mid"

    result = pd.concat([hub_sample, mid_sample, thin_sample], ignore_index=True)
    result = result.drop_duplicates(subset=["route_id"])
    return result[
        ["route_id", "src_airport", "dst_airport",
         "hub_degree_src", "hub_degree_dst", "hemisphere", "tier"]
    ].reset_index(drop=True)


def _apply_holiday_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_holiday"] = df["demand_date"].apply(
        lambda d: int(d.strftime("%m-%d") in MAJOR_HOLIDAYS)
    )
    return df


def bulk_insert_demand(
    conn: mariadb.Connection,
    df: pd.DataFrame,
    chunk_size: int = 1000,
) -> int:
    cur = conn.cursor()
    # Tier defaults to 'mid' if absent (preserves backwards compat for tests).
    if "tier" not in df.columns:
        df = df.assign(tier="mid")
    rows = [
        (
            int(r.route_id),
            r.demand_date,
            float(r.demand_volume),
            int(r.day_of_week),
            int(r.month),
            int(r.is_holiday),
            float(r.hub_score_source),
            float(r.hub_score_dest),
            str(getattr(r, "tier", "mid")),
        )
        for r in df.itertuples(index=False)
    ]
    inserted = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        cur.executemany(
            """INSERT IGNORE INTO route_demand
               (route_id, demand_date, demand_volume, day_of_week, month,
                is_holiday, hub_score_source, hub_score_dest, tier)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            chunk,
        )
        conn.commit()
        inserted += cur.rowcount
    return inserted


def run_demand_pipeline(conn: mariadb.Connection) -> pd.DataFrame:
    """Full pipeline: hub degrees -> sample routes -> generate -> insert."""
    print("Computing hub degrees...")
    hub_degrees = compute_hub_degrees(conn)

    print("Sampling routes...")
    routes = sample_routes(conn, hub_degrees)
    print(f"  Sampled {len(routes)} routes")

    print("Generating synthetic demand series...")
    demand_df = generate_demand_series(routes)
    demand_df = _apply_holiday_flags(demand_df)

    # rename columns to match DB schema
    demand_df = demand_df.rename(
        columns={"demand_date": "demand_date", "hub_score_source": "hub_score_source"}
    )
    # Ensure hub_score_source / hub_score_dest columns exist
    if "hub_score_source" not in demand_df.columns:
        demand_df["hub_score_source"] = demand_df["hub_score_src"]
    if "hub_score_dest" not in demand_df.columns:
        demand_df["hub_score_dest"] = demand_df["hub_score_dst"]

    print("Inserting demand rows...")
    n = bulk_insert_demand(conn, demand_df)
    print(f"  Inserted {n} rows into route_demand")
    return demand_df
