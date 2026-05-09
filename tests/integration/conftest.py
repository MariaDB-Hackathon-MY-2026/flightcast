"""
Integration test fixtures — requires a live MariaDB instance.
Set env var: MARIADB_TEST_URL=mariadb://user:pass@localhost:3306/flightcast_test
Or run: docker compose exec app pytest tests/integration/
"""
import os
import pytest
import mariadb

from flightcast.db.connection import get_connection


@pytest.fixture(scope="session")
def db_conn():
    conn = get_connection()
    yield conn
    conn.close()
