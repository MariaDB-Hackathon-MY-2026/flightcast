"""
FlightCast FastAPI application.
All endpoints use MariaDB FOR SYSTEM_TIME AS OF for time-travel queries.

Streamlit queries MariaDB directly for latency reasons;
FastAPI provides the "this could be a service" story for judges.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import date, datetime
from functools import wraps
from typing import Any, Callable, Generator, List, Optional

import mariadb
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from flightcast.config import load_db_config
from flightcast.db.connection import get_connection
from flightcast.api.models import (
    ForecastPoint, CoverageSample, DiffResult, BatchInfo, HealthResponse
)

# ─────────────────────────────────────────────────────────────────────
# Connection pool — replaces the previous global single-connection
# pattern that was prone to wedging after idle periods. Pool connections
# are kept alive between requests; the pool reissues a fresh socket if
# one goes bad.
# ─────────────────────────────────────────────────────────────────────

_POOL: mariadb.ConnectionPool | None = None
_POOL_SIZE = 8


def _create_pool() -> mariadb.ConnectionPool:
    cfg = load_db_config()
    return mariadb.ConnectionPool(
        pool_name="flightcast_api",
        pool_size=_POOL_SIZE,
        pool_reset_connection=False,
        **cfg.as_connect_kwargs(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _POOL
    # Retry on startup — mariadb may not be ready yet
    for attempt in range(10):
        try:
            _POOL = _create_pool()
            break
        except mariadb.Error:
            if attempt == 9:
                raise
            time.sleep(2.0)
    yield
    # Pool cleanup on shutdown
    if _POOL is not None:
        try:
            _POOL.close()
        except Exception:
            pass


app = FastAPI(
    title="FlightCast API",
    description="Aviation demand forecasting with MariaDB temporal tables + MAPIE conformal intervals.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_db() -> Generator[mariadb.Connection, None, None]:
    """
    FastAPI dependency that hands the request a pooled connection.
    `pool.get_connection()` returns immediately if a connection is free;
    if all are busy, it waits briefly. On dead/stale sockets the pool
    transparently allocates a fresh one.

    We close (= return to pool) in the finally block — this ALWAYS runs
    even if the endpoint raises, so connections never leak.
    """
    if _POOL is None:
        raise HTTPException(status_code=503, detail="Connection pool not initialised")
    try:
        conn = _POOL.get_connection()
    except mariadb.PoolError as exc:
        raise HTTPException(status_code=503, detail=f"Pool exhausted: {exc}")
    # Cheap liveness check — ping is a no-op if alive, raises on dead
    try:
        conn.ping()
    except mariadb.Error:
        # Discard the bad connection from the pool by closing the
        # underlying socket; pool will create a replacement on next acquire.
        try:
            conn.close()
        except Exception:
            pass
        # Get a fresh one
        conn = _POOL.get_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()  # returns to pool
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────
# In-memory TTL cache for static-ish endpoints (batches, sampled-routes,
# routes). These never change during a session, so caching for 60s
# eliminates the DB round-trip on rapid refreshes.
# ─────────────────────────────────────────────────────────────────────

_TTL_CACHE: dict[str, tuple[Any, float]] = {}


def ttl_cache(seconds: int = 60):
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Cache key: function name + sorted kwargs
            # (positional args are typically `conn` from Depends — exclude it
            # since the pool guarantees fungibility)
            key_kwargs = tuple(
                sorted((k, v) for k, v in kwargs.items() if k != "conn")
            )
            key = f"{fn.__name__}:{key_kwargs}"
            now = time.time()
            entry = _TTL_CACHE.get(key)
            if entry is not None and entry[1] > now:
                return entry[0]
            value = fn(*args, **kwargs)
            _TTL_CACHE[key] = (value, now + seconds)
            return value
        return wrapper
    return decorator


# Cache-Control header presets
CACHE_LONG = "public, max-age=60, stale-while-revalidate=300"
CACHE_SHORT = "public, max-age=15, stale-while-revalidate=60"
CACHE_NONE = "no-store"


# ─────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────


@app.get("/healthz", response_model=HealthResponse)
def healthz(response: Response, conn: mariadb.Connection = Depends(get_db)):
    response.headers["Cache-Control"] = CACHE_NONE
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return HealthResponse(ok=True, db_connected=db_ok)


@app.get("/batches", response_model=List[BatchInfo])
@ttl_cache(seconds=60)
def list_batches(response: Response, conn: mariadb.Connection = Depends(get_db)):
    response.headers["Cache-Control"] = CACHE_LONG
    cur = conn.cursor(named_tuple=True)
    cur.execute(
        "SELECT forecast_run_id, story_ts, row_start_ts, model_version "
        "FROM batch_run_mapping ORDER BY row_start_ts"
    )
    return [
        BatchInfo(
            forecast_run_id=r.forecast_run_id,
            story_ts=r.story_ts,
            row_start_ts=r.row_start_ts,
            model_version=r.model_version,
        )
        for r in cur.fetchall()
    ]


@app.get("/forecasts", response_model=List[ForecastPoint])
def get_forecasts(
    response: Response,
    route_id: int,
    as_of: datetime,
    run_id: Optional[int] = None,
    limit: int = Query(default=500, le=2000),
    conn: mariadb.Connection = Depends(get_db),
):
    """
    Return predictions that existed at the given timestamp.
    Uses MariaDB FOR SYSTEM_TIME AS OF — MySQL cannot run this query.

    When `run_id` is provided, scopes the result to a single batch
    (30-day forecast). Without it, returns every batch version visible
    at that timestamp (≈ 6 batches × 30 days = 180 rows on a hero route).
    Time Travel + Forecast Explorer both pass run_id; the All-history
    view in Forecast Explorer uses /forecasts/all instead.
    """
    response.headers["Cache-Control"] = CACHE_SHORT
    cur = conn.cursor(named_tuple=True)
    if run_id is None:
        cur.execute(
            """SELECT route_id, forecast_date, predicted_demand,
                      lower_bound, upper_bound, confidence_level,
                      model_version, actual_demand, coverage_score,
                      ROW_START, ROW_END
               FROM forecasts FOR SYSTEM_TIME AS OF ?
               WHERE route_id = ?
               ORDER BY forecast_date
               LIMIT ?""",
            (as_of, route_id, limit),
        )
    else:
        cur.execute(
            """SELECT route_id, forecast_date, predicted_demand,
                      lower_bound, upper_bound, confidence_level,
                      model_version, actual_demand, coverage_score,
                      ROW_START, ROW_END
               FROM forecasts FOR SYSTEM_TIME AS OF ?
               WHERE route_id = ? AND forecast_run_id = ?
               ORDER BY forecast_date
               LIMIT ?""",
            (as_of, route_id, run_id, limit),
        )
    return [
        ForecastPoint(
            route_id=r.route_id,
            forecast_date=r.forecast_date,
            predicted_demand=r.predicted_demand,
            lower_bound=r.lower_bound,
            upper_bound=r.upper_bound,
            confidence_level=r.confidence_level,
            model_version=r.model_version,
            actual_demand=r.actual_demand,
            coverage_score=r.coverage_score,
            row_start=r.ROW_START,
            row_end=r.ROW_END,
        )
        for r in cur.fetchall()
    ]


@app.get("/coverage", response_model=List[CoverageSample])
def get_coverage(response: Response, conn: mariadb.Connection = Depends(get_db)):
    """Coverage metrics per batch from FOR SYSTEM_TIME ALL."""
    response.headers["Cache-Control"] = CACHE_LONG
    cur = conn.cursor(named_tuple=True)
    cur.execute(
        """SELECT forecast_run_id,
                  AVG(coverage_score)            AS mean_coverage,
                  AVG(upper_bound - lower_bound) AS mean_interval_width,
                  COUNT(*)                       AS n_rows
           FROM forecasts FOR SYSTEM_TIME ALL
           WHERE coverage_score IS NOT NULL
           GROUP BY forecast_run_id
           ORDER BY forecast_run_id"""
    )
    return [
        CoverageSample(
            forecast_run_id=r.forecast_run_id,
            mean_coverage=r.mean_coverage,
            mean_interval_width=r.mean_interval_width,
            n_rows=r.n_rows,
        )
        for r in cur.fetchall()
    ]


@app.get("/diff", response_model=List[DiffResult])
def get_diff(
    response: Response,
    route_id: int,
    date_a: datetime,
    date_b: datetime,
    horizon_days: int = Query(default=30, le=90),
    conn: mariadb.Connection = Depends(get_db),
):
    """Compare predictions at two different temporal snapshots."""
    response.headers["Cache-Control"] = CACHE_SHORT
    cur = conn.cursor(named_tuple=True)
    cur.execute(
        """SELECT a.forecast_date,
                  a.predicted_demand  AS predicted_a,
                  b.predicted_demand  AS predicted_b,
                  b.predicted_demand - a.predicted_demand AS delta,
                  a.upper_bound - a.lower_bound  AS width_a,
                  b.upper_bound - b.lower_bound  AS width_b,
                  a.model_version AS model_a,
                  b.model_version AS model_b
           FROM
             (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF ?
              WHERE route_id = ?) a
           JOIN
             (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF ?
              WHERE route_id = ?) b
             ON a.forecast_date = b.forecast_date
           ORDER BY a.forecast_date
           LIMIT ?""",
        (date_a, route_id, date_b, route_id, horizon_days),
    )
    return [
        DiffResult(
            forecast_date=r.forecast_date,
            predicted_a=r.predicted_a,
            predicted_b=r.predicted_b,
            delta=r.delta,
            width_a=r.width_a,
            width_b=r.width_b,
            model_a=r.model_a,
            model_b=r.model_b,
        )
        for r in cur.fetchall()
    ]


@app.get("/routes")
def list_routes(
    response: Response,
    origin: Optional[str] = None,
    dest: Optional[str] = None,
    conn: mariadb.Connection = Depends(get_db),
):
    response.headers["Cache-Control"] = CACHE_LONG
    cur = conn.cursor(named_tuple=True)
    q = (
        "SELECT r.id, r.src_airport, r.dst_airport, r.airline, "
        "a1.name AS src_name, a2.name AS dst_name "
        "FROM routes r "
        "JOIN airports a1 ON r.src_airport = a1.iata "
        "JOIN airports a2 ON r.dst_airport = a2.iata "
        "WHERE 1=1"
    )
    params = []
    if origin:
        q += " AND r.src_airport = ?"
        params.append(origin.upper())
    if dest:
        q += " AND r.dst_airport = ?"
        params.append(dest.upper())
    q += " LIMIT 200"
    cur.execute(q, params)
    return [r._asdict() for r in cur.fetchall()]


@app.get("/sampled-routes")
@ttl_cache(seconds=60)
def list_sampled_routes(response: Response, conn: mariadb.Connection = Depends(get_db)):
    """The 50 routes used by the demand pipeline (subset of all routes)."""
    response.headers["Cache-Control"] = CACHE_LONG
    cur = conn.cursor()
    cur.execute(
        """SELECT DISTINCT rd.route_id,
                  r.src_airport, r.dst_airport,
                  a1.name AS src_name, a2.name AS dst_name,
                  rd.tier
           FROM route_demand rd
           JOIN routes r ON rd.route_id = r.id
           JOIN airports a1 ON r.src_airport = a1.iata
           JOIN airports a2 ON r.dst_airport = a2.iata
           ORDER BY rd.route_id"""
    )
    return [
        {
            "route_id": row[0],
            "src_airport": row[1],
            "dst_airport": row[2],
            "src_name": row[3],
            "dst_name": row[4],
            "tier": row[5],
        }
        for row in cur.fetchall()
    ]


@app.get("/forecasts/all")
def get_forecasts_all(
    response: Response,
    route_id: int,
    conn: mariadb.Connection = Depends(get_db),
):
    """
    Return EVERY historical version of every prediction for a route.
    Uses MariaDB FOR SYSTEM_TIME ALL — the audit-trail showcase query.
    """
    response.headers["Cache-Control"] = CACHE_SHORT
    cur = conn.cursor(named_tuple=True)
    cur.execute(
        """SELECT route_id, forecast_date, predicted_demand,
                  lower_bound, upper_bound, model_version,
                  forecast_run_id, ROW_START, ROW_END
           FROM forecasts FOR SYSTEM_TIME ALL
           WHERE route_id = ?
           ORDER BY forecast_run_id, forecast_date""",
        (route_id,),
    )
    return [
        {
            "route_id": r.route_id,
            "forecast_date": r.forecast_date,
            "predicted_demand": r.predicted_demand,
            "lower_bound": r.lower_bound,
            "upper_bound": r.upper_bound,
            "model_version": r.model_version,
            "forecast_run_id": r.forecast_run_id,
            "row_start": r.ROW_START,
            "row_end": r.ROW_END,
        }
        for r in cur.fetchall()
    ]


@app.get("/actuals")
def get_actuals(
    response: Response,
    route_id: int,
    run_id: int,
    conn: mariadb.Connection = Depends(get_db),
):
    """
    Return the most-recent (post-injection) actual_demand + coverage_score
    for a (route, batch) pair. Used by the dashboard's "Show actuals" toggle
    to overlay ground truth on top of the time-traveled forecast.

    Note this is intentionally NOT a FOR SYSTEM_TIME AS OF query — actuals
    are written by inject_actuals.py AFTER the original batch commit, so
    they only exist in the CURRENT temporal version.
    """
    response.headers["Cache-Control"] = CACHE_SHORT
    cur = conn.cursor()
    cur.execute(
        """SELECT forecast_date, actual_demand, coverage_score
           FROM forecasts
           WHERE route_id = ? AND forecast_run_id = ?
             AND actual_demand IS NOT NULL
           ORDER BY forecast_date""",
        (route_id, run_id),
    )
    return [
        {
            "forecast_date": str(row[0]),
            "actual_demand": float(row[1]),
            "coverage_score": float(row[2]) if row[2] is not None else None,
        }
        for row in cur.fetchall()
    ]


@app.get("/coverage/series")
def get_coverage_series(
    response: Response,
    batch_id: Optional[int] = None,
    conn: mariadb.Connection = Depends(get_db),
):
    """
    Rolling per-batch coverage data — used by the Coverage Drift chart
    on the React dashboard.
    """
    response.headers["Cache-Control"] = CACHE_LONG
    cur = conn.cursor(named_tuple=True)
    if batch_id is None:
        cur.execute(
            """SELECT forecast_run_id, forecast_date,
                      coverage_score, model_version
               FROM forecasts FOR SYSTEM_TIME ALL
               WHERE coverage_score IS NOT NULL
               ORDER BY forecast_run_id, forecast_date"""
        )
    else:
        cur.execute(
            """SELECT forecast_run_id, forecast_date,
                      coverage_score, model_version
               FROM forecasts FOR SYSTEM_TIME ALL
               WHERE coverage_score IS NOT NULL AND forecast_run_id = ?
               ORDER BY forecast_date""",
            (batch_id,),
        )
    return [
        {
            "forecast_run_id": r.forecast_run_id,
            "forecast_date": r.forecast_date,
            "coverage_score": r.coverage_score,
            "model_version": r.model_version,
        }
        for r in cur.fetchall()
    ]


@app.get("/winkler")
def get_winkler(response: Response, conn: mariadb.Connection = Depends(get_db)):
    """Per-batch Winkler interval scores — drift detection metric."""
    response.headers["Cache-Control"] = CACHE_LONG
    cur = conn.cursor()
    cur.execute(
        """SELECT forecast_run_id,
                  AVG(winkler_score) AS mean_winkler,
                  AVG(coverage_score) AS mean_coverage,
                  COUNT(*) AS n_rows
           FROM forecasts FOR SYSTEM_TIME ALL
           WHERE winkler_score IS NOT NULL
           GROUP BY forecast_run_id
           ORDER BY forecast_run_id"""
    )
    return [
        {
            "forecast_run_id": row[0],
            "mean_winkler": float(row[1]) if row[1] is not None else 0.0,
            "mean_coverage": float(row[2]) if row[2] is not None else 0.0,
            "n_rows": int(row[3]),
        }
        for row in cur.fetchall()
    ]
