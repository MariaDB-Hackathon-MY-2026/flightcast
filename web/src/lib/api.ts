/**
 * FlightCast API client — typed wrappers over the FastAPI endpoints.
 * Routes are proxied through Next.js (see next.config.js rewrites)
 * so the browser hits /api/* and Next forwards to the FastAPI container.
 */

import type {
  BatchInfo,
  ForecastPoint,
  ForecastHistoryPoint,
  ActualPoint,
  CoverageSample,
  DiffResult,
  SampledRoute,
  CoverageSeriesPoint,
  WinklerScore,
} from "./types";

const API_BASE =
  typeof window === "undefined"
    ? process.env.API_BASE_INTERNAL || "http://localhost:8000"
    : "/api";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status} ${res.statusText} on ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetchJson<{ ok: boolean; db_connected: boolean }>("/healthz"),

  batches: () => fetchJson<BatchInfo[]>("/batches"),

  sampledRoutes: () => fetchJson<SampledRoute[]>("/sampled-routes"),

  forecasts: (params: {
    route_id: number;
    as_of: string;
    run_id?: number;
    limit?: number;
  }) => {
    const qs = new URLSearchParams({
      route_id: String(params.route_id),
      as_of: params.as_of,
      ...(params.run_id !== undefined ? { run_id: String(params.run_id) } : {}),
      ...(params.limit ? { limit: String(params.limit) } : {}),
    });
    return fetchJson<ForecastPoint[]>(`/forecasts?${qs}`);
  },

  forecastsAll: (route_id: number) =>
    fetchJson<ForecastHistoryPoint[]>(`/forecasts/all?route_id=${route_id}`),

  actuals: (route_id: number, run_id: number) =>
    fetchJson<ActualPoint[]>(
      `/actuals?route_id=${route_id}&run_id=${run_id}`,
    ),

  coverage: () => fetchJson<CoverageSample[]>("/coverage"),

  coverageSeries: (batch_id?: number) => {
    const qs = batch_id !== undefined ? `?batch_id=${batch_id}` : "";
    return fetchJson<CoverageSeriesPoint[]>(`/coverage/series${qs}`);
  },

  winkler: () => fetchJson<WinklerScore[]>("/winkler"),

  diff: (params: {
    route_id: number;
    date_a: string;
    date_b: string;
    horizon_days?: number;
  }) => {
    const qs = new URLSearchParams({
      route_id: String(params.route_id),
      date_a: params.date_a,
      date_b: params.date_b,
      ...(params.horizon_days ? { horizon_days: String(params.horizon_days) } : {}),
    });
    return fetchJson<DiffResult[]>(`/diff?${qs}`);
  },
};
