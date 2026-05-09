"use client";

/**
 * FORECAST EXPLORER — port of src/flightcast/ui/pages/01_forecast.py
 *
 * Per-route deep dive:
 *   1. "Latest batch" mode — point-in-time chart from the most recent batch
 *   2. "All history" mode — every committed forecast batch overlaid on one
 *      chart (the FOR SYSTEM_TIME ALL showcase view).
 */

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Zap, Layers } from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { ForecastChart } from "@/components/charts/ForecastChart";
import { HistoryChart } from "@/components/charts/HistoryChart";
import { SqlPanel } from "@/components/common/SqlPanel";
import { MariaDbFeatureCard } from "@/components/common/MariaDbFeatureCard";
import type { ForecastHistoryPoint } from "@/lib/types";

type ViewMode = "latest" | "history";

export default function ForecastExplorerPage() {
  const { data: routes = [] } = useQuery({
    queryKey: ["sampled-routes"],
    queryFn: api.sampledRoutes,
  });
  const { data: batches = [] } = useQuery({
    queryKey: ["batches"],
    queryFn: api.batches,
  });

  const [routeId, setRouteId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("latest");

  useEffect(() => {
    if (routes.length > 0 && routeId === null) setRouteId(routes[0].route_id);
  }, [routes, routeId]);

  const routeLabel = useMemo(() => {
    if (!routeId) return "";
    const r = routes.find((x) => x.route_id === routeId);
    return r ? `${r.src_airport} → ${r.dst_airport}` : `Route ${routeId}`;
  }, [routes, routeId]);

  const latestBatch = batches[batches.length - 1];

  // Latest-batch query (point-in-time, scoped to the latest batch only)
  const { data: latestData = [], isLoading: loadingLatest } = useQuery({
    queryKey: [
      "forecasts-latest",
      routeId,
      latestBatch?.row_start_ts,
      latestBatch?.forecast_run_id,
    ],
    queryFn: () =>
      api.forecasts({
        route_id: routeId!,
        as_of: latestBatch!.row_start_ts,
        run_id: latestBatch!.forecast_run_id,
      }),
    enabled: viewMode === "latest" && !!routeId && !!latestBatch,
  });

  // Full-history query (FOR SYSTEM_TIME ALL)
  const { data: historyData = [], isLoading: loadingHistory } = useQuery<
    ForecastHistoryPoint[]
  >({
    queryKey: ["forecasts-all", routeId],
    queryFn: () => api.forecastsAll(routeId!),
    enabled: viewMode === "history" && !!routeId,
  });

  return (
    <>
      <PageHeader
        eyebrow="Per-route deep dive"
        title="Forecast Explorer"
        subtitle="Compare 90% conformal prediction bands across every model version on record."
        pills={[
          { label: "LIVE", liveDot: true },
          { label: "FOR SYSTEM_TIME AS OF", variant: "blue" },
          { label: "FOR SYSTEM_TIME ALL", variant: "violet" },
        ]}
      />

      {/* ── Controls ─────────────────────────────────────────────────── */}
      <div className="grid gap-4 mb-6" style={{ gridTemplateColumns: "1fr 1fr" }}>
        <div>
          <label className="fc-stat-label block mb-2">Route</label>
          <select
            value={routeId ?? ""}
            onChange={(e) => setRouteId(Number(e.target.value))}
            className="fc-stat w-full text-slate-100"
          >
            {routes.map((r) => (
              <option key={r.route_id} value={r.route_id}>
                {r.src_airport} → {r.dst_airport} ({r.tier})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="fc-stat-label block mb-2">View mode</label>
          <ViewModeSegmented value={viewMode} onChange={setViewMode} />
        </div>
      </div>

      {/* ── Chart ────────────────────────────────────────────────────── */}
      <div className="tour-anchor-all-history">
      {viewMode === "latest" ? (
        loadingLatest ? (
          <div className="fc-stat text-slate-400 py-12 text-center">
            Querying MariaDB for latest batch…
          </div>
        ) : (
          <>
            <ForecastChart data={latestData} routeLabel={routeLabel} />
            {latestBatch && (
              <p className="text-xs text-slate-400 mt-2">
                Batch:{" "}
                {new Date(latestBatch.story_ts).toISOString().slice(0, 10)} ·
                Model: {latestBatch.model_version}
              </p>
            )}
          </>
        )
      ) : loadingHistory ? (
        <div className="fc-stat text-slate-400 py-12 text-center">
          Querying MariaDB for full prediction history…
        </div>
      ) : (
        <>
          <HistoryChart data={historyData} routeLabel={routeLabel} />
          {historyData.length > 0 && (
            <p className="text-xs text-slate-400 mt-2">
              {new Set(historyData.map((r) => r.forecast_run_id)).size} model
              versions · {historyData.length} total rows
            </p>
          )}
        </>
      )}
      </div>

      {/* ── SQL panel + MariaDB feature card side-by-side ─────────────── */}
      <div className="tour-anchor-feature-card grid gap-4 mt-6" style={{ gridTemplateColumns: "7fr 3fr" }}>
        <SqlPanel
          sql={
            viewMode === "latest" && latestBatch && routeId
              ? `-- MariaDB-only: point-in-time temporal query
SELECT route_id, forecast_date, predicted_demand,
       lower_bound, upper_bound, model_version,
       actual_demand, coverage_score,
       ROW_START, ROW_END
FROM forecasts FOR SYSTEM_TIME AS OF '${latestBatch.row_start_ts}'
WHERE route_id = ${routeId}
  AND forecast_run_id = ${latestBatch.forecast_run_id}
ORDER BY forecast_date;`
              : routeId
              ? `-- MariaDB-only: full prediction history (every committed version)
SELECT forecast_run_id, forecast_date,
       predicted_demand, lower_bound, upper_bound,
       model_version, ROW_START, ROW_END
FROM forecasts FOR SYSTEM_TIME ALL
WHERE route_id = ${routeId}
ORDER BY ROW_START, forecast_date;`
              : "-- (waiting for route selection)"
          }
        />
        <MariaDbFeatureCard
          feature={
            viewMode === "history" ? "FOR SYSTEM_TIME ALL" : "FOR SYSTEM_TIME AS OF"
          }
        >
          {viewMode === "history" ? (
            <>
              returns every historical version of every prediction row —
              zero application-level archiving code required.
            </>
          ) : (
            <>
              reconstructs the exact prediction state at a given timestamp.
              MySQL parses this as a syntax error; PostgreSQL needs an extension.
            </>
          )}
        </MariaDbFeatureCard>
      </div>
    </>
  );
}

/**
 * ViewModeSegmented — premium segmented picker for switching between
 * "Latest batch" and "All history" views. Mirrors the SaaS-grade pickers
 * in Linear / Vercel: a single rounded shell wrapping two equal-width
 * segments, with an animated gradient fill on the active option.
 *
 * Accessibility: uses `role="tablist"` + `role="tab"` with aria-selected.
 * Keyboard: Tab to enter, Space/Enter to activate (default <button>).
 */
function ViewModeSegmented({
  value,
  onChange,
}: {
  value: ViewMode;
  onChange: (v: ViewMode) => void;
}) {
  const OPTIONS: ReadonlyArray<{
    key: ViewMode;
    label: string;
    desc: string;
    Icon: typeof Zap;
  }> = [
    {
      key: "latest",
      label: "Latest batch",
      desc: "Current run only",
      Icon: Zap,
    },
    {
      key: "history",
      label: "All history",
      desc: "Every model version",
      Icon: Layers,
    },
  ];

  return (
    <div
      role="tablist"
      aria-label="View mode"
      className="grid grid-cols-2 gap-1 rounded-2xl border border-white/[0.16] p-1"
      style={{ background: "rgba(15, 23, 42, 0.85)" }}
    >
      {OPTIONS.map(({ key, label, desc, Icon }) => {
        const isSelected = value === key;
        return (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={isSelected}
            onClick={() => onChange(key)}
            className={`flex items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-left transition ${
              isSelected
                ? "border border-accent-violet/45"
                : "border border-transparent hover:bg-white/[0.05]"
            }`}
            style={
              isSelected
                ? {
                    background:
                      "linear-gradient(135deg, rgba(124,58,237,0.45), rgba(59,130,246,0.18))",
                    boxShadow:
                      "inset 0 1px 0 rgba(255,255,255,0.08), 0 10px 24px rgba(124,58,237,0.16)",
                  }
                : undefined
            }
          >
            <Icon
              size={17}
              aria-hidden="true"
              className={isSelected ? "text-accent-violetSoft" : "text-slate-500"}
            />
            <div className="min-w-0">
              <div
                className={`text-[14px] font-bold leading-tight ${
                  isSelected ? "text-slate-50" : "text-slate-400"
                }`}
              >
                {label}
              </div>
              <div
                className={`text-[12px] font-medium leading-tight mt-0.5 ${
                  isSelected ? "text-indigo-200" : "text-slate-500"
                }`}
              >
                {desc}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
