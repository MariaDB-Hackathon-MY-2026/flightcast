interface StatItem {
  label: string;
  value: string;
  hint?: string;
}

/**
 * Mirror of `stat_strip()` in src/flightcast/ui/style.py — bordered cards
 * with small-caps labels, large numeric values, and optional hint lines.
 */
export function StatStrip({ items }: { items: StatItem[] }) {
  return (
    <div className="grid gap-3 my-5" style={{
      gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))`,
    }}>
      {items.map((it, i) => (
        <div key={i} className="fc-stat">
          <div className="fc-stat-label">{it.label}</div>
          <div className="fc-stat-value">{it.value}</div>
          {it.hint && <div className="fc-stat-hint">{it.hint}</div>}
        </div>
      ))}
    </div>
  );
}
