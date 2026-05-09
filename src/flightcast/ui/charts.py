"""
Plotly figure builders for FlightCast dashboard.
All charts use plotly_dark theme — consistent with demo recording setup.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


BAND_COLOR = "rgba(74,158,232,0.18)"
LINE_COLOR = "#4A9EE8"
ACTUAL_COLOR = "#F6C549"
TARGET_COLOR = "#22C55E"
WARN_COLOR = "#F97316"

# Softer, more professional diff palette (muted, not neon)
DIFF_UP_COLOR = "#34D399"      # mint green — demand up
DIFF_UP_EDGE = "#10B981"
DIFF_DOWN_COLOR = "#FB923C"    # warm amber — demand down
DIFF_DOWN_EDGE = "#EA580C"
GRID_COLOR = "rgba(148,163,184,0.12)"
ZERO_LINE_COLOR = "rgba(148,163,184,0.55)"
MEAN_LINE_COLOR = "#A78BFA"    # violet for the mean reference


def build_forecast_figure(df: pd.DataFrame, route_label: str) -> go.Figure:
    """90% conformal band + predicted demand line."""
    df = df.sort_values("forecast_date")
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["forecast_date"], y=df["lower_bound"],
            mode="lines", line=dict(width=0),
            showlegend=False, hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["forecast_date"], y=df["upper_bound"],
            mode="lines", line=dict(width=0),
            fill="tonexty", fillcolor=BAND_COLOR,
            name="90% conformal interval",
            hovertemplate="Upper: %{y:,.0f} pax<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["forecast_date"], y=df["predicted_demand"],
            mode="lines",
            line=dict(color=LINE_COLOR, width=2.5, shape="spline", smoothing=0.6),
            name="Predicted demand",
            hovertemplate="<b>%{x|%b %d}</b><br>Predicted: %{y:,.0f} pax<extra></extra>",
        )
    )

    if "actual_demand" in df.columns and df["actual_demand"].notna().any():
        fig.add_trace(
            go.Scatter(
                x=df["forecast_date"], y=df["actual_demand"],
                mode="markers",
                marker=dict(
                    color=ACTUAL_COLOR, size=7, symbol="circle",
                    line=dict(color="rgba(15,23,42,0.85)", width=1),
                ),
                name="Actual demand",
                hovertemplate="Actual: %{y:,.0f} pax<extra></extra>",
            )
        )

    fig.update_layout(
        title=dict(text=f"<b>Demand Forecast — {route_label}</b>", x=0.02),
        xaxis=dict(
            title="Date",
            showgrid=False,
            tickformat="%b %d",
            ticks="outside",
            ticklen=4,
            tickcolor="rgba(148,163,184,0.4)",
        ),
        yaxis=dict(
            title="Passengers",
            gridcolor=GRID_COLOR,
            zeroline=False,
            tickformat=",.0f",
        ),
        hovermode="x unified",
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, x=0,
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor="rgba(15,23,42,0.95)",
            bordercolor="rgba(148,163,184,0.4)",
            font=dict(size=12),
        ),
        margin=dict(t=80, b=50, l=70, r=30),
    )
    return fig


def build_coverage_drift_figure(df: pd.DataFrame) -> go.Figure:
    """Rolling 30-day empirical coverage vs 90% target."""
    fig = go.Figure()

    # Acceptable band 85–95%
    if not df.empty:
        fig.add_trace(
            go.Scatter(
                x=df["forecast_date"].tolist() + df["forecast_date"].tolist()[::-1],
                y=[0.95] * len(df) + [0.85] * len(df),
                fill="toself",
                fillcolor="rgba(34,197,94,0.12)",
                line=dict(width=0),
                showlegend=True,
                name="Acceptable band (85–95%)",
                hoverinfo="skip",
            )
        )

    # Target line
    if not df.empty:
        fig.add_trace(
            go.Scatter(
                x=df["forecast_date"], y=[0.90] * len(df),
                mode="lines",
                line=dict(color=TARGET_COLOR, dash="dash", width=1.5),
                name="Target 90%",
            )
        )

    if not df.empty and "empirical_coverage_30d" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["forecast_date"], y=df["empirical_coverage_30d"],
                mode="lines+markers",
                line=dict(color=LINE_COLOR, width=2.5),
                marker=dict(size=5),
                name="Empirical coverage (30d rolling)",
            )
        )

    fig.update_layout(
        title=dict(text="Calibration Drift — Empirical Coverage vs 90% Target", x=0.02),
        xaxis_title="Date",
        yaxis_title="Coverage rate",
        yaxis=dict(range=[0.7, 1.0], tickformat=".0%"),
        hovermode="x unified",
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(t=80, b=40, l=60, r=20),
    )
    return fig


def build_diff_figure(df: pd.DataFrame, route_label: str) -> go.Figure:
    """Bar chart showing prediction delta between two batch timestamps."""
    if df.empty:
        return go.Figure()

    df = df.sort_values("forecast_date").copy()

    # Per-bar color + edge: muted mint for up, warm amber for down
    fill_colors = [
        DIFF_UP_COLOR if d >= 0 else DIFF_DOWN_COLOR for d in df["delta"]
    ]
    edge_colors = [
        DIFF_UP_EDGE if d >= 0 else DIFF_DOWN_EDGE for d in df["delta"]
    ]

    # Compute reference stats for annotations
    mean_delta = float(df["delta"].mean())
    pct_change = None
    if "predicted_a" in df.columns and df["predicted_a"].abs().mean() > 0:
        pct_change = (df["delta"] / df["predicted_a"]).mean() * 100.0

    # Hover with absolute and percentage info
    hover_pct = (df["delta"] / df["predicted_a"] * 100.0) if "predicted_a" in df.columns else df["delta"] * 0
    customdata = list(zip(
        df["predicted_a"] if "predicted_a" in df.columns else df["delta"] * 0,
        df["predicted_b"] if "predicted_b" in df.columns else df["delta"] * 0,
        hover_pct,
    ))

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["forecast_date"],
            y=df["delta"],
            marker=dict(
                color=fill_colors,
                line=dict(color=edge_colors, width=1),
            ),
            name="Δ predicted demand",
            customdata=customdata,
            hovertemplate=(
                "<b>%{x|%b %d, %Y}</b><br>"
                "Batch A: %{customdata[0]:,.0f} pax<br>"
                "Batch B: %{customdata[1]:,.0f} pax<br>"
                "Change: %{y:+,.1f} pax (%{customdata[2]:+.2f}%)"
                "<extra></extra>"
            ),
            width=0.7 * 86_400_000,  # 70% of one day in ms — gives breathing room between bars
        )
    )

    # Reference line at zero
    fig.add_hline(
        y=0,
        line=dict(color=ZERO_LINE_COLOR, width=1),
    )

    # Mean delta reference line + annotation
    fig.add_hline(
        y=mean_delta,
        line=dict(color=MEAN_LINE_COLOR, width=1.5, dash="dot"),
        annotation_text=f"  mean Δ = {mean_delta:+,.1f} pax",
        annotation_position="top right",
        annotation_font=dict(color=MEAN_LINE_COLOR, size=11),
    )

    subtitle = (
        f"  ·  mean shift: {pct_change:+.2f}%" if pct_change is not None else ""
    )

    fig.update_layout(
        title=dict(
            text=f"<b>Prediction Diff — {route_label}</b><span style='color:#94A3B8;font-size:13px;font-weight:400'>{subtitle}</span>",
            x=0.02,
        ),
        xaxis=dict(
            title="Forecast date",
            showgrid=False,
            tickformat="%b %d",
            ticks="outside",
            ticklen=4,
            tickcolor="rgba(148,163,184,0.4)",
        ),
        yaxis=dict(
            title="Δ predicted demand (passengers)",
            zeroline=False,
            gridcolor=GRID_COLOR,
            tickformat=",.0f",
        ),
        template="plotly_dark",
        bargap=0.15,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hoverlabel=dict(
            bgcolor="rgba(15,23,42,0.95)",
            bordercolor="rgba(148,163,184,0.4)",
            font=dict(size=12),
        ),
        margin=dict(t=80, b=50, l=70, r=30),
    )
    return fig


def build_history_figure(df: pd.DataFrame, route_label: str) -> go.Figure:
    """All historical versions overlaid by ROW_START bucket."""
    if df.empty:
        return go.Figure()

    # A curated palette that works on dark backgrounds and reads as a sequence
    palette = [
        "#60A5FA",   # blue
        "#34D399",   # mint
        "#FBBF24",   # amber
        "#F472B6",   # pink
        "#A78BFA",   # violet
        "#FB923C",   # orange
        "#22D3EE",   # cyan
        "#F87171",   # red
    ]

    fig = go.Figure()
    for i, (run_id, grp) in enumerate(df.groupby("forecast_run_id")):
        grp = grp.sort_values("forecast_date")
        color = palette[i % len(palette)]
        label = f"Run {int(run_id)}"
        if "model_version" in grp.columns:
            label += f" · {grp['model_version'].iloc[0]}"
        fig.add_trace(
            go.Scatter(
                x=grp["forecast_date"], y=grp["predicted_demand"],
                mode="lines",
                line=dict(color=color, width=2.0, shape="spline", smoothing=0.6),
                name=label,
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "%{x|%b %d}<br>"
                    "Predicted: %{y:,.0f} pax<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text=f"<b>Full Prediction History — {route_label}</b>", x=0.02),
        xaxis=dict(
            title="Forecast date",
            showgrid=False,
            tickformat="%b %d",
            ticks="outside",
            ticklen=4,
            tickcolor="rgba(148,163,184,0.4)",
        ),
        yaxis=dict(
            title="Predicted demand (passengers)",
            gridcolor=GRID_COLOR,
            zeroline=False,
            tickformat=",.0f",
        ),
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, x=0,
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor="rgba(15,23,42,0.95)",
            bordercolor="rgba(148,163,184,0.4)",
            font=dict(size=12),
        ),
        margin=dict(t=80, b=50, l=70, r=30),
    )
    return fig
