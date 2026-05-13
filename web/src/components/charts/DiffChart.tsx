"use client";

import dynamic from "next/dynamic";
import type { DiffResult } from "@/lib/types";

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

interface Props {
  data: DiffResult[];
  routeLabel: string;
  height?: number;
}

const UP_FILL = "rgba(52,211,153,0.55)";   // mint, demand increased
const UP_EDGE = "#10B981";
const DOWN_FILL = "rgba(251,146,60,0.55)"; // amber, demand decreased
const DOWN_EDGE = "#F59E0B";

/**
 * Mirror of `build_diff_figure()` in src/flightcast/ui/charts.py.
 * Bar chart: green for positive delta, amber for negative.
 */
export function DiffChart({ data, routeLabel, height = 420 }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="fc-stat text-center text-slate-400 py-12">
        No overlapping forecast dates between the two batches.
      </div>
    );
  }
  const sorted = [...data].sort((a, b) =>
    a.forecast_date.localeCompare(b.forecast_date),
  );

  const fillColors = sorted.map((d) => (d.delta >= 0 ? UP_FILL : DOWN_FILL));
  const edgeColors = sorted.map((d) => (d.delta >= 0 ? UP_EDGE : DOWN_EDGE));

  return (
    <Plot
      data={[
        {
          x: sorted.map((d) => d.forecast_date),
          y: sorted.map((d) => d.delta),
          type: "bar",
          marker: {
            color: fillColors,
            line: { color: edgeColors, width: 1.4 },
          },
          customdata: sorted.map((d) => [
            d.predicted_a,
            d.predicted_b,
            d.predicted_a !== 0 ? (d.delta / d.predicted_a) * 100 : 0,
          ]),
          hovertemplate:
            "<b>%{x|%b %d}</b><br>" +
            "Batch A: %{customdata[0]:,.0f}<br>" +
            "Batch B: %{customdata[1]:,.0f}<br>" +
            "Δ: %{y:+,.0f} (%{customdata[2]:+.1f}%)<extra></extra>",
          name: "Δ predicted demand",
        } as never,
      ]}
      layout={{
        title: {
          text: `<b>Prediction Δ — ${routeLabel}</b>`,
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
          tickformat: "%b %d",
          showgrid: false,
          tickfont: { color: "#CBD5E1" },
        },
        yaxis: {
          title: {
            text: "Δ predicted demand (passengers)",
            font: { color: "#E2E8F0" },
          },
          gridcolor: "rgba(148,163,184,0.12)",
          zeroline: true,
          zerolinecolor: "rgba(148,163,184,0.35)",
          tickfont: { color: "#CBD5E1" },
        },
        margin: { t: 50, r: 16, b: 50, l: 60 },
        bargap: 0.15,
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
      }}
      config={{ displaylogo: false, responsive: true }}
      style={{ width: "100%", height }}
      useResizeHandler
    />
  );
}
