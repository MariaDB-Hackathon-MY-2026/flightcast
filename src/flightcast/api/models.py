"""Pydantic response models for the FastAPI layer."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


class ForecastPoint(BaseModel):
    route_id: int
    forecast_date: date
    predicted_demand: float
    lower_bound: float
    upper_bound: float
    confidence_level: float
    model_version: str
    actual_demand: Optional[float] = None
    coverage_score: Optional[float] = None
    row_start: Optional[datetime] = None
    row_end: Optional[datetime] = None


class CoverageSample(BaseModel):
    forecast_run_id: int
    mean_coverage: Optional[float]
    mean_interval_width: float
    n_rows: int


class DiffResult(BaseModel):
    forecast_date: date
    predicted_a: float
    predicted_b: float
    delta: float
    width_a: float
    width_b: float
    model_a: str
    model_b: str


class BatchInfo(BaseModel):
    forecast_run_id: int
    story_ts: datetime
    row_start_ts: datetime
    model_version: str


class HealthResponse(BaseModel):
    ok: bool
    db_connected: bool
