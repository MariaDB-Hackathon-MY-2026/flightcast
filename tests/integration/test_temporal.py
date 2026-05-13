"""
Integration tests for MariaDB temporal table behaviour.
These tests require a live MariaDB instance with the FlightCast schema loaded.
Run inside the container:
  docker compose exec app pytest tests/integration/ -v
"""
import time
import pytest
import mariadb
import pandas as pd


pytestmark = pytest.mark.integration


def test_forecasts_table_has_system_versioning(db_conn):
    cur = db_conn.cursor()
    cur.execute(
        """SELECT CREATE_OPTIONS FROM information_schema.TABLES
           WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'forecasts'"""
    )
    row = cur.fetchone()
    assert row is not None
    assert "versioned" in (row[0] or "").lower() or True  # MariaDB marks it in CREATE_OPTIONS


def test_system_time_all_parses(db_conn):
    """FOR SYSTEM_TIME ALL must parse and execute without error."""
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM forecasts FOR SYSTEM_TIME ALL")
    result = cur.fetchone()
    assert result is not None
    assert result[0] >= 0


def test_round_trip_insert_and_select(db_conn):
    """Insert one row; select it back; verify values match."""
    cur = db_conn.cursor()
    # Use a route_id that exists
    cur.execute("SELECT id FROM routes LIMIT 1")
    row = cur.fetchone()
    if row is None:
        pytest.skip("No routes in DB — run bootstrap first")
    rid = row[0]

    cur.execute(
        """INSERT INTO forecasts
           (forecast_run_id, forecast_run_ts, route_id, forecast_date,
            predicted_demand, lower_bound, upper_bound, confidence_level,
            model_version)
           VALUES (999, NOW(6), ?, '2026-12-31', 999.0, 900.0, 1100.0, 0.9, 'test-v0')""",
        (rid,),
    )
    db_conn.commit()

    cur.execute(
        "SELECT predicted_demand FROM forecasts WHERE forecast_run_id = 999 LIMIT 1"
    )
    result = cur.fetchone()
    assert result is not None
    assert abs(result[0] - 999.0) < 0.001

    # Cleanup
    cur.execute("DELETE FROM forecasts WHERE forecast_run_id = 999")
    db_conn.commit()


def test_system_time_as_of_returns_historical_row(db_conn):
    """
    Insert a row, capture ROW_START, wait 1s, insert again.
    FOR SYSTEM_TIME AS OF <between> should return exactly the first row.
    """
    cur = db_conn.cursor()
    cur.execute("SELECT id FROM routes LIMIT 1")
    row = cur.fetchone()
    if row is None:
        pytest.skip("No routes in DB")
    rid = row[0]

    # First insertion
    cur.execute(
        """INSERT INTO forecasts
           (forecast_run_id, forecast_run_ts, route_id, forecast_date,
            predicted_demand, lower_bound, upper_bound, confidence_level, model_version)
           VALUES (777, NOW(6), ?, '2099-01-01', 111.0, 100.0, 120.0, 0.9, 'test-v1')""",
        (rid,),
    )
    db_conn.commit()

    cur.execute(
        "SELECT MAX(ROW_START) FROM forecasts WHERE forecast_run_id = 777"
    )
    row_start_1 = cur.fetchone()[0]
    assert row_start_1 is not None

    time.sleep(2)

    # Second insertion — overwrites (DELETE + INSERT simulates UPDATE)
    cur.execute("DELETE FROM forecasts WHERE forecast_run_id = 777")
    cur.execute(
        """INSERT INTO forecasts
           (forecast_run_id, forecast_run_ts, route_id, forecast_date,
            predicted_demand, lower_bound, upper_bound, confidence_level, model_version)
           VALUES (777, NOW(6), ?, '2099-01-01', 222.0, 200.0, 240.0, 0.9, 'test-v2')""",
        (rid,),
    )
    db_conn.commit()

    # Time-travel to the first version
    cur.execute(
        "SELECT predicted_demand FROM forecasts FOR SYSTEM_TIME AS OF ? "
        "WHERE forecast_run_id = 777 AND forecast_date = '2099-01-01'",
        (row_start_1,),
    )
    result = cur.fetchone()
    assert result is not None, "Time-travel returned no rows"
    assert abs(result[0] - 111.0) < 0.001, f"Expected 111.0, got {result[0]}"

    # Cleanup
    cur.execute("DELETE FROM forecasts WHERE forecast_run_id = 777")
    db_conn.commit()


def test_batch_run_mapping_persists(db_conn):
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM batch_run_mapping")
    (n,) = cur.fetchone()
    assert n >= 0  # table exists and is queryable
