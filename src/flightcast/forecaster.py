"""
MAPIE v1 conformal forecaster.

★9 — Train on np.log1p(demand), invert with np.expm1. NEVER clip lower_bound
     to 0. Asymmetric clipping breaks the conformal coverage guarantee.
     Log-transform is a monotone bijection that preserves quantile ordering.

★10 — route_id_cat is included as a categorical feature to prevent thin-route
      coverage divergence from a global model.

MAPIE v1 API:
  from mapie.regression import TimeSeriesRegressor   (NOT MapieTimeSeriesRegressor)
  confidence_level=0.9                               (NOT alpha=0.1)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mapie.regression import TimeSeriesRegressor
from mapie.subsample import BlockBootstrap
from lightgbm import LGBMRegressor

from flightcast.features import FEATURE_COLS
from flightcast.config import CONFIDENCE_LEVEL, GLOBAL_SEED


def _make_base(seed: int = GLOBAL_SEED) -> LGBMRegressor:
    # n_estimators kept at 100 — Phase 2 diagnostic showed n_estimators=50 produced
    # under-trained models with larger residuals, which MAPIE then calibrated into
    # over-wide intervals (calibrated coverage ~99% instead of ~90%). Bootstrap is
    # already fast enough at n_resamplings=20 + n_estimators=100 (~12s per batch).
    # ★17 (Phase 2B): `seed` is now a parameter so each batch can train with a
    # distinct LightGBM column-subsampling and bootstrap seed. This produces
    # genuinely different models per batch (replacing the post-hoc shift hack
    # in vary_batch_predictions.py).
    return LGBMRegressor(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=seed,
        n_jobs=-1,
        verbose=-1,
    )


def train_base_model(X: np.ndarray, y_log: np.ndarray, seed: int = GLOBAL_SEED) -> LGBMRegressor:
    est = _make_base(seed=seed)
    est.fit(X, y_log)
    return est


def wrap_with_mapie(estimator: LGBMRegressor, seed: int = GLOBAL_SEED) -> TimeSeriesRegressor:
    # ★15: n_resamplings=20 (bumped from 5) makes the ENBPI bootstrap quantile
    # statistically defensible. Below n=20 the asymptotic coverage guarantee
    # becomes marginal — see MAPIE 1.3 docs and AUDIT.md Stage 7 verdict.
    # ★17 (Phase 2B): BlockBootstrap also takes the per-batch seed so the
    # resampled blocks differ per batch.
    cv = BlockBootstrap(
        n_resamplings=20,
        length=7,
        overlapping=True,
        random_state=seed,
    )
    return TimeSeriesRegressor(estimator=estimator, method="enbpi", cv=cv)


def generate_forecast_batch(
    model: TimeSeriesRegressor,
    X_future: pd.DataFrame,
    confidence_level: float = CONFIDENCE_LEVEL,
) -> pd.DataFrame:
    """
    ★9: DO NOT clip lower_bound to 0. Log transform preserves coverage.
    Returns: route_id, forecast_date, predicted_demand, lower_bound, upper_bound,
             confidence_level.
    """
    feat_cols = [c for c in FEATURE_COLS if c in X_future.columns]
    X = X_future[feat_cols].values.astype(float)

    y_pred_log, y_pis_log = model.predict(X, confidence_level=confidence_level)

    return pd.DataFrame(
        {
            "route_id": X_future["route_id"].values,
            "forecast_date": X_future["forecast_date"].values,
            "predicted_demand": np.expm1(y_pred_log),
            "lower_bound": np.expm1(y_pis_log[:, 0, 0]),   # NO clip
            "upper_bound": np.expm1(y_pis_log[:, 1, 0]),
            "confidence_level": confidence_level,
        }
    )


def train_and_wrap(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_cal: pd.DataFrame,
    y_cal: np.ndarray,
    confidence_level: float = CONFIDENCE_LEVEL,
    seed: int = GLOBAL_SEED,
    return_base: bool = False,
) -> "TimeSeriesRegressor | tuple[LGBMRegressor, TimeSeriesRegressor]":
    """
    Full train + conformal calibration pipeline.
    y_train and y_cal should be raw demand (not log-transformed here).

    `seed` controls both the LightGBM base estimator and the BlockBootstrap
    resampling. Bootstrap.py passes seed=GLOBAL_SEED+run_id so each batch's
    model is genuinely different — the Prediction Diff chart shows real
    inter-version variation rather than a post-hoc multiplicative shift.

    `return_base=True` (Phase 3) additionally returns the trained base
    LightGBM model. The recursive feature builder uses the base model for
    fast per-day step-wise prediction; only at the end does it call MAPIE
    to wrap the predictions in calibrated intervals.
    """
    feat_cols = [c for c in FEATURE_COLS if c in X_train.columns]
    X_tr = X_train[feat_cols].values.astype(float)
    X_ca = X_cal[feat_cols].values.astype(float)

    # ★9: Train and calibrate on log scale
    y_tr_log = np.log1p(y_train)
    y_ca_log = np.log1p(y_cal)

    base = train_base_model(X_tr, y_tr_log, seed=seed)
    mapie = wrap_with_mapie(base, seed=seed)
    mapie.fit(X_ca, y_ca_log)
    if return_base:
        return base, mapie
    return mapie


def compute_empirical_coverage(
    df: pd.DataFrame,
    actual_col: str = "actual_demand",
    lower_col: str = "lower_bound",
    upper_col: str = "upper_bound",
) -> float:
    """Fraction of actuals that fall within [lower, upper]."""
    mask = df[actual_col].notna()
    sub = df[mask]
    if sub.empty:
        return float("nan")
    covered = ((sub[actual_col] >= sub[lower_col]) & (sub[actual_col] <= sub[upper_col])).sum()
    return float(covered) / len(sub)
