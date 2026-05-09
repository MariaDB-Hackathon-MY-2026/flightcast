"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Calendar,
  Plane,
  Database,
  Shield,
  Square,
  CalendarDays,
  TrendingUp,
  ShieldCheck,
  Clock,
  Download,
  MessageSquare,
  ChevronDown,
  MoreVertical,
} from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { IconStatCard } from "@/components/common/IconStatCard";
import { SqlPanel } from "@/components/common/SqlPanel";
import { ForecastChart } from "@/components/charts/ForecastChart";

/**
 * TIME TRAVEL — hero page, redesigned to match the dark Apple-leaning
 * design spec: deeper background, refined cards, tighter spacing.
 *
 * Tour anchors (matching .tour-anchor-* selectors in TOUR_STEPS.ts):
 *   .tour-anchor-audit-gap   → page header
 *   .tour-anchor-callout     → "Ask MariaDB" hero banner
 *   .tour-anchor-slider      → audit-point slider card
 *   .tour-anchor-stats       → 4 KPI cards
 *   .tour-anchor-forecast    → Plotly forecast chart card
 */
export default function TimeTravelPage() {
  const { data: batches = [], isLoading: batchesLoading } = useQuery({
    queryKey: ["batches"],
    queryFn: api.batches,
  });
  const { data: routes = [], isLoading: routesLoading } = useQuery({
    queryKey: ["sampled-routes"],
    queryFn: api.sampledRoutes,
  });

  const [batchIdx, setBatchIdx] = useState<number>(0);
  const [routeId, setRouteId] = useState<number | null>(null);
  const [showActuals, setShowActuals] = useState(false);

  useEffect(() => {
    if (batches.length > 0) setBatchIdx(batches.length - 1);
  }, [batches.length]);
  useEffect(() => {
    if (routes.length > 0 && routeId === null) setRouteId(routes[0].route_id);
  }, [routes, routeId]);

  const selectedBatch = batches[batchIdx];
  const routeLabel = useMemo(() => {
    if (!routeId) return "";
    const r = routes.find((x) => x.route_id === routeId);
    return r ? `${r.src_airport} → ${r.dst_airport}` : `Route ${routeId}`;
  }, [routes, routeId]);

  const { data: forecasts = [], isLoading: forecastsLoading } = useQuery({
    queryKey: [
      "forecasts",
      routeId,
      selectedBatch?.row_start_ts,
      selectedBatch?.forecast_run_id,
    ],
    queryFn: () =>
      api.forecasts({
        route_id: routeId!,
        as_of: selectedBatch!.row_start_ts,
        // CRITICAL: scope to the selected batch — without run_id, the AS-OF
        // query returns every batch visible at that timestamp (180 rows).
        run_id: selectedBatch!.forecast_run_id,
      }),
    enabled: !!routeId && !!selectedBatch,
  });

  // Only fetch ground-truth actuals when the user toggles them on.
  const { data: actuals = [] } = useQuery({
    queryKey: ["actuals", routeId, selectedBatch?.forecast_run_id],
    queryFn: () => api.actuals(routeId!, selectedBatch!.forecast_run_id),
    enabled:
      !!routeId && !!selectedBatch && showActuals,
  });

  const stats = useMemo(() => {
    if (!forecasts || forecasts.length === 0) return null;
    const halfWidths = forecasts
      .map((f) => (f.upper_bound - f.lower_bound) / 2)
      .sort((a, b) => a - b);
    const medianHalf = halfWidths[Math.floor(halfWidths.length / 2)];
    const meanPred =
      forecasts.reduce((s, f) => s + f.predicted_demand, 0) / forecasts.length;
    const minPred = Math.min(...forecasts.map((f) => f.predicted_demand));
    const maxPred = Math.max(...forecasts.map((f) => f.predicted_demand));
    return { medianHalf, meanPred, minPred, maxPred, n: forecasts.length };
  }, [forecasts]);

  if (batchesLoading || routesLoading) {
    return <div className="text-slate-400">Loading…</div>;
  }
  if (batches.length === 0) {
    return (
      <div className="fc-stat text-amber-400">
        No batches found. Run{" "}
        <code>docker compose exec app python -m flightcast.bootstrap</code>.
      </div>
    );
  }

  const formatBatchDateOnly = (b?: { story_ts: string }) =>
    b ? new Date(b.story_ts).toISOString().slice(0, 10) : "—";

  // <story_ts date> + <row_start_ts time>, e.g. "2026-03-14 11:00:57"
  const auditPillText = selectedBatch
    ? `${new Date(selectedBatch.story_ts).toISOString().slice(0, 10)} ${new Date(
        selectedBatch.row_start_ts,
      )
        .toISOString()
        .slice(11, 19)}`
    : "—";

  // Build a CSV from current forecasts + (when on) actuals, then trigger
  // a browser download. No third-party deps; works in every modern browser.
  const handleDownload = () => {
    if (!forecasts || forecasts.length === 0 || !selectedBatch || !routeId) {
      return;
    }
    const actualsByDate = new Map(
      actuals.map((a) => [a.forecast_date, a]),
    );
    const headers = [
      "forecast_date",
      "predicted_demand",
      "lower_bound",
      "upper_bound",
      "model_version",
      "actual_demand",
      "coverage_score",
      "row_start",
    ];
    const rows = forecasts.map((f) => {
      const a = actualsByDate.get(f.forecast_date);
      return [
        f.forecast_date,
        f.predicted_demand.toFixed(2),
        f.lower_bound.toFixed(2),
        f.upper_bound.toFixed(2),
        f.model_version,
        a ? a.actual_demand.toFixed(2) : "",
        a && a.coverage_score !== null ? a.coverage_score.toFixed(0) : "",
        f.row_start,
      ];
    });
    const escape = (v: string | number) => {
      const s = String(v);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const csv =
      headers.join(",") +
      "\n" +
      rows.map((r) => r.map(escape).join(",")).join("\n") +
      "\n";

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const safeRoute = routeLabel.replace(/[^A-Za-z0-9_-]+/g, "_");
    const dateStr = new Date(selectedBatch.row_start_ts)
      .toISOString()
      .slice(0, 19)
      .replace(/[T:]/g, "-");
    a.href = url;
    a.download = `flightcast_${safeRoute}_run${selectedBatch.forecast_run_id}_${dateStr}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <>
      {/* ── Page header ──────────────────────────────────────────── */}
      <div className="tour-anchor-audit-gap">
        <PageHeader
          eyebrow="MariaDB Hackathon Malaysia 2026 · Innovation Track"
          title="FlightCast"
          subtitle="Database-native ML audit for aviation demand forecasting."
          pills={[
            { label: "Live", liveDot: true },
            { label: "MariaDB 11.8", variant: "blue" },
            { label: "MAPIE conformal · 90% coverage", variant: "violet" },
            { label: "6 model versions indexed", variant: "amber" },
          ]}
        />
      </div>

      {/* ── "Ask MariaDB" hero banner ────────────────────────────── */}
      <div className="tour-anchor-callout fc-banner-hero mb-6 flex items-start gap-4">
        <div className="w-11 h-11 shrink-0 rounded-full bg-accent-violet/20 flex items-center justify-center border border-accent-violet/40">
          <MessageSquare size={18} className="text-accent-violet" />
        </div>
        <div className="flex-1">
          <p className="text-slate-100 font-bold text-[15px] mb-0.5 leading-snug">
            Ask MariaDB: what did your model predict on this exact date — before
            it was retrained?
          </p>
          <p className="text-[13px] text-[#B8C4D8]">
            Time travel with MariaDB using <code>FOR SYSTEM_TIME AS OF</code> to
            audit model predictions as they were at that point in time.
          </p>
        </div>
      </div>

      {/* ── 3-up control row: Audit + Route + Model version ──────── */}
      <div
        className="grid gap-4 mb-6"
        style={{ gridTemplateColumns: "2fr 1fr 1fr" }}
      >
        {/* Audit-point widget */}
        <div className="tour-anchor-slider fc-stat flex flex-col !p-4 !rounded-[14px]">
          <div className="fc-stat-label">Audit point in time</div>
          <div className="flex items-start gap-3 mt-1">
            <button
              type="button"
              className="flex items-center gap-2 px-3 py-2 rounded-md bg-bg-deep border border-white/10 text-slate-100 text-[13px] font-mono whitespace-nowrap shrink-0 hover:bg-white/5 transition cursor-default"
            >
              <Calendar size={14} className="text-slate-400" />
              {auditPillText}
              <ChevronDown size={14} className="text-slate-500 ml-1" />
            </button>
            <div className="flex-1 min-w-0">
              <input
                type="range"
                min={0}
                max={batches.length - 1}
                step={1}
                value={batchIdx}
                onChange={(e) => setBatchIdx(Number(e.target.value))}
                className="w-full block"
                aria-label="Audit point in time slider"
                aria-valuemin={0}
                aria-valuemax={batches.length - 1}
                aria-valuenow={batchIdx}
                aria-valuetext={
                  selectedBatch
                    ? `Run ${selectedBatch.forecast_run_id}, model ${selectedBatch.model_version}, ${formatBatchDateOnly(selectedBatch)}`
                    : undefined
                }
              />
              <div className="grid grid-cols-3 mt-1 text-[11px]">
                <div className="text-left">
                  <span className="text-slate-400">
                    {formatBatchDateOnly(batches[0])}
                  </span>
                  <br />
                  <span className="text-slate-500">
                    ({batches[0]?.model_version})
                  </span>
                </div>
                <div className="text-center">
                  <span className="text-accent-violet font-semibold">
                    {selectedBatch ? formatBatchDateOnly(selectedBatch) : "—"}
                  </span>
                  <br />
                  <span className="text-accent-violet">
                    ({selectedBatch?.model_version})
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400">
                    {formatBatchDateOnly(batches[batches.length - 1])}
                  </span>
                  <br />
                  <span className="text-slate-500">
                    ({batches[batches.length - 1]?.model_version})
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Route selector */}
        <div className="fc-stat flex flex-col !p-4 !rounded-[14px]">
          <div className="fc-stat-label">Route</div>
          <div className="flex-1 flex items-center mt-1">
            <div className="relative w-full">
              <Plane
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none z-10"
              />
              <select
                value={routeId ?? ""}
                onChange={(e) => setRouteId(Number(e.target.value))}
                aria-label="Route"
                className="w-full h-12 pl-9 pr-9 rounded-[10px] bg-bg-deep border border-white/[0.14] text-slate-100 text-[13px]"
              >
                {routes.map((r) => (
                  <option key={r.route_id} value={r.route_id}>
                    {r.src_airport} → {r.dst_airport} ({r.tier})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Model version (read-only) */}
        <div className="fc-stat flex flex-col !p-4 !rounded-[14px]">
          <div className="fc-stat-label">Model version</div>
          <div className="flex-1 flex items-center mt-1">
            <div className="relative w-full">
              <Database
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none z-10"
              />
              <div className="w-full h-12 pl-9 pr-3 rounded-[10px] bg-bg-deep border border-white/[0.14] text-slate-100 text-[13px] flex items-center justify-between">
                <span>{selectedBatch?.model_version ?? "—"}</span>
                <ChevronDown size={14} className="text-slate-500" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── 4 KPI cards ──────────────────────────────────────────── */}
      <div
        className="tour-anchor-stats grid gap-4 mb-6"
        style={{ gridTemplateColumns: "repeat(4, 1fr)" }}
      >
        <IconStatCard
          icon={Database}
          accent="violet"
          label="Model version"
          value={selectedBatch?.model_version ?? "—"}
          hint="Active at this timestamp"
        />
        <IconStatCard
          icon={Shield}
          accent="blue"
          label="Empirical coverage"
          value="—"
          hint="Actuals not yet measured"
        />
        <IconStatCard
          icon={Square}
          accent="violet"
          label="Median 90% CI"
          value={
            stats ? `±${Math.round(stats.medianHalf).toLocaleString()} pax` : "—"
          }
          hint="Half-width (predicted ± this)"
        />
        <IconStatCard
          icon={CalendarDays}
          accent="emerald"
          label="Forecast horizon"
          value={stats ? `${stats.n} days` : "—"}
          hint={
            stats
              ? `Mean ≈ ${Math.round(stats.meanPred).toLocaleString()} pax/day`
              : ""
          }
        />
      </div>

      {/* ── Chart card ──────────────────────────────────────────── */}
      <div className="tour-anchor-forecast fc-stat mb-6 !p-5">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <h3 className="text-[16px] font-bold text-slate-100">
            {routeLabel} · 30-day forecast
          </h3>
          <div className="flex items-center gap-2">
            {/* Show actuals — proper switch role + keyboard support */}
            <button
              type="button"
              role="switch"
              aria-checked={showActuals}
              aria-label="Show actual demand alongside the forecast"
              onClick={() => setShowActuals((v) => !v)}
              onKeyDown={(e) => {
                if (e.key === " " || e.key === "Enter") {
                  e.preventDefault();
                  setShowActuals((v) => !v);
                }
              }}
              className="flex items-center gap-2 px-2.5 py-1.5 text-[12px] text-slate-300 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-violet focus-visible:ring-offset-2 focus-visible:ring-offset-bg-card"
            >
              <span
                aria-hidden="true"
                className={`relative w-8 h-[18px] rounded-full transition ${
                  showActuals
                    ? "bg-accent-violet"
                    : "bg-slate-600/60 border border-white/10"
                }`}
              >
                <span
                  className={`absolute top-[1px] w-3.5 h-3.5 rounded-full bg-white transition-all ${
                    showActuals ? "left-[15px]" : "left-[1px]"
                  }`}
                />
              </span>
              Show actuals
            </button>

            {/* Download — disabled while no data */}
            <button
              type="button"
              onClick={handleDownload}
              disabled={forecastsLoading || forecasts.length === 0}
              aria-label="Download forecast data as CSV"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] text-slate-200 border border-white/10 hover:bg-white/5 transition disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-violet focus-visible:ring-offset-2 focus-visible:ring-offset-bg-card"
            >
              <Download size={13} aria-hidden="true" />
              Download
            </button>

            <button
              type="button"
              aria-label="More chart options"
              title="More options"
              className="p-1.5 rounded-md text-slate-400 hover:bg-white/5 hover:text-slate-200 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-violet focus-visible:ring-offset-2 focus-visible:ring-offset-bg-card"
            >
              <MoreVertical size={16} aria-hidden="true" />
            </button>
          </div>
        </div>
        {forecastsLoading ? (
          <div className="text-slate-400 py-12 text-center" role="status">
            Querying MariaDB…
          </div>
        ) : (
          <ForecastChart
            data={forecasts}
            routeLabel={routeLabel}
            height={320}
            showTitle={false}
            actuals={showActuals ? actuals : undefined}
          />
        )}
      </div>

      {/* ── SQL panel + Key insights side-by-side (≈7:3 per spec) ──── */}
      <div className="tour-anchor-live-sql grid gap-4" style={{ gridTemplateColumns: "7fr 3fr" }}>
        <SqlPanel
          title="View the live MariaDB query that produced this chart"
          sql={
            selectedBatch && routeId
              ? `-- MariaDB-only syntax. MySQL cannot run this.
SELECT route_id, forecast_date,
       predicted_demand, lower_bound, upper_bound,
       model_version, actual_demand, coverage_score,
       ROW_START, ROW_END
FROM forecasts FOR SYSTEM_TIME AS OF '${selectedBatch.row_start_ts}'
WHERE route_id = ${routeId}
  AND forecast_run_id = ${selectedBatch.forecast_run_id}
ORDER BY forecast_date;`
              : "-- (waiting for batch + route)"
          }
        />

        {/* Key insights */}
        <div className="fc-stat">
          <h3 className="flex items-center gap-2 text-[16px] font-bold text-slate-100 mb-3">
            <TrendingUp size={16} className="text-accent-amber" />
            Key insights
          </h3>
          <ul className="space-y-3">
            {stats && (
              <li className="flex items-start gap-3">
                <span className="w-7 h-7 shrink-0 rounded-md bg-accent-violet/15 flex items-center justify-center text-accent-violet">
                  <TrendingUp size={14} />
                </span>
                <div>
                  <div className="text-slate-100 font-semibold text-[14px] leading-snug">
                    Forecasts range from ~
                    {Math.round(stats.minPred).toLocaleString()} to ~
                    {Math.round(stats.maxPred).toLocaleString()} pax/day
                  </div>
                  <div className="text-[13px] text-slate-400 mt-0.5">
                    Median around {Math.round(stats.meanPred).toLocaleString()}{" "}
                    pax/day.
                  </div>
                </div>
              </li>
            )}
            <li className="flex items-start gap-3">
              <span className="w-7 h-7 shrink-0 rounded-md bg-accent-blue/15 flex items-center justify-center text-accent-blue">
                <ShieldCheck size={14} />
              </span>
              <div>
                <div className="text-slate-100 font-semibold text-[14px] leading-snug">
                  90% conformal interval shown
                </div>
                <div className="text-[13px] text-slate-400 mt-0.5">
                  CI adapts with demand variability.
                </div>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <span className="w-7 h-7 shrink-0 rounded-md bg-emerald-500/15 flex items-center justify-center text-emerald-400">
                <Clock size={14} />
              </span>
              <div>
                <div className="text-slate-100 font-semibold text-[14px] leading-snug">
                  Time-traveled prediction
                </div>
                <div className="text-[13px] text-slate-400 mt-0.5">
                  Values reflect what the model knew at{" "}
                  {auditPillText}.
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </>
  );
}

