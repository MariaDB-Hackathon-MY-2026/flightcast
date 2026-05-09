"""
Streamlit session_state initialisation and shared cache helpers.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import mariadb
from flightcast.db.connection import get_db_connection
from flightcast.db.repositories import fetch_routes, fetch_batch_mapping


@st.cache_resource(show_spinner=False)
def _cached_conn() -> mariadb.Connection:
    """Cached connection. Streamlit guarantees one instance per server process."""
    return get_db_connection()


def get_conn() -> mariadb.Connection:
    """
    Return a live MariaDB connection, transparently re-establishing it if the
    cached one has gone stale (idle timeout, server restart, etc.).

    Streamlit's `@st.cache_resource` survives reruns but not server restarts;
    MariaDB's `wait_timeout` (default 8 hours) can also drop idle connections.
    The mariadb Python connector's `ping()` takes no arguments — when the
    connection is dead it raises `mariadb.OperationalError`. We catch that
    and rebuild the cached connection.
    """
    conn = _cached_conn()
    try:
        conn.ping()
        return conn
    except mariadb.Error:
        # Connection is dead — clear the cache and rebuild from scratch.
        _cached_conn.clear()
        return _cached_conn()


@st.cache_data(ttl=600, show_spinner=False)
def load_batch_mapping() -> pd.DataFrame:
    return fetch_batch_mapping(get_conn())


@st.cache_data(ttl=600, show_spinner=False)
def load_routes() -> pd.DataFrame:
    return fetch_routes(get_conn())


def route_options(routes: pd.DataFrame) -> list[int]:
    return routes["route_id"].tolist()


def route_label(route_id: int, routes: pd.DataFrame) -> str:
    row = routes[routes["route_id"] == route_id]
    if row.empty:
        return str(route_id)
    r = row.iloc[0]
    return f"{r['src_airport']} → {r['dst_airport']}"
