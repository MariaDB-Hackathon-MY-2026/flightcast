"""
Query helpers and FOR SYSTEM_TIME wrappers.
All parameterised — no f-string SQL.
"""
from __future__ import annotations

import mariadb
import pandas as pd
from datetime import datetime


def _df(cur: mariadb.Cursor) -> pd.DataFrame:
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    return pd.DataFrame(rows, columns=cols)


def fetch_routes(conn: mariadb.Connection) -> pd.DataFrame:
    """Returns only the sampled routes that have demand data (and forecasts)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.id AS route_id,
               r.src_airport, r.dst_airport,
               a1.latitude  AS src_lat, a1.longitude AS src_lon,
               a2.latitude  AS dst_lat, a2.longitude AS dst_lon,
               a1.country   AS src_country
        FROM routes r
        JOIN airports a1 ON r.src_airport = a1.iata
        JOIN airports a2 ON r.dst_airport = a2.iata
        WHERE r.id IN (SELECT DISTINCT route_id FROM route_demand)
          AND a1.latitude IS NOT NULL AND a2.latitude IS NOT NULL
          AND a1.iata != '' AND a2.iata != ''
        """
    )
    return _df(cur)


def fetch_forecasts_as_of(
    conn: mariadb.Connection,
    as_of: datetime,
    route_id: int,
    forecast_run_id: int | None = None,
) -> pd.DataFrame:
    """
    Returns forecasts visible at `as_of` for the given route.

    If `forecast_run_id` is given, the result is narrowed to that single batch
    (recommended for the Time Travel hero page so only the selected model's
    predictions render).
    """
    cur = conn.cursor()
    if forecast_run_id is None:
        cur.execute(
            """
            SELECT route_id, forecast_run_id, forecast_date, predicted_demand,
                   lower_bound, upper_bound, model_version,
                   actual_demand, coverage_score,
                   ROW_START, ROW_END
            FROM forecasts FOR SYSTEM_TIME AS OF ?
            WHERE route_id = ?
            ORDER BY forecast_date
            """,
            (as_of, route_id),
        )
    else:
        cur.execute(
            """
            SELECT route_id, forecast_run_id, forecast_date, predicted_demand,
                   lower_bound, upper_bound, model_version,
                   actual_demand, coverage_score,
                   ROW_START, ROW_END
            FROM forecasts FOR SYSTEM_TIME AS OF ?
            WHERE route_id = ? AND forecast_run_id = ?
            ORDER BY forecast_date
            """,
            (as_of, route_id, forecast_run_id),
        )
    return _df(cur)


def fetch_forecasts_all(
    conn: mariadb.Connection,
    route_id: int,
) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT forecast_id, forecast_run_id, forecast_run_ts,
               route_id, forecast_date, predicted_demand,
               lower_bound, upper_bound, confidence_level,
               model_version, coverage_score, actual_demand,
               ROW_START, ROW_END
        FROM forecasts FOR SYSTEM_TIME ALL
        WHERE route_id = ?
        ORDER BY ROW_START, forecast_date
        """,
        (route_id,),
    )
    return _df(cur)


def fetch_batch_mapping(conn: mariadb.Connection) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(
        "SELECT forecast_run_id, story_ts, row_start_ts, model_version "
        "FROM batch_run_mapping ORDER BY row_start_ts"
    )
    return _df(cur)


def fetch_coverage_series(
    conn: mariadb.Connection,
    from_date: str,
    to_date: str,
) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT forecast_date,
               AVG(coverage_score) AS empirical_coverage_30d
        FROM forecasts
        WHERE coverage_score IS NOT NULL
          AND forecast_date BETWEEN ? AND ?
        GROUP BY forecast_date
        ORDER BY forecast_date
        """,
        (from_date, to_date),
    )
    return _df(cur)


def fetch_route_distance(conn: mariadb.Connection) -> pd.DataFrame:
    """Uses MariaDB ST_DISTANCE_SPHERE — MariaDB-specific function."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.id AS route_id,
               ST_DISTANCE_SPHERE(
                   POINT(a1.longitude, a1.latitude),
                   POINT(a2.longitude, a2.latitude)
               ) / 1000 AS distance_km
        FROM routes r
        JOIN airports a1 ON r.src_airport = a1.iata
        JOIN airports a2 ON r.dst_airport = a2.iata
        WHERE a1.latitude IS NOT NULL AND a2.latitude IS NOT NULL
        """
    )
    return _df(cur)


def fetch_demand_up_to(
    conn: mariadb.Connection,
    story_ts: str,
) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT rd.demand_id, rd.route_id, rd.demand_date, rd.demand_volume,
               rd.day_of_week, rd.month, rd.is_holiday,
               rd.hub_score_source, rd.hub_score_dest
        FROM route_demand rd
        WHERE rd.demand_date < ?
        ORDER BY rd.route_id, rd.demand_date
        """,
        (story_ts,),
    )
    return _df(cur)
