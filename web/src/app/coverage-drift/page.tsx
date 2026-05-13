"use client";

/**
 * COVERAGE DRIFT — port of src/flightcast/ui/pages/03_coverage_drift.py
 *
 * Audit story (5-second scan):
 *   1. Methodology strip — what the calibrated and drift batches are
 *   2. Audit headline — "4 of 6 calibrated · 2 drifted"
 *   3. Per-batch coverage cards split into calibrated / drift groups
 *   4. Same split for Winkler scores
 *   5. SQL proof
 *   6. Prediction diff between two batches
 *   7. Why this matters takeaway
 */

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Check,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  Plane,
  Calendar,
} from "lucide-react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { DiffChart } from "@/components/charts/DiffChart";
import { RunStatusCard } from "@/components/common/RunStatusCard";
import { SqlPanel } from "@/components/common/SqlPanel";

export default function CoverageDriftPage() {
  // ── Data ──────────────────────────────────────────────────────────
  const { data: coverage = [], isLoading: loadingCov } = useQuery({
    queryKey: ["coverage"],
    queryFn: api.coverage,
  });
  const { data: winkler = [], isLoading: loadingWink } = useQuery({
    queryKey: ["winkler"],
    queryFn: api.winkler,
  });
  const { data: batches = [] } = useQuery({
    queryKey: ["batches"],
    queryFn: api.batches,
  });
  const { data: routes = [] } = useQuery({
    queryKey: ["sampled-routes"],
    queryFn: api.sampledRoutes,
  });

  // ── Diff selectors ────────────────────────────────────────────────
  const [batchAIdx, setBatchAIdx] = useState(0);
  const [batchBIdx, setBatchBIdx] = useState(1);
  const [routeId, setRouteId] = useState<number | null>(null);
  useEffect(() => {
    if (routes.length > 0 && routeId === null) setRouteId(routes[0].route_id);
  }, [routes, routeId]);
  useEffect(() => {
    if (batches.length > 1 && batchBIdx === 1 && batchAIdx === 0) {
      setBatchBIdx(Math.min(1, batches.length - 1));
    }
  }, [batches.length, batchAIdx, batchBIdx]);

  const batchA = batches[batchAIdx];
  const batchB = batches[batchBIdx];

  const { data: diffData = [], isLoading: loadingDiff } = useQuery({
    queryKey: ["diff", routeId, batchA?.row_start_ts, batchB?.row_start_ts],
    queryFn: () =>
      api.diff({
        route_id: routeId!,
        date_a: batchA!.row_start_ts,
        date_b: batchB!.row_start_ts,
      }),
    enabled:
      !!routeId &&
      !!batchA &&
      !!batchB &&
      batchA.row_start_ts !== batchB.row_start_ts,
  });

  const routeLabel = useMemo(() => {
    if (!routeId) return "";
    const r = routes.find((x) => x.route_id === routeId);
    return r ? `${r.src_airport} → ${r.dst_airport}` : `Route ${routeId}`;
  }, [routes, routeId]);

  // Baseline Winkler = mean of first 4 (calibrated) batches
  const baselineWinkler = useMemo(() => {
    const calibrated = winkler.slice(0, 4);
    if (calibrated.length === 0) return 0;
    return (
      calibrated.reduce((s, w) => s + w.mean_winkler, 0) / calibrated.length
    );
  }, [winkler]);

  // ── Group coverage by calibrated/drift status (≤−10pp = drift) ────
  const splitCoverage = useMemo(() => {
    const cal: typeof coverage = [];
    const dft: typeof coverage = [];
    for (const c of coverage) {
      const deltaPp = ((c.mean_coverage ?? 0) - 0.9) * 100;
      if (deltaPp < -10) dft.push(c);
      else cal.push(c);
    }
    const meanCal =
      cal.length > 0
        ? cal.reduce((s, c) => s + (c.mean_coverage ?? 0), 0) / cal.length
        : 0;
    const meanDft =
      dft.length > 0
        ? dft.reduce((s, c) => s + (c.mean_coverage ?? 0), 0) / dft.length
        : 0;
    return { cal, dft, meanCal, meanDft, total: coverage.length };
  }, [coverage]);

  // ── Group Winkler by stable/escalated (>10% above baseline = escalated)
  const splitWinkler = useMemo(() => {
    const stable: typeof winkler = [];
    const esc: typeof winkler = [];
    for (const w of winkler) {
      const ratio = baselineWinkler > 0 ? w.mean_winkler / baselineWinkler : 1;
      if (ratio > 1.1) esc.push(w);
      else stable.push(w);
    }
    return { stable, esc };
  }, [winkler, baselineWinkler]);

  // Diff summary stats
  const diffSummary = useMemo(() => {
    if (!diffData || diffData.length === 0) return null;
    const total = diffData.length;
    const mean = diffData.reduce((s, d) => s + d.delta, 0) / total;
    const decreases = diffData.filter((d) => d.delta < 0).length;
    const increases = diffData.filter((d) => d.delta > 0).length;
    const largestDrop = Math.min(...diffData.map((d) => d.delta));
    const largestRise = Math.max(...diffData.map((d) => d.delta));
    return { total, mean, decreases, increases, largestDrop, largestRise };
  }, [diffData]);

  return (
    <>
      <PageHeader
        eyebrow="The math payoff"
        title="Coverage Drift Audit"
        subtitle="Empirical coverage vs. the 90% conformal guarantee — proven across every model version."
        pills={[
          { label: "Live", liveDot: true },
          { label: "MAPIE conformal", variant: "violet" },
          { label: "FOR SYSTEM_TIME ALL", variant: "blue" },
          { label: "Drift detection", variant: "amber" },
        ]}
      />

      {/* ─── 1. Methodology STRIP — minimal text, scannable chips ─────── */}
      <section className="tour-anchor-methodology fc-stat mb-5 !p-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <div className="flex items-center gap-2">
            <span className="fc-stat-label !mb-0">Methodology</span>
            <span className="text-[12px] text-slate-500">·</span>
            <span className="text-[13px] text-slate-400">
              Synthetic actuals from log-normal noise on each prediction.
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <MethodologyChip
              variant="calibrated"
              label="Runs 1–4"
              formula="σ = 0.10"
            />
            <MethodologyChip
              variant="drift"
              label="Runs 5–6"
              formula="σ = 0.22"
            />
            <MethodologyChip
              variant="expected"
              label="Expected"
              formula="1–4 near 90%, 5–6 collapse"
            />
          </div>
        </div>
      </section>

      {/* ─── 2. AUDIT HEADLINE — 5-second scan answer ─────────────────── */}
      <div className="grid gap-4 md:grid-cols-2 mb-6 tour-anchor-drift-chart">
        <HeadlineTile
          variant="calibrated"
          icon={<ShieldCheck size={22} />}
          label="Calibrated"
          countText={`${splitCoverage.cal.length} / ${splitCoverage.total} runs`}
          metricLabel="Mean coverage"
          metricValue={`${(splitCoverage.meanCal * 100).toFixed(1)}%`}
          subtext={`within ±${Math.abs((splitCoverage.meanCal - 0.9) * 100).toFixed(0)}pp of the 90% target`}
        />
        <HeadlineTile
          variant="drift"
          icon={<AlertTriangle size={22} />}
          label="Drift detected"
          countText={`${splitCoverage.dft.length} / ${splitCoverage.total} runs`}
          metricLabel="Mean coverage"
          metricValue={
            splitCoverage.dft.length > 0
              ? `${(splitCoverage.meanDft * 100).toFixed(1)}%`
              : "—"
          }
          subtext={
            splitCoverage.dft.length > 0
              ? `${Math.abs((splitCoverage.meanDft - 0.9) * 100).toFixed(0)}pp below target`
              : "no drift detected"
          }
        />
      </div>

      {/* ─── 3. Empirical Coverage per Batch — split groups ───────────── */}
      <section className="mb-6">
        <header className="mb-3">
          <h2 className="text-[18px] font-bold text-slate-100">
            Empirical Coverage per Batch
          </h2>
          <p className="text-[13px] text-slate-400 mt-0.5">
            Each batch measured against the 90% conformal target.
          </p>
        </header>

        {loadingCov ? (
          <div className="text-slate-400">Loading…</div>
        ) : (
          <SplitGroup
            calibrated={splitCoverage.cal.map((c) => {
              const cov = c.mean_coverage ?? 0;
              const deltaPp = (cov - 0.9) * 100;
              return (
                <RunStatusCard
                  key={c.forecast_run_id}
                  runId={c.forecast_run_id}
                  value={`${(cov * 100).toFixed(1)}%`}
                  delta={`${deltaPp >= 0 ? "+" : ""}${deltaPp.toFixed(1)}pp vs target`}
                  status="On target"
                  variant="healthy"
                />
              );
            })}
            drift={splitCoverage.dft.map((c) => {
              const cov = c.mean_coverage ?? 0;
              const deltaPp = (cov - 0.9) * 100;
              return (
                <RunStatusCard
                  key={c.forecast_run_id}
                  runId={c.forecast_run_id}
                  value={`${(cov * 100).toFixed(1)}%`}
                  delta={`${deltaPp.toFixed(1)}pp vs target`}
                  status="Drifted"
                  variant="drift"
                />
              );
            })}
          />
        )}
      </section>

      {/* ─── 4. Winkler Score per Batch — same split ──────────────────── */}
      <section className="tour-anchor-winkler mb-6">
        <header className="mb-3">
          <h2 className="text-[18px] font-bold text-slate-100">
            Winkler Interval Score per Batch{" "}
            <span className="text-[13px] font-normal text-slate-400">
              · lower = better
            </span>
          </h2>
          <p className="text-[13px] text-slate-400 mt-0.5">
            Continuous companion to coverage —{" "}
            <strong className="text-slate-100">
              watch the 3× jump between Run 4 and Run 5
            </strong>
            .
          </p>
        </header>

        {loadingWink ? (
          <div className="text-slate-400">Loading…</div>
        ) : (
          <SplitGroup
            calibrated={splitWinkler.stable.map((w) => {
              const ratio =
                baselineWinkler > 0 ? w.mean_winkler / baselineWinkler : 1;
              const pct = (ratio - 1.0) * 100;
              return (
                <RunStatusCard
                  key={w.forecast_run_id}
                  runId={w.forecast_run_id}
                  value={Math.round(w.mean_winkler).toLocaleString()}
                  delta={`${pct >= 0 ? "+" : ""}${pct.toFixed(0)}% vs calibrated`}
                  status="Stable"
                  variant="healthy"
                />
              );
            })}
            drift={splitWinkler.esc.map((w) => {
              const ratio =
                baselineWinkler > 0 ? w.mean_winkler / baselineWinkler : 1;
              const pct = (ratio - 1.0) * 100;
              return (
                <RunStatusCard
                  key={w.forecast_run_id}
                  runId={w.forecast_run_id}
                  value={Math.round(w.mean_winkler).toLocaleString()}
                  delta={`+${pct.toFixed(0)}% vs calibrated`}
                  status="Escalated"
                  variant="drift"
                />
              );
            })}
          />
        )}
      </section>

      {/* ─── 5. Calibration-drift SQL ─────────────────────────────────── */}
      <div className="mb-8">
        <SqlPanel
          title="View SQL — calibration drift"
          defaultOpen={false}
          sql={`SELECT forecast_run_id,
       AVG(coverage_score)              AS mean_coverage,
       AVG(upper_bound - lower_bound)   AS mean_width,
       COUNT(*)                         AS n_rows
FROM forecasts FOR SYSTEM_TIME ALL
WHERE coverage_score IS NOT NULL
GROUP BY forecast_run_id
ORDER BY forecast_run_id;`}
        />
      </div>

      {/* ─── 6. Prediction Diff section ────────────────────────────────── */}
      <section className="tour-anchor-diff mb-6">
        <header className="mb-4">
          <h2 className="text-[18px] font-bold text-slate-100">
            Prediction Diff Between Two Batches
          </h2>
          <p className="text-[13px] text-slate-400 mt-0.5">
            Compare forecast changes between two temporal snapshots.
          </p>
        </header>

        <div
          className="grid gap-3 mb-4"
          style={{ gridTemplateColumns: "1fr 1fr 1fr" }}
        >
          <ControlCard label="Batch A (earlier)" icon={<Calendar size={14} />}>
            <select
              value={batchAIdx}
              onChange={(e) => setBatchAIdx(Number(e.target.value))}
              aria-label="Batch A (earlier)"
              className="w-full h-12 pl-9 pr-9 rounded-[10px] bg-bg-deep border border-white/[0.14] text-slate-100 text-[13px]"
            >
              {batches.map((b, i) => (
                <option key={b.forecast_run_id} value={i}>
                  Run {b.forecast_run_id}:{" "}
                  {new Date(b.story_ts).toISOString().slice(0, 10)} (
                  {b.model_version})
                </option>
              ))}
            </select>
          </ControlCard>

          <ControlCard label="Batch B (later)" icon={<Calendar size={14} />}>
            <select
              value={batchBIdx}
              onChange={(e) => setBatchBIdx(Number(e.target.value))}
              aria-label="Batch B (later)"
              className="w-full h-12 pl-9 pr-9 rounded-[10px] bg-bg-deep border border-white/[0.14] text-slate-100 text-[13px]"
            >
              {batches.map((b, i) => (
                <option key={b.forecast_run_id} value={i}>
                  Run {b.forecast_run_id}:{" "}
                  {new Date(b.story_ts).toISOString().slice(0, 10)} (
                  {b.model_version})
                </option>
              ))}
            </select>
          </ControlCard>

          <ControlCard label="Route" icon={<Plane size={14} />}>
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
          </ControlCard>
        </div>

        {diffSummary && (
          <div className="flex flex-wrap gap-2 mb-4">
            <SummaryChip>
              {diffSummary.total} forecast dates compared
            </SummaryChip>
            <SummaryChip>
              Mean delta: {diffSummary.mean >= 0 ? "+" : ""}
              {diffSummary.mean.toFixed(1)} pax
            </SummaryChip>
            <SummaryChip>
              {diffSummary.decreases} decreases / {diffSummary.increases}{" "}
              increases
            </SummaryChip>
          </div>
        )}

        <div className="fc-stat !p-5">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h3 className="text-[17px] font-bold text-slate-100">
              Prediction Δ — {routeLabel || "—"}
            </h3>
            <div className="flex items-center gap-3 text-[12px] text-slate-400">
              <span className="flex items-center gap-1.5">
                <span
                  className="inline-block w-2.5 h-2.5 rounded-sm"
                  style={{ background: "rgba(52,211,153,0.55)" }}
                />
                Demand increased
              </span>
              <span className="flex items-center gap-1.5">
                <span
                  className="inline-block w-2.5 h-2.5 rounded-sm"
                  style={{ background: "rgba(251,146,60,0.55)" }}
                />
                Demand decreased
              </span>
            </div>
          </div>

          {batchA && batchB && batchA.row_start_ts === batchB.row_start_ts ? (
            <div className="text-amber-400 py-8 text-center text-[13px]">
              Select two different batches to see a diff.
            </div>
          ) : loadingDiff ? (
            <div className="text-slate-400 py-12 text-center" role="status">
              Running temporal diff query…
            </div>
          ) : (
            <DiffChart
              data={diffData}
              routeLabel={routeLabel}
              height={340}
            />
          )}
        </div>

        {diffSummary && diffSummary.total > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
            <InsightTile
              icon={<TrendingDown size={15} />}
              tone="amber"
              label="Largest drop"
              value={`${diffSummary.largestDrop.toFixed(1)} pax`}
            />
            <InsightTile
              icon={<TrendingUp size={15} />}
              tone="emerald"
              label="Largest rise"
              value={`${diffSummary.largestRise >= 0 ? "+" : ""}${diffSummary.largestRise.toFixed(1)} pax`}
            />
            <InsightTile
              icon={<Calendar size={15} />}
              tone="blue"
              label="Time window"
              value={`${diffSummary.total} days`}
            />
          </div>
        )}
      </section>

      <div className="mb-8">
        <SqlPanel
          title="View SQL — temporal diff"
          defaultOpen={false}
          sql={
            batchA && batchB && routeId
              ? `SELECT a.forecast_date,
       a.predicted_demand AS predicted_a,
       b.predicted_demand AS predicted_b,
       b.predicted_demand - a.predicted_demand AS delta,
       a.model_version AS model_a,
       b.model_version AS model_b
FROM
  (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF '${batchA.row_start_ts}'
   WHERE route_id = ${routeId}) a
JOIN
  (SELECT * FROM forecasts FOR SYSTEM_TIME AS OF '${batchB.row_start_ts}'
   WHERE route_id = ${routeId}) b
  ON a.forecast_date = b.forecast_date
ORDER BY a.forecast_date;`
              : "-- (waiting for batch + route selection)"
          }
        />
      </div>

      {/* ─── 7. Why this matters ───────────────────────────────────────── */}
      <div
        className="rounded-2xl p-5 flex items-start gap-4 border border-accent-blue/20"
        style={{
          background:
            "linear-gradient(135deg, rgba(59,130,246,0.08), rgba(124,58,237,0.10))",
          boxShadow: "0 16px 40px rgba(0,0,0,0.18)",
        }}
      >
        <div className="w-11 h-11 shrink-0 rounded-xl bg-accent-blue/15 text-accent-blue flex items-center justify-center border border-accent-blue/20">
          <ShieldCheck size={20} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[16px] font-bold text-slate-100 mb-1">
            Why this matters
          </div>
          <p className="text-[14px] text-slate-300 leading-relaxed">
            Conformal prediction guarantees ≥90% empirical coverage if the
            calibration distribution is exchangeable. Drift above ±5pp signals
            distribution shift — the model needs recalibration.{" "}
            <code className="px-1.5 py-0.5 rounded bg-bg-deep text-[12px] text-accent-blue border border-white/10">
              FOR SYSTEM_TIME ALL
            </code>{" "}
            makes this audit zero-cost: no shadow tables, no log tables.
          </p>
        </div>
      </div>
    </>
  );
}

/* ─────────────────────────────────────────────────────────────────────
   Small inline helpers
   ────────────────────────────────────────────────────────────────────── */

/**
 * MethodologyChip — compact horizontal chip for the methodology strip.
 * Replaces the previous paragraph-heavy methodology card.
 */
function MethodologyChip({
  variant,
  label,
  formula,
}: {
  variant: "calibrated" | "drift" | "expected";
  label: string;
  formula: string;
}) {
  const VARIANTS = {
    calibrated: {
      border: "border-accent-blue/30",
      bg: "bg-accent-blue/[0.06]",
      labelColor: "text-accent-blue",
      formulaColor: "text-slate-100",
    },
    drift: {
      border: "border-accent-amber/35",
      bg: "bg-accent-amber/[0.06]",
      labelColor: "text-accent-amber",
      formulaColor: "text-slate-100",
    },
    expected: {
      border: "border-emerald-500/30",
      bg: "bg-emerald-500/[0.06]",
      labelColor: "text-emerald-400",
      formulaColor: "text-slate-100",
    },
  } as const;
  const v = VARIANTS[variant];
  return (
    <span
      className={`inline-flex items-center gap-2 h-8 px-3 rounded-full border text-[12px] ${v.border} ${v.bg}`}
    >
      <span className={`font-bold uppercase tracking-wider text-[11px] ${v.labelColor}`}>
        {label}
      </span>
      <code className={`font-mono ${v.formulaColor}`}>{formula}</code>
    </span>
  );
}

/**
 * HeadlineTile — the big 5-second-scan summary card.
 * Two of these sit side-by-side (calibrated vs drift) at the top of
 * the audit data, so the user knows the answer before reading details.
 */
function HeadlineTile({
  variant,
  icon,
  label,
  countText,
  metricLabel,
  metricValue,
  subtext,
}: {
  variant: "calibrated" | "drift";
  icon: React.ReactNode;
  label: string;
  countText: string;
  metricLabel: string;
  metricValue: string;
  subtext: string;
}) {
  const isDrift = variant === "drift";
  const tones = isDrift
    ? {
        border: "border-accent-amber/35",
        bg: "bg-accent-amber/[0.05]",
        chip: "bg-accent-amber/15 text-accent-amber",
        accent: "text-accent-amber",
        badge: "bg-accent-amber/15 text-accent-amber border-accent-amber/35",
      }
    : {
        border: "border-accent-blue/30",
        bg: "bg-accent-blue/[0.04]",
        chip: "bg-accent-blue/15 text-accent-blue",
        accent: "text-accent-blue",
        badge: "bg-accent-blue/15 text-accent-blue border-accent-blue/30",
      };
  return (
    <div
      className={`rounded-2xl border p-5 ${tones.border} ${tones.bg}`}
      style={{ boxShadow: "0 16px 40px rgba(0,0,0,0.18)" }}
    >
      <div className="flex items-center gap-3 mb-3">
        <span
          className={`w-11 h-11 shrink-0 rounded-xl flex items-center justify-center border border-white/5 ${tones.chip}`}
        >
          {icon}
        </span>
        <div className="min-w-0">
          <div
            className={`text-[11px] uppercase tracking-[0.142em] font-bold ${tones.accent}`}
          >
            {label}
          </div>
          <div className="text-[26px] font-extrabold text-slate-50 leading-none mt-0.5">
            {countText}
          </div>
        </div>
      </div>
      <div className="flex items-baseline justify-between flex-wrap gap-x-3">
        <div className="text-[13px] text-slate-400">
          <span className="text-slate-300">{metricLabel}:</span>{" "}
          <span className={`font-bold ${tones.accent}`}>{metricValue}</span>
        </div>
        <div className="text-[12px] text-slate-500">{subtext}</div>
      </div>
    </div>
  );
}

/**
 * SplitGroup — two visually-distinct containers for grouping run cards.
 * Calibrated runs on the left in a 2-col grid, drift runs on the right
 * in a 1-col grid, side-by-side at md+. Each group has its own labelled
 * header + tinted backdrop so the user instantly sees the partition.
 */
function SplitGroup({
  calibrated,
  drift,
}: {
  calibrated: React.ReactNode[];
  drift: React.ReactNode[];
}) {
  return (
    <div
      className="grid gap-4"
      style={{ gridTemplateColumns: "minmax(0, 2fr) minmax(0, 1fr)" }}
    >
      <div className="rounded-2xl border border-accent-blue/15 bg-accent-blue/[0.025] p-3.5">
        <header className="flex items-center gap-2 mb-3 px-1">
          <span className="w-6 h-6 rounded-md bg-accent-blue/15 text-accent-blue flex items-center justify-center">
            <Check size={14} />
          </span>
          <span className="text-[11px] uppercase tracking-[0.142em] font-bold text-accent-blue">
            Calibrated · {calibrated.length}
          </span>
        </header>
        <div className="grid grid-cols-2 gap-3">{calibrated}</div>
      </div>

      <div className="rounded-2xl border border-accent-amber/30 bg-accent-amber/[0.04] p-3.5">
        <header className="flex items-center gap-2 mb-3 px-1">
          <span className="w-6 h-6 rounded-md bg-accent-amber/15 text-accent-amber flex items-center justify-center">
            <AlertTriangle size={14} />
          </span>
          <span className="text-[11px] uppercase tracking-[0.142em] font-bold text-accent-amber">
            Drift · {drift.length}
          </span>
        </header>
        <div className="grid grid-cols-1 gap-3">{drift}</div>
      </div>
    </div>
  );
}

function ControlCard({
  label,
  icon,
  children,
}: {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="fc-stat !p-4 !rounded-[14px]">
      <div className="fc-stat-label !mb-2">{label}</div>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none z-10">
          {icon}
        </span>
        {children}
      </div>
    </div>
  );
}

function SummaryChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 h-8 px-3 rounded-full text-[12px] font-medium border border-white/[0.14] bg-bg-deep text-slate-300">
      {children}
    </span>
  );
}

function InsightTile({
  icon,
  tone,
  label,
  value,
}: {
  icon: React.ReactNode;
  tone: "amber" | "emerald" | "blue";
  label: string;
  value: string;
}) {
  const TONES: Record<typeof tone, string> = {
    amber: "bg-accent-amber/15 text-accent-amber",
    emerald: "bg-emerald-500/15 text-emerald-400",
    blue: "bg-accent-blue/15 text-accent-blue",
  };
  return (
    <div className="fc-stat !p-3 flex items-center gap-3">
      <span
        className={`w-9 h-9 shrink-0 rounded-lg ${TONES[tone]} flex items-center justify-center border border-white/5`}
      >
        {icon}
      </span>
      <div className="min-w-0">
        <div className="text-[11px] uppercase tracking-[0.142em] text-slate-400 font-semibold">
          {label}
        </div>
        <div className="text-[15px] font-bold text-slate-100 leading-tight">
          {value}
        </div>
      </div>
    </div>
  );
}
