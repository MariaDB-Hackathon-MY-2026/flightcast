type Pill = {
  label: string;
  variant?: "default" | "blue" | "violet" | "amber";
  liveDot?: boolean;
};

interface Props {
  eyebrow: string;
  title: string;
  subtitle?: string;
  pills?: Pill[];
}

/**
 * Mirror of `page_header()` in src/flightcast/ui/style.py — small-caps
 * eyebrow, large title, subtitle, status pills row.
 */
export function PageHeader({ eyebrow, title, subtitle, pills = [] }: Props) {
  return (
    <header className="pb-6 mb-8 border-b border-white/10">
      <div className="fc-eyebrow">{eyebrow}</div>
      <h1 className="fc-h1 mt-2">{title}</h1>
      {subtitle && <p className="fc-subtitle mt-2">{subtitle}</p>}
      {pills.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-4">
          {pills.map((p, i) => (
            <span
              key={i}
              className={`fc-pill ${
                p.variant === "blue"
                  ? "fc-pill-blue"
                  : p.variant === "violet"
                  ? "fc-pill-violet"
                  : p.variant === "amber"
                  ? "fc-pill-amber"
                  : ""
              }`}
            >
              {p.liveDot && <span className="fc-dot" />}
              {p.label}
            </span>
          ))}
        </div>
      )}
    </header>
  );
}
