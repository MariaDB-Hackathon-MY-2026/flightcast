"""
Page 1: Forecast Explorer — per-route deep dive with full prediction history overlay.
"""
import streamlit as st
import pandas as pd

from flightcast.ui.state import get_conn, load_batch_mapping, load_routes, route_label
from flightcast.db.repositories import fetch_forecasts_all, fetch_forecasts_as_of
from flightcast.ui.charts import build_forecast_figure, build_history_figure
from flightcast.ui.style import page_header
from flightcast.ui.tour import (
    PAGE_FORECAST,
    render_tour_banner,
    render_sidebar_trigger,
)

render_sidebar_trigger()
render_tour_banner(PAGE_FORECAST)

page_header(
    eyebrow="Per-route deep dive",
    title="Forecast Explorer",
    subtitle="Compare 90% conformal prediction bands across every model version on record.",
    pills=[
        ("LIVE", "default"),
        ("FOR SYSTEM_TIME AS OF", "blue"),
        ("FOR SYSTEM_TIME ALL", "violet"),
    ],
)

routes = load_routes()
batches = load_batch_mapping()

if routes.empty:
    st.error("No routes loaded. Run bootstrap first.")
    st.stop()

route_ids = routes["route_id"].tolist()

with st.sidebar:
    st.subheader("Controls")
    chosen_route = st.selectbox(
        "Route",
        options=route_ids,
        format_func=lambda rid: route_label(rid, routes),
    )
    view_mode = st.radio("View mode", ["Latest batch", "All history"])

rlabel = route_label(chosen_route, routes)

if view_mode == "Latest batch":
    if batches.empty:
        st.warning("No batches. Run bootstrap.")
        st.stop()
    latest = batches.iloc[-1]
    as_of = latest["row_start_ts"]
    latest_run_id = int(latest["forecast_run_id"])
    with st.spinner("Fetching latest forecasts..."):
        df = fetch_forecasts_as_of(get_conn(), as_of, chosen_route, latest_run_id)

    if df.empty:
        st.warning("No data for this route in the latest batch.")
    else:
        st.plotly_chart(build_forecast_figure(df, rlabel), use_container_width=True)
        st.caption(f"Batch: {latest['story_ts']} · Model: {latest['model_version']}")

    with st.expander("View SQL"):
        as_of_str = str(as_of)
        st.code(
            f"SELECT route_id, forecast_date, predicted_demand,\n"
            f"       lower_bound, upper_bound, model_version,\n"
            f"       actual_demand, coverage_score,\n"
            f"       ROW_START, ROW_END\n"
            f"FROM forecasts FOR SYSTEM_TIME AS OF '{as_of_str}'\n"
            f"WHERE route_id = {chosen_route}\n"
            f"  AND forecast_run_id = {latest_run_id}\n"
            f"ORDER BY forecast_date;",
            language="sql",
        )

else:
    with st.spinner("Fetching full prediction history..."):
        df = fetch_forecasts_all(get_conn(), chosen_route)

    if df.empty:
        st.warning("No historical data for this route.")
    else:
        st.plotly_chart(build_history_figure(df, rlabel), use_container_width=True)
        st.caption(f"{df['forecast_run_id'].nunique()} model versions · {len(df)} total rows")

    with st.expander("View SQL"):
        st.code(
            f"SELECT forecast_run_id, forecast_date,\n"
            f"       predicted_demand, lower_bound, upper_bound,\n"
            f"       model_version, ROW_START, ROW_END\n"
            f"FROM forecasts FOR SYSTEM_TIME ALL\n"
            f"WHERE route_id = {chosen_route}\n"
            f"ORDER BY ROW_START, forecast_date;",
            language="sql",
        )

st.info(
    "**MariaDB feature:** `FOR SYSTEM_TIME ALL` returns every historical version "
    "of every prediction row — zero application-level archiving code required."
)
