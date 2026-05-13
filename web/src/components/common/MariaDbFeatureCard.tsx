import type { ReactNode } from "react";
import { Database } from "lucide-react";

interface Props {
  /** Inline pill text — e.g. "FOR SYSTEM_TIME ALL". */
  feature: string;
  /** Body description shown next to / under the pill. */
  children: ReactNode;
}

/**
 * MariaDbFeatureCard — paired with a SqlPanel to highlight the specific
 * MariaDB primitive the SQL relies on. Violet database icon (left),
 * label "MariaDB feature:" + amber feature pill + description (right).
 */
export function MariaDbFeatureCard({ feature, children }: Props) {
  return (
    <div className="fc-stat flex items-start gap-4">
      <div className="w-11 h-11 shrink-0 rounded-xl bg-accent-violet/15 text-accent-violet flex items-center justify-center border border-accent-violet/20">
        <Database size={20} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
          <span className="text-[14px] font-bold text-slate-100">
            MariaDB feature:
          </span>
          <span className="fc-pill fc-pill-amber !h-7 !text-[12px] font-mono">
            {feature}
          </span>
        </div>
        <p className="text-[13px] text-slate-400 leading-relaxed">
          {children}
        </p>
      </div>
    </div>
  );
}
