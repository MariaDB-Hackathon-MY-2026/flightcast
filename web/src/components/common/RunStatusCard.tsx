import type { ReactNode } from "react";

interface Props {
  runId: number;
  value: string;
  delta: string;
  status: string;
  /** "healthy" → blue/violet accent · "drift" → amber accent */
  variant: "healthy" | "drift";
  /** Optional secondary line below the delta, e.g. model version. */
  hint?: ReactNode;
}

/**
 * RunStatusCard — KPI card with a status pill and color-coded accent.
 * Shared between Empirical Coverage and Winkler Score sections so the
 * visual rhythm is consistent: healthy runs read blue/violet, drifted
 * runs read amber.
 */
export function RunStatusCard({
  runId,
  value,
  delta,
  status,
  variant,
  hint,
}: Props) {
  const isDrift = variant === "drift";
  const cardBorder = isDrift
    ? "border-accent-amber/30"
    : "border-accent-blue/20";
  const valueColor = isDrift ? "text-accent-amber" : "text-slate-50";
  const badgeClass = isDrift
    ? "bg-accent-amber/15 text-accent-amber border-accent-amber/35"
    : "bg-accent-blue/15 text-accent-blue border-accent-blue/30";
  return (
    <div
      className={`fc-stat ${cardBorder} flex flex-col`}
      style={{ minHeight: 124 }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="fc-stat-label !mb-0 !tracking-[0.142em]">
          Run {runId}
        </span>
        <span
          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border ${badgeClass}`}
        >
          {status}
        </span>
      </div>
      <div className={`text-[26px] font-extrabold leading-none ${valueColor}`}>
        {value}
      </div>
      <div className="text-[13px] text-slate-400 mt-1.5">{delta}</div>
      {hint && (
        <div className="text-[11px] text-slate-500 mt-auto pt-2">{hint}</div>
      )}
    </div>
  );
}
