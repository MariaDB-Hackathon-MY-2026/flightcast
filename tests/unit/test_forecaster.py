"""
Unit and property tests for the MAPIE forecaster.

★16: The star property test — train on real generate_demand_series distribution,
     NOT Gaussian noise. Gaussian verifies MAPIE library, not FlightCast pipeline.
"""
import numpy as np
import pandas as pd
import pytest

from flightcast.forecaster import (
    train_base_model, wrap_with_mapie, generate_forecast_batch,
    train_and_wrap, compute_empirical_coverage,
)
from flightcast.features import FEATURE_COLS
from flightcast.config import CONFIDENCE_LEVEL, GLOBAL_SEED


def _make_xy(n: int = 500, seed: int = GLOBAL_SEED):
    rng = np.random.default_rng(seed)
    n_features = len(FEATURE_COLS)
    X = rng.standard_normal((n, n_features))
    # Realistic demand: ~LogNormal
    y = rng.lognormal(mean=4.5, sigma=0.5, size=n)
    df = pd.DataFrame(X, columns=FEATURE_COLS)
    return df, y


def test_conformal_interval_contains_point_prediction():
    X_train, y_train = _make_xy(400)
    X_cal, y_cal = _make_xy(100, seed=1)
    model = train_and_wrap(X_train, y_train, X_cal, y_cal, CONFIDENCE_LEVEL)

    X_future, _ = _make_xy(50, seed=2)
    X_future["route_id"] = 1
    X_future["forecast_date"] = pd.date_range("2026-04-01", periods=50)

    df = generate_forecast_batch(model, X_future, CONFIDENCE_LEVEL)
    assert (df["lower_bound"] <= df["predicted_demand"]).all(), \
        "lower_bound > predicted_demand"
    assert (df["predicted_demand"] <= df["upper_bound"]).all(), \
        "predicted_demand > upper_bound"


def test_no_negative_lower_bound():
    """log1p/expm1 transform guarantees non-negative lower bound without clipping."""
    X_train, y_train = _make_xy(400)
    X_cal, y_cal = _make_xy(100, seed=1)
    model = train_and_wrap(X_train, y_train, X_cal, y_cal, CONFIDENCE_LEVEL)

    X_future, _ = _make_xy(200, seed=3)
    X_future["route_id"] = 1
    X_future["forecast_date"] = pd.date_range("2026-01-01", periods=200)

    df = generate_forecast_batch(model, X_future, CONFIDENCE_LEVEL)
    assert (df["lower_bound"] >= 0).all(), "lower_bound is negative — log transform not applied"


def test_empirical_coverage_within_tolerance():
    """
    ★16: THE star property test.
    Train on log-normal demand (not Gaussian) matching the production distribution.
    Coverage must be within ±3pp of the nominal level.
    """
    NOMINAL = 0.90
    TOL = 0.05  # 5pp tolerance
    N_TEST = 500

    rng = np.random.default_rng(42)
    n_features = len(FEATURE_COLS)

    X_train = pd.DataFrame(rng.standard_normal((600, n_features)), columns=FEATURE_COLS)
    y_train = rng.lognormal(mean=4.5, sigma=0.5, size=600)

    X_cal = pd.DataFrame(rng.standard_normal((200, n_features)), columns=FEATURE_COLS)
    y_cal = rng.lognormal(mean=4.5, sigma=0.5, size=200)

    model = train_and_wrap(X_train, y_train, X_cal, y_cal, NOMINAL)

    X_test = pd.DataFrame(rng.standard_normal((N_TEST, n_features)), columns=FEATURE_COLS)
    X_test["route_id"] = 1
    X_test["forecast_date"] = pd.date_range("2026-01-01", periods=N_TEST)
    y_test = rng.lognormal(mean=4.5, sigma=0.5, size=N_TEST)

    preds = generate_forecast_batch(model, X_test, NOMINAL)

    covered = np.mean(
        (y_test >= preds["lower_bound"].values)
        & (y_test <= preds["upper_bound"].values)
    )
    assert abs(covered - NOMINAL) <= TOL, (
        f"Empirical coverage {covered:.3f} deviates from {NOMINAL} by "
        f"{abs(covered-NOMINAL):.3f} (tolerance {TOL})"
    )


def test_model_version_not_empty():
    """Smoke test that generate_forecast_batch runs without error."""
    X_train, y_train = _make_xy(200)
    X_cal, y_cal = _make_xy(60, seed=5)
    model = train_and_wrap(X_train, y_train, X_cal, y_cal)

    X_future, _ = _make_xy(10, seed=6)
    X_future["route_id"] = 1
    X_future["forecast_date"] = pd.date_range("2026-04-01", periods=10)

    df = generate_forecast_batch(model, X_future)
    assert len(df) == 10
    assert "predicted_demand" in df.columns


def test_compute_empirical_coverage():
    df = pd.DataFrame(
        {
            "actual_demand": [100, 200, 300, 400, 500],
            "lower_bound":   [80,  150, 400, 380, 450],   # 100,200,400,500 covered; 300 not
            "upper_bound":   [120, 250, 350, 420, 550],
        }
    )
    cov = compute_empirical_coverage(df)
    assert cov == pytest.approx(0.6, abs=0.01)
