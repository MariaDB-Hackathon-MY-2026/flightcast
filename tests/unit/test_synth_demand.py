"""
Unit tests for synthetic demand generation.
No database connection required.
"""
import numpy as np
import pandas as pd
import pytest

from flightcast.synth_demand import generate_demand_series, _pandemic_shock
from flightcast.config import GLOBAL_SEED


def _make_routes(n: int = 3) -> pd.DataFrame:
    hubs_src = ([300, 50, 5] * (n // 3 + 1))[:n]
    hubs_dst = ([350, 60, 8] * (n // 3 + 1))[:n]
    hemispheres = (["N", "N", "S"] * (n // 3 + 1))[:n]
    return pd.DataFrame(
        {
            "route_id": list(range(1, n + 1)),
            "hub_degree_src": hubs_src,
            "hub_degree_dst": hubs_dst,
            "hemisphere": hemispheres,
        }
    )


def test_deterministic():
    routes = _make_routes()
    df1 = generate_demand_series(routes, n_days=30, rng=np.random.default_rng(42))
    df2 = generate_demand_series(routes, n_days=30, rng=np.random.default_rng(42))
    pd.testing.assert_frame_equal(df1, df2)


def test_shape():
    routes = _make_routes(5)
    df = generate_demand_series(routes, n_days=100)
    assert df.shape[0] == 5 * 100
    required_cols = {"route_id", "demand_date", "demand_volume", "day_of_week", "month"}
    assert required_cols.issubset(df.columns)


def test_no_negative_demand():
    routes = _make_routes()
    df = generate_demand_series(routes, n_days=365)
    assert (df["demand_volume"] >= 0).all()


def test_hub_routes_higher_demand_than_thin():
    routes = pd.DataFrame(
        {
            "route_id": [1, 2],
            "hub_degree_src": [500, 2],
            "hub_degree_dst": [500, 2],
            "hemisphere": ["N", "N"],
        }
    )
    df = generate_demand_series(routes, n_days=365, rng=np.random.default_rng(42))
    hub_mean = df[df.route_id == 1]["demand_volume"].mean()
    thin_mean = df[df.route_id == 2]["demand_volume"].mean()
    assert hub_mean >= 5 * thin_mean


def test_pandemic_shock_before_start():
    t = np.arange(400)
    shock = _pandemic_shock(t, start_day=440)
    assert (shock == 0).all()


def test_pandemic_shock_recovery():
    t = np.array([440, 500, 600, 800])
    shock = _pandemic_shock(t, start_day=440, depth=0.60, recovery_rate=0.003)
    assert shock[0] == pytest.approx(0.60, abs=0.001)
    assert shock[1] < shock[0]
    assert shock[2] < shock[1]
    assert shock[3] < shock[2]


def test_southern_hemisphere_phase_shift():
    routes_n = pd.DataFrame(
        {"route_id": [1], "hub_degree_src": [100], "hub_degree_dst": [100], "hemisphere": ["N"]}
    )
    routes_s = pd.DataFrame(
        {"route_id": [1], "hub_degree_src": [100], "hub_degree_dst": [100], "hemisphere": ["S"]}
    )
    df_n = generate_demand_series(routes_n, n_days=365, rng=np.random.default_rng(42))
    df_s = generate_demand_series(routes_s, n_days=365, rng=np.random.default_rng(42))
    # N peaks mid-year (summer), S peaks end/start of year (antipodal summer)
    peak_n = df_n.groupby("month")["demand_volume"].mean().idxmax()
    peak_s = df_s.groupby("month")["demand_volume"].mean().idxmax()
    assert peak_n != peak_s
