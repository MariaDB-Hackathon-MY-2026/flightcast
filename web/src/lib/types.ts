/**
 * Shared TypeScript types — match Pydantic models in src/flightcast/api/models.py.
 * If the Python side changes, mirror the change here.
 */

export interface BatchInfo {
  forecast_run_id: number;
  story_ts: string;       // ISO datetime
  row_start_ts: string;   // ISO datetime
  model_version: string;
}

export interface ForecastPoint {
  route_id: number;
  forecast_date: string;
  predicted_demand: number;
  lower_bound: number;
  upper_bound: number;
  confidence_level: number;
  model_version: string;
  actual_demand: number | null;
  coverage_score: number | null;
  row_start: string;
  row_end: string;
}

export interface ActualPoint {
  forecast_date: string;
  actual_demand: number;
  coverage_score: number | null;
}

/** /forecasts/all adds forecast_run_id to each row for the history overlay. */
export interface ForecastHistoryPoint extends Omit<ForecastPoint, "confidence_level"> {
  forecast_run_id: number;
}

export interface CoverageSample {
  forecast_run_id: number;
  mean_coverage: number | null;
  mean_interval_width: number | null;
  n_rows: number;
}

export interface DiffResult {
  forecast_date: string;
  predicted_a: number;
  predicted_b: number;
  delta: number;
  width_a: number;
  width_b: number;
  model_a: string;
  model_b: string;
}

export interface SampledRoute {
  route_id: number;
  src_airport: string;
  dst_airport: string;
  src_name: string;
  dst_name: string;
  tier: "hub" | "mid" | "thin";
}

export interface CoverageSeriesPoint {
  forecast_run_id: number;
  forecast_date: string;
  coverage_score: number;
  model_version: string;
}

export interface WinklerScore {
  forecast_run_id: number;
  mean_winkler: number;
  mean_coverage: number;
  n_rows: number;
}
