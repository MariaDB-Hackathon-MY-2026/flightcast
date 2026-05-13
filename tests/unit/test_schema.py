"""
Schema sanity tests — no DB needed, reads the SQL file directly.
"""
import pathlib


SQL_PATH = pathlib.Path(__file__).parents[2] / "initdb" / "03-flightcast-schema.sql"
VERSIONING_PATH = pathlib.Path(__file__).parents[2] / "initdb" / "04-system-versioning.sql"


def _read(path):
    return path.read_text(encoding="utf-8").upper()


def test_forecasts_has_system_versioning():
    content = _read(VERSIONING_PATH)
    assert "ADD SYSTEM VERSIONING" in content


def test_forecasts_has_forecast_run_id():
    content = _read(SQL_PATH)
    assert "FORECAST_RUN_ID" in content


def test_interval_width_is_virtual():
    content = _read(SQL_PATH)
    assert "VIRTUAL" in content
    assert "INTERVAL_WIDTH" in content


def test_fk_is_restrict_not_cascade_on_versioned():
    content = _read(SQL_PATH)
    # Verify forecasts FK is RESTRICT (not CASCADE)
    # routes has CASCADE (non-versioned), forecasts should have RESTRICT
    assert "ON UPDATE RESTRICT" in content


def test_batch_run_mapping_exists():
    content = _read(SQL_PATH)
    assert "BATCH_RUN_MAPPING" in content


def test_routes_has_primary_key():
    routes_path = pathlib.Path(__file__).parents[2] / "initdb" / "01-openflights-create.sql"
    content = routes_path.read_text(encoding="utf-8").upper()
    assert "PRIMARY KEY" in content
    assert "AUTO_INCREMENT" in content
