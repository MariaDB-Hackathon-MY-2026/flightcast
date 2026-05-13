import type { LucideIcon } from "lucide-react";

interface Props {
  icon: LucideIcon;
  label: string;
  value: string;
  hint?: string;
  accent?: "violet" | "blue" | "emerald" | "amber" | "default";
}

const ACCENTS = {
  violet: "bg-accent-violet/15 text-accent-violet",
  blue: "bg-accent-blue/15 text-accent-blue",
  emerald: "bg-emerald-500/15 text-emerald-400",
  amber: "bg-accent-amber/15 text-accent-amber",
  default: "bg-slate-500/15 text-slate-400",
};

/**
 * KPI card per design spec: 44–48px icon tile (left), uppercase 12px
 * label, 24px weight-800 value, 13px helper line. Targets ~96px card
 * height under default content.
 */
export function IconStatCard({
  icon: Icon,
  label,
  value,
  hint,
  accent = "default",
}: Props) {
  const accentClass = ACCENTS[accent];
  return (
    <div className="fc-stat flex items-center gap-4">
      <div
        className={`w-11 h-11 shrink-0 rounded-xl ${accentClass} flex items-center justify-center border border-white/5`}
      >
        <Icon size={20} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="fc-stat-label !mb-0.5">{label}</div>
        <div className="fc-stat-value">{value}</div>
        {hint && <div className="fc-stat-hint">{hint}</div>}
      </div>
    </div>
  );
}
