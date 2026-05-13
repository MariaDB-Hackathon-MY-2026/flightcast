"""
Hero SQL helpers for MariaDB FOR SYSTEM_TIME queries.
Every function here is a MariaDB-specific feature — MySQL cannot run this code.
"""
from __future__ import annotations

import mariadb
import pandas as pd
from datetime import datetime


HERO_AS_OF_SQL = """
-- MariaDB-only: returns the prediction batch that existed at the given timestamp
SELECT route_id, forecast_date, predicted_demand,
       lower_bound, upper_bound, model_version,
       ROW_START, ROW_END
FROM forecasts FOR SYSTEM_TIME AS OF ?
WHERE route_id = ?
ORDER BY forecast_date
"""

HERO_DIFF_SQL = """
-- Compare two prediction batches at different points in time
SELECT
    a.route_id,
    a.forecast_date,
    a.predicted_demand  AS predicted_a,
    b.predicted_demand  AS predicted_b,
    b.predicted_demand - a.predicted_demand AS delta,
    a.upper_bound - a.lower_bound           AS width_a,
    b.upper_bound - b.lower_bound           AS width_b,
    a.model_version AS model_a,
    b.model_version AS model_b
FROM
    (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF ? WHERE route_id = ?) a
JOIN
    (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF ? WHERE route_id = ?) b
    ON a.forecast_date = b.forecast_date
ORDER BY a.forecast_date
"""

HERO_ALL_HISTORY_SQL = """
-- Full audit log: every version of every prediction
SELECT forecast_run_id, forecast_date, predicted_demand,
       lower_bound, upper_bound, model_version,
       ROW_START, ROW_END
FROM forecasts FOR SYSTEM_TIME ALL
WHERE route_id = ?
ORDER BY ROW_START, forecast_date
"""

HERO_COVERAGE_SQL = """
-- Rolling 30-day empirical coverage — the calibration drift chart
SELECT forecast_date,
       AVG(coverage_score) AS empirical_coverage_30d,
       COUNT(*)            AS sample_size
FROM forecasts
WHERE coverage_score IS NOT NULL
  AND forecast_date BETWEEN DATE_SUB(?, INTERVAL 30 DAY) AND ?
GROUP BY forecast_date
ORDER BY forecast_date
"""

STORAGE_SAVINGS_SQL = """
-- Versioned vs manual-history storage comparison (used in benchmark)
SELECT
    'forecasts (versioned)' AS table_name,
    ROUND(DATA_LENGTH / 1024 / 1024, 2) AS data_mb,
    ROUND(INDEX_LENGTH / 1024 / 1024, 2) AS index_mb,
    TABLE_ROWS AS row_count
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'forecasts'
UNION ALL
SELECT
    'forecasts_manual (control)',
    ROUND(DATA_LENGTH / 1024 / 1024, 2),
    ROUND(INDEX_LENGTH / 1024 / 1024, 2),
    TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'forecasts_manual'
"""


def _df(cur: mariadb.Cursor) -> pd.DataFrame:
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    return pd.DataFrame(rows, columns=cols)


def query_as_of(
    conn: mariadb.Connection,
    as_of: datetime,
    route_id: int,
) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(HERO_AS_OF_SQL, (as_of, route_id))
    return _df(cur)


def query_diff(
    conn: mariadb.Connection,
    date_a: datetime,
    date_b: datetime,
    route_id: int,
) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(HERO_DIFF_SQL, (date_a, route_id, date_b, route_id))
    return _df(cur)


def query_all_history(
    conn: mariadb.Connection,
    route_id: int,
) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(HERO_ALL_HISTORY_SQL, (route_id,))
    return _df(cur)


def query_coverage_series(
    conn: mariadb.Connection,
    from_date: str,
    to_date: str,
) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(HERO_COVERAGE_SQL, (to_date, to_date))
    return _df(cur)


def query_storage_comparison(conn: mariadb.Connection) -> pd.DataFrame:
    cur = conn.cursor()
    cur.execute(STORAGE_SAVINGS_SQL)
    return _df(cur)
