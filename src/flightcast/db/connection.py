"""
MariaDB connection factory.
Uses the official mariadb connector (binary wheels, no Connector/C MSI needed).
"""
import time
import mariadb
from flightcast.config import load_db_config

_CONN: mariadb.Connection | None = None


def get_connection(retries: int = 10, delay: float = 3.0) -> mariadb.Connection:
    """Return a live MariaDB connection, retrying on startup lag."""
    cfg = load_db_config()
    for attempt in range(retries):
        try:
            conn = mariadb.connect(**cfg.as_connect_kwargs())
            return conn
        except mariadb.Error as exc:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise RuntimeError(
                    f"Could not connect to MariaDB after {retries} attempts"
                ) from exc
    raise RuntimeError("Unreachable")


def get_db_connection() -> mariadb.Connection:
    """Cached singleton for Streamlit. Use get_connection() elsewhere."""
    global _CONN
    if _CONN is None or not _CONN.open:
        _CONN = get_connection()
    return _CONN
