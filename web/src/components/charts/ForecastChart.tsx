"use client";

import dynamic from "next/dynamic";
import type { ForecastPoint, ActualPoint } from "@/lib/types";

// react-plotly.js hardcodes a `plotly.js/dist/plotly` import, but we install
// the lighter `plotly.js-dist-min` bundle (saves ~2 MB gzipped). Wire them
// together via the factory to avoid the build-time module resolution error.
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
  data: ForecastPoint[];
  routeLabel: string;
  height?: number;
  showTitle?: boolean;
  /**
   * When provided, overlays a scatter of measured ground-truth values on
   * top of the forecast line. Pass an empty array (or omit) to hide.
   */
  actuals?: ActualPoint[];
}

/**
 * Mirror of `build_forecast_figure()` in src/flightcast/ui/charts.py.
 * Renders the conformal-band line chart with median + lower/upper interval.
 */
export function ForecastChart({
  data,
  routeLabel,
  height = 320,
  showTitle = true,
  actuals,
}: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="fc-stat text-center text-slate-400 py-12">
        No forecast data for this route at the selected timestamp.
      </div>
    );
  }
  const x = data.map((d) => d.forecast_date);

  const traces: unknown[] = [
    {
      x,
      y: data.map((d) => d.upper_bound),
      mode: "lines",
      line: { width: 0 },
      name: "Upper",
      showlegend: false,
      hoverinfo: "skip",
    },
    {
      x,
      y: data.map((d) => d.lower_bound),
      mode: "lines",
      line: { width: 0 },
      name: "90% conformal interval",
      fill: "tonexty",
      fillcolor: "rgba(124,58,237,0.24)",
      hoverinfo: "skip",
    },
    {
      x,
      y: data.map((d) => d.predicted_demand),
      mode: "lines+markers",
      name: "Predicted demand",
      line: { color: "#A78BFA", width: 2 },
      marker: { size: 5, color: "#C4B5FD" },
    },
  ];

  if (actuals && actuals.length > 0) {
    traces.push({
      x: actuals.map((a) => a.forecast_date),
      y: actuals.map((a) => a.actual_demand),
      mode: "markers",
      name: "Actual demand",
      type: "scatter",
      marker: {
        size: 7,
        color: "#FBBF24",
        symbol: "circle",
        line: { color: "#451A03", width: 1 },
      },
      hovertemplate:
        "<b>Actual</b><br>%{x|%b %d}<br>%{y:,.0f} pax<extra></extra>",
    });
  }

  return (
    <Plot
      data={traces as never}
      layout={{
        title: showTitle
          ? {
              text: `<b>${routeLabel}</b> · 30-day forecast`,
              font: { color: "#F1F5F9", size: 16 },
              x: 0.02,
            }
          : undefined,
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: {
          family:
            'Inter, -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif',
          color: "#CBD5E1",
        },
        xaxis: {
          title: { text: "Forecast date", font: { color: "#E2E8F0" } },
          gridcolor: "rgba(148,163,184,0.12)",
          zeroline: false,
          tickfont: { color: "#CBD5E1" },
        },
        yaxis: {
          title: {
            text: "Demand (passengers / day)",
            font: { color: "#E2E8F0" },
          },
          gridcolor: "rgba(148,163,184,0.12)",
          zeroline: false,
          tickfont: { color: "#CBD5E1" },
        },
        margin: { t: showTitle ? 36 : 8, r: 12, b: 40, l: 56 },
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
        legend: {
          orientation: "h",
          y: -0.18,
          font: { color: "#CBD5E1", size: 12 },
        },
      }}
      config={{ displaylogo: false, responsive: true }}
      style={{ width: "100%", height }}
      useResizeHandler
    />
  );
}
