"use client";

import dynamic from "next/dynamic";
import type { ForecastHistoryPoint } from "@/lib/types";

const Plot = dynamic(
  async () => {
    const [{ default: createPlotlyComponent }, { default: Plotly }] =
      await Promise.all([
        import("react-plotly.js/factory"),
        import("plotly.js-dist-min"),
      ]);
    return createPlotlyComponent(Plotly as never);
  },
  { ssr: false },
);

const PALETTE = [
  "#60A5FA", // blue
  "#34D399", // mint
  "#FBBF24", // amber
  "#F472B6", // pink
  "#A78BFA", // violet
  "#FB923C", // orange
  "#22D3EE", // cyan
  "#F87171", // red
];

interface Props {
  data: ForecastHistoryPoint[];
  routeLabel: string;
  height?: number;
}

/**
 * Mirror of `build_history_figure()` in src/flightcast/ui/charts.py.
 * Renders one Plotly trace per forecast_run_id so the user sees how the
 * model's predictions changed across versions — the FOR SYSTEM_TIME ALL
 * showcase chart.
 */
export function HistoryChart({ data, routeLabel, height = 460 }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="fc-stat text-center text-slate-400 py-12">
        No historical data for this route yet.
      </div>
    );
  }

  // Group by forecast_run_id, preserving insertion order
  const groups = new Map<number, ForecastHistoryPoint[]>();
  for (const row of data) {
    const arr = groups.get(row.forecast_run_id) ?? [];
    arr.push(row);
    groups.set(row.forecast_run_id, arr);
  }

  const traces = Array.from(groups.entries()).map(([runId, rows], i) => {
    const sorted = [...rows].sort((a, b) =>
      a.forecast_date.localeCompare(b.forecast_date),
    );
    const label = `Run ${runId} · ${sorted[0].model_version}`;
    const color = PALETTE[i % PALETTE.length];
    return {
      x: sorted.map((r) => r.forecast_date),
      y: sorted.map((r) => r.predicted_demand),
      mode: "lines",
      type: "scatter",
      name: label,
      line: { color, width: 2.2, shape: "spline", smoothing: 0.6 },
      hovertemplate: `<b>${label}</b><br>%{x|%b %d}<br>Predicted: %{y:,.0f} pax<extra></extra>`,
    } as never;
  });

  return (
    <Plot
      data={traces}
      layout={{
        title: {
          text: `<b>Full Prediction History — ${routeLabel}</b>`,
          x: 0.02,
          font: { color: "#F1F5F9", size: 16 },
        },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: {
          family:
            'Inter, -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif',
          color: "#CBD5E1",
        },

        xaxis: {
          title: { text: "Forecast date", font: { color: "#E2E8F0" } },
          showgrid: false,
          tickformat: "%b %d",
          tickfont: { color: "#CBD5E1" },
        },
        yaxis: {
          title: {
            text: "Predicted demand (passengers)",
            font: { color: "#E2E8F0" },
          },
          gridcolor: "rgba(148,163,184,0.12)",
          zeroline: false,
          tickfont: { color: "#CBD5E1" },
        },
        margin: { t: 50, r: 16, b: 50, l: 60 },
        hovermode: "x unified",
        hoverlabel: {
          bgcolor: "#172033",
          bordercolor: "rgba(148,163,184,0.2)",
          font: {
            color: "#F8FAFC",
            family:
              'Inter, -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif',
            size: 12,
          },
        },
        legend: { orientation: "h", y: -0.18 },
      }}
      config={{ displaylogo: false, responsive: true }}
      style={{ width: "100%", height }}
      useResizeHandler
    />
  );
}
